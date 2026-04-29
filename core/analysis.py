"""分析层核心（Phase A——纯规则，零外部依赖）。

对应 `docs/02-design/实现映射设计.md` 第六步"补分析层"与
`docs/01-requirements/MVP场景定义.md` 10.3 节"最终输出"。

**分层约束**：

- 本模块**主依赖** `models/*` + stdlib——`analyze_run` 及所有 Phase A 函数
  **不**依赖 `core/runtime.py` / `core/providers/*` / `core/events.py`
- 数据源是**磁盘上的 `runs/<run_id>/` 目录**——`events.jsonl` + `snapshots/tick_N.json`
  Runtime 跑完后任何时候都能再调用本模块做二次分析
- Phase C LLM 增强通过 `enhance_with_llm()` 函数实现——它**依赖** `core/providers/base`
  的 `LLMProvider` ABC + `core/errors.LLMProtocolError`。其余 Phase A 函数保持零 LLM 依赖
- 本模块除 `enhance_with_llm` 外**不**调用任何 LLM——所有 Phase A 分析都是确定性聚合统计

**对外 API**（五个公开函数）：

- `analyze_run(run_dir)`——读目录 → 返回 `AnalysisResult`（Phase A）
- `enhance_with_llm(result, provider, config)`——给 `AnalysisResult` 填 3 个 LLM 字段（Phase C）
- `render_markdown(result)`——`AnalysisResult` → markdown 字符串
- `render_json(result)`——`AnalysisResult` → pretty JSON 字符串
- `write_analysis(run_dir, result)`——把两份产物写到 `<run_dir>/analysis/`

**输出文件约定**（对齐 `StorageConfig` docstring）：

- `<run_dir>/analysis/final.md`——给人读的 markdown
- `<run_dir>/analysis/final.json`——给机器读 / UI 消费的结构化版本
- 两份内容来自同一 `AnalysisResult`，保证一致性

**turning_points 定义**（v1）：

- 对每对相邻快照 `snap_{t-1}`、`snap_t`，对每个实体的每个属性，若值发生变化，
  记作候选
- 按 `|delta|` 降序取前 K 条（默认 K=5）；非数值属性 `delta=None` 视为 0 排在末尾
- v1 **不**把 relation_changed / scheduled_event 纳入 turning_points——这些通过
  环境变量轨迹与事件分布已经可见
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from core.errors import LLMProtocolError
from core.providers.base import LLMProvider
from models.analysis_models import (
    ActorStat,
    AnalysisResult,
    AttributeChange,
    EntityComparison,
    EnvironmentChange,
    KindStat,
    TickValuePoint,
    TrajectorySummary,
    TurningPoint,
)
from models.config_models import RuntimeConfig
from models.runtime_models import EventRecord, Snapshot
from models.scenario_models import Scenario
from models.world_models import WorldDefinition


# =============================================================================
# I/O——从 run 目录加载事件与快照
# =============================================================================


def _load_events_from_file(path: Path) -> list[EventRecord]:
    """从 `events.jsonl` 流式解析并 Pydantic 校验。

    空行忽略；格式非法立即抛 ``ValueError``——不静默吃错，否则分析结果不可信。
    """
    if not path.exists():
        raise FileNotFoundError(f"events.jsonl 不存在：{path}")
    records: list[EventRecord] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                records.append(EventRecord.model_validate_json(line))
            except Exception as exc:  # noqa: BLE001 Pydantic ValidationError 保底
                raise ValueError(
                    f"{path}:{line_no} EventRecord 校验失败：{exc}"
                ) from exc
    return records


def _load_snapshots_from_dir(path: Path) -> dict[int, Snapshot]:
    """从 `snapshots/` 目录读取所有 `tick_*.json` 文件。

    - 目录缺失：抛 `FileNotFoundError`
    - 目录空：返回空 dict（合法场景，例如 snapshot_mode=never）
    - 文件名必须是 `tick_<int>.json`——不匹配的文件忽略（兼容未来扩展）
    """
    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(f"snapshots 目录不存在：{path}")
    snapshots: dict[int, Snapshot] = {}
    for file in sorted(path.glob("tick_*.json")):
        try:
            snap = Snapshot.model_validate_json(
                file.read_text(encoding="utf-8")
            )
        except Exception as exc:  # noqa: BLE001
            raise ValueError(
                f"{file} Snapshot 校验失败：{exc}"
            ) from exc
        snapshots[snap.tick] = snap
    return snapshots


# =============================================================================
# 聚合子步骤（都是纯函数，可独立测试）
# =============================================================================


def _summarize_events(events: list[EventRecord]) -> TrajectorySummary:
    """按 kind / actor 聚合事件计数，找暂停点与命中断点。

    - `total_ticks = max(ev.tick)`——即"实际推进到的最后一 tick"；无事件时为 0
    - `events_by_actor` 只计入 `action_executed` / `decision_rejected`——
      其他 kind 的 actor_id 含噪音大（如 `scheduled_event_triggered`.actor_id=None）
    """
    kind_counter: Counter[str] = Counter(ev.kind for ev in events)
    action_counter: Counter[str] = Counter(
        ev.actor_id
        for ev in events
        if ev.kind == "action_executed" and ev.actor_id is not None
    )
    rejected_counter: Counter[str] = Counter(
        ev.actor_id
        for ev in events
        if ev.kind == "decision_rejected" and ev.actor_id is not None
    )
    breakpoints_triggered = [
        str(ev.payload.get("breakpoint_id", ""))
        for ev in events
        if ev.kind == "breakpoint_triggered"
    ]
    paused_ticks = sorted(
        {ev.tick for ev in events if ev.kind == "breakpoint_triggered"}
    )
    total_ticks = max((ev.tick for ev in events), default=0)

    by_kind = [
        KindStat(kind=k, count=c) for k, c in sorted(kind_counter.items())
    ]
    actor_ids = set(action_counter) | set(rejected_counter)
    by_actor = [
        ActorStat(
            actor_id=aid,
            action_count=action_counter.get(aid, 0),
            decision_rejected_count=rejected_counter.get(aid, 0),
        )
        for aid in sorted(actor_ids)
    ]

    return TrajectorySummary(
        total_ticks=total_ticks,
        total_events=len(events),
        events_by_kind=by_kind,
        events_by_actor=by_actor,
        paused_ticks=paused_ticks,
        breakpoints_triggered=breakpoints_triggered,
    )


def _is_numeric(value: Any) -> bool:
    """与 `core/runtime.py._is_numeric` 语义一致：int/float 算数值，bool 不算。

    .. note::
        本函数与 ``core/runtime.py:_is_numeric`` 是**有意保留**的双份实现。
        本模块顶层 docstring 明确"零 runtime 依赖"——不能 ``from core.runtime
        import _is_numeric``。项目也不开 ``utils/`` 共享层（AGENTS.md 4.3）。
        于是接受双存。修改本函数时请同步修改 ``core/runtime.py:_is_numeric``。
    """
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _find_turning_points(
    snapshots: dict[int, Snapshot], *, top_k: int = 5
) -> list[TurningPoint]:
    """扫相邻快照差异，按 |delta| 降序取前 `top_k` 条。"""
    if len(snapshots) < 2:
        return []
    sorted_ticks = sorted(snapshots)
    candidates: list[TurningPoint] = []
    for prev_t, curr_t in zip(sorted_ticks, sorted_ticks[1:]):
        prev_snap = snapshots[prev_t]
        curr_snap = snapshots[curr_t]
        for eid, curr_attrs in curr_snap.entity_state_summary.items():
            prev_attrs = prev_snap.entity_state_summary.get(eid, {})
            for attr, curr_val in curr_attrs.items():
                prev_val = prev_attrs.get(attr)
                if prev_val == curr_val:
                    continue
                delta: float | None = None
                if _is_numeric(curr_val) and _is_numeric(prev_val):
                    delta = float(curr_val) - float(prev_val)
                candidates.append(
                    TurningPoint(
                        tick=curr_t,
                        actor_id=eid,
                        attribute=attr,
                        before=prev_val,
                        after=curr_val,
                        delta=delta,
                    )
                )
    candidates.sort(
        key=lambda tp: abs(tp.delta) if tp.delta is not None else 0.0,
        reverse=True,
    )
    return candidates[:top_k]


def _trace_environment(
    snapshots: dict[int, Snapshot],
) -> list[EnvironmentChange]:
    """追踪环境变量 tick 序列——只收录值变化过的 tick。"""
    if not snapshots:
        return []
    sorted_ticks = sorted(snapshots)
    per_var: dict[str, list[TickValuePoint]] = defaultdict(list)

    # 初始 tick：所有环境变量都记一条
    initial_env = snapshots[sorted_ticks[0]].environment_state
    for var, val in initial_env.items():
        per_var[var].append(TickValuePoint(tick=sorted_ticks[0], value=val))

    # 后续 tick：只记变化的变量
    for prev_t, curr_t in zip(sorted_ticks, sorted_ticks[1:]):
        prev_env = snapshots[prev_t].environment_state
        curr_env = snapshots[curr_t].environment_state
        for var in set(curr_env) | set(prev_env):
            if curr_env.get(var) != prev_env.get(var):
                per_var[var].append(
                    TickValuePoint(tick=curr_t, value=curr_env.get(var))
                )

    return [
        EnvironmentChange(variable=var, values=values)
        for var, values in sorted(per_var.items())
    ]


def _compare_entities(
    snapshots: dict[int, Snapshot],
) -> list[EntityComparison]:
    """对比第一份与最后一份快照，列出每个实体的属性初值/终值/变化。"""
    if not snapshots:
        return []
    sorted_ticks = sorted(snapshots)
    first = snapshots[sorted_ticks[0]]
    last = snapshots[sorted_ticks[-1]]

    comparisons: list[EntityComparison] = []
    all_eids = set(first.entity_state_summary) | set(last.entity_state_summary)
    for eid in sorted(all_eids):
        initial = dict(first.entity_state_summary.get(eid, {}))
        final = dict(last.entity_state_summary.get(eid, {}))
        changes: list[AttributeChange] = []
        for attr in sorted(set(initial) | set(final)):
            before = initial.get(attr)
            after = final.get(attr)
            if before != after:
                changes.append(
                    AttributeChange(
                        attribute=attr, before=before, after=after
                    )
                )
        comparisons.append(
            EntityComparison(
                entity_id=eid,
                initial_attributes=initial,
                final_attributes=final,
                changes=changes,
            )
        )
    return comparisons


# =============================================================================
# 公开 API——聚合入口
# =============================================================================


def analyze_run(run_dir: Path) -> AnalysisResult:
    """读 `<run_dir>/events.jsonl` + `<run_dir>/snapshots/`，返回分析结果。

    Args:
        run_dir: 某次 run 的目录；必须存在且至少含 `events.jsonl`

    Raises:
        FileNotFoundError: run_dir 或其必需子项不存在
        ValueError: events.jsonl 或 snapshot 文件格式非法

    Note:
        `run_id` 取自 `run_dir.name`——依赖 Runtime 的 `generate_run_id` 约定。
        若目录被人工重命名过，`run_id` 字段会反映新名字（视为 feature，不是 bug）。
    """
    events_file = run_dir / "events.jsonl"
    snapshot_dir = run_dir / "snapshots"

    events = _load_events_from_file(events_file)
    # snapshots 允许空目录（snapshot_mode=never 时合法）
    snapshots = (
        _load_snapshots_from_dir(snapshot_dir)
        if snapshot_dir.exists()
        else {}
    )

    summary = _summarize_events(events)
    turning_points = _find_turning_points(snapshots)
    entity_comparisons = _compare_entities(snapshots)
    environment_trajectory = _trace_environment(snapshots)

    return AnalysisResult(
        version="0.1",
        run_id=run_dir.name,
        summary=summary,
        turning_points=turning_points,
        entity_comparisons=entity_comparisons,
        environment_trajectory=environment_trajectory,
    )


# =============================================================================
# Phase C——LLM 增强（prompt 构造 / 响应解析 / 公开 API）
# =============================================================================
#
# 与 `core/llm_policy.py` 的分工：
# - llm_policy 是**决策协议层**——每 entity 每 tick 一次，返回一个动作
# - 本节是**分析增强层**——整个 run 结束后一次，为 AnalysisResult 填三个叙事字段
# 两层都遵守同一个规约：prompt 后追加自然语言指令注入 output_language


# 分析增强的 system/user prompt 以 JSON-first 风格：把 World Definition / Scenario /
# Phase A 的确定性聚合结果一起作为 payload，附带严格 JSON 输出约定 + 证据要求。
# 与决策协议风格对齐（JSON in, JSON out）。
_ANALYSIS_SYSTEM_PROMPT = (
    "You are a simulation trajectory analyst. You will be given: "
    "(a) a World Definition describing entity types, attributes, action types, "
    "relation types; "
    "(b) a Scenario describing initial entities, initial relations, "
    "scheduled events, and the simulation goal; "
    "(c) a structured JSON analysis of the completed run (turning points, "
    "entity comparisons, environment trajectory). "
    "Your job is to write a reader-friendly report containing four parts: "
    "world_overview (explain the initial world in plain language: what entities "
    "exist, what their roles mean, what the relations mean, what the scenario "
    "goal is), narrative_summary (the trajectory in plain language), "
    "situation_judgement (final situation + advantages + risks), and "
    "next_action_suggestions (concrete actionable suggestions). "
    "CRITICAL: situation_judgement and each next_action_suggestions item "
    "MUST cite concrete evidence by referencing specific tick numbers, "
    "attribute changes, or entity ids drawn from the analysis JSON "
    "(for example: 'at tick <N>, <actor_id>.<attribute> changed from <X> to <Y>'). "
    "Your response MUST be a valid JSON object with EXACTLY four keys: "
    '{"world_overview", "narrative_summary", "situation_judgement", '
    '"next_action_suggestions"}. '
    "Do NOT include any prose, markdown, or explanation outside the JSON object."
)
"""Phase C 分析增强专用 system prompt。

