"""BaseRules 通用实现测试（D-009 路线 1）。

对应 `docs/02-design/规则层设计.md` 全章、`docs/01-requirements/验收标准.md`
7.1（动作合法性验收）/ 7.2（效果映射验收）。

覆盖：

1. BaseRules 抽象契约——未实现 `resolve_effects` 的子类不可实例化
2. `validate_action` 各维度校验路径 + 多错误一次性聚合
3. `apply_constraints` 对数值属性 / 环境变量的 clamp，对关系 / 消息的透传
4. `resolve_conflicts` 三种策略（both / priority / random）+ seed 可复现 +
   未知策略的防御式退化
5. 反向测试：`_conflict_key` 对关系 / 消息返回 None，不触发冲突合并

不覆盖：

- `resolve_effects`——抽象，留给具体世界测试（如 `test_rules_minimal_market.py`）
- Runtime 层如何调用规则——属 `test_runtime.py`
- 合法 world / scenario 的 loader 校验——已在 `test_definition_loader.py` 等覆盖
"""

from __future__ import annotations

import pytest

from models.runtime_models import (
    ActionProposal,
    AttributeEffect,
    EntityRuntimeState,
    EnvironmentEffect,
    MessageEffect,
    MessageEnvelope,
    RelationEffect,
    WorldState,
)
from models.world_models import WorldDefinition
from rules.base import BaseRules


# =============================================================================
# 测试用的最小可实例化子类
# =============================================================================


class _NoOpRules(BaseRules):
    """测试 fixture：resolve_effects 返回空列表，其他方法走 BaseRules 默认实现。"""

    def resolve_effects(self, world, state, proposal):  # type: ignore[override]
        return []


# =============================================================================
# 测试用的最小 WorldDefinition / WorldState 构造
# =============================================================================


def _make_world() -> WorldDefinition:
    """构造一个最小但结构完整的 world：一个 Company 类型 + promote/do_nothing 动作。"""
    return WorldDefinition.model_validate(
        {
            "version": "0.1",
            "world": {"id": "test-world", "name": "Test World"},
            "entity_types": {
                "Company": {
                    "decision_mode": "llm",
                    "attributes": {
                        "cash": {"type": "number", "min": 0, "max": 200, "default": 100},
                        "reputation": {
                            "type": "number",
                            "min": 0,
                            "max": 100,
                            "default": 50,
                        },
                        "strategy": {
                            "type": "enum",
                            "values": ["aggressive", "balanced"],
                            "default": "balanced",
                        },
                    },
                    "actions": ["promote", "do_nothing"],
                },
                "Regulator": {
                    "decision_mode": "rule",
                    "attributes": {
                        "strictness": {"type": "number", "min": 0, "max": 100, "default": 50}
                    },
                    "actions": ["do_nothing"],
                },
            },
            "action_types": {
                "promote": {
                    "actor_types": ["Company"],
                    "params": {
                        "budget": {"type": "number", "required": True},
                        "channel": {"type": "string", "required": False},
                    },
                    "effects": [{"kind": "self_attribute"}],
                },
                "do_nothing": {
                    "actor_types": ["Company", "Regulator"],
                    "params": {},
                    "effects": [],
                },
            },
            "environment": {
                "variables": {
                    "demand": {"type": "number", "min": 0, "max": 100, "default": 50},
                    "unbounded_var": {"type": "number", "default": 0},
                }
            },
            "defaults": {
                "conflict_resolution": "both",
                "action_effect_order": ["self_attribute", "relation", "environment", "message"],
            },
        }
    )


def _make_state() -> WorldState:
    return WorldState(
        tick=1,
        entities={
            "company_a": EntityRuntimeState(
                id="company_a",
                type="Company",
                attributes={"cash": 100, "reputation": 50, "strategy": "balanced"},
            ),
            "company_b": EntityRuntimeState(
                id="company_b",
                type="Company",
                attributes={"cash": 80, "reputation": 40, "strategy": "aggressive"},
            ),
            "regulator": EntityRuntimeState(
                id="regulator",
                type="Regulator",
                attributes={"strictness": 50},
            ),
        },
        environment={"demand": 50, "unbounded_var": 1000},
    )


