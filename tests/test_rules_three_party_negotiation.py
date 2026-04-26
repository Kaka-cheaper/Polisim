"""三人谈判规则测试（D-009 路线 1 的第二份具体兑现）。

对应 `rules/three_party_negotiation.py` 与
`scenarios/three_party_negotiation/`。

测试分组：

1. **validate_action 业务前置条件**：propose 自指 / target 不存在 / price 为负；
   accept|reject 自指 / offer_from 不存在
2. **resolve_effects 单元**：propose / accept / reject / do_nothing 的 effect 形状
3. **trust clamp**：accept 触上限 100、reject 触下限 0
4. **混合 effects 路径**：accept 同时产生 RelationEffect + AttributeEffect + MessageEffect
5. **端到端 walkthrough**：scripted Mock 驱动 alice，验证 tick 推进 / direct 消息投递 /
   trust 累积 / breakpoint 触发
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import pytest

from core.definition_loader import load_world_definition
from core.providers.mock import MockProvider
from core.runtime import Runtime
from core.scenario_loader import load_scenario
from models.config_models import RuntimeConfig, StorageConfig
from models.runtime_models import (
    ActionProposal,
    AttributeEffect,
    EntityRuntimeState,
    MessageEffect,
    RelationEffect,
    RelationRuntimeState,
    WorldState,
)
from models.scenario_models import Scenario
from models.world_models import WorldDefinition
from rules.three_party_negotiation import NegotiationRules


# =============================================================================
# Fixtures
# =============================================================================


_SCENARIO_DIR = Path("scenarios/three_party_negotiation")


@pytest.fixture
def world() -> WorldDefinition:
    return load_world_definition(_SCENARIO_DIR / "world.yaml")


@pytest.fixture
def scenario(world: WorldDefinition) -> Scenario:
    return load_scenario(_SCENARIO_DIR / "scenario.yaml", world)


@pytest.fixture
def rules() -> NegotiationRules:
    return NegotiationRules(random_seed=42)


def _state_with_three_negotiators() -> WorldState:
    """构造 3 实体 + 6 双向 trust 关系的最小 WorldState（不依赖 scenario.yaml）。"""
    entities = {
        "alice": EntityRuntimeState(
            id="alice",
            type="Negotiator",
            attributes={"cash": 200, "target_price": 80, "flexibility": 25, "max_trust": 50},
        ),
        "bob": EntityRuntimeState(
            id="bob",
            type="RuleNegotiator",
            attributes={"cash": 150, "target_price": 120, "flexibility": 15, "max_trust": 50},
        ),
        "charlie": EntityRuntimeState(
            id="charlie",
            type="RandomNegotiator",
            attributes={"cash": 180, "target_price": 100, "flexibility": 30, "max_trust": 50},
        ),
    }
    relations = [
        RelationRuntimeState(type="trust", source=s, target=t, value=50.0)
        for s, t in [
            ("alice", "bob"), ("alice", "charlie"),
            ("bob", "alice"), ("bob", "charlie"),
            ("charlie", "alice"), ("charlie", "bob"),
        ]
    ]
    return WorldState(tick=0, entities=entities, relations=relations, mailboxes={})


def _propose(actor: str, target: str, price: float = 100) -> ActionProposal:
    return ActionProposal(
        tick=1,
        actor_id=actor,
        action_type="propose",
        params={"target_id": target, "price": price},
        decision_mode="llm",
        status="proposed",
    )


def _accept(actor: str, offer_from: str, price: float = 90) -> ActionProposal:
    return ActionProposal(
        tick=2,
        actor_id=actor,
        action_type="accept",
        params={"offer_from": offer_from, "price": price},
        decision_mode="llm",
        status="proposed",
    )


def _reject(actor: str, offer_from: str) -> ActionProposal:
    return ActionProposal(
        tick=2,
        actor_id=actor,
        action_type="reject",
        params={"offer_from": offer_from},
        decision_mode="llm",
        status="proposed",
    )


# =============================================================================
# 1. validate_action 业务前置条件
# =============================================================================


class TestValidateAction:
    def test_propose_to_self_rejected(
        self, world: WorldDefinition, rules: NegotiationRules
    ) -> None:
        state = _state_with_three_negotiators()
        result = rules.validate_action(
            world, state, _propose("alice", "alice", 90)
        )
        assert not result.valid
        assert any("不能是自己" in e for e in result.errors)

    def test_propose_to_unknown_actor_rejected(
        self, world: WorldDefinition, rules: NegotiationRules
    ) -> None:
        state = _state_with_three_negotiators()
        result = rules.validate_action(
            world, state, _propose("alice", "ghost", 90)
        )
        assert not result.valid
        assert any("ghost" in e for e in result.errors)

    def test_propose_negative_price_rejected(
        self, world: WorldDefinition, rules: NegotiationRules
    ) -> None:
        state = _state_with_three_negotiators()
        result = rules.validate_action(
            world, state, _propose("alice", "bob", -5)
        )
        assert not result.valid
        assert any("price" in e for e in result.errors)

    def test_propose_happy_path_accepted(
        self, world: WorldDefinition, rules: NegotiationRules
    ) -> None:
        state = _state_with_three_negotiators()
        result = rules.validate_action(
            world, state, _propose("alice", "bob", 90)
        )
        assert result.valid
        assert result.errors == []

    def test_accept_self_rejected(
        self, world: WorldDefinition, rules: NegotiationRules
    ) -> None:
        state = _state_with_three_negotiators()
        result = rules.validate_action(world, state, _accept("alice", "alice"))
        assert not result.valid

    def test_accept_unknown_offer_from_rejected(
        self, world: WorldDefinition, rules: NegotiationRules
    ) -> None:
        state = _state_with_three_negotiators()
        result = rules.validate_action(world, state, _accept("alice", "ghost"))
        assert not result.valid

    def test_reject_unknown_offer_from_rejected(
        self, world: WorldDefinition, rules: NegotiationRules
    ) -> None:
        state = _state_with_three_negotiators()
        result = rules.validate_action(world, state, _reject("alice", "ghost"))
        assert not result.valid


# =============================================================================
# 2. resolve_effects 单元
# =============================================================================


class TestResolveEffects:
    def test_do_nothing_returns_empty(
        self, world: WorldDefinition, rules: NegotiationRules
    ) -> None:
        state = _state_with_three_negotiators()
        proposal = ActionProposal(
            tick=1,
            actor_id="alice",
            action_type="do_nothing",
            params={},
            decision_mode="rule",
            status="proposed",
        )
        assert rules.resolve_effects(world, state, proposal) == []

    def test_propose_yields_single_message_effect(
        self, world: WorldDefinition, rules: NegotiationRules
    ) -> None:
        state = _state_with_three_negotiators()
        effects = rules.resolve_effects(world, state, _propose("alice", "bob", 90))
        assert len(effects) == 1
        eff = effects[0]
        assert isinstance(eff, MessageEffect)
        assert eff.envelope.message_type == "offer"
        assert eff.envelope.from_actor == "alice"
        assert eff.envelope.payload["target_id"] == "bob"
        assert eff.envelope.payload["price"] == 90.0
        assert eff.envelope.payload["from_negotiator"] == "alice"

    def test_accept_yields_three_effect_kinds(
        self, world: WorldDefinition, rules: NegotiationRules
    ) -> None:
        """关键：accept 同时产生 RelationEffect + AttributeEffect + MessageEffect。

        这是 minimal_market 没演示的混合 effects 路径——验证 BaseRules
        / Runtime 流水线对三种 effect 共存的处理。
        """
        state = _state_with_three_negotiators()  # alice→bob trust=50, alice.max_trust=50
        effects = rules.resolve_effects(world, state, _accept("alice", "bob", 90))
        kinds = {type(eff).__name__ for eff in effects}
        assert kinds == {"RelationEffect", "AttributeEffect", "MessageEffect"}

        rel_eff = next(e for e in effects if isinstance(e, RelationEffect))
        assert rel_eff.operation == "update_value"
        assert rel_eff.relation_type == "trust"
        assert rel_eff.source == "alice"
        assert rel_eff.target == "bob"
        # 50 + 20 = 70
        assert rel_eff.value == 70.0

        attr_eff = next(e for e in effects if isinstance(e, AttributeEffect))
        assert attr_eff.actor_id == "alice"
        assert attr_eff.attribute == "max_trust"
        # max(50, 70) - 50 = 20
        assert attr_eff.delta == 20.0

        msg_eff = next(e for e in effects if isinstance(e, MessageEffect))
        assert msg_eff.envelope.message_type == "agreement"
        assert msg_eff.envelope.payload["acceptor"] == "alice"
        assert msg_eff.envelope.payload["counterparty"] == "bob"
        assert msg_eff.envelope.payload["price"] == 90.0

    def test_accept_skips_attribute_effect_when_max_unchanged(
        self, world: WorldDefinition, rules: NegotiationRules
    ) -> None:
        """alice.max_trust=80 时再 accept bob（trust 50→70），新 max 仍 80→ 不发 AttributeEffect。"""
        state = _state_with_three_negotiators()
        state.entities["alice"].attributes["max_trust"] = 80
        effects = rules.resolve_effects(world, state, _accept("alice", "bob", 90))
        kinds = {type(eff).__name__ for eff in effects}
        # 没有 AttributeEffect——避免 0 delta 噪声
        assert kinds == {"RelationEffect", "MessageEffect"}

    def test_reject_yields_single_relation_effect(
        self, world: WorldDefinition, rules: NegotiationRules
    ) -> None:
        state = _state_with_three_negotiators()
        effects = rules.resolve_effects(world, state, _reject("alice", "bob"))
        assert len(effects) == 1
        eff = effects[0]
        assert isinstance(eff, RelationEffect)
        # 50 - 10 = 40
        assert eff.value == 40.0


# =============================================================================
# 3. trust clamp 边界
# =============================================================================


class TestTrustClamp:
    def test_accept_clamps_at_100(
        self, world: WorldDefinition, rules: NegotiationRules
    ) -> None:
        state = _state_with_three_negotiators()
        # 把 trust 调到 90，再 accept +20 应被 clamp 在 100
        for rel in state.relations:
            if rel.source == "alice" and rel.target == "bob":
                rel.value = 90
        effects = rules.resolve_effects(world, state, _accept("alice", "bob", 90))
        rel_eff = next(e for e in effects if isinstance(e, RelationEffect))
        assert rel_eff.value == 100.0

    def test_reject_clamps_at_0(
        self, world: WorldDefinition, rules: NegotiationRules
    ) -> None:
        state = _state_with_three_negotiators()
        for rel in state.relations:
            if rel.source == "alice" and rel.target == "bob":
                rel.value = 5
        effects = rules.resolve_effects(world, state, _reject("alice", "bob"))
        rel_eff = effects[0]
        assert isinstance(rel_eff, RelationEffect)
        # 5 - 10 = -5 → clamp 0
        assert rel_eff.value == 0.0


# =============================================================================
# 4. 端到端 walkthrough
# =============================================================================


def _scripted_alice_provider(*responses: dict) -> MockProvider:
    """构造 alice 的脚本响应序列（按 tick 顺序）。"""
    return MockProvider(scripted_responses=[json.dumps(r) for r in responses])


def _make_runtime(
    world: WorldDefinition, scenario: Scenario, provider: MockProvider
) -> Runtime:
    return Runtime(
        world,
        scenario,
        provider,
        runtime_config=RuntimeConfig(version="0.1", random_seed=42),
        storage_config=StorageConfig(version="0.1", persist=False, runs_root="./runs"),
    )


class TestWalkthrough:
    def test_propose_then_accept_drives_trust_to_70(
        self, world: WorldDefinition, scenario: Scenario
    ) -> None:
        """tick1 alice propose → tick2 alice accept → trust 50→70, max_trust 50→70。"""
        provider = _scripted_alice_provider(
            {"action": "propose", "params": {"target_id": "bob", "price": 90}},
            {"action": "accept", "params": {"offer_from": "bob", "price": 90}},
        )
        with _make_runtime(world, scenario, provider) as rt:
            rt.step()
            rt.step()
            state = rt.get_state()

        assert state.entities["alice"].attributes["max_trust"] == 70.0
        trust_alice_to_bob = next(
            r.value for r in state.relations
            if r.source == "alice" and r.target == "bob"
        )
        assert trust_alice_to_bob == 70.0

    def test_breakpoint_triggers_when_alice_max_trust_reaches_80(
        self, world: WorldDefinition, scenario: Scenario
    ) -> None:
        """alice 连续 accept 让 max_trust 从 50 升到 90 → 触发 breakpoint。

        默认 trust 50；3 次 accept 即可（50→70→90→100，70 后 max=70；
        90 后 max=90 ≥ 80 立即触发）。每次 accept 是不同 tick 的脚本响应。
        """
        provider = _scripted_alice_provider(
            # tick 1: 先 propose（让 bob 有 offer，虽然本场景 rules 不查 inbox）
            {"action": "propose", "params": {"target_id": "bob", "price": 90}},
            # tick 2: accept bob → trust 70, max_trust 70
            {"action": "accept", "params": {"offer_from": "bob", "price": 90}},
            # tick 3: accept bob 又一次 → trust 90, max_trust 90 → 触发 breakpoint
            {"action": "accept", "params": {"offer_from": "bob", "price": 90}},
        )
        with _make_runtime(world, scenario, provider) as rt:
            rt.step()  # tick 1
            r2 = rt.step()  # tick 2
            assert r2.triggered_breakpoints == []
            r3 = rt.step()  # tick 3
            assert r3.triggered_breakpoints == ["alice_high_trust"]
            assert r3.paused_after is True
            assert rt.get_state().entities["alice"].attributes["max_trust"] == 90.0

    def test_offer_message_routed_directly_to_bob(
        self, world: WorldDefinition, scenario: Scenario
    ) -> None:
        """direct 消息：alice 发 offer 给 bob，下一 tick 应只在 bob 的 mailbox 里。"""
        provider = _scripted_alice_provider(
            {"action": "propose", "params": {"target_id": "bob", "price": 90}},
            {"action": "do_nothing", "params": {}},
        )
        with _make_runtime(world, scenario, provider) as rt:
            rt.step()  # tick 1：alice 发 offer
            rt.step()  # tick 2：投递发生在 step 开头
            state = rt.get_state()

        bob_inbox = state.mailboxes.get("bob", [])
        offers_to_bob = [m for m in bob_inbox if m.message_type == "offer"]
        assert len(offers_to_bob) == 1
        assert offers_to_bob[0].payload["from_negotiator"] == "alice"
        # alice / charlie 不应收到（direct，target_id=bob）
        alice_inbox = state.mailboxes.get("alice", [])
        charlie_inbox = state.mailboxes.get("charlie", [])
        assert all(m.message_type != "offer" for m in alice_inbox)
        assert all(m.message_type != "offer" for m in charlie_inbox)

    def test_three_decision_modes_all_active(
        self, world: WorldDefinition, scenario: Scenario
    ) -> None:
        """覆盖证明：3 实体同 tick 决策，分别走 llm / rule / random 三种 mode。"""
        provider = _scripted_alice_provider(
            {"action": "do_nothing", "params": {}},
        )
        with _make_runtime(world, scenario, provider) as rt:
            r = rt.step()

        # 每实体一条 decision_proposed 事件
        proposed = [e for e in r.events if e.kind == "decision_proposed"]
        modes = {e.actor_id: e.payload["decision_mode"] for e in proposed}
        assert modes == {
            "alice": "llm",
            "bob": "rule",
            "charlie": "random",
        }

    def test_scheduled_environment_event_lifts_market_pressure(
        self, world: WorldDefinition, scenario: Scenario
    ) -> None:
        """tick 2 的 scheduled_event 把 market_pressure 50→80。"""
        provider = _scripted_alice_provider(
            {"action": "do_nothing", "params": {}},
            {"action": "do_nothing", "params": {}},
        )
        with _make_runtime(world, scenario, provider) as rt:
            rt.step()  # tick 1
            assert rt.get_state().environment["market_pressure"] == 50
            rt.step()  # tick 2 触发 scheduled_event
            assert rt.get_state().environment["market_pressure"] == 80
