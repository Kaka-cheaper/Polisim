"""Runtime 主循环（D-008 + D-010 落地）。

对应 `docs/02-design/运行时与事件轨迹设计.md` 全文（重点：三节 single-tick 流程、
十三节步进式接口）与 `docs/02-design/实现映射设计.md` 4.4 节。

**分层约束**：

- 本模块是 Polisim 的**编排层**：读 `WorldDefinition` + `Scenario`，调用 `BaseRules`
  与 `LLMProvider`，写 `EventLog` 与 `WorldState`
- **不**包含业务规则（走 `rules/`）、**不**知道具体 LLM SDK（走 `core/providers/`）
- **不**做跨文件 schema 校验（那是 loaders 的事，到 Runtime 时已经校验过）

**step-based API**（D-008）：

- `step()` 执行单个 tick，返回 `TickResult`
- `run_until(tick)` 连续 step 直到目标 tick 或 total_ticks 或暂停
- `pause()` / `resume()` 切换暂停标志；暂停时 `step()` 抛 `RuntimeError`
- `get_state()` / `get_snapshot(tick)` / `current_tick()` 做状态查询
- `intervene(intervention)` 应用人工干预（三种 kind）

**v1 已知简化**（由 `pitfalls.md` 或 docstring 显式标注）：

- activation 未实现——v1 每 tick 激活所有实体；未来按 `EntityTypeSchema.activation` 过滤
- LLM 协议重试未实现——v1 一次调用，不合法即 fallback；step 5 再补
- 消息投递只支持 `broadcast` 与 `direct`（payload 带 `target_id`）；`by_relation` v1 跳过
- 激活 / 感知 / 上下文压缩均按"所有信息都给 LLM"的最粗粒度实现
"""

from __future__ import annotations

import logging
from pathlib import Path
from random import Random
from types import TracebackType
from typing import Any

from core import llm_policy
from core.errors import (
    InvalidStateError,
    LLMProtocolError,
    PausedError,
    ProviderError,
    RulesError,
    TerminatedError,
)
from core.events import EventLog, generate_run_id
from core.providers.base import LLMProvider
from core.rules_loader import load_rules_class
from core.semantic_validator import validate_semantics
from models.config_models import RuntimeConfig, StorageConfig
from models.runtime_models import (
    ActionProposal,
    AttributeEffect,
    ChainedActionEffect,
    Effect,
    EntityCreateEffect,
    EntityDestroyEffect,
    EntityRuntimeState,
    EnvironmentEffect,
    EventKind,
    EventRecord,
    Intervention,
    MessageEffect,
    MessageEnvelope,
    MessageSummary,
    RelationEffect,
    RelationRuntimeState,
    Snapshot,
    TickResult,
    WorldState,
)
from models.llm_models import PromptContext
from models.scenario_models import Scenario
from models.world_models import ActionParamSchema, WorldDefinition
from rules.base import BaseRules

logger = logging.getLogger(__name__)


