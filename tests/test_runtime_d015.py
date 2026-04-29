"""D-015 全量版运行时端到端测试（session 28 落地）。

对应 `docs/02-design/decisions/D-015-effect系统扩充.md` 第二节 + 第五节。

**测试范围**：

1. **EntityCreate**——动态创建实体 + 初始关系 + 下一 tick 激活 + 唯一性校验
2. **EntityDestroy**——cascade=all/preserve_relations/preserve_messages 三策略 +
   不存在实体跳过
3. **ChainedAction**——同 tick 立即递归 + 跨 tick 延后 fire + 防无限递归抛
   `RulesError` + max_chain_depth 可配置 + 跨 tick 链不计入深度上限

**测试架构**：

- 程序化构造测试 world（Worker / Manager + 一组演示动作）——避免污染 minimal_market
- 自定义 `_D015TestRules` 按 ``action_type`` 产出对应 D-015 effect
- 用 ``force_action`` Intervention 在指定 tick 让 alice 执行特定动作
- 两实体均 ``decision_mode=rule``——不调 LLM，避免 mock 复杂性
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from core.errors import RulesError
from core.providers.mock import MockProvider
from core.runtime import Runtime
from models.config_models import RuntimeConfig, StorageConfig
from models.runtime_models import (
    ActionProposal,
    AttributeEffect,
    ChainedActionEffect,
    Effect,
    EntityCreateEffect,
    EntityDestroyEffect,
    Intervention,
    RelationEffect,
    WorldState,
)
from models.scenario_models import Scenario
from models.world_models import WorldDefinition
from rules.base import BaseRules


# =============================================================================
# 测试 world / scenario：含 D-015 三类新 effect 的演示动作
# =============================================================================


def _make_d015_world() -> WorldDefinition:
    return WorldDefinition.model_validate(
        {
            "version": "0.1",
            "world": {"id": "d015-test", "name": "D-015 Test World"},
            "entity_types": {
                "Worker": {
                    "decision_mode": "rule",
                    "attributes": {
                        "salary": {
                            "type": "number",
                            "min": 0,
                            "max": 1000,
                            "default": 100,
                        },
                    },
                    "actions": [
                        "do_nothing",
                        "work",
                        "report",
                        "acknowledge",
                        "fire",
                        "hire",
                        "recursive_chain",
                        "delayed_chain",
                        "hire_invalid_type",
                    ],
                },
                "Manager": {
                    "decision_mode": "rule",
                    "attributes": {
                        "approvals": {
                            "type": "number",
                            "min": 0,
                            "max": 100,
                            "default": 0,
                        },
                    },
                    "actions": ["do_nothing", "acknowledge"],
                },
            },
            "action_types": {
                "do_nothing": {
                    "actor_types": ["Worker", "Manager"],
                    "params": {},
                    "effects": [],
                },
                "work": {
                    "actor_types": ["Worker"],
                    "params": {},
                    "effects": [{"kind": "self_attribute"}],
                },
                "report": {
                    "actor_types": ["Worker"],
                    "params": {},
                    "effects": [{"kind": "self_attribute"}],
                },
                "acknowledge": {
                    "actor_types": ["Worker", "Manager"],
                    "params": {},
                    "effects": [{"kind": "self_attribute"}],
                },
                "fire": {
                    "actor_types": ["Worker"],
                    "params": {
                        "target_id": {
                            "type": "entity_ref",
                            "required": True,
                            "entity_type_filter": ["Worker"],
                        }
                    },
                    "effects": [{"kind": "self_attribute"}],
                },
                "hire": {
                    "actor_types": ["Worker"],
                    "params": {
                        "new_id": {"type": "string", "required": True},
                    },
                    "effects": [{"kind": "self_attribute"}],
                },
                "recursive_chain": {
                    "actor_types": ["Worker"],
                    "params": {},
                    "effects": [{"kind": "self_attribute"}],
                },
                "delayed_chain": {
                    "actor_types": ["Worker"],
                    "params": {},
                    "effects": [{"kind": "self_attribute"}],
                },
                "hire_invalid_type": {
                    "actor_types": ["Worker"],
                    "params": {},
                    "effects": [{"kind": "self_attribute"}],
                },
            },
            "relation_types": {
                "reports_to": {"directed": True, "transient": False},
            },
            "defaults": {
                "fallback_action": "do_nothing",
                "conflict_resolution": "both",
            },
        }
    )


def _make_d015_scenario() -> Scenario:
    return Scenario.model_validate(
        {
            "version": "0.1",
            "world_id": "d015-test",
            "scenario": {"id": "d015-scenario", "name": "D-015 Scenario"},
            "entities": [
                {"id": "alice", "type": "Worker"},
                {"id": "manager", "type": "Manager"},
            ],
            "config": {"total_ticks": 10},
        }
    )


# =============================================================================
# 测试 rules：根据 action_type 产出 D-015 各类 effect
# =============================================================================


class _D015TestRules(BaseRules):
    """D-015 全量版测试用 rules。

    动作 → effect 映射：

    - ``work`` → AttributeEffect(salary +10)
    - ``report`` → ChainedActionEffect(actor=manager, action=acknowledge, delay=0)
    - ``acknowledge`` → AttributeEffect(approvals +1) [Manager] / [] [Worker]
    - ``fire(target_id)`` → EntityDestroyEffect(target_id, cascade=...)
    - ``hire(new_id)`` → EntityCreateEffect(new_id, type=Worker, attrs+relation)
    - ``recursive_chain`` → ChainedActionEffect(actor=alice, action=recursive_chain, delay=0)
      [触发同 tick 链超深]
    - ``delayed_chain`` → ChainedActionEffect(actor=manager, action=acknowledge, delay=2)
      [跨 tick 链]
    - ``hire_invalid_type`` → EntityCreateEffect(..., entity_type="UnknownType")
      [触发未声明类型 RulesError]
    - ``do_nothing`` → []
    """

    def __init__(
        self,
        *,
        random_seed: int | None = 42,
        fire_cascade: str = "all",
    ) -> None:
        super().__init__(random_seed=random_seed)
        self._fire_cascade = fire_cascade

    def actions_handled(self) -> set[str]:
        return {
            "do_nothing",
            "work",
            "report",
            "acknowledge",
            "fire",
            "hire",
            "recursive_chain",
            "delayed_chain",
            "hire_invalid_type",
        }

    def resolve_effects(
        self,
        world: WorldDefinition,
        state: WorldState,
        proposal: ActionProposal,
    ) -> list[Effect]:
        action = proposal.action_type
        actor_id = proposal.actor_id

        if action == "do_nothing":
            return []

        if action == "work":
            return [
                AttributeEffect(
                    actor_id=actor_id, attribute="salary", delta=10
                )
            ]

        if action == "report":
            return [
                ChainedActionEffect(
                    actor_id="manager",
                    action_type="acknowledge",
                    params={},
                    delay_ticks=0,
                )
            ]

        if action == "acknowledge":
            actor = state.entities.get(actor_id)
            if actor is not None and actor.type == "Manager":
                return [
                    AttributeEffect(
                        actor_id=actor_id,
                        attribute="approvals",
                        delta=1,
                    )
                ]
            return []

        if action == "fire":
            target = proposal.params.get("target_id", "")
            return [
                EntityDestroyEffect(
                    entity_id=target, cascade=self._fire_cascade  # type: ignore[arg-type]
                )
            ]

        if action == "hire":
            new_id = proposal.params.get("new_id", "")
            return [
                EntityCreateEffect(
                    entity_id=new_id,
                    entity_type="Worker",
                    initial_attributes={"salary": 50},
                    initial_relations=[
                        RelationEffect(
                            operation="add",
                            relation_type="reports_to",
                            source=new_id,
                            target=actor_id,
                            value=1.0,
                        )
                    ],
                )
            ]

        if action == "recursive_chain":
            # 故意让 alice 触发自己的 recursive_chain → 同 tick 内无限链
            return [
                ChainedActionEffect(
                    actor_id="alice",
                    action_type="recursive_chain",
                    params={},
                    delay_ticks=0,
                )
            ]

        if action == "delayed_chain":
            return [
                ChainedActionEffect(
                    actor_id="manager",
                    action_type="acknowledge",
                    params={},
                    delay_ticks=2,
                )
            ]

        if action == "hire_invalid_type":
            return [
                EntityCreateEffect(
                    entity_id="ghost",
                    entity_type="UnknownType",  # world 没声明
                )
            ]

        return []


# =============================================================================
# fixtures
# =============================================================================


@pytest.fixture
def d015_world() -> WorldDefinition:
    return _make_d015_world()


@pytest.fixture
def d015_scenario() -> Scenario:
    return _make_d015_scenario()


@pytest.fixture
def d015_rules() -> _D015TestRules:
    return _D015TestRules(random_seed=42)


@pytest.fixture
def storage(tmp_path: Path) -> StorageConfig:
    """每个测试隔离 runs_root；persist=False 减少 IO 开销。"""
    return StorageConfig(
        version="0.1", persist=False, runs_root=str(tmp_path / "runs")
    )


@pytest.fixture
def provider() -> MockProvider:
    """Worker / Manager 都是 rule mode——provider 不会被调用，但 Runtime 仍要传。"""
    return MockProvider(fixed_response='{"action":"do_nothing","params":{}}')


def _force_intervention(
    actor_id: str, action_type: str, params: dict[str, Any] | None = None
) -> Intervention:
    """工具：构造 force_action Intervention，让指定 actor 在下次 step 执行某动作。"""
    return Intervention(
        tick=1,
        kind="force_action",
        target_actor=actor_id,
        action={"action_type": action_type, "params": params or {}},
    )


# =============================================================================
# 1. EntityCreate 测试
# =============================================================================


class TestEntityCreate:
    def test_hire_creates_new_worker_with_attributes_and_relation(
        self, d015_world, d015_scenario, d015_rules, storage, provider
    ) -> None:
        """alice hire(new_id='bob') → bob 实体创建 + reports_to 关系建立。"""
        with Runtime(
            d015_world,
            d015_scenario,
            provider,
            rules=d015_rules,
            storage_config=storage,
        ) as rt:
            rt.intervene(_force_intervention("alice", "hire", {"new_id": "bob"}))
            result = rt.step()

            # bob 已加入 state.entities
            assert "bob" in rt.get_state().entities
            bob = rt.get_state().entities["bob"]
            assert bob.type == "Worker"
            assert bob.attributes["salary"] == 50

            # reports_to 关系建立
            relations = rt.get_state().relations
            matching = [
                r
                for r in relations
                if r.type == "reports_to"
                and r.source == "bob"
                and r.target == "alice"
            ]
            assert len(matching) == 1

            # 事件含 entity_created
            kinds = {ev.kind for ev in result.events}
            assert "entity_created" in kinds

    def test_new_worker_activates_next_tick_not_same_tick(
        self, d015_world, d015_scenario, d015_rules, storage, provider
    ) -> None:
        """spec 第六节决策：新建实体不参与同 tick 激活，下一 tick 才激活。"""
        with Runtime(
            d015_world,
            d015_scenario,
            provider,
            rules=d015_rules,
            storage_config=storage,
        ) as rt:
            rt.intervene(_force_intervention("alice", "hire", {"new_id": "bob"}))
            r1 = rt.step()
            r2 = rt.step()

            tick1_decision_actors = {
                ev.actor_id
                for ev in r1.events
                if ev.kind == "decision_proposed"
            }
            tick2_decision_actors = {
                ev.actor_id
                for ev in r2.events
                if ev.kind == "decision_proposed"
            }
            assert "bob" not in tick1_decision_actors
            assert "bob" in tick2_decision_actors

    def test_hire_existing_entity_id_raises_rules_error(
        self, d015_world, d015_scenario, d015_rules, storage, provider
    ) -> None:
        """hire(new_id='alice') —— alice 已存在，违反唯一性 → RulesError。"""
        with Runtime(
            d015_world,
            d015_scenario,
            provider,
            rules=d015_rules,
            storage_config=storage,
        ) as rt:
            rt.intervene(
                _force_intervention("alice", "hire", {"new_id": "alice"})
            )
            with pytest.raises(RulesError, match="已存在"):
                rt.step()

    def test_hire_unknown_entity_type_raises_rules_error(
        self, d015_world, d015_scenario, d015_rules, storage, provider
    ) -> None:
        """rules 触发 EntityCreate(entity_type='UnknownType') → RulesError。"""
        with Runtime(
            d015_world,
            d015_scenario,
            provider,
            rules=d015_rules,
            storage_config=storage,
        ) as rt:
            rt.intervene(_force_intervention("alice", "hire_invalid_type"))
            with pytest.raises(RulesError, match="未在 world.entity_types"):
                rt.step()


# =============================================================================
# 2. EntityDestroy 测试
# =============================================================================


class TestEntityDestroy:
    def test_fire_destroys_target_with_cascade_all(
        self, d015_world, d015_scenario, d015_rules, storage, provider
    ) -> None:
        """alice 先 hire(bob)，下一 tick alice 再 fire(target=bob)→ bob + 关系全清。"""
        with Runtime(
            d015_world,
            d015_scenario,
            provider,
            rules=d015_rules,
            storage_config=storage,
        ) as rt:
            # tick 1: hire bob
            rt.intervene(_force_intervention("alice", "hire", {"new_id": "bob"}))
            rt.step()
            assert "bob" in rt.get_state().entities
            assert any(
                r.source == "bob" for r in rt.get_state().relations
            )

            # tick 2: alice fire bob
            rt.intervene(
                _force_intervention("alice", "fire", {"target_id": "bob"})
            )
            result = rt.step()

            # bob 已删除
            assert "bob" not in rt.get_state().entities
            # cascade=all 默认——关系也删除
            assert all(
                r.source != "bob" and r.target != "bob"
                for r in rt.get_state().relations
            )
            # 事件含 entity_destroyed
            kinds = {ev.kind for ev in result.events}
            assert "entity_destroyed" in kinds

    def test_fire_with_preserve_relations_keeps_relations(
        self, d015_world, d015_scenario, storage, provider
    ) -> None:
        """cascade=preserve_relations → 删实体 + 邮箱，但关系保留为 dangling。"""
        rules = _D015TestRules(fire_cascade="preserve_relations")
        with Runtime(
            d015_world,
            d015_scenario,
            provider,
            rules=rules,
            storage_config=storage,
        ) as rt:
            rt.intervene(_force_intervention("alice", "hire", {"new_id": "bob"}))
            rt.step()  # tick 1: bob 创建 + reports_to(bob → alice) 建立
            assert any(r.source == "bob" for r in rt.get_state().relations)

            rt.intervene(
                _force_intervention("alice", "fire", {"target_id": "bob"})
            )
            rt.step()  # tick 2: bob 删除但保留关系
            assert "bob" not in rt.get_state().entities
            # 关系仍在（dangling 引用）
            assert any(
                r.type == "reports_to"
                and r.source == "bob"
                and r.target == "alice"
                for r in rt.get_state().relations
            )

    def test_destroy_nonexistent_entity_skips_with_warning(
        self,
        d015_world,
        d015_scenario,
        d015_rules,
        storage,
        provider,
        caplog,
    ) -> None:
        """fire 不存在的 target → warning 但不抛异常（与 _apply_attribute_effect 风格一致）。"""
        with Runtime(
            d015_world,
            d015_scenario,
            provider,
            rules=d015_rules,
            storage_config=storage,
        ) as rt:
            # alice fire 不存在的 ghost
            rt.intervene(
                _force_intervention("alice", "fire", {"target_id": "ghost"})
            )
            # 不应抛异常——只有 warning
            with caplog.at_level("WARNING"):
                result = rt.step()
            # 未产生 entity_destroyed 事件
            kinds = {ev.kind for ev in result.events}
            assert "entity_destroyed" not in kinds


# =============================================================================
# 3. ChainedAction 同 tick 立即执行测试
# =============================================================================


class TestChainedActionImmediate:
    def test_report_triggers_acknowledge_in_same_tick(
        self, d015_world, d015_scenario, d015_rules, storage, provider
    ) -> None:
        """alice report → manager acknowledge 立即执行 → manager.approvals +1。"""
        with Runtime(
            d015_world,
            d015_scenario,
            provider,
            rules=d015_rules,
            storage_config=storage,
        ) as rt:
            before = rt.get_state().entities["manager"].attributes["approvals"]
            rt.intervene(_force_intervention("alice", "report"))
            result = rt.step()

            after = rt.get_state().entities["manager"].attributes["approvals"]
            assert after == before + 1

            # 事件流含 chained_action_triggered + action_executed (source=chained)
            kinds = [ev.kind for ev in result.events]
            assert "chained_action_triggered" in kinds
            chained_acks = [
                ev
                for ev in result.events
                if ev.kind == "action_executed"
                and ev.payload.get("source") == "chained_action"
                and ev.payload.get("action_type") == "acknowledge"
            ]
            assert len(chained_acks) == 1

    def test_chained_action_triggered_event_has_depth_one(
        self, d015_world, d015_scenario, d015_rules, storage, provider
    ) -> None:
        """alice report → chained event 的 depth=1（首层链）。"""
        with Runtime(
            d015_world,
            d015_scenario,
            provider,
            rules=d015_rules,
            storage_config=storage,
        ) as rt:
            rt.intervene(_force_intervention("alice", "report"))
            result = rt.step()
            triggered = [
                ev
                for ev in result.events
                if ev.kind == "chained_action_triggered"
            ]
            assert len(triggered) == 1
            assert triggered[0].payload["depth"] == 1
            assert triggered[0].payload["delay_ticks"] == 0
            assert triggered[0].payload["delayed"] is False


# =============================================================================
# 4. ChainedAction 跨 tick 延后执行测试
# =============================================================================


class TestChainedActionDelayed:
    def test_delay_ticks_2_fires_two_ticks_later(
        self, d015_world, d015_scenario, d015_rules, storage, provider
    ) -> None:
        """alice delayed_chain (delay=2) → tick 1 入队，tick 3 fire。"""
        with Runtime(
            d015_world,
            d015_scenario,
            provider,
            rules=d015_rules,
            storage_config=storage,
        ) as rt:
            before = rt.get_state().entities["manager"].attributes["approvals"]
            rt.intervene(_force_intervention("alice", "delayed_chain"))

            # tick 1: 触发 delayed_chain → 入队，approvals 不变
            r1 = rt.step()
            assert (
                rt.get_state().entities["manager"].attributes["approvals"]
                == before
            )
            # tick 1 应有 chained_action_triggered (delayed=True)
            t1_triggered = [
                ev
                for ev in r1.events
                if ev.kind == "chained_action_triggered"
            ]
            assert len(t1_triggered) == 1
            assert t1_triggered[0].payload["delayed"] is True
            assert t1_triggered[0].payload["target_tick"] == 3

            # tick 2: 队列等待，approvals 仍不变
            rt.step()
            assert (
                rt.get_state().entities["manager"].attributes["approvals"]
                == before
            )

            # tick 3: 队列 fire → manager.approvals +1
            r3 = rt.step()
            assert (
                rt.get_state().entities["manager"].attributes["approvals"]
                == before + 1
            )
            # tick 3 应有 chained_action_triggered (delayed=False，fire 时刻)
            t3_triggered = [
                ev
                for ev in r3.events
                if ev.kind == "chained_action_triggered"
            ]
            # fire 时 _execute_chained_action 写一次（depth+1=1, delayed=False）
            assert any(ev.payload["delayed"] is False for ev in t3_triggered)


# =============================================================================
# 5. 防递归测试
# =============================================================================


class TestChainedActionRecursionGuard:
    def test_self_recursive_chain_raises_rules_error(
        self, d015_world, d015_scenario, d015_rules, storage, provider
    ) -> None:
        """recursive_chain → recursive_chain 同 tick 自循环 → 抛 RulesError。

        默认 max_chain_depth=3，depth 0/1/2/3 → 第 4 次（depth=3）抛错。
        """
        with Runtime(
            d015_world,
            d015_scenario,
            provider,
            rules=d015_rules,
            storage_config=storage,
        ) as rt:
            rt.intervene(_force_intervention("alice", "recursive_chain"))
            with pytest.raises(RulesError, match="链深度"):
                rt.step()

    def test_max_chain_depth_configurable_low_passes(
        self, d015_world, d015_scenario, d015_rules, storage, provider
    ) -> None:
        """非递归链深度 1（report → acknowledge）远小于默认 3——通过。"""
        # 用默认 max_chain_depth=3 跑 report → 链深 1，OK
        with Runtime(
            d015_world,
            d015_scenario,
            provider,
            rules=d015_rules,
            storage_config=storage,
        ) as rt:
            rt.intervene(_force_intervention("alice", "report"))
            result = rt.step()
            # 事件流包含 acknowledge 的 action_executed
            kinds = [
                ev.payload.get("action_type")
                for ev in result.events
                if ev.kind == "action_executed"
            ]
            assert "acknowledge" in kinds

    def test_max_chain_depth_one_blocks_recursion_at_second_level(
        self, d015_world, d015_scenario, d015_rules, storage, provider
    ) -> None:
        """max_chain_depth=1 配合 recursive_chain → 第 2 层（depth=1）抛 RulesError。

        证明 max_chain_depth 字段真正生效（与默认 3 不同，更紧的限制更早抛）。
        语义：max_chain_depth=N 允许同 tick 内链长度 ≤ N（spec 第 90 行）。
        depth 从 0 起算；进入 _execute 时检查 ``depth >= max_chain_depth`` 抛错。
        """
        runtime_config = RuntimeConfig(version="0.1", max_chain_depth=1)
        with Runtime(
            d015_world,
            d015_scenario,
            provider,
            rules=d015_rules,
            runtime_config=runtime_config,
            storage_config=storage,
        ) as rt:
            rt.intervene(_force_intervention("alice", "recursive_chain"))
            with pytest.raises(RulesError, match="链深度"):
                rt.step()

    def test_cross_tick_chain_does_not_count_toward_depth(
        self, d015_world, d015_scenario, d015_rules, storage, provider
    ) -> None:
        """spec 第 91 行：跨 tick 链（delay_ticks>0）每 tick 重置 depth。

        max_chain_depth=1 + delayed_chain（delay=2）→ 跨 tick fire 时 depth=0，
        不会因为 max_chain_depth=1 抛错。
        """
        runtime_config = RuntimeConfig(version="0.1", max_chain_depth=1)
        with Runtime(
            d015_world,
            d015_scenario,
            provider,
            rules=d015_rules,
            runtime_config=runtime_config,
            storage_config=storage,
        ) as rt:
            before = rt.get_state().entities["manager"].attributes["approvals"]
            rt.intervene(_force_intervention("alice", "delayed_chain"))
            # tick 1:入队（不抛错——延后链不计深度）
            rt.step()
            # tick 2: 等待
            rt.step()
            # tick 3: fire delayed → depth=0 进 _execute → 0>=1 False → 通过
            # acknowledge 子 effect 是 AttributeEffect，无嵌套链
            rt.step()
            after = rt.get_state().entities["manager"].attributes["approvals"]
            assert after == before + 1
