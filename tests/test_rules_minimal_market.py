"""Walkthrough 最小市场规则测试（D-009 路线 1 的具体兑现）。

对应：

- `docs/01-requirements/最小示例Walkthrough.md` 全文
- `docs/01-requirements/验收标准.md` 7.1 / 7.2 + 14 节最小闭环的"规则层 + 场景加载"部分
- D-009 路线 1："接口通用（base）+ 公式插件化（minimal_market）"

覆盖：

1. `scenarios/minimal_market/world.yaml` 通过 `load_world_definition` 加载
2. `scenarios/minimal_market/scenario.yaml` 通过 `load_scenario` 加载且与 world 一致
3. `MinimalMarketRules` 可实例化，继承自 `BaseRules`
4. `resolve_effects` 对 `promote(budget=B)` 映射为 `cash -B` + `reputation +5`
5. `resolve_effects` 对 `do_nothing` 映射为空列表
6. `validate_action` 在 `cash >= budget` 时通过
7. `validate_action` 在 `cash < budget` 时拒绝并给出可读错误
8. `validate_action` 仍然透传 `BaseRules` 的基础校验（未知动作、缺必填参数等）
9. **端到端**：真实 world + scenario + rules，validate → resolve → apply_constraints 全部跑通

不覆盖：

- Runtime 主循环（留给 `test_runtime.py`）
- LLM 决策协议（留给 `test_llm_policy.py`）
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.definition_loader import load_world_definition
from core.scenario_loader import load_scenario
from models.runtime_models import (
    ActionProposal,
    AttributeEffect,
    EntityRuntimeState,
    WorldState,
)
from rules.base import BaseRules
from rules.minimal_market import MinimalMarketRules


# =============================================================================
# 固定资源：walkthrough 真实 YAML 路径
# =============================================================================


_SCENARIO_DIR = Path(__file__).resolve().parents[1] / "scenarios" / "minimal_market"
_WORLD_YAML = _SCENARIO_DIR / "world.yaml"
_SCENARIO_YAML = _SCENARIO_DIR / "scenario.yaml"


# =============================================================================
# fixtures
# =============================================================================


@pytest.fixture(scope="module")
def world():
    """加载 walkthrough 的 world.yaml。此 fixture 同时验证 YAML 通过 loader。"""
    return load_world_definition(_WORLD_YAML)


@pytest.fixture(scope="module")
def scenario(world):
    """加载 walkthrough 的 scenario.yaml；依赖 world 做跨文件校验。"""
    return load_scenario(_SCENARIO_YAML, world)


@pytest.fixture
def state_initial(world, scenario) -> WorldState:
    """按 scenario 构造一个 tick=0 的初始 WorldState（简化版——不经 Runtime 真实 bootstrap）。"""
    entities = {}
    for ent in scenario.entities:
        entity_type = world.entity_types[ent.type]
        merged_attrs: dict = {}
        # 先填默认值
        for attr_name, attr_schema in entity_type.attributes.items():
            merged_attrs[attr_name] = attr_schema.default
        # 再用 scenario 的覆盖值
        merged_attrs.update(ent.attributes)
        entities[ent.id] = EntityRuntimeState(
            id=ent.id,
            type=ent.type,
            name=ent.name,
            attributes=merged_attrs,
        )
    return WorldState(tick=0, entities=entities, environment=dict(scenario.environment))


def _proposal(
    actor_id: str = "company_a",
    action_type: str = "promote",
    params: dict | None = None,
    tick: int = 1,
) -> ActionProposal:
    return ActionProposal(
        tick=tick,
        actor_id=actor_id,
        action_type=action_type,
        params=params if params is not None else {"budget": 20},
        decision_mode="llm",
        status="proposed",
    )


# =============================================================================
# YAML 加载：walkthrough 的 world + scenario 可被 loader 接受
# =============================================================================


def test_world_yaml_loads_with_expected_shape(world) -> None:
    assert world.world.id == "minimal-market"
    assert set(world.entity_types.keys()) == {"Company", "Regulator"}
    assert set(world.action_types.keys()) == {"promote", "do_nothing"}
    # Company 的 decision_mode 是 llm（对齐 walkthrough 第六节）
    assert world.entity_types["Company"].decision_mode == "llm"
    # promote 有必填 budget 参数
    assert world.action_types["promote"].params["budget"].required is True
    # policy_signal 消息类型存在（供 scheduled_event 使用）
    assert world.message_types is not None
    assert "policy_signal" in world.message_types
    # policy_pressure 环境变量存在
    assert world.environment is not None
    assert "policy_pressure" in world.environment.variables


def test_scenario_yaml_loads_with_expected_shape(scenario) -> None:
    assert scenario.world_id == "minimal-market"
    assert scenario.scenario.id == "walkthrough-min"
    # D-010：scenario.yaml 声明了 rules_module，指向本模块的 MinimalMarketRules
    assert scenario.rules_module == "rules.minimal_market:MinimalMarketRules"
    assert len(scenario.entities) == 2
    entity_ids = {e.id for e in scenario.entities}
    assert entity_ids == {"company_a", "regulator_main"}
    assert scenario.config.total_ticks == 5
    assert scenario.environment == {"policy_pressure": 20}
    # tick=2 的 scheduled event 存在
    events_at_tick_2 = [e for e in scenario.scheduled_events if e.tick == 2]
    assert len(events_at_tick_2) == 1
    assert events_at_tick_2[0].type == "message_injection"


def test_scenario_yaml_rules_module_resolves_via_rules_loader(scenario) -> None:
    """端到端：从 scenario.yaml 读取 rules_module → load_rules_class → 实例化 →
    与直接 import 的 MinimalMarketRules 等价（D-010 完整链路验证）。"""
    from core.rules_loader import load_rules_class
    from rules.minimal_market import MinimalMarketRules

    assert scenario.rules_module is not None
    cls = load_rules_class(scenario.rules_module)
    assert cls is MinimalMarketRules
    # 可实例化（不是抽象）
    assert isinstance(cls(), MinimalMarketRules)


# =============================================================================
# MinimalMarketRules：基本契约
# =============================================================================


def test_minimal_market_rules_is_base_rules_subclass() -> None:
    rules = MinimalMarketRules()
    assert isinstance(rules, BaseRules)


def test_minimal_market_rules_accepts_random_seed() -> None:
    # 与 BaseRules 构造签名一致（为未来 Runtime 注入 seed 预留）
    rules = MinimalMarketRules(random_seed=42)
    assert isinstance(rules, BaseRules)


# =============================================================================
# resolve_effects：公式映射
# =============================================================================


def test_resolve_effects_promote_produces_cash_and_reputation_deltas(
    world, state_initial
) -> None:
    rules = MinimalMarketRules()
    effects = rules.resolve_effects(
        world, state_initial, _proposal(params={"budget": 20})
    )
    assert len(effects) == 2
    # 都是 AttributeEffect
    assert all(isinstance(e, AttributeEffect) for e in effects)
    # 分别对应 cash 与 reputation
    by_attr = {e.attribute: e for e in effects}
    assert by_attr["cash"].delta == -20.0
    assert by_attr["reputation"].delta == 5.0
    assert by_attr["cash"].actor_id == "company_a"


def test_resolve_effects_promote_scales_with_budget(world, state_initial) -> None:
    rules = MinimalMarketRules()
    effects_small = rules.resolve_effects(
        world, state_initial, _proposal(params={"budget": 5})
    )
    effects_large = rules.resolve_effects(
        world, state_initial, _proposal(params={"budget": 80})
    )
    cash_small = next(e for e in effects_small if e.attribute == "cash")
    cash_large = next(e for e in effects_large if e.attribute == "cash")
    assert cash_small.delta == -5.0
    assert cash_large.delta == -80.0


def test_resolve_effects_do_nothing_returns_empty(world, state_initial) -> None:
    rules = MinimalMarketRules()
    effects = rules.resolve_effects(
        world,
        state_initial,
        _proposal(action_type="do_nothing", params={}),
    )
    assert effects == []


def test_resolve_effects_unknown_action_defensive_empty(world, state_initial) -> None:
    """防御式：未知动作（正常走 validate_action 已拦下）应返回空列表。"""
    rules = MinimalMarketRules()
    effects = rules.resolve_effects(
        world,
        state_initial,
        _proposal(action_type="mystery", params={}),
    )
    assert effects == []


# =============================================================================
# validate_action：业务前置条件
# =============================================================================


def test_validate_action_promote_sufficient_cash_passes(world, state_initial) -> None:
    """company_a 初始 cash=100，budget=20 → valid。"""
    rules = MinimalMarketRules()
    result = rules.validate_action(
        world, state_initial, _proposal(params={"budget": 20})
    )
    assert result.valid is True
    assert result.errors == []


def test_validate_action_promote_insufficient_cash_rejects(
    world, state_initial
) -> None:
    """budget > 当前 cash → 拒绝并给出含 cash / budget 数值的具体错误。"""
    rules = MinimalMarketRules()
    result = rules.validate_action(
        world, state_initial, _proposal(params={"budget": 200})
    )
    assert result.valid is False
    assert len(result.errors) == 1
    err = result.errors[0]
    assert "promote 前置条件不满足" in err
    assert "cash=100" in err
    assert "budget=200" in err


def test_validate_action_do_nothing_never_requires_cash(
    world, state_initial
) -> None:
    """do_nothing 无前置条件，即便 cash=0 也通过。"""
    # 修改一个实体的 cash 到 0
    state_initial.entities["company_a"].attributes["cash"] = 0
    rules = MinimalMarketRules()
    result = rules.validate_action(
        world,
        state_initial,
        _proposal(action_type="do_nothing", params={}),
    )
    assert result.valid is True


def test_validate_action_delegates_to_base_for_unknown_action(
    world, state_initial
) -> None:
    """继承 BaseRules：未知动作应被基础校验拒绝，业务校验不重复报错。"""
    rules = MinimalMarketRules()
    result = rules.validate_action(
        world,
        state_initial,
        _proposal(action_type="mystery", params={}),
    )
    assert result.valid is False
    # 只有一条"action_type 未在 World Definition 中声明"
    assert len(result.errors) == 1
    assert "未在 World Definition 中声明" in result.errors[0]


def test_validate_action_delegates_to_base_for_missing_budget(
    world, state_initial
) -> None:
    """继承 BaseRules：promote 未提供 budget，基础校验即拒绝；不会到业务层。"""
    rules = MinimalMarketRules()
    result = rules.validate_action(
        world, state_initial, _proposal(params={})
    )
    assert result.valid is False
    assert any("必填参数 'budget' 缺失" in e for e in result.errors)


def test_validate_action_delegates_to_base_for_wrong_actor_type(
    world, state_initial
) -> None:
    """Regulator 不在 promote.actor_types，基础校验即拒绝。"""
    rules = MinimalMarketRules()
    result = rules.validate_action(
        world,
        state_initial,
        _proposal(actor_id="regulator_main", action_type="promote"),
    )
    assert result.valid is False
    assert any("actor_types" in e for e in result.errors)


# =============================================================================
# 端到端：validate → resolve → apply_constraints 完整链路
# =============================================================================


def test_end_to_end_promote_pipeline_with_clamp(world, state_initial) -> None:
    """
    真实 YAML + MinimalMarketRules 组合，跑通单条 promote 的完整链路。

    场景：cash=100, reputation=50, budget=60
    - validate: cash(100) >= budget(60) ✓
    - resolve_effects: cash -60, reputation +5
    - apply_constraints: reputation 100-clamp 限制下 50+5=55 在范围内，无需裁剪
    """
    rules = MinimalMarketRules()
    proposal = _proposal(params={"budget": 60})

    # 1. 校验
    result = rules.validate_action(world, state_initial, proposal)
    assert result.valid, result.errors

    # 2. 解析效果
    effects = rules.resolve_effects(world, state_initial, proposal)

    # 3. 约束裁剪
    clamped = rules.apply_constraints(world, state_initial, effects)

    # 验证结果：cash 应减 60, reputation 应加 5
    by_attr = {e.attribute: e for e in clamped}
    assert by_attr["cash"].delta == -60.0
    assert by_attr["reputation"].delta == 5.0


def test_end_to_end_promote_pipeline_clamps_reputation_overflow(
    world, scenario
) -> None:
    """
    当 reputation 已达 98，promote(budget=10) 产生 +5 delta，apply_constraints
    应把 delta 裁剪到 2（100 - 98）以确保不超过 max=100。
    """
    # 自构一个 reputation=98 的状态
    state = WorldState(
        tick=0,
        entities={
            "company_a": EntityRuntimeState(
                id="company_a",
                type="Company",
                attributes={"cash": 100, "reputation": 98},
            )
        },
        environment=dict(scenario.environment),
    )
    rules = MinimalMarketRules()
    proposal = _proposal(params={"budget": 10})

    result = rules.validate_action(world, state, proposal)
    assert result.valid

    effects = rules.resolve_effects(world, state, proposal)
    clamped = rules.apply_constraints(world, state, effects)

    by_attr = {e.attribute: e for e in clamped}
    # cash: 100-10=90，在 [0, ∞)，不裁剪
    assert by_attr["cash"].delta == -10.0
    # reputation: 98+5=103 → clamp 到 100 → delta 改为 2
    assert by_attr["reputation"].delta == 2.0


def test_end_to_end_insufficient_cash_blocks_before_effect_resolution(
    world, state_initial
) -> None:
    """
    前置条件不满足时，validate 返回 invalid；Runtime 不应继续 resolve_effects。
    本测试固化此契约——invalid 的 proposal 不产生状态变化建议。
    """
    rules = MinimalMarketRules()
    proposal = _proposal(params={"budget": 500})  # 远超 cash=100

    result = rules.validate_action(world, state_initial, proposal)
    assert not result.valid

    # 约定：Runtime 看到 invalid 就不 resolve。本测试强调这个顺序——
    # 但即便 Runtime 误调用 resolve_effects，公式本身仍会产出 delta，由
    # apply_constraints 的 cash min=0 兜底。下面验证兜底链路也工作。
    effects = rules.resolve_effects(world, state_initial, proposal)
    clamped = rules.apply_constraints(world, state_initial, effects)
    cash_eff = next(e for e in clamped if e.attribute == "cash")
    # cash 100 - 500 = -400 → clamp 到 0 → delta = -100
    assert cash_eff.delta == -100.0