def _is_numeric(value: Any) -> bool:
    """判定值是否为 numeric（int / float，明确排除 bool）。

    Python 的 ``bool`` 是 ``int`` 的子类，赤裸 ``isinstance(x, (int, float))``
    会把 ``True`` 判为 number——这与 Effect / Environment 值的语义不符
    （数值型属性/环境不应包含 bool）。本工具函数集中处理此陷阱，
    供 Runtime 多处统一复用。

    .. note::
        ``core/analysis.py`` 中有一份语义完全一致的 `_is_numeric` 实现。
        两份双存是**分层纪律**的后果：``analysis`` 遵守「零 runtime 依赖」
        （见 `core/analysis` 顶层 docstring），不能 `from core.runtime import _is_numeric`。
        项目也不开 `utils/` 垃圾桶目录（AGENTS.md 4.3）——于是接受双存。
        修改本函数时请同步修改 ``core/analysis.py:_is_numeric``，保语义一致。
    """
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class Runtime:
    """Polisim 仿真运行时（D-008 步进式 API）。

    **构造参数**（位置参数 3 个 + keyword-only）：

    - ``world``：已加载的 `WorldDefinition`
    - ``scenario``：已加载的 `Scenario`（可能含 ``rules_module`` 字段）
    - ``provider``：`LLMProvider` 实例，用于 ``decision_mode=llm`` 实体
    - 关键字参数：
      - ``rules``：`BaseRules` 实例；为 None 时从 ``scenario.rules_module`` 经
        `core.rules_loader.load_rules_class` 解析并实例化（D-010）
      - ``runtime_config`` / ``storage_config``：系统级配置；None 时用各自默认
      - ``run_id``：run 标识；None 时由 `generate_run_id` 自动生成

    **典型用法**：

    .. code-block:: python

        with Runtime(world, scenario, provider=mock) as rt:
            while rt.current_tick() < scenario.config.total_ticks:
                result = rt.step()
                if result.paused_after:
                    # 交给 UI / CLI 处理暂停
                    break
    """

    # ------------------------------------------------------------------
    # 构造 / 资源管理
    # ------------------------------------------------------------------

    def __init__(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        provider: LLMProvider,
        *,
        rules: BaseRules | None = None,
        runtime_config: RuntimeConfig | None = None,
        storage_config: StorageConfig | None = None,
        run_id: str | None = None,
    ) -> None:
        self._world = world
        self._scenario = scenario
        self._provider = provider
        self._runtime_config = runtime_config or RuntimeConfig(version="0.1")
        self._storage_config = storage_config or StorageConfig(version="0.1")

        # Rules 装配（D-010）：优先使用显式传入的实例；否则走 rules_module
        self._rules = self._resolve_rules(rules)

        # 跨层语义校验（D-013）——loader 看不到 rules 实例的部分在此完成。
        # 失败时抛 SemanticValidationError（属 SimEngineError），CLI 顶层兜住。
        # 必须在 EventLog 构造前——避免失败时落下空 run 目录。
        validate_semantics(world, scenario, self._rules)

        # 随机数生成器：与 BaseRules 共享 seed 来源（D-008 副作用——seed 单源）
        self._rng = Random(self._runtime_config.random_seed)

        # run_id：显式优先，否则自动生成（D-007）
        self._run_id = run_id or generate_run_id(
            world.world.id, scenario.scenario.id
        )

        # EventLog——所有事件 / 快照的唯一写入口（D-006 / D-007）
        self._event_log = EventLog(self._run_id, self._storage_config)

        # 运行时可变状态
        self._state: WorldState = self._bootstrap_world_state()
        self._outbox: list[MessageEnvelope] = []
        self._forced_actions: dict[str, dict[str, Any]] = {}
        self._paused: bool = False
        self._event_counter: int = 0

        # D-016 第 6 步：临时 PromptContext 容器
        # 由 _decide_via_llm 在调 llm_policy.decide 后写入；
        # 主循环写 decision_proposed 事件时从此 dict 弹出并塞入 payload。
        # 仅 LLM 决策路径会写入；rule / random / fallback 模式跳过。
        self._last_llm_prompt_context: dict[str, PromptContext] = {}

        # D-015 全量版（session 28）：跨 tick 延后的 chained_action 队列
        # 每项 (target_tick, ChainedActionEffect)；step 主循环步 2.5 在 next_tick
        # 等于 target_tick 时取出 fire（depth 重置为 0——跨 tick 链不计入同
        # tick 链深度）。延后链与 scenario.scheduled_events 概念上相似，但语义
        # 不同：scheduled_events 是场景静态配置，延后链是规则在运行期动态产生。
        self._delayed_chained_actions: list[tuple[int, ChainedActionEffect]] = []

        # 初始 tick=0 快照（供未来"从头回放"使用）
        self._event_log.save_snapshot(self._make_snapshot(tick=0))

    def _resolve_rules(self, rules_arg: BaseRules | None) -> BaseRules:
        """按 D-010 决策解析规则实例。

        优先级：
        1. 显式传入的 ``rules`` 参数（测试 / CLI 自定义场景）
        2. `scenario.rules_module` 字段 + 动态导入（常规生产路径）
        3. 两者都没有 → 报错（Runtime 不能无规则运行）
        """
        if rules_arg is not None:
            return rules_arg
        if self._scenario.rules_module is None:
            raise InvalidStateError(
                "Runtime 构造时必须提供 rules 实例，或在 scenario.yaml 中声明 "
                "rules_module 字段（D-010）"
            )
        rules_cls = load_rules_class(self._scenario.rules_module)
        # 用 runtime_config.random_seed 注入 RNG 保证复现（本函数始终在 __init__
        # 赋值之后调用，_runtime_config 已经就绪）
        return rules_cls(random_seed=self._runtime_config.random_seed)

    def _bootstrap_world_state(self) -> WorldState:
        """从 Scenario 构造初始 WorldState（tick=0）。

        - 实体属性 = world 默认值 ∪ scenario 覆盖值（后者胜出）
        - 环境变量 = world 默认值 ∪ scenario 覆盖值
        - 关系来自 scenario.relations
        - mailboxes 初始为空
        """
        entities: dict[str, EntityRuntimeState] = {}
        for inst in self._scenario.entities:
            type_schema = self._world.entity_types[inst.type]
            merged_attrs: dict[str, Any] = {
                name: attr.default for name, attr in type_schema.attributes.items()
            }
            merged_attrs.update(inst.attributes)
            entities[inst.id] = EntityRuntimeState(
                id=inst.id,
                type=inst.type,
                name=inst.name,
                attributes=merged_attrs,
            )

        env: dict[str, Any] = {}
        if self._world.environment is not None:
            env = {
                name: var.default
                for name, var in self._world.environment.variables.items()
            }
        env.update(self._scenario.environment)

        relations = [
            RelationRuntimeState(
                type=r.type, source=r.source, target=r.target, value=r.value
            )
            for r in self._scenario.relations
        ]

        return WorldState(
            tick=0,
            entities=entities,
            relations=relations,
            environment=env,
            mailboxes={},
        )

    def close(self) -> None:
        """关闭底层 EventLog 文件句柄。幂等。"""
        self._event_log.close()

    def __enter__(self) -> Runtime:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    # ------------------------------------------------------------------
    # 状态查询（D-008）
    # ------------------------------------------------------------------

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def run_dir(self) -> Path | None:
        """产物目录 `<runs_root>/<run_id>/`；内存模式（persist=False）为 None。

        供 CLI / 分析层在仿真结束后定位 events.jsonl + snapshots/；不透出
        `_event_log` 私有引用，保持封装。
        """
        return self._event_log.run_dir

    @property
    def world(self) -> WorldDefinition:
        """只读访问 World Definition（v0.2 server 接入需要）。

        RuntimeRegistry / RunService 等上层需要读取 ``world.id`` /
        ``world.entity_types`` 等元信息以构造响应模型。返回**同一引用**——
        调用方不应修改返回值（WorldDefinition 是 Pydantic 模型且场景生命周期内不变）。
        """
        return self._world

    @property
    def scenario(self) -> Scenario:
        """只读访问 Scenario（v0.2 server 接入需要）。

        与 ``world`` property 对称——上层需要 ``scenario.config.total_ticks`` /
        ``scenario.scenario.id`` / ``scenario.ui_layout`` 等。
        """
        return self._scenario

    @property
    def event_log(self) -> EventLog:
        """只读访问 EventLog（v0.2 server 事件查询需要）。

        RunService.query_events 需要调 ``event_log.get_events(...)`` 走过滤 + 分页。
        v1 CLI 通过读 ``run_dir/events.jsonl`` 文件实现；server 直接走内存 EventLog
        更高效。返回的引用调用方**不应** ``close()``——生命周期归 Runtime 管。
        """
        return self._event_log

    @property
    def runtime_config(self) -> RuntimeConfig:
        """只读访问 RuntimeConfig（v0.2 server / 分析层需要）。

        AnalysisService.enhance_with_llm 需要 ``runtime_config.output_language``
        与 ``runtime_config.llm_request_timeout_sec`` 等字段；RunService 构造
        RunDetail 响应时也需要把生效的 runtime_config 透传给前端。
        """
        return self._runtime_config

    @property
    def provider(self) -> LLMProvider:
        """只读访问 LLMProvider 实例（v0.2 server 分析增强需要）。

        AnalysisService.enhance_with_llm 复用 Runtime 自身的 provider 做 Phase C
        分析增强——保持同一 run 的语境一致（同 mock / openai key）。返回的引用
        调用方**不应**修改 provider 状态——它仍由 Runtime 持有 + 用于 LLM 决策。
        """
        return self._provider

    def current_tick(self) -> int:
        return self._state.tick

    def is_paused(self) -> bool:
        return self._paused

    def get_state(self) -> WorldState:
        """返回当前 WorldState 的**引用**——调用方修改会影响 Runtime 内部状态。

        需要独立副本时，使用 ``runtime.get_state().model_copy(deep=True)``。
        """
        return self._state

    def get_snapshot(self, tick: int) -> Snapshot | None:
        return self._event_log.get_snapshot(tick)

    # ------------------------------------------------------------------
    # 推进控制（D-008）
    # ------------------------------------------------------------------

    def pause(self) -> None:
        """设置暂停标志；下一次 `step()` 将抛 `PausedError` 直至 `resume()`。"""
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def step(self) -> TickResult:
        """推进一个 tick 并返回 `TickResult`。

        **流程**（对齐 `运行时与事件轨迹设计.md` 三节，与下方代码 comment 编号一致）：

        - 步 0：防御——暂停则拒绝；已达 total_ticks 则拒绝；tick += 1
        - 步 1：投递上一 tick 的 outbox 到 mailboxes
        - 步 2：处理本 tick 的 scheduled_events（触发消息 / 环境事件）
        - 步 2.5（D-015 全量版）：fire 跨 tick 延后的 chained_actions
          （depth 重置为 0；与本 tick 实体决策并行存在）
        - 步 3：激活实体（v1：全部，D-015 后排除本 tick 之前已 destroy 的）
        - 步 4：每个激活实体收集 ActionProposal（写 decision_proposed 事件）
        - 步 5：validate_action，失败走 fallback（写 decision_rejected / fallback_used 事件）
        - 步 6：resolve_conflicts → apply_constraints（按 conflict_resolution 策略）
        - 步 7：应用效果（mutate state + outbox 入队消息；D-015 后含 entity 生命周期 + chained 链）
        - 步 8：写 action_executed 事件
        - 步 9：检查断点（写 breakpoint_triggered 事件）
        - 步 10：暂停判定（every_tick / 断点命中 → paused_after）
        - 步 11：按 snapshot_mode 决定是否保存快照（依赖 paused_after）
        """
        if self._paused:
            raise PausedError("Runtime 处于暂停状态；请先调用 resume()")
        total_ticks = self._scenario.config.total_ticks
        if self._state.tick >= total_ticks:
            raise TerminatedError(
                f"已达 total_ticks={total_ticks}，不可再 step()"
            )

        next_tick = self._state.tick + 1
        self._state.tick = next_tick
        tick_events: list[EventRecord] = []

        # 1. 投递 outbox → mailboxes
        self._deliver_outbox(next_tick)

        # 2. scheduled_events
        tick_events.extend(self._process_scheduled_events(next_tick))

        # 2.5. 跨 tick 延后 chained_actions fire（D-015 全量版）
        tick_events.extend(self._process_delayed_chained_actions(next_tick))

        # 3. 激活实体（v1：全体）
        active_ids = list(self._state.entities.keys())

        # 4. 决策
        proposals: list[ActionProposal] = []
        for entity_id in active_ids:
            proposal = self._make_decision(entity_id, next_tick)
            proposals.append(proposal)

            payload: dict[str, Any] = {
                "action_type": proposal.action_type,
                "params": proposal.params,
                "decision_mode": proposal.decision_mode,
            }
            # D-016 第 6 步：LLM 模式下注入 prompt_context（rule/random/fallback 跳过）。
            # pop 保证消费一次即清——下个 tick 的同 actor 决策会重新写入。
            ctx = self._last_llm_prompt_context.pop(proposal.actor_id, None)
            if ctx is not None:
                payload["prompt_context"] = ctx.model_dump()

            tick_events.append(
                self._record_event(
                    "decision_proposed",
                    actor_id=proposal.actor_id,
                    payload=payload,
                )
            )

        # 5. 校验 + fallback
        final_proposals: list[ActionProposal] = []
        effect_groups: list[list[Effect]] = []
        for proposal in proposals:
            result = self._rules.validate_action(
                self._world, self._state, proposal
            )
            if result.valid:
                final_proposals.append(proposal)
                effect_groups.append(
                    self._rules.resolve_effects(
                        self._world, self._state, proposal
                    )
                )
            else:
                tick_events.append(
                    self._record_event(
                        "decision_rejected",
                        actor_id=proposal.actor_id,
                        payload={
                            "action_type": proposal.action_type,
                            "errors": result.errors,
                        },
                    )
                )
                fb = self._fallback_proposal(proposal.actor_id, next_tick)
                tick_events.append(
                    self._record_event(
                        "fallback_used",
                        actor_id=proposal.actor_id,
                        payload={"fallback_action": fb.action_type},
                    )
                )
                final_proposals.append(fb)
                effect_groups.append(
                    self._rules.resolve_effects(self._world, self._state, fb)
                )

        # 6. 冲突解决 + 约束裁剪
        flat = self._rules.resolve_conflicts(
            self._world, self._state, effect_groups
        )
        constrained = self._rules.apply_constraints(
            self._world, self._state, flat
        )

        # 7. 应用效果
        tick_events.extend(self._apply_effects(constrained, next_tick))

        # 8. action_executed 事件
        for proposal in final_proposals:
            tick_events.append(
                self._record_event(
                    "action_executed",
                    actor_id=proposal.actor_id,
                    payload={
                        "action_type": proposal.action_type,
                        "params": proposal.params,
                    },
                )
            )

        # 9. 断点检查——同时产生 breakpoint_triggered 事件
        triggered_bps, bp_events = self._check_breakpoints()
        tick_events.extend(bp_events)

        # 10. 暂停判定
        pause_mode = self._scenario.config.pause_mode
        auto_pause = bool(pause_mode and pause_mode.every_tick)
        paused_after = auto_pause or bool(triggered_bps)

        # 11. snapshot 决策（依赖 paused_after）
        snapshot_obj = self._maybe_save_snapshot(next_tick, paused_after)
        if snapshot_obj is not None:
            tick_events.append(
                self._record_event(
                    "snapshot_saved", actor_id=None, payload={"tick": next_tick}
                )
            )

        if paused_after:
            self._paused = True

        return TickResult(
            tick=next_tick,
            events=tick_events,
            snapshot=snapshot_obj,
            paused_after=paused_after,
            triggered_breakpoints=triggered_bps,
            reached_total_ticks=(next_tick >= total_ticks),
        )

    def run_until(self, tick: int) -> list[TickResult]:
        """连续推进直到目标 tick 或更早（暂停 / total_ticks）。"""
        if tick < self._state.tick:
            raise InvalidStateError(
                f"run_until 目标 tick={tick} 小于当前 tick={self._state.tick}"
            )
        results: list[TickResult] = []
        while self._state.tick < tick and not self._paused:
            total_ticks = self._scenario.config.total_ticks
            if self._state.tick >= total_ticks:
                break
            result = self.step()
            results.append(result)
            if result.paused_after or result.reached_total_ticks:
                break
        return results

    # ------------------------------------------------------------------
    # 干预（D-008 / 需求分析 8.3）
    # ------------------------------------------------------------------

    def intervene(self, intervention: Intervention) -> EventRecord:
        """应用一条人工干预并写入 ``intervention_applied`` 事件。

        三种 kind 的行为：

        - ``inject_message``：直接进 mailbox（target_actor）或广播（None）
        - ``force_action``：暂存为 forced_actions；下一 tick 决策时覆盖 LLM 输出
        - ``override_attribute``：直接改 state.entities[target].attributes

        **tick 语义澄清**：产生的 ``EventRecord.tick`` 用的是 **Runtime 当前
        tick**（即 ``intervene()`` 被调用的瞬间实际处于的 tick）；而 ``payload["tick"]``
        是 ``intervention.tick``（用户声明的"期望生效 tick"，用于审计）。
        两者在常规调用下相等；但如果用户在 tick=2 刚结束时声明一条
        ``intervention.tick=5``的干预，本函数会立即应用并在 tick=2 写事件——
        v1 **不**支持"暂存干预，到期再生效"语义，若需要由调用方自行排序。
        """
        if intervention.kind == "inject_message":
            assert intervention.message is not None  # model_validator 保证
            env = MessageEnvelope(
                tick_emitted=intervention.tick,
                tick_delivered=intervention.tick,
                message_type=intervention.message["type"],
                from_actor=None,
                payload=intervention.message.get("payload", {}),
            )
            if intervention.target_actor:
                self._state.mailboxes.setdefault(
                    intervention.target_actor, []
                ).append(env)
            else:
                # 广播
                for entity_id in self._state.entities:
                    self._state.mailboxes.setdefault(entity_id, []).append(env)
        elif intervention.kind == "force_action":
            assert intervention.action is not None
            assert intervention.target_actor is not None
            self._forced_actions[intervention.target_actor] = intervention.action
        elif intervention.kind == "override_attribute":
            assert intervention.target_actor is not None
            assert intervention.attribute_changes is not None
            entity = self._state.entities.get(intervention.target_actor)
            if entity is not None:
                entity.attributes.update(intervention.attribute_changes)

        return self._record_event(
            "intervention_applied",
            actor_id=intervention.target_actor,
            payload={
                "kind": intervention.kind,
                "tick": intervention.tick,
                "reason": intervention.reason,
            },
        )

    # ==================================================================
    # 以下为私有辅助方法
    # ==================================================================

    # ------------------------------------------------------------------
    # 决策
    # ------------------------------------------------------------------

    def _make_decision(self, entity_id: str, tick: int) -> ActionProposal:
        """为给定实体生成 ActionProposal（先查 forced_actions，否则按模式）。"""
        # 干预路径：force_action 一次性生效
        if entity_id in self._forced_actions:
            forced = self._forced_actions.pop(entity_id)
            return ActionProposal(
                tick=tick,
                actor_id=entity_id,
                action_type=forced["action_type"],
                params=forced.get("params", {}),
                decision_mode="rule",
                raw_reasoning_summary="intervention: force_action",
                status="proposed",
            )

        entity = self._state.entities[entity_id]
        type_schema = self._world.entity_types[entity.type]
        mode = type_schema.decision_mode

        if mode == "llm":
            return self._decide_via_llm(entity_id, tick)
        if mode == "rule":
            return self._decide_via_rule(entity_id, tick)
        if mode == "random":
            return self._decide_via_random(entity_id, tick)
        # 不可达（Pydantic Literal 已限制）；用 InvalidStateError 标明这是
        # Runtime 内部状态不一致的断言型错误，不是用户输入错或运行期异常
        raise InvalidStateError(f"unknown decision_mode: {mode}")

    def _decide_via_llm(self, entity_id: str, tick: int) -> ActionProposal:
        """通过 `core.llm_policy` 编排 LLM 决策；任一层失败即 fallback。

        v1 不做协议级重试（留给 Phase B.3）。传输错（`ProviderError`）与协议错
        （`LLMProtocolError`）都走 `fallback_action`，但日志会区分原因。
        """
        try:
            result = llm_policy.decide(
                self._provider,
                self._world,
                self._scenario,
                self._state,
                entity_id,
                tick,
                config=self._runtime_config,
                event_log=self._event_log,
                rules=self._rules,
            )
            # D-016 第 6 步：存 ctx 供主循环写 decision_proposed 时塞 payload
            self._last_llm_prompt_context[entity_id] = result.prompt_context
            return result.proposal
        except ProviderError as exc:
            logger.warning(
                "provider error for %s: %s; using fallback", entity_id, exc
            )
            return self._fallback_proposal(entity_id, tick)
        except LLMProtocolError as exc:
            logger.warning(
                "LLM protocol error for %s: %s; using fallback",
                entity_id,
                exc,
            )
            return self._fallback_proposal(entity_id, tick)

    def _decide_via_rule(self, entity_id: str, tick: int) -> ActionProposal:
        """v1 默认规则策略：优先 do_nothing，否则列表首项。

        现实中各世界会希望更丰富的 rule 逻辑——那时由具体 rules 模块通过
        继承 Runtime 或扩展接口来定制。v1 先给 walkthrough 能跑通的最简实现。
        """
        entity = self._state.entities[entity_id]
        actions = self._world.entity_types[entity.type].actions
        picked = "do_nothing" if "do_nothing" in actions else actions[0]
        return ActionProposal(
            tick=tick,
            actor_id=entity_id,
            action_type=picked,
            params={},
            decision_mode="rule",
            status="proposed",
        )

    def _decide_via_random(self, entity_id: str, tick: int) -> ActionProposal:
        """随机模式：动作均匀采样 + **D-014**：按 schema 填参（结清 pitfalls P2 顶条）。

        v1 旧行为：``params={}`` 空字典——遇到 required 参数立即被 validate_action
        判 ``decision_rejected`` → 走 fallback。**75% 失败率**（pitfalls 顶条 P2）。

        D-014 新行为：用 ``ActionParamSchema`` 给每个声明的参数填值——
        ``required=True`` 必填、``required=False`` 也填以提升 random 路径覆盖。
        填值优先级：``default`` > ``type`` 采样（受 min/max/values/entity_type_filter 约束）。

        seeded RNG 保证可复现。
        """
        entity = self._state.entities[entity_id]
        actions = self._world.entity_types[entity.type].actions
        picked = self._rng.choice(actions)

        # D-014：按 schema 填参
        action_schema = self._world.action_types.get(picked)
        params: dict[str, Any] = {}
        if action_schema is not None:
            for p_name, p_schema in action_schema.params.items():
                params[p_name] = self._random_param_value(p_schema)

        return ActionProposal(
            tick=tick,
            actor_id=entity_id,
            action_type=picked,
            params=params,
            decision_mode="random",
            status="proposed",
        )

    def _random_param_value(self, schema: ActionParamSchema) -> Any:
        """根据 ``ActionParamSchema`` 给参数采样一个合法值（D-014）。

        策略（按优先级）：

        1. 若 ``schema.default`` 非 None，直接用——尊重场景 YAML 的偏好
        2. 否则按 ``schema.type`` 采样：
           - ``number``：``rng.uniform(min, max)``，默认范围 [0, 100]
           - ``string``：从 ``values`` 列表选；无则空串（场景设计建议用 default）
           - ``boolean``：50/50
           - ``entity_ref``：从 ``state.entities`` 选（按 ``entity_type_filter`` 过滤）；
             无候选时返回空串（让 validate_action 拦截，降级走 fallback）

        返回值类型与 ``schema.type`` 对齐。F8（session 27）：原版用 ``Any`` 类型
        以"避免 import 链"，但 runtime.py 已从 world_models 导入 WorldDefinition，
        加 ActionParamSchema 不引入新依赖——改回精确类型提升 IDE / mypy 体验。
        """
        if schema.default is not None:
            return schema.default

        if schema.type == "number":
            lo = schema.min if schema.min is not None else 0.0
            hi = schema.max if schema.max is not None else 100.0
            return self._rng.uniform(lo, hi)
        if schema.type == "string":
            if schema.values:
                return self._rng.choice(schema.values)
            return ""
        if schema.type == "boolean":
            return self._rng.choice([True, False])
        if schema.type == "entity_ref":
            candidates = list(self._state.entities.keys())
            if schema.entity_type_filter is not None:
                candidates = [
                    eid for eid in candidates
                    if self._state.entities[eid].type in schema.entity_type_filter
                ]
            if not candidates:
                return ""  # 无候选——validate_action 会拦截，降级 fallback
            return self._rng.choice(candidates)

        return None  # 未知类型：防御式

    def _fallback_proposal(self, entity_id: str, tick: int) -> ActionProposal:
        """走 `world.defaults.fallback_action`；未定义则 ``do_nothing``。"""
        fallback_name = "do_nothing"
        if (
            self._world.defaults is not None
            and self._world.defaults.fallback_action is not None
        ):
            fallback_name = self._world.defaults.fallback_action
        return ActionProposal(
            tick=tick,
            actor_id=entity_id,
            action_type=fallback_name,
            params={},
            decision_mode="fallback",
            status="fallback",
        )

    # ------------------------------------------------------------------
    # 效果应用
    # ------------------------------------------------------------------

    def _apply_effects(
        self, effects: list[Effect], tick: int, depth: int = 0
    ) -> list[EventRecord]:
        """把 Effect 列表逐个落到 state + 产生事件。

        - `AttributeEffect`：mutate state.entities[id].attributes[name]
          （**D-015 缩限版**：支持 ``delta`` 数值增量或 ``new_value`` 绝对值赋值二选一）
        - `EnvironmentEffect`：mutate state.environment + 写 ``environment_changed``
        - `RelationEffect`：改 state.relations + 写 ``relation_changed``
        - `MessageEffect`：envelope 入 outbox（下一 tick 投递）+ 写 ``message_emitted``
        - **D-015 全量版**（session 28）三类新 effect：

          - `EntityCreateEffect`：加 state.entities + 应用 initial_relations + 写 ``entity_created``
          - `EntityDestroyEffect`：按 cascade 清理（关系/邮箱/outbox/forced）+ 写 ``entity_destroyed``
          - `ChainedActionEffect`：同 tick 立即递归 / 跨 tick 入延后队列 + 写 ``chained_action_triggered``

        AttributeEffect 不产生独立事件——`action_executed` 已覆盖"谁做了什么"。

        **depth 参数**（D-015 全量版）：递归调用计数。原始动作 effect 应用 depth=0；
        chained 链中第 N 层的子 effect 应用 depth=N。同 tick 内链总深度若超过
        ``RuntimeConfig.max_chain_depth``，抛 `RulesError` 防无限递归。
        跨 tick 链每 tick 重置 depth=0，不计入此上限。
        """
        events: list[EventRecord] = []
        for effect in effects:
            if isinstance(effect, AttributeEffect):
                self._apply_attribute_effect(effect)
            elif isinstance(effect, EnvironmentEffect):
                self._apply_environment_effect(effect)
                events.append(
                    self._record_event(
                        "environment_changed",
                        actor_id=None,
                        payload={
                            "variable": effect.variable,
                            "delta": effect.delta,
                        },
                    )
                )
            elif isinstance(effect, RelationEffect):
                self._apply_relation_effect(effect)
                events.append(
                    self._record_event(
                        "relation_changed",
                        actor_id=None,
                        payload={
                            "operation": effect.operation,
                            "relation_type": effect.relation_type,
                            "source": effect.source,
                            "target": effect.target,
                            "value": effect.value,
                        },
                    )
                )
            elif isinstance(effect, MessageEffect):
                env = effect.envelope.model_copy(deep=True)
                env.tick_emitted = tick
                env.tick_delivered = None  # 还没投递
                self._outbox.append(env)
                events.append(
                    self._record_event(
                        "message_emitted",
                        actor_id=env.from_actor,
                        payload={
                            "message_type": env.message_type,
                            "from": env.from_actor,
                            "payload": env.payload,
                        },
                    )
                )
            # ── D-015 全量版（session 28）──
            elif isinstance(effect, EntityCreateEffect):
                events.extend(self._apply_entity_create_effect(effect))
            elif isinstance(effect, EntityDestroyEffect):
                events.extend(self._apply_entity_destroy_effect(effect))
            elif isinstance(effect, ChainedActionEffect):
                events.extend(
                    self._apply_chained_action_effect(effect, tick, depth)
                )
        return events

    def _apply_entity_create_effect(
        self, effect: EntityCreateEffect
    ) -> list[EventRecord]:
        """应用 `EntityCreateEffect`——加 state.entities + 初始关系 + 写事件（D-015）。

        - ``entity_id`` 必须唯一——已存在则抛 `RulesError`（rules 设计错）
        - ``entity_type`` 必须在 ``world.entity_types`` 已声明——否则 `RulesError`
        - ``initial_attributes`` 与 type schema 默认值合并（覆盖语义）
        - ``initial_relations`` 中每条 RelationEffect 走标准 `_apply_relation_effect`
          + 写 ``relation_changed`` 事件——保 audit 一致性
        - 新实体**不参与同 tick 激活**——下一 tick 才进入决策流程（spec 第 150 行）

        Returns:
            含 1 条 ``entity_created`` 事件 + N 条 ``relation_changed`` 事件
        """
        if effect.entity_id in self._state.entities:
            raise RulesError(
                f"EntityCreateEffect: entity_id='{effect.entity_id}' 已存在；"
                f"违反「全局唯一」约定。请检查 rules.resolve_effects 中是否对"
                f"已存在实体重复触发了 EntityCreate。"
            )
        type_schema = self._world.entity_types.get(effect.entity_type)
        if type_schema is None:
            raise RulesError(
                f"EntityCreateEffect: entity_type='{effect.entity_type}' "
                f"未在 world.entity_types 中声明。可用类型："
                f"{sorted(self._world.entity_types.keys())}"
            )

        # 合并默认值 + 覆盖值——与 _bootstrap_world_state 同语义
        merged_attrs: dict[str, Any] = {
            name: attr.default for name, attr in type_schema.attributes.items()
        }
        merged_attrs.update(effect.initial_attributes)

        self._state.entities[effect.entity_id] = EntityRuntimeState(
            id=effect.entity_id,
            type=effect.entity_type,
            attributes=merged_attrs,
        )

        events: list[EventRecord] = [
            self._record_event(
                "entity_created",
                actor_id=effect.entity_id,
                payload={
                    "entity_id": effect.entity_id,
                    "entity_type": effect.entity_type,
                    "initial_attributes": dict(merged_attrs),
                },
            )
        ]

        # 应用初始关系——逐条走 _apply_relation_effect + 写 relation_changed
        for rel_eff in effect.initial_relations:
            self._apply_relation_effect(rel_eff)
            events.append(
                self._record_event(
                    "relation_changed",
                    actor_id=None,
                    payload={
                        "operation": rel_eff.operation,
                        "relation_type": rel_eff.relation_type,
                        "source": rel_eff.source,
                        "target": rel_eff.target,
                        "value": rel_eff.value,
                        "source_effect": "entity_create",
                    },
                )
            )

        return events

    def _apply_entity_destroy_effect(
        self, effect: EntityDestroyEffect
    ) -> list[EventRecord]:
        """应用 `EntityDestroyEffect`——按 cascade 策略清理（D-015）。

        三种 cascade（详见 `EntityDestroyEffect` docstring）：

        - ``"all"``——删实体 + 关系 + 邮箱 + outbox 中其待发消息 + forced/ctx
        - ``"preserve_relations"``——只删实体 + 邮箱（保留关系 dangling）
        - ``"preserve_messages"``——只删实体 + 关系（保留邮箱与已 emit 消息）

        实体不存在时跳过 + warning（与 `_apply_attribute_effect` 同风格）。

        Returns:
            含 1 条 ``entity_destroyed`` 事件
        """
        eid = effect.entity_id
        if eid not in self._state.entities:
            logger.warning(
                "EntityDestroyEffect 目标实体 '%s' 不存在，跳过", eid
            )
            return []

        # 删主实体（在所有 cascade 模式下都做）
        del self._state.entities[eid]

        # cascade 决定附属数据怎么处理
        if effect.cascade in ("all", "preserve_messages"):
            # 删关系——该实体作为 source 或 target 的所有关系
            self._state.relations = [
                r
                for r in self._state.relations
                if r.source != eid and r.target != eid
            ]

        if effect.cascade in ("all", "preserve_relations"):
            # 删邮箱
            self._state.mailboxes.pop(eid, None)

        if effect.cascade == "all":
            # outbox 中 from_actor 是该实体的待发消息
            self._outbox = [env for env in self._outbox if env.from_actor != eid]
            # forced_actions 与 _last_llm_prompt_context 中的同 id
            self._forced_actions.pop(eid, None)
            self._last_llm_prompt_context.pop(eid, None)

        return [
            self._record_event(
                "entity_destroyed",
                actor_id=eid,
                payload={"entity_id": eid, "cascade": effect.cascade},
            )
        ]

    def _apply_chained_action_effect(
        self, effect: ChainedActionEffect, tick: int, depth: int
    ) -> list[EventRecord]:
        """应用 `ChainedActionEffect`——同 tick 立即递归 / 跨 tick 入队（D-015）。

        - ``delay_ticks > 0``：加入 ``self._delayed_chained_actions`` 队列，
          目标 tick 主循环步 2.5 取出 fire（depth 重置为 0）。本次只写
          ``chained_action_triggered`` 事件标记声明瞬间
        - ``delay_ticks == 0``：调用 `_execute_chained_action` 立即递归——
          包含 validate + resolve + apply 完整链路，depth+1 计入

        Returns:
            含 ``chained_action_triggered`` 事件 + （同 tick 时）链中所有子事件
        """
        if effect.delay_ticks > 0:
            target_tick = tick + effect.delay_ticks
            self._delayed_chained_actions.append((target_tick, effect))
            return [
                self._record_event(
                    "chained_action_triggered",
                    actor_id=effect.actor_id,
                    payload={
                        "action_type": effect.action_type,
                        "params": dict(effect.params),
                        "depth": depth,
                        "delay_ticks": effect.delay_ticks,
                        "target_tick": target_tick,
                        "delayed": True,
                    },
                )
            ]

        # 同 tick 立即——走完整执行链路
        return self._execute_chained_action(
            actor_id=effect.actor_id,
            action_type=effect.action_type,
            params=dict(effect.params),
            tick=tick,
            depth=depth,
        )

    def _execute_chained_action(
        self,
        *,
        actor_id: str,
        action_type: str,
        params: dict[str, Any],
        tick: int,
        depth: int,
    ) -> list[EventRecord]:
        """构造 chained ActionProposal + validate + resolve + 递归应用（D-015）。

        被两处调用：

        1. `_apply_chained_action_effect` 当 ``delay_ticks=0`` 时（同 tick 链）
        2. `_process_delayed_chained_actions` fire 跨 tick 延后链时（depth=0）

        **流程**：

        - 检查 ``depth >= max_chain_depth``——超限抛 `RulesError`
        - 构造 ActionProposal（``decision_mode="rule"``，标 ``raw_reasoning_summary``）
        - 写 ``chained_action_triggered`` 事件（含 depth + 1，表本次执行的层）
        - 走 `validate_action`——失败写 ``decision_rejected`` 立即终止
        - 走 ``resolve_effects + apply_constraints``
        - 写 ``action_executed`` 事件（payload 加 ``source="chained_action"``）
        - 递归调 ``_apply_effects(sub_effects, tick, depth=depth+1)``

        **不**走主循环的 conflict_resolution——chained 是规则主动设计的连锁，
        rules 应自己保证不冲突。
        """
        if depth >= self._runtime_config.max_chain_depth:
            raise RulesError(
                f"ChainedAction 链深度 {depth} 已达上限 max_chain_depth="
                f"{self._runtime_config.max_chain_depth}；"
                f"actor='{actor_id}' action='{action_type}'。"
                f"通常是 rules 写错让 A→B→A 循环触发——检查 resolve_effects "
                f"中的 ChainedActionEffect 逻辑或调高 RuntimeConfig.max_chain_depth"
            )

        proposal = ActionProposal(
            tick=tick,
            actor_id=actor_id,
            action_type=action_type,
            params=params,
            decision_mode="rule",
            raw_reasoning_summary=f"chained_action depth={depth + 1}",
            status="proposed",
        )

        events: list[EventRecord] = [
            self._record_event(
                "chained_action_triggered",
                actor_id=actor_id,
                payload={
                    "action_type": action_type,
                    "params": dict(params),
                    "depth": depth + 1,
                    "delay_ticks": 0,
                    "delayed": False,
                },
            )
        ]

        # validate_action——chained 仍走标准校验（D-014 强约束兜底）
        validation = self._rules.validate_action(
            self._world, self._state, proposal
        )
        if not validation.valid:
            events.append(
                self._record_event(
                    "decision_rejected",
                    actor_id=actor_id,
                    payload={
                        "action_type": action_type,
                        "errors": validation.errors,
                        "source": "chained_action",
                    },
                )
            )
            return events

        sub_effects = self._rules.resolve_effects(
            self._world, self._state, proposal
        )
        constrained = self._rules.apply_constraints(
            self._world, self._state, sub_effects
        )

        events.append(
            self._record_event(
                "action_executed",
                actor_id=actor_id,
                payload={
                    "action_type": action_type,
                    "params": dict(params),
                    "source": "chained_action",
                },
            )
        )

        # 递归——depth+1 计入
        events.extend(self._apply_effects(constrained, tick, depth=depth + 1))
        return events

    def _process_delayed_chained_actions(
        self, tick: int
    ) -> list[EventRecord]:
        """主循环步 2.5——fire 目标 tick 等于本 tick 的所有延后链（D-015）。

        每个被 fire 的延后链 depth 重置为 0（spec 第 91 行：跨 tick 链每 tick
        重置深度，不计入同 tick 链上限）。fire 后从 ``_delayed_chained_actions``
        队列移除。
        """
        events: list[EventRecord] = []
        remaining: list[tuple[int, ChainedActionEffect]] = []
        for target_tick, effect in self._delayed_chained_actions:
            if target_tick == tick:
                events.extend(
                    self._execute_chained_action(
                        actor_id=effect.actor_id,
                        action_type=effect.action_type,
                        params=dict(effect.params),
                        tick=tick,
                        depth=0,  # 跨 tick 链每 tick 重置 depth
                    )
                )
            else:
                remaining.append((target_tick, effect))
        self._delayed_chained_actions = remaining
        return events

    def _apply_attribute_effect(self, effect: AttributeEffect) -> None:
        entity = self._state.entities.get(effect.actor_id)
        if entity is None:
            logger.warning(
                "AttributeEffect 目标实体 '%s' 不存在，跳过", effect.actor_id
            )
            return

        # D-015：new_value 形式——直接赋值（覆盖任何类型；不做 numeric 校验）
        if effect.new_value is not None:
            entity.attributes[effect.attribute] = effect.new_value
            return

        # delta 形式（数值增量）——保留原有 numeric 校验
        current = entity.attributes.get(effect.attribute, 0)
        if not _is_numeric(current):
            logger.warning(
                "属性 %s.%s 非 numeric，跳过 delta",
                effect.actor_id,
                effect.attribute,
            )
            return
        entity.attributes[effect.attribute] = current + effect.delta

    def _apply_environment_effect(self, effect: EnvironmentEffect) -> None:
        current = self._state.environment.get(effect.variable, 0)
        if not _is_numeric(current):
            logger.warning(
                "环境变量 %s 非 numeric，跳过 delta", effect.variable
            )
            return
        self._state.environment[effect.variable] = current + effect.delta

    def _apply_relation_effect(self, effect: RelationEffect) -> None:
        if effect.operation == "add":
            self._state.relations.append(
                RelationRuntimeState(
                    type=effect.relation_type,
                    source=effect.source,
                    target=effect.target,
                    value=effect.value,
                )
            )
        elif effect.operation == "update_value":
            for rel in self._state.relations:
                if (
                    rel.type == effect.relation_type
                    and rel.source == effect.source
                    and rel.target == effect.target
                ):
                    rel.value = effect.value
                    return
            logger.warning(
                "update_value 未找到匹配关系 %s:%s→%s",
                effect.relation_type,
                effect.source,
                effect.target,
            )
        elif effect.operation == "remove":
            self._state.relations = [
                r
                for r in self._state.relations
                if not (
                    r.type == effect.relation_type
                    and r.source == effect.source
                    and r.target == effect.target
                )
            ]

    # ------------------------------------------------------------------
    # 消息投递
    # ------------------------------------------------------------------

    def _deliver_outbox(self, tick: int) -> None:
        """把 outbox 中的消息按 delivery 规则投递到目标 mailbox。

        v1 的 outbox 语义是"一批处完"：不管成功投递还是被丢弃（未声明
        message_type / direct 无有效 target / by_relation 未实现），处理完后
        一律清空 outbox。不存在"消息跨 tick 滯留"场景。
        """
        if not self._outbox:
            return
        message_types = self._world.message_types or {}
        for env in self._outbox:
            mt_schema = message_types.get(env.message_type)
            if mt_schema is None:
                logger.warning(
                    "未知 message_type='%s'，丢弃消息", env.message_type
                )
                continue
            env.tick_delivered = tick
            if mt_schema.delivery == "broadcast":
                for entity_id in self._state.entities:
                    self._state.mailboxes.setdefault(entity_id, []).append(env)
            elif mt_schema.delivery == "direct":
                target = env.payload.get("target_id") if isinstance(env.payload, dict) else None
                if isinstance(target, str) and target in self._state.entities:
                    self._state.mailboxes.setdefault(target, []).append(env)
                else:
                    logger.warning(
                        "direct 消息 %s 未指定有效 target_id（payload 需含 target_id 字段）",
                        env.message_type,
                    )
            else:
                # by_relation：v1 未实现
                logger.warning(
                    "delivery='%s' 在 v1 Runtime 中未实现，消息被丢弃",
                    mt_schema.delivery,
                )
        self._outbox = []

    # ------------------------------------------------------------------
    # scheduled_events
    # ------------------------------------------------------------------

    def _process_scheduled_events(self, tick: int) -> list[EventRecord]:
        events: list[EventRecord] = []
        for sched in self._scenario.scheduled_events:
            if sched.tick != tick:
                continue
            events.append(
                self._record_event(
                    "scheduled_event_triggered",
                    actor_id=None,
                    payload={
                        "name": sched.name,
                        "type": sched.type,
                    },
                )
            )
            if sched.type == "message_injection" and sched.message is not None:
                env = MessageEnvelope(
                    tick_emitted=tick,
                    tick_delivered=None,
                    message_type=sched.message["type"],
                    from_actor=None,
                    payload=sched.message.get("payload", {}),
                )
                self._outbox.append(env)
                events.append(
                    self._record_event(
                        "message_emitted",
                        actor_id=None,
                        payload={
                            "message_type": env.message_type,
                            "from": None,
                            "source": "scheduled_event",
                            "payload": env.payload,
                        },
                    )
                )
            elif sched.type == "environment_event" and sched.payload is not None:
                events.extend(self._apply_scheduled_environment_event(sched.payload))
        return events

    def _apply_scheduled_environment_event(
        self, payload: dict[str, Any]
    ) -> list[EventRecord]:
        """应用 scheduled environment_event 的 payload，产生 environment_changed 事件。

        校验原则（F4 加固）：

        - 若 ``var`` 未在 ``world.environment.variables`` 声明 → warn + 跳过
          （保持与 scenario_loader 跨文件校验的同构防御）
        - 若声明为数值型但 ``new_value`` 非 numeric → warn + 跳过
        - 其他类型（string / enum / boolean）目前原值转交，delta 不可算 → 记为 None
        """
        events: list[EventRecord] = []
        env_schema = (
            self._world.environment.variables
            if self._world.environment is not None
            else {}
        )
        for var, new_value in payload.items():
            var_schema = env_schema.get(var)
            if var_schema is None:
                logger.warning(
                    "scheduled environment_event 引用未声明的环境变量 '%s'，跳过",
                    var,
                )
                continue
            if var_schema.type == "number" and not _is_numeric(new_value):
                logger.warning(
                    "scheduled environment_event 对数值变量 '%s' 提供非 numeric 值 %r，跳过",
                    var,
                    new_value,
                )
                continue
            current = self._state.environment.get(var, 0)
            if _is_numeric(current) and _is_numeric(new_value):
                delta = new_value - current
            else:
                delta = None
            self._state.environment[var] = new_value
            events.append(
                self._record_event(
                    "environment_changed",
                    actor_id=None,
                    payload={
                        "variable": var,
                        "new_value": new_value,
                        "delta": delta,
                        "source": "scheduled_event",
                    },
                )
            )
        return events

    # ------------------------------------------------------------------
    # 断点 / 快照 / 事件工具
    # ------------------------------------------------------------------

    def _check_breakpoints(self) -> tuple[list[str], list[EventRecord]]:
        """遍历断点，每命中一条写入一条 breakpoint_triggered 事件。

        返回 ``(triggered_ids, events)``：
        - ``triggered_ids``：命中的断点 id 列表（对外组装进 TickResult）
        - ``events``：对应的 EventRecord 列表（已 append 到 EventLog）
        """
        triggered: list[str] = []
        events: list[EventRecord] = []
        for bp in self._scenario.breakpoints:
            if self._breakpoint_matches(bp):
                triggered.append(bp.id)
                events.append(
                    self._record_event(
                        "breakpoint_triggered",
                        actor_id=None,
                        payload={
                            "breakpoint_id": bp.id,
                            "tick": self._state.tick,
                        },
                    )
                )
        return triggered, events

    def _breakpoint_matches(self, bp: Any) -> bool:
        # 环境变量条件：任一命中即整个断点命中
        for var, cond in bp.when.environment.items():
            val = self._state.environment.get(var)
            if not _is_numeric(val):
                continue
            if cond.gte is not None and val >= cond.gte:
                return True
            if cond.lte is not None and val <= cond.lte:
                return True
        # 实体属性条件
        ent_cond = bp.when.entity
        if ent_cond is not None:
            entity = self._state.entities.get(ent_cond.id)
            if entity is not None:
                val = entity.attributes.get(ent_cond.attribute)
                if _is_numeric(val):
                    if ent_cond.gte is not None and val >= ent_cond.gte:
                        return True
                    if ent_cond.lte is not None and val <= ent_cond.lte:
                        return True
        return False

    def _maybe_save_snapshot(
        self, tick: int, will_pause: bool
    ) -> Snapshot | None:
        """按 snapshot_mode 决定是否保存快照。v1 模式：every_tick / on_pause / on_end。"""
        mode = self._scenario.config.snapshot_mode or "every_tick"
        total_ticks = self._scenario.config.total_ticks
        should_save = (
            mode == "every_tick"
            or (mode == "on_pause" and will_pause)
            or (mode == "on_end" and tick >= total_ticks)
        )
        if not should_save:
            return None
        snap = self._make_snapshot(tick)
        self._event_log.save_snapshot(snap)
        return snap

    def _make_snapshot(self, tick: int) -> Snapshot:
        # F1 修正：emitted / delivered_next_tick 均基于 outbox——因为 v1 outbox 每 tick
        # 全清空，本 tick 末 outbox 中的消息既代表"本 tick 产生"，也代表
        # "将在下一 tick 投递"。之前用 sum(mailboxes) 是累积投递数——与
        # delivered_next_tick 语义错位（bug）。
        outbox_count = len(self._outbox)
        return Snapshot(
            tick=tick,
            entity_state_summary={
                e.id: dict(e.attributes) for e in self._state.entities.values()
            },
            relation_state_summary=[
                {
                    "type": r.type,
                    "source": r.source,
                    "target": r.target,
                    "value": r.value,
                }
                for r in self._state.relations
            ],
            environment_state=dict(self._state.environment),
            message_summary=MessageSummary(
                emitted=outbox_count,
                delivered_next_tick=outbox_count,
            ),
        )

    def _record_event(
        self,
        kind: EventKind,
        *,
        actor_id: str | None,
        payload: dict[str, Any] | None = None,
    ) -> EventRecord:
        """生成 EventRecord、append 到 EventLog、返回副本。"""
        self._event_counter += 1
        record = EventRecord(
            event_id=f"evt_{self._event_counter:06d}",
            tick=self._state.tick,
            kind=kind,
            actor_id=actor_id,
            payload=payload or {},
        )
        self._event_log.append(record)
        return record
