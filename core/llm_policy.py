"""LLM 决策协议层（第 3 步 / Phase B）。

对应 `docs/02-design/LLM决策协议设计.md` 第四、五、七节。

**职责边界**（与相邻层的分工）：

- `core/providers/*`——**传输层**：只把 prompt 发出去、把原始文本拿回来；失败抛
  `ProviderError`
- `core/llm_policy`（本文件）——**协议层**：prompt 构造、JSON 输出校验、动作白
  名单校验、失败抛 `LLMProtocolError`；后续 Phase B.3 会在此加指数退避重试
- `core/runtime`——**编排层**：调 `llm_policy.decide` 拿到 `ActionProposal`，
  捕获 `ProviderError` / `LLMProtocolError` 后走 fallback；本层**不**知道 fallback
  是什么——那是 World 的 `defaults.fallback_action` 配置

**为什么把协议层独立出来**（session 19 Phase B.1 重构理由）：

1. Runtime 原本的 `_decide_via_llm` 把 prompt 构造 / 解析 / 校验 / fallback 混在
   一起，任何一处改动都要动 Runtime——违反单一职责
2. 未来接真实 LLM 后要加**协议级重试**（session 19 Phase B.3），重试循环不应
   写在 Runtime 里——Runtime 的 tick 主循环应该对 LLM 是否重试无感
3. Phase C LLM 增强分析（`core/analysis.enhance_with_llm`）也会调 provider——
   两者共享 `LLMProvider` ABC 与 `LLMProtocolError` 契约，各自维护自己的
   prompt / parse 逻辑（语义不同，不强行共享 prompt 模板）

**v1 不做**：

- 协议级重试（留给 Phase B.3）——本版 `decide` 调一次、失败即抛
- 结构化输出（OpenAI ``response_format=Pydantic``）——`generate` 返回 `str`
  是 `LLMProvider` ABC 的契约，本层用 ``json.loads`` 解析；未来可扩 ABC 再加
- 上下文压缩 / 记忆流（Stanford generative-agents 的 memory stream）——那是
  Phase C++ 的内容
"""

from __future__ import annotations

import json
import logging
from typing import Any

from core.errors import LLMProtocolError, ProviderError
from core.events import EventLog
from core.providers.base import LLMProvider
from models.config_models import RuntimeConfig
from models.llm_models import LLMDecisionResult, PromptContext
from models.runtime_models import ActionProposal, WorldState
from models.scenario_models import Scenario
from models.world_models import WorldDefinition

logger = logging.getLogger(__name__)


# =============================================================================
# Prompt 构造
# =============================================================================


def build_prompt(
    world: WorldDefinition,
    scenario: Scenario,
    state: WorldState,
    entity_id: str,
    tick: int,
    *,
    language: str = "zh-CN",
    event_log: EventLog | None = None,
    history_size: int = 0,
    rules: Any | None = None,
) -> str:
    """把 Runtime 当前上下文打成 LLM 可消费的 prompt 文本。

    **D-016 重构**（v0.1.1）：本函数现在是 :func:`build_prompt_context` +
    :meth:`PromptContext.render` 的薄壳。**输出与 D-014 时代字节级等价**——
    当 ``event_log=None`` / ``history_size=0`` / ``rules=None`` 且 actor 不
    涉及关系时成立（详见 `models/llm_models.PromptContext.render` docstring）。

    向后兼容意义：旧调用方（不传 ``event_log`` / ``history_size`` / ``rules``）
    行为完全不变。

    Args:
        world / scenario / state / entity_id / tick: Runtime 当前上下文
        language: 自然语言字段的填写语种（session 19 多语言机制；附在 prompt 尾部）
        event_log: D-016 第 4 步——若提供且 ``history_size > 0``，从中抽 actor
            最近 N 条 ``decision_proposed`` 事件注入 ``actor_view.recent_decisions``
        history_size: 注入多少条历史决策。``0`` 完全关闭（默认）；
            ``RuntimeConfig.prompt_history_size`` 是其在 Runtime 编排层的来源
        rules: D-016 第 5 步——若提供，构造 ctx 后调 ``rules.enrich_prompt``
            注入场景特化段。类型用 ``Any`` 以避免循环导入（实际为
            :class:`rules.base.BaseRules`）

    Raises:
        KeyError: ``entity_id`` 未注册或实体类型未在 world 中声明（这些本应由
            Scenario loader 预检，到本层仍出错表示 Runtime 状态不一致）
    """
    ctx = build_prompt_context(
        world,
        scenario,
        state,
        entity_id,
        tick,
        language=language,
        event_log=event_log,
        history_size=history_size,
        rules=rules,
    )
    return ctx.render()


