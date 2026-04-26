"""scenario_loader 的加载与校验测试。

对应 `docs/01-requirements/验收标准.md`：

- 6.2 Scenario 验收——合法文件通过、非法文件失败并给出明确错误
- `max_ticks >= total_ticks` 等跨字段约束会被 loader 正确检查

本测试分层组织：

1. 合法路径（最小场景、walkthrough、端到端 YAML→Scenario）
2. JSON Schema 层（结构非法）
3. Pydantic 层（类型非法）
4. 跨字段/跨文件层（引用 / 属性 override / max_ticks 等）
5. 断点与预设事件的专项校验
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from jsonschema import ValidationError as JsonSchemaValidationError

from core.definition_loader import load_world_definition_from_dict
from core.scenario_loader import (
    ScenarioReferenceError,
    load_scenario,
    load_scenario_from_dict,
)
from models.world_models import WorldDefinition


# ---------- fixtures ----------


def _make_walkthrough_world() -> WorldDefinition:
    """walkthrough 最小世界：2 个实体类型、2 个动作、1 个消息、1 个环境变量。"""
    data = {
        "version": "0.1",
        "world": {"id": "walkthrough-min", "name": "最小 walkthrough 世界"},
        "entity_types": {
            "Company": {
                "decision_mode": "llm",
                "attributes": {
                    "cash": {"type": "number", "default": 100},
                    "reputation": {"type": "number", "min": 0, "max": 100, "default": 50},
                },
                "actions": ["promote", "do_nothing"],
            },
            "Regulator": {
                "decision_mode": "rule",
                "attributes": {"strictness": {"type": "number", "default": 50}},
                "actions": ["do_nothing"],
            },
        },
        "relation_types": {
            "competition": {"directed": False, "transient": False},
        },
        "message_types": {
            "policy_signal": {
                "delivery": "broadcast",
                "payload": {
                    "signal": {"type": "string"},
                    "strength": {"type": "number"},
                },
            },
        },
        "action_types": {
            "promote": {
                "actor_types": ["Company"],
                "params": {"budget": {"type": "number", "required": True}},
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
                "policy_pressure": {"type": "number", "min": 0, "max": 100, "default": 30},
                "risk_level": {"type": "number", "min": 0, "max": 100, "default": 20},
            },
        },
    }
    return load_world_definition_from_dict(data)


@pytest.fixture
def walkthrough_world() -> WorldDefinition:
    return _make_walkthrough_world()


MIN_VALID_SCENARIO: dict = {
    "version": "0.1",
    "world_id": "walkthrough-min",
    "scenario": {"id": "s", "name": "最小场景"},
    "entities": [
        {"id": "company_a", "type": "Company"},
        {"id": "regulator_main", "type": "Regulator"},
    ],
    "config": {"total_ticks": 5},
}


# ---------- 合法路径 ----------


def test_minimal_valid_scenario_loads(walkthrough_world: WorldDefinition) -> None:
    """最小合法场景（只含必填字段）能完整加载。"""
    s = load_scenario_from_dict(MIN_VALID_SCENARIO, walkthrough_world)
    assert s.world_id == "walkthrough-min"
    assert len(s.entities) == 2
    # D-001 默认空容器
    assert s.relations == []
    assert s.environment == {}


def test_walkthrough_full_scenario_loads(walkthrough_world: WorldDefinition) -> None:
    """walkthrough 描述的完整最小场景（含 environment + scheduled_event）能加载。"""
    payload = {
        "version": "0.1",
        "world_id": "walkthrough-min",
        "scenario": {"id": "walkthrough", "name": "Walkthrough 示例"},
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
    s = load_scenario_from_dict(payload, walkthrough_world)
    assert s.scheduled_events[0].tick == 2


def test_load_scenario_from_yaml_file(
    walkthrough_world: WorldDefinition, tmp_path: Path
) -> None:
    """从 YAML 文件加载场景。"""
    path = tmp_path / "scenario.yaml"
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(MIN_VALID_SCENARIO, f, allow_unicode=True)
    s = load_scenario(path, walkthrough_world)
    assert s.scenario.id == "s"


def test_yaml_top_level_non_dict_raises(
    walkthrough_world: WorldDefinition, tmp_path: Path
) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ScenarioReferenceError):
        load_scenario(path, walkthrough_world)


# ---------- JSON Schema 层 ----------


def test_schema_rejects_missing_required_field(walkthrough_world: WorldDefinition) -> None:
    """顶层缺 config。"""
    payload = {k: v for k, v in MIN_VALID_SCENARIO.items() if k != "config"}
    with pytest.raises(JsonSchemaValidationError):
        load_scenario_from_dict(payload, walkthrough_world)


def test_schema_rejects_empty_entities(walkthrough_world: WorldDefinition) -> None:
    """D-003：空 entities 应被 JSON Schema `minItems: 1` 挡下。"""
    payload = {**MIN_VALID_SCENARIO, "entities": []}
    with pytest.raises(JsonSchemaValidationError):
        load_scenario_from_dict(payload, walkthrough_world)


# ---------- 跨文件：world_id ----------


def test_mismatched_world_id_is_rejected(walkthrough_world: WorldDefinition) -> None:
    payload = {**MIN_VALID_SCENARIO, "world_id": "other-world"}
    with pytest.raises(ScenarioReferenceError) as exc_info:
        load_scenario_from_dict(payload, walkthrough_world)
    assert "world_id" in str(exc_info.value)


# ---------- 跨文件：实体 type ----------


def test_unknown_entity_type_is_rejected(walkthrough_world: WorldDefinition) -> None:
    payload = {
        **MIN_VALID_SCENARIO,
        "entities": [{"id": "e1", "type": "GhostType"}],
    }
    with pytest.raises(ScenarioReferenceError) as exc_info:
        load_scenario_from_dict(payload, walkthrough_world)
    assert "GhostType" in str(exc_info.value)


def test_duplicate_entity_ids_are_rejected(walkthrough_world: WorldDefinition) -> None:
    payload = {
        **MIN_VALID_SCENARIO,
        "entities": [
            {"id": "dup", "type": "Company"},
            {"id": "dup", "type": "Regulator"},
        ],
    }
    with pytest.raises(ScenarioReferenceError) as exc_info:
        load_scenario_from_dict(payload, walkthrough_world)
    assert "dup" in str(exc_info.value)


def test_entity_attribute_override_not_declared_is_rejected(
    walkthrough_world: WorldDefinition,
) -> None:
    payload = {
        **MIN_VALID_SCENARIO,
        "entities": [
            {
                "id": "company_a",
                "type": "Company",
                "attributes": {"cash": 200, "unknown_attr": 1},
            },
            {"id": "regulator_main", "type": "Regulator"},
        ],
    }
    with pytest.raises(ScenarioReferenceError) as exc_info:
        load_scenario_from_dict(payload, walkthrough_world)
    assert "unknown_attr" in str(exc_info.value)


# ---------- 跨文件：关系 ----------


def test_unknown_relation_type_is_rejected(walkthrough_world: WorldDefinition) -> None:
    payload = {
        **MIN_VALID_SCENARIO,
        "relations": [
            {"type": "alliance", "source": "company_a", "target": "regulator_main"}
        ],
    }
    with pytest.raises(ScenarioReferenceError) as exc_info:
        load_scenario_from_dict(payload, walkthrough_world)
    assert "alliance" in str(exc_info.value)


def test_relation_source_or_target_unknown_entity_is_rejected(
    walkthrough_world: WorldDefinition,
) -> None:
    payload = {
        **MIN_VALID_SCENARIO,
        "relations": [
            {"type": "competition", "source": "ghost", "target": "company_a"}
        ],
    }
    with pytest.raises(ScenarioReferenceError) as exc_info:
        load_scenario_from_dict(payload, walkthrough_world)
    assert "ghost" in str(exc_info.value)


# ---------- 跨文件：环境变量 ----------


def test_unknown_environment_variable_is_rejected(
    walkthrough_world: WorldDefinition,
) -> None:
    payload = {
        **MIN_VALID_SCENARIO,
        "environment": {"mystery_var": 10},
    }
    with pytest.raises(ScenarioReferenceError) as exc_info:
        load_scenario_from_dict(payload, walkthrough_world)
    assert "mystery_var" in str(exc_info.value)


# ---------- config ----------


def test_max_ticks_less_than_total_ticks_is_rejected(
    walkthrough_world: WorldDefinition,
) -> None:
    """跨字段约束 `max_ticks >= total_ticks` 由 loader 挡下。"""
    payload = {
        **MIN_VALID_SCENARIO,
        "config": {"total_ticks": 10, "max_ticks": 5},
    }
    with pytest.raises(ScenarioReferenceError) as exc_info:
        load_scenario_from_dict(payload, walkthrough_world)
    assert "max_ticks" in str(exc_info.value)


def test_max_ticks_equal_to_total_ticks_is_allowed(
    walkthrough_world: WorldDefinition,
) -> None:
    """边界：`max_ticks == total_ticks` 应通过。"""
    payload = {
        **MIN_VALID_SCENARIO,
        "config": {"total_ticks": 10, "max_ticks": 10},
    }
    s = load_scenario_from_dict(payload, walkthrough_world)
    assert s.config.max_ticks == 10


# ---------- 断点 ----------


def test_breakpoint_with_no_condition_is_rejected(
    walkthrough_world: WorldDefinition,
) -> None:
    """断点 when 为空（无 entity 无 environment）被拒。"""
    payload = {
        **MIN_VALID_SCENARIO,
        "breakpoints": [{"id": "bp1", "when": {}}],
    }
    with pytest.raises(ScenarioReferenceError) as exc_info:
        load_scenario_from_dict(payload, walkthrough_world)
    assert "bp1" in str(exc_info.value)


def test_breakpoint_entity_reference_unknown_is_rejected(
    walkthrough_world: WorldDefinition,
) -> None:
    payload = {
        **MIN_VALID_SCENARIO,
        "breakpoints": [
            {
                "id": "bp_ghost",
                "when": {"entity": {"id": "ghost", "attribute": "cash", "lte": 10}},
            }
        ],
    }
    with pytest.raises(ScenarioReferenceError) as exc_info:
        load_scenario_from_dict(payload, walkthrough_world)
    assert "ghost" in str(exc_info.value)


def test_breakpoint_entity_attribute_unknown_is_rejected(
    walkthrough_world: WorldDefinition,
) -> None:
    payload = {
        **MIN_VALID_SCENARIO,
        "breakpoints": [
            {
                "id": "bp_attr",
                "when": {
                    "entity": {"id": "company_a", "attribute": "ghost_attr", "lte": 10}
                },
            }
        ],
    }
    with pytest.raises(ScenarioReferenceError) as exc_info:
        load_scenario_from_dict(payload, walkthrough_world)
    assert "ghost_attr" in str(exc_info.value)


def test_breakpoint_entity_without_threshold_is_rejected(
    walkthrough_world: WorldDefinition,
) -> None:
    payload = {
        **MIN_VALID_SCENARIO,
        "breakpoints": [
            {
                "id": "bp_no_threshold",
                "when": {"entity": {"id": "company_a", "attribute": "cash"}},
            }
        ],
    }
    with pytest.raises(ScenarioReferenceError) as exc_info:
        load_scenario_from_dict(payload, walkthrough_world)
    assert "阈值" in str(exc_info.value)


def test_breakpoint_environment_unknown_var_is_rejected(
    walkthrough_world: WorldDefinition,
) -> None:
    payload = {
        **MIN_VALID_SCENARIO,
        "breakpoints": [
            {
                "id": "bp_env",
                "when": {"environment": {"unknown_var": {"gte": 50}}},
            }
        ],
    }
    with pytest.raises(ScenarioReferenceError) as exc_info:
        load_scenario_from_dict(payload, walkthrough_world)
    assert "unknown_var" in str(exc_info.value)


def test_breakpoint_environment_without_threshold_is_rejected(
    walkthrough_world: WorldDefinition,
) -> None:
    payload = {
        **MIN_VALID_SCENARIO,
        "breakpoints": [
            {
                "id": "bp_env_no_thr",
                "when": {"environment": {"risk_level": {}}},
            }
        ],
    }
    with pytest.raises(ScenarioReferenceError) as exc_info:
        load_scenario_from_dict(payload, walkthrough_world)
    assert "阈值" in str(exc_info.value)


def test_valid_breakpoint_with_both_entity_and_environment_passes(
    walkthrough_world: WorldDefinition,
) -> None:
    """同时配置 entity 与 environment 也应合法。"""
    payload = {
        **MIN_VALID_SCENARIO,
        "breakpoints": [
            {
                "id": "bp_combined",
                "when": {
                    "entity": {"id": "company_a", "attribute": "cash", "lte": 20},
                    "environment": {"risk_level": {"gte": 80}},
                },
            }
        ],
    }
    s = load_scenario_from_dict(payload, walkthrough_world)
    assert len(s.breakpoints) == 1


# ---------- 预设事件 ----------


def test_environment_event_requires_payload(walkthrough_world: WorldDefinition) -> None:
    payload = {
        **MIN_VALID_SCENARIO,
        "scheduled_events": [{"tick": 3, "type": "environment_event"}],
    }
    with pytest.raises(ScenarioReferenceError) as exc_info:
        load_scenario_from_dict(payload, walkthrough_world)
    assert "environment_event" in str(exc_info.value)
    assert "payload" in str(exc_info.value)


def test_environment_event_must_not_have_message(walkthrough_world: WorldDefinition) -> None:
    payload = {
        **MIN_VALID_SCENARIO,
        "scheduled_events": [
            {
                "tick": 3,
                "type": "environment_event",
                "payload": {"risk_level_delta": 10},
                "message": {"type": "policy_signal"},
            }
        ],
    }
    with pytest.raises(ScenarioReferenceError):
        load_scenario_from_dict(payload, walkthrough_world)


def test_message_injection_requires_message(walkthrough_world: WorldDefinition) -> None:
    payload = {
        **MIN_VALID_SCENARIO,
        "scheduled_events": [{"tick": 3, "type": "message_injection"}],
    }
    with pytest.raises(ScenarioReferenceError) as exc_info:
        load_scenario_from_dict(payload, walkthrough_world)
    assert "message_injection" in str(exc_info.value)
    assert "message" in str(exc_info.value)


def test_message_injection_rejects_unknown_message_type(
    walkthrough_world: WorldDefinition,
) -> None:
    payload = {
        **MIN_VALID_SCENARIO,
        "scheduled_events": [
            {
                "tick": 3,
                "type": "message_injection",
                "message": {"type": "unknown_msg", "payload": {}},
            }
        ],
    }
    with pytest.raises(ScenarioReferenceError) as exc_info:
        load_scenario_from_dict(payload, walkthrough_world)
    assert "unknown_msg" in str(exc_info.value)


# ---------- 多错误聚合 ----------


def test_multiple_errors_reported_together(walkthrough_world: WorldDefinition) -> None:
    """多处错误应该一次性报告。"""
    payload = {
        "version": "0.1",
        "world_id": "wrong-world",
        "scenario": {"id": "s", "name": "bad"},
        "entities": [
            {"id": "dup", "type": "GhostType"},
            {"id": "dup", "type": "Regulator"},
        ],
        "environment": {"mystery_var": 10},
        "config": {"total_ticks": 10, "max_ticks": 5},
    }
    with pytest.raises(ScenarioReferenceError) as exc_info:
        load_scenario_from_dict(payload, walkthrough_world)
    msg = str(exc_info.value)
    assert "world_id" in msg
    assert "dup" in msg
    assert "GhostType" in msg
    assert "mystery_var" in msg
    assert "max_ticks" in msg


# ---------- 端到端：world + scenario 文件同时加载 ----------


def test_end_to_end_yaml_load(tmp_path: Path) -> None:
    """从两份 YAML 文件分别加载 World + Scenario，完整通过所有三层校验。

    对应 `验收标准.md` 第十四节"最小闭环验收"的配置加载部分。
    """
    from core.definition_loader import load_world_definition

    # --- 写 world.yaml ---
    world_data = {
        "version": "0.1",
        "world": {"id": "e2e", "name": "E2E 测试世界"},
        "entity_types": {
            "Company": {
                "decision_mode": "llm",
                "attributes": {"cash": {"type": "number", "default": 100}},
                "actions": ["do_nothing"],
            }
        },
        "action_types": {
            "do_nothing": {
                "actor_types": ["Company"],
                "params": {},
                "effects": [],
            }
        },
    }
    world_path = tmp_path / "world.yaml"
    with world_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(world_data, f, allow_unicode=True)

    # --- 写 scenario.yaml ---
    scenario_data = {
        "version": "0.1",
        "world_id": "e2e",
        "scenario": {"id": "demo", "name": "端到端示例"},
        "entities": [{"id": "company_a", "type": "Company"}],
        "config": {"total_ticks": 3},
    }
    scenario_path = tmp_path / "scenario.yaml"
    with scenario_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(scenario_data, f, allow_unicode=True)

    # --- 端到端加载 ---
    wd = load_world_definition(world_path)
    s = load_scenario(scenario_path, wd)
    assert wd.world.id == "e2e"
    assert s.world_id == "e2e"
    assert s.entities[0].id == "company_a"