与决策层 system prompt（`OpenAIProvider._DEFAULT_SYSTEM_PROMPT`）的角色定位
不同——决策层定位 "decision-making agent"，要求返回 ``{action, params, reason}``；
本常量定位 "trajectory analyst"，要求返回 ``{world_overview, narrative_summary,
situation_judgement, next_action_suggestions}``——四字段结构（v0.1.1 收官后扩展，
新增 world_overview 段以解释初始世界、降低读者理解门槛）。``enhance_with_llm``
通过 ``provider.generate(..., system_prompt=_ANALYSIS_SYSTEM_PROMPT)`` 覆盖默认值，
避免与决策层 system prompt 角色冲突。

证据要求：``situation_judgement`` 与 ``next_action_suggestions`` 每条必须引用
具体 tick / 属性变化 / 实体 id 作为支撑——避免 LLM 给出"凭空判断"。

约束：必须含 ``"JSON"`` 关键词——OpenAI ``response_format={"type":"json_object"}``
模式要求 prompt 中至少出现一次 "json"，否则 API 拒绝请求。
"""

_ANALYSIS_PROMPT_HEADER = (
    "You are a simulation trajectory analyst. Three JSON sections follow:\n"
    "1. World Definition (entity types / attributes / actions / relations)\n"
    "2. Scenario (initial entities, initial relations, scheduled events, goal)\n"
    "3. Phase A analysis result (trajectory summary, turning points, "
    "entity comparisons, environment trajectory)\n\n"
    "Read all three carefully before writing your output.\n\n"
)

_ANALYSIS_PROMPT_INSTRUCTIONS = (
    "\n\nRespond with ONLY a single JSON object (no markdown code fences, "
    "no surrounding prose) containing exactly these four keys:\n"
    "- \"world_overview\": string, 3-6 sentences explaining the initial world. "
    "Cover: what entities exist (id + type + role), what their key initial "
    "attributes mean, what the initial relations mean, and what the scenario "
    "goal is. Write for a reader unfamiliar with the YAML config.\n"
    "- \"narrative_summary\": string, 2-4 sentences describing the overall "
    "trajectory. Reference key turning points by tick.\n"
    "- \"situation_judgement\": string, 2-3 sentences on the final situation, "
    "which entity has the advantage, and key risks. MUST cite at least one "
    "concrete evidence (tick + attribute change, or entity comparison row).\n"
    "- \"next_action_suggestions\": array of 2-5 concrete, actionable "
    "suggestion strings for a human operator. EACH suggestion MUST embed "
    "supporting evidence (e.g. 'because regulator_main.strictness rose to 80 "
    "at tick 4, consider...')."
)


def _build_analysis_prompt(
    result: AnalysisResult,
    world: WorldDefinition,
    scenario: Scenario,
    *,
    language: str = "zh-CN",
) -> str:
    """为 `enhance_with_llm` 构造 LLM prompt。

    Prompt 由三段 JSON 拼成：

    1. **World Definition**——实体类型 / 属性 schema / 动作类型 / 关系类型
    2. **Scenario**——初始实体（含初始属性）/ 初始关系 / scheduled events / 目标
    3. **Phase A AnalysisResult**——结构化轨迹（已剔除四个增强字段，避免"让
       LLM 看自己的旧答案"）

    LLM 据此输出 four-key JSON：``world_overview / narrative_summary /
    situation_judgement / next_action_suggestions``。

    语言注入机制与 `core/llm_policy.build_prompt_context.render` 对齐：prompt
    尾部追加 "All natural-language fields must be in {language}"。**不**影响
    JSON 结构字段名。
    """
    # 1. World Definition——只送 LLM 真正用得上的字段（节省 token）
    world_payload = world.model_dump()
    world_json = json.dumps(world_payload, ensure_ascii=False, indent=2)

    # 2. Scenario——同样全量 dump（含初始关系 / scheduled / goal 等关键背景）
    scenario_payload = scenario.model_dump()
    scenario_json = json.dumps(scenario_payload, ensure_ascii=False, indent=2)

    # 3. Phase A 结果——剔除四个增强字段
    result_payload = result.model_dump(
        exclude={
            "world_overview",
            "narrative_summary",
            "situation_judgement",
            "next_action_suggestions",
        }
    )
    result_json = json.dumps(result_payload, ensure_ascii=False, indent=2)

    language_instruction = (
        f"\n\nAll natural-language fields in your JSON output "
        f"(world_overview, narrative_summary, situation_judgement, and each "
        f"string in next_action_suggestions) MUST be written in {language}. "
        f"JSON keys remain in English."
    )
    return (
        _ANALYSIS_PROMPT_HEADER
        + "World Definition (JSON):\n"
        + world_json
        + "\n\nScenario (JSON):\n"
        + scenario_json
        + "\n\nPhase A analysis result (JSON):\n"
        + result_json
        + _ANALYSIS_PROMPT_INSTRUCTIONS
        + language_instruction
    )


def _parse_analysis_response(raw: str) -> dict[str, Any]:
    """解析 LLM 原始文本，校验为合法的分析增强 dict。

    协议约定：

    - 顶层必须是 object；否则 `LLMProtocolError`
    - ``world_overview``：必填非空字符串（v0.1.1 收官后新增）
    - ``narrative_summary``：必填非空字符串
    - ``situation_judgement``：必填非空字符串
    - ``next_action_suggestions``：必填 list[str]，长度 ≥ 1，每项非空字符串
    - 其他 key 容忍（忽略）——LLM 偶尔会额外加解释字段，不作为错误

    Returns:
        ``{"world_overview": str, "narrative_summary": str,
        "situation_judgement": str, "next_action_suggestions": list[str]}``

    Raises:
        LLMProtocolError: 解析或校验失败
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMProtocolError(
            f"LLM 分析响应不是合法 JSON：{exc.msg}；原始文本前 200 字符："
            f"{raw[:200]!r}"
        ) from exc
    except TypeError as exc:
        raise LLMProtocolError(
            f"LLM 分析响应类型非法（预期 str）：{type(raw).__name__}"
        ) from exc

    if not isinstance(data, dict):
        raise LLMProtocolError(
            f"LLM 分析响应顶层必须是 object，实际为 {type(data).__name__}"
        )

    overview = data.get("world_overview")
    if not isinstance(overview, str) or not overview.strip():
        raise LLMProtocolError(
            "LLM 分析响应缺失 world_overview 或值非空字符串"
        )

    narrative = data.get("narrative_summary")
    if not isinstance(narrative, str) or not narrative.strip():
        raise LLMProtocolError(
            "LLM 分析响应缺失 narrative_summary 或值非空字符串"
        )

    judgement = data.get("situation_judgement")
    if not isinstance(judgement, str) or not judgement.strip():
        raise LLMProtocolError(
            "LLM 分析响应缺失 situation_judgement 或值非空字符串"
        )

    suggestions = data.get("next_action_suggestions")
    if not isinstance(suggestions, list) or not suggestions:
        raise LLMProtocolError(
            "LLM 分析响应的 next_action_suggestions 必须是非空数组"
        )
    for idx, item in enumerate(suggestions):
        if not isinstance(item, str) or not item.strip():
            raise LLMProtocolError(
                f"next_action_suggestions[{idx}] 必须是非空字符串，"
                f"实际为 {type(item).__name__}"
            )

    return {
        "world_overview": overview.strip(),
        "narrative_summary": narrative.strip(),
        "situation_judgement": judgement.strip(),
        "next_action_suggestions": [s.strip() for s in suggestions],
    }