def _proposal(
    actor_id: str = "company_a",
    action_type: str = "promote",
    params: dict | None = None,
) -> ActionProposal:
    return ActionProposal(
        tick=1,
        actor_id=actor_id,
        action_type=action_type,
        params=params if params is not None else {"budget": 20},
        decision_mode="llm",
        status="proposed",
    )


# =============================================================================
# 抽象契约
# =============================================================================


def test_base_rules_cannot_be_instantiated_directly() -> None:
    """BaseRules 直接实例化应抛 TypeError（缺少 resolve_effects）。"""
    with pytest.raises(TypeError):
        BaseRules()  # type: ignore[abstract]


def test_subclass_without_resolve_effects_cannot_instantiate() -> None:
    class _Incomplete(BaseRules):
        pass

    with pytest.raises(TypeError):
        _Incomplete()  # type: ignore[abstract]


def test_subclass_with_resolve_effects_instantiates_and_runs() -> None:
    rules = _NoOpRules()
    world = _make_world()
    state = _make_state()
    assert rules.resolve_effects(world, state, _proposal()) == []


# =============================================================================
# validate_action
# =============================================================================


def test_validate_action_happy_path() -> None:
    rules = _NoOpRules()
    result = rules.validate_action(_make_world(), _make_state(), _proposal())
    assert result.valid is True
    assert result.errors == []


def test_validate_action_rejects_unknown_action_type() -> None:
    rules = _NoOpRules()
    result = rules.validate_action(
        _make_world(),
        _make_state(),
        _proposal(action_type="unknown_action"),
    )
    assert result.valid is False
    assert any("未在 World Definition 中声明" in e for e in result.errors)


def test_validate_action_short_circuits_on_unknown_action() -> None:
    """未知 action_type 时短路：不再报其他错（后续校验依赖 action_schema）。"""
    rules = _NoOpRules()
    # 给一个完全错的提议：未知动作 + 未知实体
    result = rules.validate_action(
        _make_world(),
        _make_state(),
        _proposal(
            actor_id="ghost_entity",
            action_type="unknown",
            params={"random_param": "x"},
        ),
    )
    # 只应该有 1 条错误
    assert result.valid is False
    assert len(result.errors) == 1


def test_validate_action_rejects_unknown_actor() -> None:
    rules = _NoOpRules()
    result = rules.validate_action(
        _make_world(),
        _make_state(),
        _proposal(actor_id="ghost_entity"),
    )
    assert result.valid is False
    assert any("未在当前世界状态中" in e for e in result.errors)


def test_validate_action_rejects_actor_type_mismatch() -> None:
    """Regulator 不在 promote.actor_types 中，应被拒。"""
    rules = _NoOpRules()
    result = rules.validate_action(
        _make_world(),
        _make_state(),
        _proposal(actor_id="regulator", action_type="promote"),
    )
    assert result.valid is False
    assert any("不在动作" in e and "actor_types" in e for e in result.errors)


def test_validate_action_rejects_missing_required_param() -> None:
    rules = _NoOpRules()
    result = rules.validate_action(
        _make_world(),
        _make_state(),
        _proposal(params={}),  # budget 缺失
    )
    assert result.valid is False
    assert any("必填参数 'budget' 缺失" in e for e in result.errors)


def test_validate_action_rejects_undeclared_param() -> None:
    rules = _NoOpRules()
    result = rules.validate_action(
        _make_world(),
        _make_state(),
        _proposal(params={"budget": 20, "mystery": "x"}),
    )
    assert result.valid is False
    assert any("'mystery' 未在动作" in e for e in result.errors)


def test_validate_action_rejects_wrong_param_type_number() -> None:
    rules = _NoOpRules()
    result = rules.validate_action(
        _make_world(),
        _make_state(),
        _proposal(params={"budget": "twenty"}),  # string instead of number
    )
    assert result.valid is False
    assert any("类型不匹配" in e for e in result.errors)


