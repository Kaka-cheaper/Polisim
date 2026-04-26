"""Runtime 测试（D-008 步进式 API + D-010 装配机制）。

对应 `core/runtime.py` 与 `docs/02-design/运行时与事件轨迹设计.md`。

测试分组：

1. **构造 / bootstrap**：显式 rules、D-010 rules_module、无规则报错、初始状态、run_id
2. **单 tick**：tick 推进、事件生成、状态变更
3. **多 tick 集成**：walkthrough 完整跑通 5 ticks
4. **scheduled_events**：message_injection 触发 + 下一 tick 投递
5. **消息投递**：broadcast / direct / 未知 type
6. **intervene**：inject_message / force_action / override_attribute
7. **pause / resume / 断点**：状态机 + paused_after 标志
8. **snapshot_mode**：every_tick / on_end
9. **Fallback**：LLM JSON 解析失败 / 选非法动作
10. **Context manager**：close 被调用
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import pytest

from core.errors import InvalidStateError, PausedError, TerminatedError
from core.providers.mock import MockProvider
from core.runtime import Runtime
from core.scenario_loader import load_scenario
from core.definition_loader import load_world_definition
from models.config_models import RuntimeConfig, StorageConfig
from models.runtime_models import (
    EventRecord,
    Intervention,
    TickResult,
    WorldState,
)
from models.scenario_models import Scenario
from models.world_models import WorldDefinition
from rules.base import BaseRules
from rules.minimal_market import MinimalMarketRules


# =============================================================================
# Fixtures
# =============================================================================


WALKTHROUGH_DIR = Path(__file__).resolve().parent.parent / "scenarios" / "minimal_market"


@pytest.fixture
def walkthrough_world() -> WorldDefinition:
    return load_world_definition(WALKTHROUGH_DIR / "world.yaml")


@pytest.fixture
def walkthrough_scenario(walkthrough_world: WorldDefinition) -> Scenario:
    return load_scenario(WALKTHROUGH_DIR / "scenario.yaml", walkthrough_world)


@pytest.fixture
def storage(tmp_path: Path) -> StorageConfig:
    """隔离每个测试的 runs_root——防止污染仓库。"""
    return StorageConfig(version="0.1", runs_root=str(tmp_path / "runs"))


@pytest.fixture
def scripted_provider() -> MockProvider:
    """5 tick 足够的 LLM 响应脚本——专供 company_a（walkthrough 唯一 llm 实体）。

    Budget 设计保证 cash 一直非负：100 → 80 → 65 → 65 → 55 → 55
    """
    return MockProvider(
        scripted_responses=[
            json.dumps({"action": "promote", "params": {"budget": 20}}),
            json.dumps({"action": "promote", "params": {"budget": 15}}),
            json.dumps({"action": "do_nothing", "params": {}}),
            json.dumps({"action": "promote", "params": {"budget": 10}}),
            json.dumps({"action": "do_nothing", "params": {}}),
            # 循环：若 scripted 耗尽，MockProvider 回到开头
        ]
    )


@pytest.fixture
def runtime(
    walkthrough_world: WorldDefinition,
    walkthrough_scenario: Scenario,
    scripted_provider: MockProvider,
    storage: StorageConfig,
) -> Iterator[Runtime]:
    rt = Runtime(
        walkthrough_world,
        walkthrough_scenario,
        scripted_provider,
        storage_config=storage,
    )
    yield rt
    rt.close()


# =============================================================================
# 1. 构造 / bootstrap
# =============================================================================


def test_runtime_construction_with_explicit_rules(
    walkthrough_world: WorldDefinition,
    walkthrough_scenario: Scenario,
    scripted_provider: MockProvider,
    storage: StorageConfig,
) -> None:
    """显式传入 rules 实例，走 D-010 的"参数优先"路径。"""
    rules = MinimalMarketRules()
    rt = Runtime(
        walkthrough_world,
        walkthrough_scenario,
        scripted_provider,
        rules=rules,
        storage_config=storage,
    )
    assert rt.current_tick() == 0
    assert rt.is_paused() is False
    rt.close()


def test_runtime_construction_via_rules_module(
    walkthrough_world: WorldDefinition,
    walkthrough_scenario: Scenario,
    scripted_provider: MockProvider,
    storage: StorageConfig,
) -> None:
    """D-010 路径：rules=None → 从 scenario.rules_module 加载。"""
    rt = Runtime(
        walkthrough_world,
        walkthrough_scenario,
        scripted_provider,
        storage_config=storage,
    )
    # rules 字段是私有的，但可以通过行为验证——step 后 cash 按 promote 公式变动
    rt.close()


def test_runtime_construction_errors_without_rules_or_module(
    walkthrough_world: WorldDefinition,
    walkthrough_scenario: Scenario,
    scripted_provider: MockProvider,
    storage: StorageConfig,
) -> None:
    """两个路径都空：构造失败。"""
    # 强行把 rules_module 清掉（原 walkthrough scenario 有）
    scenario_copy = walkthrough_scenario.model_copy(update={"rules_module": None})
    with pytest.raises(InvalidStateError, match="rules_module"):
        Runtime(
            walkthrough_world,
            scenario_copy,
            scripted_provider,
            storage_config=storage,
        )


def test_runtime_initial_state_bootstrap(runtime: Runtime) -> None:
    """初始状态：tick=0、实体属性=world默认∪scenario覆盖、环境变量已合并。"""
    state = runtime.get_state()
    assert isinstance(state, WorldState)
    assert state.tick == 0
    # 实体存在
    assert set(state.entities.keys()) == {"company_a", "regulator_main"}
    company = state.entities["company_a"]
    # walkthrough scenario 显式设置 cash=100 / reputation=50（与 world 默认值一致）
    assert company.attributes["cash"] == 100
    assert company.attributes["reputation"] == 50
    # regulator_main 的 strictness=50（来自 world 默认 + scenario 一致覆盖）
    assert state.entities["regulator_main"].attributes["strictness"] == 50
    # 环境变量 policy_pressure 来自 scenario
    assert state.environment["policy_pressure"] == 20
    # mailboxes 空
    assert state.mailboxes == {}


def test_runtime_generates_run_id_if_not_provided(
    walkthrough_world: WorldDefinition,
    walkthrough_scenario: Scenario,
    scripted_provider: MockProvider,
    storage: StorageConfig,
) -> None:
    rt = Runtime(
        walkthrough_world,
        walkthrough_scenario,
        scripted_provider,
        storage_config=storage,
    )
    assert rt.run_id  # 非空
    assert "minimal-market" in rt.run_id or "walkthrough-min" in rt.run_id
    rt.close()


def test_runtime_accepts_explicit_run_id(
    walkthrough_world: WorldDefinition,
    walkthrough_scenario: Scenario,
    scripted_provider: MockProvider,
    storage: StorageConfig,
) -> None:
    rt = Runtime(
        walkthrough_world,
        walkthrough_scenario,
        scripted_provider,
        storage_config=storage,
        run_id="custom_run_42",
    )
    assert rt.run_id == "custom_run_42"
    rt.close()


def test_runtime_saves_tick_zero_snapshot(runtime: Runtime) -> None:
    """Bootstrap 后应有 tick=0 快照（可用于从头回放）。"""
    snap = runtime.get_snapshot(0)
    assert snap is not None
    assert snap.tick == 0
    assert "company_a" in snap.entity_state_summary
    assert snap.environment_state["policy_pressure"] == 20


# =============================================================================
# 2. 单 tick 流程
# =============================================================================


def test_step_advances_tick_counter(runtime: Runtime) -> None:
    assert runtime.current_tick() == 0
    result = runtime.step()
    assert runtime.current_tick() == 1
    assert result.tick == 1


def test_step_returns_tick_result_with_events(runtime: Runtime) -> None:
    result = runtime.step()
    assert isinstance(result, TickResult)
    # 至少有 2 个 decision_proposed（company_a + regulator_main）
    # + 2 个 action_executed + 1 个 snapshot_saved
    kinds = [e.kind for e in result.events]
    assert kinds.count("decision_proposed") == 2
    assert kinds.count("action_executed") == 2
    assert "snapshot_saved" in kinds


def test_decision_proposed_event_contains_prompt_context_for_llm_mode(
    runtime: Runtime,
) -> None:
    """D-016 第 6 步：LLM 模式 actor 的 decision_proposed payload 含 prompt_context。"""
    result = runtime.step()
    decision_events = [e for e in result.events if e.kind == "decision_proposed"]

    # company_a 是 LLM 模式 → payload 含 prompt_context
    company_decision = next(
        e for e in decision_events if e.actor_id == "company_a"
    )
    assert "prompt_context" in company_decision.payload
    ctx_dump = company_decision.payload["prompt_context"]
    assert isinstance(ctx_dump, dict)
    # 关键字段齐全
    assert "actor_view" in ctx_dump
    assert "perception" in ctx_dump
    assert "available_actions" in ctx_dump
    # actor_view 含 D-016 第 1-5 步累进字段
    assert ctx_dump["actor_view"]["id"] == "company_a"

    # regulator_main 是 rule 模式 → payload 不含 prompt_context
    regulator_decision = next(
        e for e in decision_events if e.actor_id == "regulator_main"
    )
    assert "prompt_context" not in regulator_decision.payload


def test_step_applies_promote_effect(runtime: Runtime) -> None:
    """scripted 首个响应是 promote(budget=20) → cash: 100 → 80, reputation: 50 → 55."""
    runtime.step()
    state = runtime.get_state()
    company = state.entities["company_a"]
    assert company.attributes["cash"] == 80
    assert company.attributes["reputation"] == 55


def test_step_rule_mode_entity_does_nothing(runtime: Runtime) -> None:
    """regulator_main decision_mode=rule，v1 默认走 do_nothing → 属性不变。"""
    before = dict(runtime.get_state().entities["regulator_main"].attributes)
    runtime.step()
    after = runtime.get_state().entities["regulator_main"].attributes
    assert after == before


def test_step_refuses_past_total_ticks(runtime: Runtime) -> None:
    runtime.run_until(5)
    assert runtime.current_tick() == 5
    with pytest.raises(TerminatedError, match="total_ticks"):
        runtime.step()


# =============================================================================
# 3. 多 tick 集成：walkthrough 5-tick
# =============================================================================


def test_run_until_completes_walkthrough(runtime: Runtime) -> None:
    """跑满 5 tick，检查最终状态与事件轨迹完整性。"""
    results = runtime.run_until(5)
    assert len(results) == 5
    assert [r.tick for r in results] == [1, 2, 3, 4, 5]
    assert results[-1].reached_total_ticks is True

    state = runtime.get_state()
    assert state.tick == 5
    # company_a 按 scripted：promote(20) + promote(15) + do_nothing + promote(10) + do_nothing
    # cash: 100 → 80 → 65 → 65 → 55 → 55
    # reputation clamped at ≤100 每次 promote +5：50 → 55 → 60 → 60 → 65 → 65
    assert state.entities["company_a"].attributes["cash"] == 55
    assert state.entities["company_a"].attributes["reputation"] == 65


def test_run_until_accumulates_events_across_ticks(runtime: Runtime) -> None:
    results = runtime.run_until(3)
    total_events = sum(len(r.events) for r in results)
    # 每 tick 至少 5 个事件（2 decision_proposed + 2 action_executed + 1 snapshot_saved）
    # tick 2 还有 scheduled_event_triggered + message_emitted
    assert total_events >= 15


def test_run_until_rejects_past_target_below_current(runtime: Runtime) -> None:
    runtime.step()
    with pytest.raises(InvalidStateError, match="小于当前"):
        runtime.run_until(0)


def test_run_until_same_tick_is_noop(runtime: Runtime) -> None:
    assert runtime.run_until(0) == []


# =============================================================================
# 4. scheduled_events
# =============================================================================


def test_scheduled_event_fires_at_correct_tick(runtime: Runtime) -> None:
    """walkthrough 在 tick=2 注入 policy_signal。tick 1 无触发，tick 2 有。"""
    r1 = runtime.step()
    r2 = runtime.step()
    kinds_1 = [e.kind for e in r1.events]
    kinds_2 = [e.kind for e in r2.events]
    assert "scheduled_event_triggered" not in kinds_1
    assert "scheduled_event_triggered" in kinds_2
    # 同时生成 message_emitted
    assert "message_emitted" in kinds_2


def test_scheduled_message_delivered_next_tick(runtime: Runtime) -> None:
    """tick 2 入 outbox；tick 3 开始时 deliver 到 mailboxes（broadcast）。"""
    runtime.step()  # tick 1
    runtime.step()  # tick 2: scheduled event fires → outbox
    # tick 2 结束时 mailboxes 还是空（消息未投递）
    assert runtime.get_state().mailboxes == {}
    runtime.step()  # tick 3: deliver
    mailboxes = runtime.get_state().mailboxes
    # broadcast 到所有实体
    assert "company_a" in mailboxes
    assert "regulator_main" in mailboxes
    # 每个 mailbox 里都有一条 policy_signal
    assert any(m.message_type == "policy_signal" for m in mailboxes["company_a"])


def test_scheduled_environment_event_applies_legal_value(
    walkthrough_world: WorldDefinition,
    walkthrough_scenario: Scenario,
    scripted_provider: MockProvider,
    storage: StorageConfig,
) -> None:
    """F4 正路径：policy_pressure 从 20 覆盖到 60，产生 environment_changed 事件。"""
    from models.scenario_models import ScheduledEvent

    sc = walkthrough_scenario.model_copy(deep=True)
    sc.scheduled_events = [
        ScheduledEvent(
            tick=1,
            type="environment_event",
            name="pressure_up",
            payload={"policy_pressure": 60},
        )
    ]
    rt = Runtime(walkthrough_world, sc, scripted_provider, storage_config=storage)
    result = rt.step()
    assert rt.get_state().environment["policy_pressure"] == 60
    env_changes = [
        e for e in result.events
        if e.kind == "environment_changed" and e.payload.get("source") == "scheduled_event"
    ]
    assert len(env_changes) == 1
    assert env_changes[0].payload["variable"] == "policy_pressure"
    assert env_changes[0].payload["delta"] == 40  # 60 - 20
    rt.close()


def test_scheduled_environment_event_skips_undeclared_variable(
    walkthrough_world: WorldDefinition,
    walkthrough_scenario: Scenario,
    scripted_provider: MockProvider,
    storage: StorageConfig,
) -> None:
    """F4 防御：引用 world 未声明的变量 → 跳过 + 不改 state + 不产生 environment_changed 事件。"""
    from models.scenario_models import ScheduledEvent

    sc = walkthrough_scenario.model_copy(deep=True)
    sc.scheduled_events = [
        ScheduledEvent(
            tick=1,
            type="environment_event",
            name="bogus",
            payload={"undeclared_var": 42},
        )
    ]
    rt = Runtime(walkthrough_world, sc, scripted_provider, storage_config=storage)
    result = rt.step()
    assert "undeclared_var" not in rt.get_state().environment
    env_changes = [
        e for e in result.events
        if e.kind == "environment_changed" and e.payload.get("source") == "scheduled_event"
    ]
    assert env_changes == []
    rt.close()


def test_scheduled_environment_event_skips_non_numeric_for_number_var(
    walkthrough_world: WorldDefinition,
    walkthrough_scenario: Scenario,
    scripted_provider: MockProvider,
    storage: StorageConfig,
) -> None:
    """F4 防御：数值变量 policy_pressure 提供字符串 → 跳过 + 保持原值。"""
    from models.scenario_models import ScheduledEvent

    sc = walkthrough_scenario.model_copy(deep=True)
    sc.scheduled_events = [
        ScheduledEvent(
            tick=1,
            type="environment_event",
            name="type_mismatch",
            payload={"policy_pressure": "high"},
        )
    ]
    rt = Runtime(walkthrough_world, sc, scripted_provider, storage_config=storage)
    rt.step()
    # policy_pressure 仍为初始值（20），未被字符串覆盖
    assert rt.get_state().environment["policy_pressure"] == 20
    rt.close()


# =============================================================================
# 5. 消息投递（基于 MessageEffect；minimal_market 不主动 emit，需单独构造）
# =============================================================================


def test_message_broadcast_delivery_via_scheduled_event(runtime: Runtime) -> None:
    """复用 scheduled policy_signal（delivery=broadcast）验证投递机制。"""
    runtime.run_until(3)
    mailboxes = runtime.get_state().mailboxes
    assert len(mailboxes.get("company_a", [])) == 1
    assert len(mailboxes.get("regulator_main", [])) == 1


# =============================================================================
# 6. Intervene（D-008 三种 kind）
# =============================================================================


def test_intervene_inject_message_broadcast(runtime: Runtime) -> None:
    """inject_message 无 target_actor → 广播到所有实体 mailbox。"""
    intervention = Intervention(
        tick=1,
        kind="inject_message",
        target_actor=None,
        reason="test",
        message={
            "type": "policy_signal",
            "payload": {"strength": 0.5},
        },
    )
    event = runtime.intervene(intervention)
    assert event.kind == "intervention_applied"
    assert event.payload["kind"] == "inject_message"

    # 两个实体 mailbox 都有消息（Runtime 直接写 mailbox，不经 outbox）
    mailboxes = runtime.get_state().mailboxes
    assert len(mailboxes.get("company_a", [])) == 1
    assert len(mailboxes.get("regulator_main", [])) == 1


def test_intervene_inject_message_targeted(runtime: Runtime) -> None:
    intervention = Intervention(
        tick=1,
        kind="inject_message",
        target_actor="company_a",
        reason="test",
        message={
            "type": "policy_signal",
            "payload": {"strength": 0.9},
        },
    )
    runtime.intervene(intervention)
    mailboxes = runtime.get_state().mailboxes
    assert len(mailboxes.get("company_a", [])) == 1
    assert len(mailboxes.get("regulator_main", [])) == 0


def test_intervene_override_attribute(runtime: Runtime) -> None:
    intervention = Intervention(
        tick=1,
        kind="override_attribute",
        target_actor="company_a",
        reason="debugging",
        attribute_changes={"cash": 999},
    )
    runtime.intervene(intervention)
    state = runtime.get_state()
    assert state.entities["company_a"].attributes["cash"] == 999


def test_intervene_force_action_overrides_decision(runtime: Runtime) -> None:
    """force_action：下一 tick 强制 company_a 执行指定动作，无视 LLM 输出。"""
    intervention = Intervention(
        tick=1,
        kind="force_action",
        target_actor="company_a",
        reason="test",
        action={"action_type": "do_nothing", "params": {}},
    )
    runtime.intervene(intervention)

    # scripted[0] 是 promote(20)，但应被 do_nothing 覆盖 → cash 不变
    runtime.step()
    state = runtime.get_state()
    assert state.entities["company_a"].attributes["cash"] == 100
    # reputation 也不变（walkthrough 起点 50）
    assert state.entities["company_a"].attributes["reputation"] == 50


# =============================================================================
# 7. pause / resume / 断点
# =============================================================================


def test_pause_blocks_step(runtime: Runtime) -> None:
    runtime.pause()
    assert runtime.is_paused() is True
    with pytest.raises(PausedError, match="暂停"):
        runtime.step()


def test_resume_unblocks_step(runtime: Runtime) -> None:
    runtime.pause()
    runtime.resume()
    assert runtime.is_paused() is False
    result = runtime.step()
    assert result.tick == 1


def test_run_until_stops_on_pause(runtime: Runtime) -> None:
    """pause 后 run_until 立即返回空列表。"""
    runtime.pause()
    assert runtime.run_until(3) == []


def test_every_tick_pause_sets_paused_after(
    walkthrough_world: WorldDefinition,
    walkthrough_scenario: Scenario,
    scripted_provider: MockProvider,
    storage: StorageConfig,
) -> None:
    """scenario.config.pause_mode.every_tick=True 时每 tick 结束都应 paused_after。"""
    from models.scenario_models import PauseMode

    sc = walkthrough_scenario.model_copy(deep=True)
    sc.config.pause_mode = PauseMode(manual=True, every_tick=True)
    rt = Runtime(
        walkthrough_world, sc, scripted_provider, storage_config=storage
    )
    result = rt.step()
    assert result.paused_after is True
    assert rt.is_paused() is True
    rt.close()


def test_run_until_stops_when_paused_after(
    walkthrough_world: WorldDefinition,
    walkthrough_scenario: Scenario,
    scripted_provider: MockProvider,
    storage: StorageConfig,
) -> None:
    """every_tick 模式下 run_until(5) 实际只跑 1 tick 就停。"""
    from models.scenario_models import PauseMode

    sc = walkthrough_scenario.model_copy(deep=True)
    sc.config.pause_mode = PauseMode(manual=True, every_tick=True)
    rt = Runtime(
        walkthrough_world, sc, scripted_provider, storage_config=storage
    )
    results = rt.run_until(5)
    assert len(results) == 1
    assert results[0].paused_after is True
    rt.close()


def test_breakpoint_triggers_paused_after(
    walkthrough_world: WorldDefinition,
    walkthrough_scenario: Scenario,
    scripted_provider: MockProvider,
    storage: StorageConfig,
) -> None:
    """注入一条 policy_pressure>=80 断点，跑一步后应命中。

    walkthrough scenario 默认不含 breakpoints 数组；本测试深拷贝后追加一个，
    验证 Runtime._check_breakpoints 的环境变量分支。
    """
    from models.scenario_models import (
        Breakpoint,
        BreakpointEnvironmentCondition,
        BreakpointWhen,
    )

    sc = walkthrough_scenario.model_copy(deep=True)
    sc.breakpoints = [
        Breakpoint(
            id="bp_pressure_high",
            when=BreakpointWhen(
                environment={
                    "policy_pressure": BreakpointEnvironmentCondition(gte=80)
                },
            ),
        )
    ]
    rt = Runtime(
        walkthrough_world, sc, scripted_provider, storage_config=storage
    )
    # 初始 policy_pressure=20；手动推高到 95 再 step
    rt._state.environment["policy_pressure"] = 95
    result = rt.step()
    assert "bp_pressure_high" in result.triggered_breakpoints
    assert result.paused_after is True
    assert rt.is_paused() is True
    # F3: 命中的断点必须在 TickResult.events 里有对应 breakpoint_triggered 事件
    bp_events = [e for e in result.events if e.kind == "breakpoint_triggered"]
    assert len(bp_events) == 1
    assert bp_events[0].payload["breakpoint_id"] == "bp_pressure_high"
    rt.close()


# =============================================================================
# 8. snapshot_mode
# =============================================================================


def test_snapshot_mode_every_tick_saves_each(runtime: Runtime) -> None:
    runtime.run_until(3)
    # tick 0/1/2/3 都应有快照
    for t in [0, 1, 2, 3]:
        assert runtime.get_snapshot(t) is not None


def test_snapshot_message_summary_reflects_outbox_not_mailbox(
    runtime: Runtime,
) -> None:
    """F1 回归：snapshot.message_summary 必须基于当前 outbox，不受 mailboxes 累积影响。

    walkthrough 的 tick=2 scheduled policy_signal 会进 outbox；tick=2 末尾快照
    的 emitted = delivered_next_tick = 1（outbox 中唯一的那条）。
    tick=3 开始投递到 2 个 mailbox，但 tick=3 末尾 outbox 已清空，快照应 = 0，
    而不是 2（若仍按旧 bug 用 sum(mailboxes) 会是 2）。
    """
    runtime.step()  # tick 1
    r2 = runtime.step()  # tick 2: scheduled event → outbox[1]
    assert r2.snapshot is not None
    assert r2.snapshot.message_summary.emitted == 1
    assert r2.snapshot.message_summary.delivered_next_tick == 1

    r3 = runtime.step()  # tick 3: deliver → outbox[0]，mailboxes 累积 2
    assert r3.snapshot is not None
    assert r3.snapshot.message_summary.emitted == 0
    assert r3.snapshot.message_summary.delivered_next_tick == 0


def test_snapshot_mode_on_end_saves_only_final(
    walkthrough_world: WorldDefinition,
    walkthrough_scenario: Scenario,
    scripted_provider: MockProvider,
    storage: StorageConfig,
) -> None:
    sc = walkthrough_scenario.model_copy(deep=True)
    sc.config.snapshot_mode = "on_end"
    rt = Runtime(
        walkthrough_world, sc, scripted_provider, storage_config=storage
    )
    rt.run_until(5)
    # tick=0 有（bootstrap），中间没有，tick=5 有
    assert rt.get_snapshot(0) is not None
    assert rt.get_snapshot(3) is None
    assert rt.get_snapshot(5) is not None
    rt.close()


# =============================================================================
# 9. Fallback
# =============================================================================


def test_fallback_on_unparseable_llm_json(
    walkthrough_world: WorldDefinition,
    walkthrough_scenario: Scenario,
    storage: StorageConfig,
) -> None:
    """LLM 返回非 JSON 字符串 → fallback_used + do_nothing。"""
    bad_provider = MockProvider(fixed_response="this is not json at all")
    rt = Runtime(
        walkthrough_world,
        walkthrough_scenario,
        bad_provider,
        storage_config=storage,
    )
    result = rt.step()
    kinds = [e.kind for e in result.events]
    # fallback 路径：不走 decision_rejected（因为 LLM 层就失败了）
    # 而是 _fallback_proposal 直接产出 do_nothing，走正常 validate
    action_events = [e for e in result.events if e.kind == "action_executed"]
    company_action = next(
        e for e in action_events if e.actor_id == "company_a"
    )
    assert company_action.payload["action_type"] == "do_nothing"
    # cash 不变
    assert rt.get_state().entities["company_a"].attributes["cash"] == 100
    rt.close()


def test_fallback_on_llm_invalid_action_name(
    walkthrough_world: WorldDefinition,
    walkthrough_scenario: Scenario,
    storage: StorageConfig,
) -> None:
    bad_provider = MockProvider(
        fixed_response=json.dumps({"action": "unknown_action", "params": {}})
    )
    rt = Runtime(
        walkthrough_world,
        walkthrough_scenario,
        bad_provider,
        storage_config=storage,
    )
    result = rt.step()
    company_action = next(
        e for e in result.events
        if e.kind == "action_executed" and e.actor_id == "company_a"
    )
    assert company_action.payload["action_type"] == "do_nothing"
    rt.close()


def test_fallback_on_validation_failure(
    walkthrough_world: WorldDefinition,
    walkthrough_scenario: Scenario,
    storage: StorageConfig,
) -> None:
    """LLM 返回语义有效但规则拒绝（如 budget > cash）→ decision_rejected + fallback_used."""
    # company_a 初始 cash=100；要求 budget=1000 → 规则层拒绝
    bad_provider = MockProvider(
        fixed_response=json.dumps({"action": "promote", "params": {"budget": 1000}})
    )
    rt = Runtime(
        walkthrough_world,
        walkthrough_scenario,
        bad_provider,
        storage_config=storage,
    )
    result = rt.step()
    kinds = [e.kind for e in result.events]
    assert "decision_rejected" in kinds
    assert "fallback_used" in kinds
    # 最终动作是 fallback 后的 do_nothing
    company_action = next(
        e for e in result.events
        if e.kind == "action_executed" and e.actor_id == "company_a"
    )
    assert company_action.payload["action_type"] == "do_nothing"
    rt.close()


# =============================================================================
# 10. Context manager
# =============================================================================


def test_runtime_context_manager_closes_event_log(
    walkthrough_world: WorldDefinition,
    walkthrough_scenario: Scenario,
    scripted_provider: MockProvider,
    storage: StorageConfig,
) -> None:
    with Runtime(
        walkthrough_world,
        walkthrough_scenario,
        scripted_provider,
        storage_config=storage,
    ) as rt:
        rt.step()
        # 进入 with 块时，文件句柄开启（通过行为推断）
        assert rt.current_tick() == 1
    # 退出后 close 被调用（幂等再 close 一次不报错）
    rt.close()


def test_events_jsonl_file_written_when_persist_true(
    walkthrough_world: WorldDefinition,
    walkthrough_scenario: Scenario,
    scripted_provider: MockProvider,
    tmp_path: Path,
) -> None:
    storage = StorageConfig(version="0.1", persist=True, runs_root=str(tmp_path / "runs"))
    with Runtime(
        walkthrough_world,
        walkthrough_scenario,
        scripted_provider,
        storage_config=storage,
    ) as rt:
        rt.run_until(2)
        run_dir = Path(storage.runs_root) / rt.run_id
    events_file = run_dir / "events.jsonl"
    assert events_file.exists()
    lines = events_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) > 0
    # 每行都是合法 JSON
    for line in lines:
        json.loads(line)