def enhance_with_llm(
    result: AnalysisResult,
    provider: LLMProvider,
    config: RuntimeConfig,
    *,
    world: WorldDefinition,
    scenario: Scenario,
) -> AnalysisResult:
    """用 LLM 为 `AnalysisResult` 补齐四个叙事字段，返回**新对象**。

    这是 Phase C 的公开入口。典型调用点是 CLI 的 ``run`` 子命令在
    ``analyze_run`` + ``write_analysis`` 之后、仅当用户显式要求（``--llm-enhance``）
    时调用。

    **v0.1.1 收官扩展**：新增 ``world`` + ``scenario`` 关键字参数（必填），
    LLM 据此先解释初始世界（``world_overview``），并在 ``situation_judgement``
    与 ``next_action_suggestions`` 中援引具体证据（tick / 属性变化 / 实体）。

    Args:
        result: Phase A 已产出的 ``AnalysisResult``（可能已含增强字段——会被覆盖）
        provider: 任意 ``LLMProvider`` 实例（mock / openai / ...）
        config: 取 ``output_language`` + ``llm_request_timeout_sec`` 两项
        world: World Definition——LLM 据此解释实体/动作/关系类型含义
        scenario: Scenario——LLM 据此解释初始实体/初始关系/场景目标

    Returns:
        新的 ``AnalysisResult``——原前五个字段不变，后四个字段被填充

    Raises:
        ProviderError: 传输层失败（原样上抛，由调用方决定降级策略）
        LLMProtocolError: 协议层失败（响应非合法 JSON / 字段缺失或类型错）

    Note:
        本函数不做传输/协议重试——与 ``llm_policy.decide`` 对齐。若失败由上层
        （通常 CLI）捕获并决定"保留 Phase A 报告 + 打 warning"或其他降级。

        ``system_prompt`` 显式传给 provider——避免与决策层 system prompt
        角色冲突（详见 ``_ANALYSIS_SYSTEM_PROMPT`` docstring）。识别此 kwarg
        的 provider（OpenAIProvider）会用本常量替换构造期默认值；
        不识别的 provider（MockProvider）按 ABC 约定静默忽略。
    """
    prompt = _build_analysis_prompt(
        result, world, scenario, language=config.output_language
    )

    # max_tokens 比决策层 (512) 大——四段叙事（含 world_overview）+ 5 条建议的
    # 合理上限。v0.1.1 收官升 1500 → 2000 容纳新增的 world_overview 段
    raw = provider.generate(
        prompt,
        temperature=0.5,
        max_tokens=2000,
        timeout=config.llm_request_timeout_sec,
        system_prompt=_ANALYSIS_SYSTEM_PROMPT,
    )

    parsed = _parse_analysis_response(raw)

    # 用 model_copy(update=...) 返新对象——Pydantic v2 惯用法，保持不可变性
    return result.model_copy(
        update={
            "world_overview": parsed["world_overview"],
            "narrative_summary": parsed["narrative_summary"],
            "situation_judgement": parsed["situation_judgement"],
            "next_action_suggestions": parsed["next_action_suggestions"],
        }
    )