def build_prompt_context(
    world: WorldDefinition,
    scenario: Scenario,
    state: WorldState,
    entity_id: str,
    tick: int,
    *,
    language: str = "zh-CN",
    event_log: EventLog | None = None,
    history_size: int = 0,
    rules: Any | None = None,
) -> PromptContext:
    """构造结构化 :class:`PromptContext`（D-016）。

    **当前 v0.1.1 阶段**（D-016 第 1-5 步全部落地）：

    - ``actor_view``：含 ``id`` / ``type`` / ``attributes``，以及（非空时）
      ``relations`` / ``recent_decisions`` 段
    - ``perception``：含 ``tick`` / ``remaining_ticks`` / ``inbox`` / ``environment``
    - ``available_actions``：D-014 完整 ParamSchema 渲染，None 字段过滤
    - ``system_role`` / ``custom_segments``：默认 None / {}；若 ``rules`` 提供，
      由 :meth:`BaseRules.enrich_prompt` 注入

    Args:
        event_log: 可选事件日志。提供且 ``history_size > 0`` 时，从中抽 actor
            最近 N 条 ``decision_proposed`` 事件注入 ``actor_view.recent_decisions``
        history_size: 历史决策注入条数（0 表示关闭——保持 D-014 时代行为）
        rules: D-016 第 5 步——可选规则模块，提供时构造完毕后调
            ``rules.enrich_prompt(ctx, ...)`` 让场景注入 system_role / custom_segments

    Raises:
        KeyError: ``entity_id`` 未注册或实体类型未在 world 中声明
    """
    entity = state.entities[entity_id]
    type_schema = world.entity_types[entity.type]
    inbox = state.mailboxes.get(entity_id, [])

    # available_actions（D-014 完整 ParamSchema，None 字段过滤）
    available_actions = _build_available_actions(world, type_schema)

    # actor_view（D-016 第 1-4 步累进）
    actor_view: dict[str, Any] = {
        "id": entity.id,
        "type": entity.type,
        "attributes": dict(entity.attributes),  # 浅拷贝防止外层 mutate
    }

    # D-016 第 3 步：补 actor 涉及的关系子集（outgoing/incoming）。
    # 空时省略字段——保 actor 不涉及关系的场景（如 minimal_market 的 company_a）
    # 仍输出与 D-014 时代字节级等价的 prompt，向后兼容承诺持续成立。
    relations_view = _extract_actor_relations(state, entity_id)
    if relations_view["outgoing"] or relations_view["incoming"]:
        actor_view["relations"] = relations_view

    # D-016 第 4 步：补 actor 最近 N 条决策。空时省略字段——保字节级等价。
    if event_log is not None and history_size > 0:
        recent_decisions = _extract_recent_decisions(
            event_log, entity_id, history_size
        )
        if recent_decisions:
            actor_view["recent_decisions"] = recent_decisions

    # perception（外部感知）
    perception: dict[str, Any] = {
        "tick": tick,
        "remaining_ticks": scenario.config.total_ticks - tick,
        "inbox": [
            {
                "message_type": m.message_type,
                "from": m.from_actor,
                "payload": dict(m.payload),
            }
            for m in inbox
        ],
        "environment": dict(state.environment),
    }

    ctx = PromptContext(
        actor_view=actor_view,
        perception=perception,
        available_actions=available_actions,
        language_hint=language,
        # system_role / custom_segments 留默认（None / {}）
        # 这两个段为空时 render 输出与 D-014 时代字节级等价
    )

    # D-016 第 5 步：rules.enrich_prompt 钩子注入场景特化段（可选）
    if rules is not None:
        ctx = rules.enrich_prompt(
            ctx, world, scenario, state, entity_id, tick
        )

    return ctx


def _extract_actor_relations(
    state: WorldState,
    entity_id: str,
) -> dict[str, list[dict[str, Any]]]:
    """从 state.relations 抽 actor 涉及的关系子集（D-016 第 3 步）。

    返回结构按 D-016 spec 第 2.1 节：

    ```
    {
        "outgoing": [{"type": str, "to": str, "value": float | None}, ...],
        "incoming": [{"type": str, "from": str, "value": float | None}, ...]
    }
    ```

    **关键设计**：

    - **只抽 actor 局部**——避免 LLM context 爆炸（spec 第六节决策）。前端
      可从 EventLog / 完整 WorldState 看全图，prompt 不含
    - ``outgoing`` 用 ``to`` 键、``incoming`` 用 ``from`` 键——明确语义方向，
      避免 LLM 误读"哪一头是我"

    Args:
        state: 当前世界状态
        entity_id: 主体实体 id

    Returns:
        含 outgoing 与 incoming 两个 list 的 dict（任一可能为空 list）
    """
    outgoing: list[dict[str, Any]] = []
    incoming: list[dict[str, Any]] = []
    for rel in state.relations:
        if rel.source == entity_id:
            outgoing.append(
                {"type": rel.type, "to": rel.target, "value": rel.value}
            )
        if rel.target == entity_id:
            incoming.append(
                {"type": rel.type, "from": rel.source, "value": rel.value}
            )
    return {"outgoing": outgoing, "incoming": incoming}