def test_validate_action_rejects_bool_as_number() -> None:
    """Python bool 是 int 子类，但 number 校验必须拒绝 bool。"""
    rules = _NoOpRules()
    result = rules.validate_action(
        _make_world(),
        _make_state(),
        _proposal(params={"budget": True}),
    )
    assert result.valid is False
    assert any("类型不匹配" in e for e in result.errors)


def test_validate_action_accepts_int_and_float_as_number() -> None:
    rules = _NoOpRules()
    r1 = rules.validate_action(
        _make_world(), _make_state(), _proposal(params={"budget": 20})
    )
    r2 = rules.validate_action(
        _make_world(), _make_state(), _proposal(params={"budget": 20.5})
    )
    assert r1.valid and r2.valid


def test_validate_action_accepts_missing_optional_param() -> None:
    """channel 是 optional（required=False），缺失应通过。"""
    rules = _NoOpRules()
    result = rules.validate_action(
        _make_world(),
        _make_state(),
        _proposal(params={"budget": 20}),
    )
    assert result.valid is True


def test_validate_action_aggregates_multiple_errors() -> None:
    """多错一次性返回，不短路（只有 action_type 未知才短路）。"""
    rules = _NoOpRules()
    result = rules.validate_action(
        _make_world(),
        _make_state(),
        _proposal(
            actor_id="regulator",  # 类型不匹配
            params={"mystery": "x"},  # 未声明参数 + 缺 budget
        ),
    )
    assert result.valid is False
    assert len(result.errors) >= 3  # actor type + missing budget + undeclared mystery


# =============================================================================
# apply_constraints
# =============================================================================


def test_apply_constraints_in_range_passthrough() -> None:
    rules = _NoOpRules()
    eff = AttributeEffect(actor_id="company_a", attribute="reputation", delta=10)
    [out] = rules.apply_constraints(_make_world(), _make_state(), [eff])
    # current=50, delta=10 → target=60，在 [0,100] 内，不变
    assert out is eff


def test_apply_constraints_clamps_at_max() -> None:
    rules = _NoOpRules()
    eff = AttributeEffect(actor_id="company_a", attribute="reputation", delta=80)
    [out] = rules.apply_constraints(_make_world(), _make_state(), [eff])
    # current=50, delta=80 → target=130 → clamp 到 100 → delta 应为 50
    assert isinstance(out, AttributeEffect)
    assert out.delta == 50


def test_apply_constraints_clamps_at_min() -> None:
    rules = _NoOpRules()
    eff = AttributeEffect(actor_id="company_a", attribute="cash", delta=-150)
    [out] = rules.apply_constraints(_make_world(), _make_state(), [eff])
    # current=100, delta=-150 → target=-50 → clamp 到 0 → delta 应为 -100
    assert out.delta == -100


def test_apply_constraints_unknown_actor_passthrough() -> None:
    rules = _NoOpRules()
    eff = AttributeEffect(actor_id="ghost", attribute="cash", delta=-1000)
    [out] = rules.apply_constraints(_make_world(), _make_state(), [eff])
    # 未知 actor：原样透传（留给 Runtime 处理）
    assert out is eff


def test_apply_constraints_unknown_attribute_passthrough() -> None:
    rules = _NoOpRules()
    eff = AttributeEffect(actor_id="company_a", attribute="unknown_attr", delta=999)
    [out] = rules.apply_constraints(_make_world(), _make_state(), [eff])
    assert out is eff


def test_apply_constraints_non_numeric_attribute_passthrough() -> None:
    """对 enum 类属性施加 delta 无意义——透传（不应尝试 clamp）。"""
    rules = _NoOpRules()
    eff = AttributeEffect(actor_id="company_a", attribute="strategy", delta=1)
    [out] = rules.apply_constraints(_make_world(), _make_state(), [eff])
    assert out is eff