# =============================================================================
# 渲染——Markdown / JSON
# =============================================================================


def _format_any(value: Any) -> str:
    """把任意 JSON 兼容值格式化成 markdown 表格单元格。

    - `None` → `—`（U+2014，可视化缺失）
    - 数值 → 去尾随 0（`100.0` → `100`，`80.5` → `80.5`）
    - 其余 → `str(value)`
    """
    if value is None:
        return "—"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:g}"
    return str(value)


def _format_delta(delta: float | None) -> str:
    if delta is None:
        return "—"
    if delta == 0:
        return "0"
    sign = "+" if delta > 0 else ""
    return f"{sign}{delta:g}"


def render_markdown(result: AnalysisResult) -> str:
    """把 `AnalysisResult` 渲染成 markdown 字符串。

    **章节顺序**（v0.1.1 收官重排）：

    1. 元信息（run_id / schema 版本 / tick 数 / 事件数）
    2. **LLM 增强段（可选）**——放在最前为读者建立背景：
       - 世界概览（解释初始世界、实体角色、关系含义、场景目标）
       - 全过程叙事（自然语言描述轨迹）
       - 局势判断（含援引证据）
       - 面向用户的建议（每条含援引证据）
    3. **Phase A 确定性数据段**（始终渲染，作为 LLM 段的支撑）：
       - 全轨迹总结
       - 关键转折点
       - 各实体最终状态比较
       - 环境变量轨迹

    Phase C 的 LLM 增强字段（`world_overview` / `narrative_summary` /
    `situation_judgement` / `next_action_suggestions`）若为 None 则对应 section
    省略；纯 Phase A 模式（无 LLM 增强）只渲染元信息 + Phase A 四段。

    **去章节编号**：标题不再前缀 "一、二、..."——LLM 段是否存在会影响后段编号
    位置，去编号后语义清晰且不与测试的子串断言耦合。
    """
    lines: list[str] = []
    lines.append("# 仿真分析报告")
    lines.append("")
    lines.append(f"- **run_id**：`{result.run_id}`")
    lines.append(f"- **schema 版本**：{result.version}")
    lines.append(f"- **总 tick**：{result.summary.total_ticks}")
    lines.append(f"- **总事件数**：{result.summary.total_events}")
    lines.append("")

    # ============================================================
    # LLM 增强段（可选）——放在最前为读者建立背景
    # ============================================================

    # ---- 世界概览（LLM 增强，可选）
    if result.world_overview is not None:
        lines.append("## 世界概览")
        lines.append("")
        lines.append(result.world_overview)
        lines.append("")

    # ---- 全过程叙事（LLM 增强，可选）
    if result.narrative_summary is not None:
        lines.append("## 全过程叙事（自然语言总览）")
        lines.append("")
        lines.append(result.narrative_summary)
        lines.append("")

    # ---- 局势判断（LLM 增强，可选）
    if result.situation_judgement is not None:
        lines.append("## 局势判断")
        lines.append("")
        lines.append(result.situation_judgement)
        lines.append("")

    # ---- 面向用户的建议（LLM 增强，可选）
    if result.next_action_suggestions:
        lines.append("## 面向用户的建议")
        lines.append("")
        for sug in result.next_action_suggestions:
            lines.append(f"- {sug}")
        lines.append("")

    # ============================================================
    # Phase A 确定性数据段（始终渲染——LLM 段的"原始证据"）
    # ============================================================

    # ---- 全轨迹总结
    lines.append("## 全轨迹总结")
    lines.append("")
    if result.summary.events_by_kind:
        lines.append("### 事件分布（按类型）")
        lines.append("")
        lines.append("| kind | 数量 |")
        lines.append("|---|---|")
        for stat in result.summary.events_by_kind:
            lines.append(f"| `{stat.kind}` | {stat.count} |")
        lines.append("")
    if result.summary.events_by_actor:
        lines.append("### 行为分布（按实体）")
        lines.append("")
        lines.append("| 实体 | 执行动作数 | 被拒决策数 |")
        lines.append("|---|---|---|")
        for stat in result.summary.events_by_actor:
            lines.append(
                f"| `{stat.actor_id}` | {stat.action_count} "
                f"| {stat.decision_rejected_count} |"
            )
        lines.append("")
    if result.summary.paused_ticks:
        lines.append("### 暂停与断点")
        lines.append("")
        lines.append(
            f"- 触发 breakpoint 的 tick：{result.summary.paused_ticks}"
        )
        lines.append(
            f"- 命中的 breakpoint id：{result.summary.breakpoints_triggered}"
        )
        lines.append("")

    # ---- 关键转折点
    lines.append("## 关键转折点（按 |delta| 降序）")
    lines.append("")
    if not result.turning_points:
        lines.append("_无显著属性变化——实体整个仿真保持稳定_")
        lines.append("")
    else:
        lines.append("| tick | 实体 | 属性 | 前值 | 后值 | delta |")
        lines.append("|---|---|---|---|---|---|")
        for tp in result.turning_points:
            lines.append(
                f"| {tp.tick} | `{tp.actor_id}` | `{tp.attribute}` "
                f"| {_format_any(tp.before)} | {_format_any(tp.after)} "
                f"| {_format_delta(tp.delta)} |"
            )
        lines.append("")

    # ---- 各实体最终状态比较
    lines.append("## 各实体最终状态比较")
    lines.append("")
    if not result.entity_comparisons:
        lines.append("_未发现任何实体快照_")
        lines.append("")
    else:
        for comp in result.entity_comparisons:
            lines.append(f"### `{comp.entity_id}`")
            lines.append("")
            if not comp.changes:
                lines.append("_无属性变化_")
                lines.append("")
                continue
            lines.append("| 属性 | 初值 | 终值 |")
            lines.append("|---|---|---|")
            for ch in comp.changes:
                lines.append(
                    f"| `{ch.attribute}` | {_format_any(ch.before)} "
                    f"| {_format_any(ch.after)} |"
                )
            lines.append("")

    # ---- 环境变量轨迹
    lines.append("## 环境变量轨迹")
    lines.append("")
    if not result.environment_trajectory:
        lines.append("_无环境变量_")
        lines.append("")
    else:
        for env in result.environment_trajectory:
            lines.append(f"### `{env.variable}`")
            lines.append("")
            lines.append("| tick | value |")
            lines.append("|---|---|")
            for point in env.values:
                lines.append(
                    f"| {point.tick} | {_format_any(point.value)} |"
                )
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_json(result: AnalysisResult) -> str:
    """把 `AnalysisResult` 渲染成 pretty JSON 字符串。

    走 Pydantic 的 `model_dump_json(indent=2)`；确保 JSON schema 与
    `models/analysis_models.py` 完全对齐（UI 消费方读这份文件即可）。
    """
    return result.model_dump_json(indent=2)


def write_analysis(run_dir: Path, result: AnalysisResult) -> tuple[Path, Path]:
    """把分析结果写到 `<run_dir>/analysis/final.{md,json}`。

    目录不存在时自动创建。覆盖同名文件（分析是"run 结束后一次性产物"，
    无 append-only 语义）。

    Returns:
        `(final_md_path, final_json_path)` 两份产物的绝对路径
    """
    analysis_dir = run_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    md_path = analysis_dir / "final.md"
    json_path = analysis_dir / "final.json"
    md_path.write_text(render_markdown(result), encoding="utf-8")
    json_path.write_text(render_json(result), encoding="utf-8")
    return md_path, json_path