def _extract_recent_decisions(
    event_log: EventLog,
    entity_id: str,
    n: int,
) -> list[dict[str, Any]]:
    """从 EventLog 抽 actor 最近 N 条 ``decision_proposed`` 事件（D-016 第 4 步）。

    返回结构按 D-016 spec 第 2.1 节：

    ```
    [{"tick": int, "action": str, "params": dict, "reason": str | None}, ...]
    ```

    **关键设计**：

    - **按 tick 降序返回**——最新的在最前。前端时间线展示与 LLM 阅读直觉一致
    - **取最后 N 条**而非 N 个时刻：若同 tick 有多次决策（D-008 干预重决策），
      它们都计入 N 之内
    - ``reason`` 字段当前总为 None——D-016 第 6 步 EventLog 持久化 prompt_context
      后会从 payload 取 ``raw_reasoning_summary``（届时本 helper 会更新）

    Args:
        event_log: 仿真事件日志
        entity_id: 主体实体 id
        n: 取最近多少条；调用方应已确保 ``n > 0``

    Returns:
        最多 N 条决策记录的 list；不足 N 条时返回实际数；按 tick 降序
    """
    decisions = event_log.get_events(
        kind="decision_proposed", actor_id=entity_id
    )
    # 按 tick 降序——EventLog.get_events 返回 append 顺序（即 tick 升序），
    # 反转后取前 N 条即"最近 N 条按 tick 降序"
    decisions.reverse()
    recent = decisions[:n]
    return [
        {
            "tick": ev.tick,
            "action": ev.payload.get("action_type"),
            "params": dict(ev.payload.get("params", {})),
            "reason": ev.payload.get("reason"),
        }
        for ev in recent
    ]


def _build_available_actions(
    world: WorldDefinition,
    type_schema: Any,
) -> list[dict[str, Any]]:
    """组装 actor 当前 tick 允许采取的动作列表（含 D-014 完整 ParamSchema）。

    None 字段被过滤——LLM 看到 ``"description": null`` 会浪费 token 也容易被
    误解为"该字段无值"，去掉更干净。
    """
    available_actions: list[dict[str, Any]] = []
    for action_name in type_schema.actions:
        action_schema = world.action_types.get(action_name)
        if action_schema is None:
            # 跨引用已由 loader 校验过；到本层仍缺失表示编排层异常，静默跳过
            continue

        params_payload: dict[str, dict[str, Any]] = {}
        for p_name, p in action_schema.params.items():
            param_dict: dict[str, Any] = {"type": p.type, "required": p.required}
            if p.description is not None:
                param_dict["description"] = p.description
            if p.default is not None:
                param_dict["default"] = p.default
            if p.min is not None:
                param_dict["min"] = p.min
            if p.max is not None:
                param_dict["max"] = p.max
            if p.values is not None:
                param_dict["values"] = p.values
            if p.entity_type_filter is not None:
                param_dict["entity_type_filter"] = p.entity_type_filter
            params_payload[p_name] = param_dict

        action_entry: dict[str, Any] = {
            "name": action_name,
            "params": params_payload,
        }
        if action_schema.description is not None:
            action_entry["description"] = action_schema.description

        available_actions.append(action_entry)

    return available_actions


# =============================================================================
# 响应解析 + 校验
# =============================================================================