def test_apply_constraints_environment_clamp() -> None:
    rules = _NoOpRules()
    eff = EnvironmentEffect(variable="demand", delta=80)
    # current=50, delta=80 → target=130 → clamp 到 100 → delta=50
    [out] = rules.apply_constraints(_make_world(), _make_state(), [eff])
    assert isinstance(out, EnvironmentEffect)
    assert out.delta == 50


def test_apply_constraints_environment_unbounded_passthrough() -> None:
    """无 min/max 的环境变量不裁剪。"""
    rules = _NoOpRules()
    eff = EnvironmentEffect(variable="unbounded_var", delta=99999)
    [out] = rules.apply_constraints(_make_world(), _make_state(), [eff])
    assert out is eff


def test_apply_constraints_relation_and_message_passthrough() -> None:
    rules = _NoOpRules()
    rel = RelationEffect(
        operation="add",
        relation_type="alliance",
        source="company_a",
        target="company_b",
        value=1.0,
    )
    msg = MessageEffect(
        envelope=MessageEnvelope(tick_emitted=1, message_type="policy_signal")
    )
    out = rules.apply_constraints(_make_world(), _make_state(), [rel, msg])
    assert out[0] is rel
    assert out[1] is msg


def test_apply_constraints_returns_new_list() -> None:
    rules = _NoOpRules()
    inp = [AttributeEffect(actor_id="company_a", attribute="cash", delta=0)]
    out = rules.apply_constraints(_make_world(), _make_state(), inp)
    assert out is not inp


def test_apply_constraints_mixed_batch() -> None:
    rules = _NoOpRules()
    effects = [
        AttributeEffect(actor_id="company_a", attribute="reputation", delta=200),  # clamp
        AttributeEffect(actor_id="company_a", attribute="reputation", delta=5),  # ok
        EnvironmentEffect(variable="demand", delta=-70),  # clamp
    ]
    out = rules.apply_constraints(_make_world(), _make_state(), effects)
    assert out[0].delta == 50  # 200 clamped to 50
    assert out[1] is effects[1]  # in range, passthrough
    assert out[2].delta == -50  # demand 50 - 50 = 0


# =============================================================================
# resolve_conflicts
# =============================================================================


def _world_with_strategy(strategy: str) -> WorldDefinition:
    world = _make_world()
    # 直接改 defaults 字段
    assert world.defaults is not None
    world.defaults.conflict_resolution = strategy  # type: ignore[assignment]
    return world


def test_resolve_conflicts_both_concatenates_all() -> None:
    rules = _NoOpRules()
    world = _world_with_strategy("both")
    # 两个 actor 对同一 (actor=company_a, attribute=cash) 写不同 delta
    e1 = AttributeEffect(actor_id="company_a", attribute="cash", delta=-20)
    e2 = AttributeEffect(actor_id="company_a", attribute="cash", delta=+10)
    out = rules.resolve_conflicts(world, _make_state(), [[e1], [e2]])
    assert out == [e1, e2]  # 都保留


def test_resolve_conflicts_priority_first_wins() -> None:
    rules = _NoOpRules()
    world = _world_with_strategy("priority")
    e1 = AttributeEffect(actor_id="company_a", attribute="cash", delta=-20)
    e2 = AttributeEffect(actor_id="company_a", attribute="cash", delta=+10)
    out = rules.resolve_conflicts(world, _make_state(), [[e1], [e2]])
    assert out == [e1]  # 第一个胜出


def test_resolve_conflicts_random_deterministic_with_seed() -> None:
    """同 seed 两次执行必须给出相同结果。"""
    world = _world_with_strategy("random")
    e1 = AttributeEffect(actor_id="company_a", attribute="cash", delta=-20)
    e2 = AttributeEffect(actor_id="company_a", attribute="cash", delta=+10)

    rules_a = _NoOpRules(random_seed=42)
    out_a = rules_a.resolve_conflicts(world, _make_state(), [[e1], [e2]])

    rules_b = _NoOpRules(random_seed=42)
    out_b = rules_b.resolve_conflicts(world, _make_state(), [[e1], [e2]])

    assert out_a == out_b
    assert len(out_a) == 1
    assert out_a[0] in (e1, e2)


