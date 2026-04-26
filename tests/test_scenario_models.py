"""scenario_models 的结构校验测试。

对应 `docs/01-requirements/验收标准.md` 6.2 节 "Scenario 验收"。

本测试只校验 Pydantic 层的结构约束：
1. D-001：`relations / environment / scheduled_events / breakpoints` 可缺省且默认空容器
2. D-003：`entities` 至少 1 个元素
3. `extra="forbid"`：未声明字段被拒绝
4. 基础数值约束：`total_ticks / tick / max_ticks` 下限

不覆盖跨文件校验（`world_id` 一致性、实体 type 存在性等），那些属于 `scenario_loader`。
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from models.scenario_models import Scenario


# ---------- fixtures ----------

WALKTHROUGH_MIN_SCENARIO: dict = {
    "version": "0.1",
    "world_id": "market-competition",
    "scenario": {"id": "walkthrough-min", "name": "最小 walkthrough 示例"},
    "entities": [
        {"id": "company_a", "type": "Company"},
        {"id": "regulator_main", "type": "Regulator"},
    ],
    "environment": {"policy_pressure": 20},
    "scheduled_events": [
        {
            "tick": 2,
            "type": "message_injection",
            "message": {
                "type": "policy_signal",
                "delivery": "broadcast",
                "payload": {"signal": "加强审查", "strength": 80},
            },
        }
    ],
    "config": {"total_ticks": 5},
}


# ---------- 合法路径 ----------


def test_walkthrough_minimal_scenario_parses() -> None:
    """walkthrough 描述的最小场景能被 Scenario 直接加载。"""
    s = Scenario.model_validate(WALKTHROUGH_MIN_SCENARIO)
    assert s.world_id == "market-competition"
    assert len(s.entities) == 2
    assert s.entities[0].id == "company_a"
    assert s.config.total_ticks == 5


def test_d001_optional_fields_default_to_empty_containers() -> None:
    """D-001：未提供的 relations/environment/scheduled_events/breakpoints 应为空容器，而非 None。"""
    payload = {
        "version": "0.1",
        "world_id": "w",
        "scenario": {"id": "s", "name": "s"},
        "entities": [{"id": "e1", "type": "T"}],
        "config": {"total_ticks": 1},
    }
    s = Scenario.model_validate(payload)

    # 容器必须存在且为对应类型，不能是 None
    assert s.relations == []
    assert s.environment == {}
    assert s.scheduled_events == []
    assert s.breakpoints == []

    # 实体内部 attributes 同样走 default_factory=dict
    assert s.entities[0].attributes == {}


def test_entity_attributes_accepts_mixed_primitive_values() -> None:
    """实体属性可以是数值、字符串、布尔等各种基本类型。"""
    payload = {
        "version": "0.1",
        "world_id": "w",
        "scenario": {"id": "s", "name": "s"},
        "entities": [
            {
                "id": "e1",
                "type": "Company",
                "attributes": {
                    "market_share": 25,
                    "cash": 120.5,
                    "strategy_bias": "aggressive",
                    "active": True,
                },
            }
        ],
        "config": {"total_ticks": 1},
    }
    s = Scenario.model_validate(payload)
    assert s.entities[0].attributes["market_share"] == 25
    assert s.entities[0].attributes["strategy_bias"] == "aggressive"


# ---------- D-003：entities 不得为空 ----------


def test_d003_empty_entities_is_rejected() -> None:
    """D-003：`entities` 为空数组时必须被拒绝。"""
    payload = {
        "version": "0.1",
        "world_id": "w",
        "scenario": {"id": "s", "name": "s"},
        "entities": [],
        "config": {"total_ticks": 1},
    }
    with pytest.raises(ValidationError) as exc_info:
        Scenario.model_validate(payload)
    # 错误信息应当指向 entities 字段
    assert any("entities" in str(err["loc"]) for err in exc_info.value.errors())


# ---------- extra="forbid" ----------


def test_unknown_top_level_field_is_rejected() -> None:
    """顶层多余字段应被 `extra='forbid'` 拒绝。"""
    payload = {**WALKTHROUGH_MIN_SCENARIO, "unknown_top": 1}
    with pytest.raises(ValidationError):
        Scenario.model_validate(payload)


def test_unknown_field_inside_scenario_info_is_rejected() -> None:
    """嵌套对象内部的未知字段同样应被拒绝。"""
    payload = {
        **WALKTHROUGH_MIN_SCENARIO,
        "scenario": {"id": "s", "name": "n", "extra_meta": "x"},
    }
    with pytest.raises(ValidationError):
        Scenario.model_validate(payload)


# ---------- 数值下限 ----------


def test_total_ticks_must_be_positive() -> None:
    """`total_ticks` 必须 >= 1。"""
    payload = {**WALKTHROUGH_MIN_SCENARIO, "config": {"total_ticks": 0}}
    with pytest.raises(ValidationError):
        Scenario.model_validate(payload)


def test_scheduled_event_tick_must_be_positive() -> None:
    """`scheduled_events[*].tick` 必须 >= 1。"""
    payload = {
        **WALKTHROUGH_MIN_SCENARIO,
        "scheduled_events": [{"tick": 0, "type": "environment_event"}],
    }
    with pytest.raises(ValidationError):
        Scenario.model_validate(payload)


# ---------- 边界：loader 职责不在此层 ----------


def test_max_ticks_less_than_total_ticks_is_not_checked_here() -> None:
    """跨字段约束 `max_ticks >= total_ticks` 属于 scenario_loader，不在本模型层校验。

    本测试固化这一边界：Pydantic 层接受结构合法但语义不合理的组合。
    若未来将此校验下移到模型层（例如加 `model_validator`），本测试应随之改写。
    """
    payload = {
        **WALKTHROUGH_MIN_SCENARIO,
        "config": {"total_ticks": 10, "max_ticks": 5},
    }
    # Pydantic 层此处应通过，由 loader 后续拒绝
    s = Scenario.model_validate(payload)
    assert s.config.total_ticks == 10
    assert s.config.max_ticks == 5


# ---------- 完整字段构造 ----------


def test_full_scenario_with_all_optional_fields() -> None:
    """构造一份包含全部可选字段的场景，确保嵌套模型都能正确实例化。"""
    payload = {
        "version": "0.1",
        "world_id": "market-competition",
        "scenario": {
            "id": "market-demo-001",
            "name": "完整字段示例",
            "description": "覆盖所有可选字段的测试 fixture",
        },
        "entities": [
            {
                "id": "company_a",
                "type": "Company",
                "name": "企业A",
                "attributes": {"market_share": 25, "cash": 120},
            }
        ],
        "relations": [
            {"type": "competition", "source": "company_a", "target": "company_b", "value": 1.0}
        ],
        "environment": {"market_demand": 55, "policy_pressure": 30},
        "scheduled_events": [
            {
                "tick": 5,
                "type": "environment_event",
                "name": "raw_material_cost_rise",
                "payload": {"resource_cost_delta": 15},
            }
        ],
        "breakpoints": [
            {
                "id": "high_risk",
                "when": {"environment": {"risk_level": {"gte": 80}}},
            },
            {
                "id": "company_a_low_cash",
                "when": {
                    "entity": {"id": "company_a", "attribute": "cash", "lte": 20}
                },
            },
        ],
        "config": {
            "total_ticks": 30,
            "max_ticks": 40,
            "pause_mode": {"manual": True, "every_tick": False},
            "snapshot_mode": "every_tick",
            "analysis": {"snapshot_fields": ["entities", "relations", "environment"]},
        },
    }
    s = Scenario.model_validate(payload)
    assert len(s.breakpoints) == 2
    assert s.breakpoints[0].when.environment["risk_level"].gte == 80
    assert s.breakpoints[1].when.entity is not None
    assert s.breakpoints[1].when.entity.attribute == "cash"
    assert s.config.analysis is not None
    assert s.config.analysis.snapshot_fields == ["entities", "relations", "environment"]


# ---------- D-010：rules_module 字段 ----------


def test_d010_rules_module_defaults_to_none() -> None:
    """D-010：未声明 rules_module 时，字段为 None（不影响现有场景）。"""
    payload = {
        "version": "0.1",
        "world_id": "w",
        "scenario": {"id": "s", "name": "s"},
        "entities": [{"id": "e1", "type": "T"}],
        "config": {"total_ticks": 1},
    }
    s = Scenario.model_validate(payload)
    assert s.rules_module is None


def test_d010_rules_module_accepts_well_formed_path() -> None:
    """D-010：合法 'module.path:ClassName' 被接受。"""
    payload = {
        "version": "0.1",
        "world_id": "w",
        "rules_module": "rules.minimal_market:MinimalMarketRules",
        "scenario": {"id": "s", "name": "s"},
        "entities": [{"id": "e1", "type": "T"}],
        "config": {"total_ticks": 1},
    }
    s = Scenario.model_validate(payload)
    assert s.rules_module == "rules.minimal_market:MinimalMarketRules"


@pytest.mark.parametrize(
    "bad_value",
    [
        "",  # 空串
        "rules.minimal_market",  # 缺冒号
        ":MinimalMarketRules",  # 模块为空
        "rules.minimal_market:",  # 类名为空
        "rules.minimal_market:Class:Extra",  # 多冒号
        "1rules.x:Y",  # 模块以数字开头
        "rules.x:1Class",  # 类名以数字开头
        "rules.x:Class-Name",  # 类名含非法字符
        "rules. x:Y",  # 含空格
    ],
)
def test_d010_rules_module_rejects_malformed_paths(bad_value: str) -> None:
    """D-010：格式不符 Pydantic pattern 的字符串一律被拒（与 schema 对齐）。"""
    payload = {
        "version": "0.1",
        "world_id": "w",
        "rules_module": bad_value,
        "scenario": {"id": "s", "name": "s"},
        "entities": [{"id": "e1", "type": "T"}],
        "config": {"total_ticks": 1},
    }
    with pytest.raises(ValidationError):
        Scenario.model_validate(payload)