def parse_response(raw: str, allowed_actions: list[str]) -> dict[str, Any]:
    """解析 LLM 原始文本，校验为合法的 action dict。

    协议约定（`LLM决策协议设计.md` 第四节）的最小子集：

    - 顶层必须是 object；否则 `LLMProtocolError`
    - ``action`` 字段必须是字符串且在 ``allowed_actions`` 中；否则 `LLMProtocolError`
    - ``params`` 字段若存在必须是 object；非 object 时归 0（取空 dict）——
      这是"宽容式降级"：LLM 可能把 params 写成 null / list，但核心是 action
      合法，宽容允许继续
    - ``reason`` 字段可选，字符串或 None——用于 `raw_reasoning_summary`

    Returns:
        标准化后的 dict：``{"action": str, "params": dict, "reason": str | None}``

    Raises:
        LLMProtocolError: 解析或校验失败；原始文本附在 ``__cause__`` 或 msg 中
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMProtocolError(
            f"LLM 响应不是合法 JSON：{exc.msg}；原始文本前 200 字符："
            f"{raw[:200]!r}"
        ) from exc
    except TypeError as exc:
        # raw 非 str/bytes——provider 实现违约；按协议错误处理（走 fallback）
        raise LLMProtocolError(
            f"LLM 响应类型非法（预期 str）：{type(raw).__name__}"
        ) from exc

    if not isinstance(data, dict):
        raise LLMProtocolError(
            f"LLM 响应顶层必须是 object，实际为 {type(data).__name__}"
        )

    action = data.get("action")
    if not isinstance(action, str):
        raise LLMProtocolError(
            f"LLM 响应 action 字段缺失或非字符串，实际为 {type(action).__name__}"
        )
    if action not in allowed_actions:
        raise LLMProtocolError(
            f"LLM 选择了不在白名单内的 action='{action}'；"
            f"允许: {sorted(allowed_actions)}"
        )

    params = data.get("params")
    if not isinstance(params, dict):
        # 宽容降级：params 非 object 时归 0
        params = {}

    reason = data.get("reason")
    if reason is not None and not isinstance(reason, str):
        reason = None

    return {"action": action, "params": params, "reason": reason}


# =============================================================================
# 决策编排——Runtime 的单点入口
# =============================================================================


def decide(
    provider: LLMProvider,
    world: WorldDefinition,
    scenario: Scenario,
    state: WorldState,
    entity_id: str,
    tick: int,
    *,
    config: RuntimeConfig,
    event_log: EventLog | None = None,
    rules: Any | None = None,
) -> LLMDecisionResult:
    """调 provider → 解析 → 校验 → 返回 :class:`LLMDecisionResult`。

    **D-016 第 6 步签名变更**：返回类型从 ``ActionProposal`` 升为
    :class:`LLMDecisionResult`，封装 ``proposal`` 与本次决策的 ``prompt_context``——
    后者由 Runtime 序列化进 ``decision_proposed`` 事件 payload。
    旧调用方需改为 ``result = decide(...); proposal = result.proposal``。

    v1 单次调用；Phase B.3 会在此处加指数退避重试（`config.llm_request_timeout_sec`
    与 `LLMProviderConfig.max_retries` 联动）。

    **D-016 完整能力**：

    - 第 4 步——可选 ``event_log``：传入时启用历史决策注入
    - 第 5 步——可选 ``rules``：传入时启用 enrich_prompt 钩子注入场景特化段
    - 第 6 步——返回 LLMDecisionResult，让 Runtime 把 prompt_context 进 EventLog

    Args:
        event_log: D-016 第 4 步——可选事件日志；提供时启用历史决策注入
        rules: D-016 第 5 步——可选规则模块；提供时启用 enrich_prompt 钩子。
            类型用 ``Any`` 以避免循环导入（实际为 :class:`rules.base.BaseRules`）

    Returns:
        LLMDecisionResult: 含 ``proposal`` 与 ``prompt_context`` 两个字段

    Raises:
        ProviderError: 传输层失败（原样上抛给 Runtime）
        LLMProtocolError: 协议层失败——JSON 不合法 / action 不在白名单 / params 结构不合约

    Note:
        Fallback 不在本层做——那需要知道 ``world.defaults.fallback_action``，是 Runtime
        职责。本函数只负责"拿到一条合法的 LLM 提议"或"把失败原因抛上去"。
    """
    # 拆开 build_prompt 为 build_prompt_context + ctx.render() 两步——
    # 保持对 ctx 的引用以塞进 LLMDecisionResult
    ctx = build_prompt_context(
        world,
        scenario,
        state,
        entity_id,
        tick,
        language=config.output_language,
        event_log=event_log,
        history_size=config.prompt_history_size,
        rules=rules,
    )
    prompt = ctx.render()
    entity = state.entities[entity_id]
    type_schema = world.entity_types[entity.type]
    allowed_actions = list(type_schema.actions)

    # ProviderError / LLMProtocolError 都向上自然冒泡——Runtime 在 _decide_via_llm
    # 一并捕获后走 fallback；本层不再做空 try/except 重抛
    raw = provider.generate(
        prompt,
        temperature=0.7,
        max_tokens=512,
        timeout=config.llm_request_timeout_sec,
    )
    parsed = parse_response(raw, allowed_actions)

    proposal = ActionProposal(
        tick=tick,
        actor_id=entity_id,
        action_type=parsed["action"],
        params=parsed["params"],
        decision_mode="llm",
        raw_reasoning_summary=parsed["reason"],
        status="proposed",
    )
    return LLMDecisionResult(proposal=proposal, prompt_context=ctx)