def test_resolve_conflicts_non_conflicting_always_kept() -> None:
    """不同 (actor, attribute) 不视为冲突，三种策略下都保留。"""
    rules = _NoOpRules(random_seed=42)
    e1 = AttributeEffect(actor_id="company_a", attribute="cash", delta=-20)
    e2 = AttributeEffect(actor_id="company_b", attribute="cash", delta=-10)
    for strategy in ("both", "priority", "random"):
        world = _world_with_strategy(strategy)
        out = rules.resolve_conflicts(world, _make_state(), [[e1], [e2]])
        assert len(out) == 2
        # Pydantic 模型默认不可 hash，用成员检测代替 set 比较
        assert e1 in out
        assert e2 in out


def test_resolve_conflicts_environment_variable_same_key_priority() -> None:
    rules = _NoOpRules()
    world = _world_with_strategy("priority")
    e1 = EnvironmentEffect(variable="demand", delta=5)
    e2 = EnvironmentEffect(variable="demand", delta=-3)
    out = rules.resolve_conflicts(world, _make_state(), [[e1], [e2]])
    assert out == [e1]


def test_resolve_conflicts_relation_and_message_never_conflict() -> None:
    """v1 不做关系 / 消息冲突检测——即使 priority 策略下也都保留。"""
    rules = _NoOpRules()
    world = _world_with_strategy("priority")
    r1 = RelationEffect(
        operation="add",
        relation_type="alliance",
        source="company_a",
        target="company_b",
        value=1.0,
    )
    r2 = RelationEffect(
        operation="add",
        relation_type="alliance",
        source="company_a",
        target="company_b",
        value=0.5,
    )
    m1 = MessageEffect(
        envelope=MessageEnvelope(tick_emitted=1, message_type="policy_signal")
    )
    m2 = MessageEffect(
        envelope=MessageEnvelope(tick_emitted=1, message_type="policy_signal")
    )
    out = rules.resolve_conflicts(world, _make_state(), [[r1, m1], [r2, m2]])
    assert len(out) == 4  # 全部保留


def test_resolve_conflicts_defaults_none_treats_as_both() -> None:
    """world.defaults 为 None 时默认 both 策略。"""
    rules = _NoOpRules()
    world = _make_world()
    world.defaults = None  # type: ignore[assignment]
    e1 = AttributeEffect(actor_id="company_a", attribute="cash", delta=-20)
    e2 = AttributeEffect(actor_id="company_a", attribute="cash", delta=+10)
    out = rules.resolve_conflicts(world, _make_state(), [[e1], [e2]])
    assert out == [e1, e2]


def test_resolve_conflicts_empty_input() -> None:
    rules = _NoOpRules()
    world = _world_with_strategy("priority")
    assert rules.resolve_conflicts(world, _make_state(), []) == []
    assert rules.resolve_conflicts(world, _make_state(), [[], []]) == []


def test_resolve_conflicts_preserves_order_of_non_conflicting() -> None:
    """non_conflicting 按 insertion 顺序排在 resolved 的前面，conflicting 随后。"""
    rules = _NoOpRules()
    world = _world_with_strategy("priority")
    e_rel = RelationEffect(
        operation="add",
        relation_type="alliance",
        source="company_a",
        target="company_b",
        value=1.0,
    )
    e_attr1 = AttributeEffect(actor_id="company_a", attribute="cash", delta=-20)
    e_attr2 = AttributeEffect(actor_id="company_a", attribute="cash", delta=+10)
    out = rules.resolve_conflicts(world, _make_state(), [[e_rel, e_attr1], [e_attr2]])
    # 关系不冲突 → 先出现；属性冲突 priority → 保留第一个
    assert len(out) == 2
    assert e_rel in out
    assert e_attr1 in out
    assert e_attr2 not in out
