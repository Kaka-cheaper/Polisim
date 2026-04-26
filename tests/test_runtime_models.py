"""runtime_models 的结构校验测试。

对应 `docs/01-requirements/验收标准.md` 第 14 节最小闭环第 2 步"Runtime 骨架"的
**数据模型子项**——tick 主循环 / 事件写入 / 快照生成的前置条件。

本测试只校验 Pydantic 层：

1. 每类模型的最小合法构造
2. ``extra="forbid"`` 阻止未声明字段
3. 所有字段的下限 / 枚举 / 必填约束
4. 可选字段的默认值与默认空容器
5. 嵌套模型的级联校验

不覆盖：

- 跨 World / Scenario 的语义一致性（由 Runtime / Loader 层负责）
- tick 主循环、事件记录顺序、快照触发时机（由 `core/runtime.py` / `core/events.py`）
- 动作效果的计算（由 Rules 层）
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from models.runtime_models import (
    ActionProposal,
    AttributeEffect,
    EntityRuntimeState,
    EnvironmentEffect,
    EventRecord,
    Intervention,
    MessageEffect,
    MessageEnvelope,
    MessageSummary,
    RelationEffect,
    RelationRuntimeState,
    Snapshot,
    TickResult,
    ValidationResult,
    WorldState,
)


# =============================================================================
# MessageEnvelope
# =============================================================================


def test_message_envelope_minimal_in_outbox() -> None:
    """刚发出、未投递的消息：tick_delivered 默认 None，payload 默认空。"""
    env = MessageEnvelope(tick_emitted=3, message_type="policy_signal")
    assert env.tick_emitted == 3
    assert env.tick_delivered is None
    assert env.from_actor is None
    assert env.payload == {}


def test_message_envelope_delivered_and_full_fields() -> None:
    """完整字段：已投递、有发送方、带 payload。"""
    env = MessageEnvelope(
        tick_emitted=3,
        tick_delivered=4,
        message_type="trade",
        from_actor="company_a",
        payload={"price": 100, "qty": 5},
    )
    assert env.tick_delivered == 4
    assert env.from_actor == "company_a"
    assert env.payload["price"] == 100


def test_message_envelope_rejects_zero_tick() -> None:
    """tick_emitted 下限为 1。"""
    with pytest.raises(ValidationError):
        MessageEnvelope(tick_emitted=0, message_type="x")


def test_message_envelope_rejects_zero_tick_delivered() -> None:
    """tick_delivered 若提供，也要 ge=1。"""
    with pytest.raises(ValidationError):
        MessageEnvelope(tick_emitted=1, tick_delivered=0, message_type="x")


def test_message_envelope_rejects_empty_message_type() -> None:
    """message_type 必须非空。"""
    with pytest.raises(ValidationError):
        MessageEnvelope(tick_emitted=1, message_type="")


def test_message_envelope_rejects_extra_field() -> None:
    """extra='forbid'：多余字段被拒。"""
    with pytest.raises(ValidationError):
        MessageEnvelope(
            tick_emitted=1,
            message_type="x",
            unknown_field="oops",  # type: ignore[call-arg]
        )


# =============================================================================
# EntityRuntimeState
# =============================================================================


def test_entity_runtime_state_minimal() -> None:
    """最小合法实体状态：id/type 非空，attributes 默认空。"""
    e = EntityRuntimeState(id="company_a", type="Company")
    assert e.id == "company_a"
    assert e.name is None
    assert e.attributes == {}


def test_entity_runtime_state_full() -> None:
    """完整字段。"""
    e = EntityRuntimeState(
        id="company_a",
        type="Company",
        name="A 公司",
        attributes={"market_share": 27, "cash": 100, "reputation": 65},
    )
    assert e.name == "A 公司"
    assert e.attributes["market_share"] == 27


def test_entity_runtime_state_rejects_empty_id() -> None:
    with pytest.raises(ValidationError):
        EntityRuntimeState(id="", type="Company")


def test_entity_runtime_state_rejects_empty_type() -> None:
    with pytest.raises(ValidationError):
        EntityRuntimeState(id="x", type="")


def test_entity_runtime_state_rejects_extra_field() -> None:
    with pytest.raises(ValidationError):
        EntityRuntimeState(
            id="x", type="Company", mood="happy"  # type: ignore[call-arg]
        )


# =============================================================================
# RelationRuntimeState
# =============================================================================


def test_relation_runtime_state_minimal() -> None:
    """最小合法关系：value 可选。"""
    r = RelationRuntimeState(type="competition", source="a", target="b")
    assert r.value is None


def test_relation_runtime_state_with_value() -> None:
    r = RelationRuntimeState(type="competition", source="a", target="b", value=0.8)
    assert r.value == 0.8


def test_relation_runtime_state_rejects_empty_fields() -> None:
    with pytest.raises(ValidationError):
        RelationRuntimeState(type="", source="a", target="b")
    with pytest.raises(ValidationError):
        RelationRuntimeState(type="x", source="", target="b")
    with pytest.raises(ValidationError):
        RelationRuntimeState(type="x", source="a", target="")


def test_relation_runtime_state_rejects_extra_field() -> None:
    with pytest.raises(ValidationError):
        RelationRuntimeState(
            type="x", source="a", target="b", weight=1.0  # type: ignore[call-arg]
        )


# =============================================================================
# WorldState
# =============================================================================


def test_world_state_initial_tick_zero() -> None:
    """初始状态：tick=0，所有容器默认空。"""
    ws = WorldState(tick=0)
    assert ws.tick == 0
    assert ws.entities == {}
    assert ws.relations == []
    assert ws.environment == {}
    assert ws.mailboxes == {}


def test_world_state_full_construction() -> None:
    """完整字段构造，包含嵌套实体 / 关系 / 收件箱。"""
    ws = WorldState(
        tick=3,
        entities={
            "a": EntityRuntimeState(id="a", type="Company", attributes={"cash": 100}),
            "b": EntityRuntimeState(id="b", type="Company", attributes={"cash": 80}),
        },
        relations=[RelationRuntimeState(type="competition", source="a", target="b")],
        environment={"demand": 55},
        mailboxes={
            "a": [MessageEnvelope(tick_emitted=2, tick_delivered=3, message_type="trade")]
        },
    )
    assert ws.tick == 3
    assert ws.entities["a"].attributes["cash"] == 100
    assert len(ws.mailboxes["a"]) == 1


def test_world_state_rejects_negative_tick() -> None:
    with pytest.raises(ValidationError):
        WorldState(tick=-1)


def test_world_state_rejects_extra_field() -> None:
    with pytest.raises(ValidationError):
        WorldState(tick=0, unknown="x")  # type: ignore[call-arg]


def test_world_state_nested_mailbox_validation_cascades() -> None:
    """mailboxes 内 envelope 非法会触发嵌套校验失败。"""
    with pytest.raises(ValidationError):
        WorldState(
            tick=1,
            mailboxes={"a": [{"tick_emitted": 0, "message_type": "x"}]},  # type: ignore[arg-type]
        )


# =============================================================================
# ActionProposal
# =============================================================================


def test_action_proposal_minimal_llm() -> None:
    """LLM 模式最小提议：params/raw_reasoning_summary 可省略。"""
    p = ActionProposal(
        tick=1,
        actor_id="a",
        action_type="promote",
        decision_mode="llm",
        status="proposed",
    )
    assert p.params == {}
    assert p.raw_reasoning_summary is None


def test_action_proposal_fallback_branch() -> None:
    """降级提议：decision_mode='fallback' + status='fallback'。"""
    p = ActionProposal(
        tick=2,
        actor_id="a",
        action_type="do_nothing",
        decision_mode="fallback",
        status="fallback",
    )
    assert p.decision_mode == "fallback"
    assert p.status == "fallback"


def test_action_proposal_rejects_zero_tick() -> None:
    with pytest.raises(ValidationError):
        ActionProposal(
            tick=0,
            actor_id="a",
            action_type="x",
            decision_mode="llm",
            status="proposed",
        )


def test_action_proposal_rejects_empty_actor_or_action() -> None:
    with pytest.raises(ValidationError):
        ActionProposal(
            tick=1,
            actor_id="",
            action_type="x",
            decision_mode="llm",
            status="proposed",
        )
    with pytest.raises(ValidationError):
        ActionProposal(
            tick=1,
            actor_id="a",
            action_type="",
            decision_mode="llm",
            status="proposed",
        )


def test_action_proposal_rejects_invalid_decision_mode() -> None:
    """decision_mode 必须 ∈ {llm, rule, random, fallback}。"""
    with pytest.raises(ValidationError):
        ActionProposal(
            tick=1,
            actor_id="a",
            action_type="x",
            decision_mode="scripted",  # type: ignore[arg-type]
            status="proposed",
        )


def test_action_proposal_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        ActionProposal(
            tick=1,
            actor_id="a",
            action_type="x",
            decision_mode="llm",
            status="pending",  # type: ignore[arg-type]
        )


def test_action_proposal_rejects_extra_field() -> None:
    with pytest.raises(ValidationError):
        ActionProposal(
            tick=1,
            actor_id="a",
            action_type="x",
            decision_mode="llm",
            status="proposed",
            priority=1,  # type: ignore[call-arg]
        )


# =============================================================================
# EventRecord
# =============================================================================


ALL_EVENT_KINDS = [
    "decision_proposed",
    "decision_rejected",
    "decision_retried",
    "fallback_used",
    "action_executed",
    "message_emitted",
    "relation_changed",
    "environment_changed",
    "scheduled_event_triggered",
    "intervention_applied",
    "breakpoint_triggered",
    "snapshot_saved",
]


@pytest.mark.parametrize("kind", ALL_EVENT_KINDS)
def test_event_record_accepts_all_declared_kinds(kind: str) -> None:
    """设计文档第九节列出的 12 种事件类型全部可构造。"""
    rec = EventRecord(event_id=f"evt_{kind}", tick=1, kind=kind)  # type: ignore[arg-type]
    assert rec.kind == kind


def test_event_record_tick_zero_for_init_event() -> None:
    """初始化事件允许 tick=0。"""
    rec = EventRecord(event_id="evt_init", tick=0, kind="snapshot_saved")
    assert rec.tick == 0
    assert rec.actor_id is None
    assert rec.payload == {}


def test_event_record_full_with_payload_and_actor() -> None:
    rec = EventRecord(
        event_id="evt_0001",
        tick=5,
        kind="action_executed",
        actor_id="company_a",
        payload={
            "action_type": "promote",
            "params": {"budget": 20},
            "effects": {"reputation_delta": 5},
        },
    )
    assert rec.actor_id == "company_a"
    assert rec.payload["action_type"] == "promote"


def test_event_record_rejects_negative_tick() -> None:
    with pytest.raises(ValidationError):
        EventRecord(event_id="x", tick=-1, kind="snapshot_saved")


def test_event_record_rejects_empty_event_id() -> None:
    with pytest.raises(ValidationError):
        EventRecord(event_id="", tick=1, kind="snapshot_saved")


def test_event_record_rejects_unknown_kind() -> None:
    with pytest.raises(ValidationError):
        EventRecord(
            event_id="x", tick=1, kind="custom_kind"  # type: ignore[arg-type]
        )


def test_event_record_rejects_extra_field() -> None:
    with pytest.raises(ValidationError):
        EventRecord(
            event_id="x", tick=1, kind="snapshot_saved", priority=1  # type: ignore[call-arg]
        )


# =============================================================================
# MessageSummary
# =============================================================================


def test_message_summary_defaults_zero() -> None:
    ms = MessageSummary()
    assert ms.emitted == 0
    assert ms.delivered_next_tick == 0


def test_message_summary_rejects_negative() -> None:
    with pytest.raises(ValidationError):
        MessageSummary(emitted=-1)
    with pytest.raises(ValidationError):
        MessageSummary(delivered_next_tick=-1)


def test_message_summary_rejects_extra_field() -> None:
    with pytest.raises(ValidationError):
        MessageSummary(emitted=1, pending=2)  # type: ignore[call-arg]


# =============================================================================
# Snapshot
# =============================================================================


def test_snapshot_initial_tick_zero() -> None:
    """tick=0 的初始快照，所有子字段默认空/零。"""
    snap = Snapshot(tick=0)
    assert snap.tick == 0
    assert snap.entity_state_summary == {}
    assert snap.relation_state_summary == []
    assert snap.environment_state == {}
    assert snap.message_summary.emitted == 0
    assert snap.message_summary.delivered_next_tick == 0


def test_snapshot_full_matches_design_example() -> None:
    """对齐 `运行时与事件轨迹设计.md` 第十一节示例结构。"""
    snap = Snapshot(
        tick=5,
        entity_state_summary={
            "company_a": {"market_share": 27, "cash": 100, "reputation": 65},
        },
        relation_state_summary=[
            {"type": "competition", "source": "company_a", "target": "company_b", "value": 1.0},
        ],
        environment_state={"market_demand": 55, "public_sentiment": 8},
        message_summary=MessageSummary(emitted=3, delivered_next_tick=3),
    )
    assert snap.entity_state_summary["company_a"]["market_share"] == 27
    assert snap.message_summary.emitted == 3


def test_snapshot_rejects_negative_tick() -> None:
    with pytest.raises(ValidationError):
        Snapshot(tick=-1)


def test_snapshot_rejects_extra_field() -> None:
    with pytest.raises(ValidationError):
        Snapshot(tick=0, extra_field=1)  # type: ignore[call-arg]


def test_snapshot_message_summary_nested_validation() -> None:
    """嵌套 MessageSummary 的负数会触发级联校验失败。"""
    with pytest.raises(ValidationError):
        Snapshot(tick=1, message_summary={"emitted": -1, "delivered_next_tick": 0})  # type: ignore[arg-type]


# =============================================================================
# Intervention（D-008 副产物，对齐需求分析 8.3）
# =============================================================================


def test_intervention_inject_message_minimal() -> None:
    """inject_message：广播时 target_actor 可省。"""
    iv = Intervention(
        tick=3,
        kind="inject_message",
        message={"message_type": "policy_signal", "payload": {"strength": 80}},
    )
    assert iv.kind == "inject_message"
    assert iv.target_actor is None
    assert iv.reason is None


def test_intervention_inject_message_to_specific_actor() -> None:
    iv = Intervention(
        tick=3,
        kind="inject_message",
        target_actor="company_a",
        message={"message_type": "hint", "payload": {"text": "小心"}},
        reason="用户手动提示",
    )
    assert iv.target_actor == "company_a"
    assert iv.reason == "用户手动提示"


def test_intervention_force_action_full() -> None:
    iv = Intervention(
        tick=5,
        kind="force_action",
        target_actor="company_b",
        action={"action_type": "do_nothing", "params": {}},
    )
    assert iv.action["action_type"] == "do_nothing"


def test_intervention_override_attribute_full() -> None:
    iv = Intervention(
        tick=5,
        kind="override_attribute",
        target_actor="company_a",
        attribute_changes={"cash": 200, "reputation": 80},
    )
    assert iv.attribute_changes["cash"] == 200


def test_intervention_inject_message_missing_message_rejected() -> None:
    """kind='inject_message' 但未提供 message：model_validator 拒绝。"""
    with pytest.raises(ValidationError):
        Intervention(tick=1, kind="inject_message")


def test_intervention_force_action_missing_action_rejected() -> None:
    with pytest.raises(ValidationError):
        Intervention(tick=1, kind="force_action", target_actor="a")


def test_intervention_force_action_missing_target_rejected() -> None:
    """force_action 必须提供 target_actor。"""
    with pytest.raises(ValidationError):
        Intervention(
            tick=1,
            kind="force_action",
            action={"action_type": "x", "params": {}},
        )


def test_intervention_override_attribute_missing_changes_rejected() -> None:
    with pytest.raises(ValidationError):
        Intervention(tick=1, kind="override_attribute", target_actor="a")


def test_intervention_override_attribute_missing_target_rejected() -> None:
    with pytest.raises(ValidationError):
        Intervention(
            tick=1, kind="override_attribute", attribute_changes={"cash": 0}
        )


def test_intervention_rejects_zero_tick() -> None:
    with pytest.raises(ValidationError):
        Intervention(
            tick=0,
            kind="inject_message",
            message={"message_type": "x", "payload": {}},
        )


def test_intervention_rejects_unknown_kind() -> None:
    with pytest.raises(ValidationError):
        Intervention(tick=1, kind="teleport")  # type: ignore[arg-type]


def test_intervention_rejects_extra_field() -> None:
    with pytest.raises(ValidationError):
        Intervention(
            tick=1,
            kind="inject_message",
            message={"message_type": "x", "payload": {}},
            priority=1,  # type: ignore[call-arg]
        )


# =============================================================================
# Effect 子类（D-009 路线 1）
# =============================================================================


def test_attribute_effect_minimal() -> None:
    eff = AttributeEffect(actor_id="company_a", attribute="cash", delta=-20)
    assert eff.kind == "self_attribute"
    assert eff.delta == -20


def test_attribute_effect_rejects_empty_fields() -> None:
    with pytest.raises(ValidationError):
        AttributeEffect(actor_id="", attribute="cash", delta=1)
    with pytest.raises(ValidationError):
        AttributeEffect(actor_id="a", attribute="", delta=1)


def test_attribute_effect_rejects_extra_field() -> None:
    with pytest.raises(ValidationError):
        AttributeEffect(
            actor_id="a", attribute="x", delta=1, priority=1  # type: ignore[call-arg]
        )


def test_relation_effect_add_and_update_require_value() -> None:
    # 合法：add/update_value + value
    RelationEffect(
        operation="add", relation_type="alliance", source="a", target="b", value=1.0
    )
    RelationEffect(
        operation="update_value",
        relation_type="competition",
        source="a",
        target="b",
        value=0.8,
    )

    # 不合法：add/update_value 无 value
    with pytest.raises(ValidationError, match="必须提供 value"):
        RelationEffect(
            operation="add", relation_type="alliance", source="a", target="b"
        )
    with pytest.raises(ValidationError, match="必须提供 value"):
        RelationEffect(
            operation="update_value",
            relation_type="competition",
            source="a",
            target="b",
        )


def test_relation_effect_remove_accepts_no_value() -> None:
    eff = RelationEffect(
        operation="remove", relation_type="alliance", source="a", target="b"
    )
    assert eff.value is None


def test_relation_effect_rejects_unknown_operation() -> None:
    with pytest.raises(ValidationError):
        RelationEffect(
            operation="swap",  # type: ignore[arg-type]
            relation_type="x",
            source="a",
            target="b",
            value=1.0,
        )


def test_message_effect_wraps_envelope() -> None:
    env = MessageEnvelope(
        tick_emitted=3, message_type="policy_signal", payload={"strength": 80}
    )
    eff = MessageEffect(envelope=env)
    assert eff.kind == "message"
    assert eff.envelope.tick_emitted == 3


def test_message_effect_rejects_invalid_envelope() -> None:
    """嵌套 envelope 的非法字段会触发级联 ValidationError。"""
    with pytest.raises(ValidationError):
        MessageEffect(envelope={"tick_emitted": 0, "message_type": "x"})  # type: ignore[arg-type]


def test_environment_effect_minimal() -> None:
    eff = EnvironmentEffect(variable="market_demand", delta=5.0)
    assert eff.kind == "environment"
    assert eff.delta == 5.0


def test_environment_effect_rejects_empty_variable() -> None:
    with pytest.raises(ValidationError):
        EnvironmentEffect(variable="", delta=1.0)


# =============================================================================
# ValidationResult
# =============================================================================


def test_validation_result_valid_with_empty_errors() -> None:
    vr = ValidationResult(valid=True)
    assert vr.valid is True
    assert vr.errors == []


def test_validation_result_invalid_with_errors() -> None:
    vr = ValidationResult(
        valid=False,
        errors=["参数 budget 缺失", "actor 类型不匹配"],
    )
    assert vr.valid is False
    assert len(vr.errors) == 2


def test_validation_result_rejects_extra_field() -> None:
    with pytest.raises(ValidationError):
        ValidationResult(valid=True, code=200)  # type: ignore[call-arg]


# =============================================================================
# TickResult（D-008 Runtime.step() 的返回对象）
# =============================================================================


def test_tick_result_minimal() -> None:
    tr = TickResult(tick=1)
    assert tr.tick == 1
    assert tr.events == []
    assert tr.snapshot is None
    assert tr.paused_after is False
    assert tr.triggered_breakpoints == []
    assert tr.reached_total_ticks is False


def test_tick_result_full_fields() -> None:
    ev = EventRecord(event_id="e1", tick=1, kind="action_executed", actor_id="a")
    snap = Snapshot(tick=1, entity_state_summary={"a": {"cash": 80}})
    tr = TickResult(
        tick=1,
        events=[ev],
        snapshot=snap,
        paused_after=True,
        triggered_breakpoints=["bp_alpha"],
        reached_total_ticks=True,
    )
    assert len(tr.events) == 1
    assert tr.snapshot is snap
    assert tr.paused_after is True
    assert tr.triggered_breakpoints == ["bp_alpha"]
    assert tr.reached_total_ticks is True


def test_tick_result_rejects_zero_tick() -> None:
    """tick 必须从 1 起；tick=0 是初始化状态，不是 step() 的结果。"""
    with pytest.raises(ValidationError):
        TickResult(tick=0)


def test_tick_result_rejects_extra_field() -> None:
    with pytest.raises(ValidationError):
        TickResult(tick=1, duration_ms=100)  # type: ignore[call-arg]
