"""definition_loader 的加载与校验测试。

对应 `docs/01-requirements/验收标准.md`：

- 6.1 World Definition 验收——合法文件通过、非法文件失败并给出明确错误
- 第 15 节不通过典型情况——"schema 能过，但 loader 无法加载"必须能被捕获

本测试按三层校验组织：

1. JSON Schema 层（结构）
2. Pydantic 层（类型）
3. Loader 跨字段/语义层（引用一致性、enum values、min/max 等）
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import ValidationError as JsonSchemaValidationError
from pydantic import ValidationError as PydanticValidationError

from core.definition_loader import (
    WorldDefinitionReferenceError,
    load_world_definition,
    load_world_definition_from_dict,
)


# ---------- fixtures ----------

MIN_VALID_WORLD: dict = {
    "version": "0.1",
    "world": {"id": "w", "name": "最小世界"},
    "entity_types": {
        "Company": {
            "decision_mode": "llm",
            "attributes": {"cash": {"type": "number", "default": 100}},
            "actions": ["promote", "do_nothing"],
        }
    },
    "action_types": {
        "promote": {
            "actor_types": ["Company"],
            "params": {"budget": {"type": "number", "required": True}},
            "effects": [{"kind": "self_attribute"}],
        },
        "do_nothing": {
            "actor_types": ["Company"],
            "params": {},
            "effects": [],
        },
    },
}


# ---------- 合法路径 ----------


def test_minimal_valid_world_loads() -> None:
    """最小合法世界定义能被完整加载。"""
    wd = load_world_definition_from_dict(MIN_VALID_WORLD)
    assert wd.world.id == "w"
    assert "promote" in wd.action_types


def test_load_from_yaml_file(tmp_path: Path) -> None:
    """从 YAML 文件路径加载成功。"""
    yaml_path = tmp_path / "world.yaml"
    with yaml_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(MIN_VALID_WORLD, f, allow_unicode=True)
    wd = load_world_definition(yaml_path)
    assert wd.world.id == "w"


def test_yaml_top_level_non_dict_raises(tmp_path: Path) -> None:
    """YAML 顶层不是对象时应明确报错。"""
    yaml_path = tmp_path / "bad.yaml"
    yaml_path.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(WorldDefinitionReferenceError):
        load_world_definition(yaml_path)


# ---------- JSON Schema 层 ----------


def test_schema_rejects_missing_required_field() -> None:
    """顶层缺失必填字段由 JSON Schema 挡下。"""
    payload = {k: v for k, v in MIN_VALID_WORLD.items() if k != "world"}
    with pytest.raises(JsonSchemaValidationError):
        load_world_definition_from_dict(payload)


def test_schema_rejects_unknown_top_level_field() -> None:
    """顶层多余字段由 JSON Schema 挡下（additionalProperties: false）。"""
    payload = {**MIN_VALID_WORLD, "unknown": 1}
    with pytest.raises(JsonSchemaValidationError):
        load_world_definition_from_dict(payload)


def test_schema_rejects_invalid_version() -> None:
    """version 只能是 '0.1'。"""
    payload = {**MIN_VALID_WORLD, "version": "0.2"}
    with pytest.raises(JsonSchemaValidationError):
        load_world_definition_from_dict(payload)


# ---------- Pydantic 层 ----------


def test_pydantic_rejects_invalid_decision_mode() -> None:
    """`decision_mode` 在 Pydantic 层挡下（也可由 schema 挡下，这里断言至少抛错）。

    实际走的是 JsonSchemaValidationError（schema 层先挡），但如果有一天 schema 放宽
    而 Pydantic 仍严格，这条测试仍应挡下——故用 Exception 保险。
    """
    payload = {
        **MIN_VALID_WORLD,
        "entity_types": {
            "Company": {
                "decision_mode": "custom",  # 非法
                "attributes": {"cash": {"type": "number"}},
                "actions": ["do_nothing"],
            }
        },
    }
    with pytest.raises((JsonSchemaValidationError, PydanticValidationError)):
        load_world_definition_from_dict(payload)


# ---------- 跨字段引用层 ----------


def test_ref_error_when_entity_references_undefined_action() -> None:
    """实体类型引用未声明的动作 → WorldDefinitionReferenceError。"""
    payload = {
        **MIN_VALID_WORLD,
        "entity_types": {
            "Company": {
                "decision_mode": "llm",
                "attributes": {"cash": {"type": "number"}},
                "actions": ["promote", "ghost_action"],
            }
        },
    }
    with pytest.raises(WorldDefinitionReferenceError) as exc_info:
        load_world_definition_from_dict(payload)
    assert "ghost_action" in str(exc_info.value)


def test_ref_error_when_action_references_undefined_actor_type() -> None:
    """动作 actor_types 引用未声明的实体类型 → WorldDefinitionReferenceError。"""
    payload = {
        **MIN_VALID_WORLD,
        "action_types": {
            "promote": {
                "actor_types": ["Company", "Ghost"],  # Ghost 未声明
                "params": {},
                "effects": [],
            },
            "do_nothing": {
                "actor_types": ["Company"],
                "params": {},
                "effects": [],
            },
        },
    }
    with pytest.raises(WorldDefinitionReferenceError) as exc_info:
        load_world_definition_from_dict(payload)
    assert "Ghost" in str(exc_info.value)


def test_ref_error_when_fallback_action_not_declared() -> None:
    """defaults.fallback_action 未声明 → WorldDefinitionReferenceError。"""
    payload = {
        **MIN_VALID_WORLD,
        "defaults": {"fallback_action": "nonexistent"},
    }
    with pytest.raises(WorldDefinitionReferenceError) as exc_info:
        load_world_definition_from_dict(payload)
    assert "nonexistent" in str(exc_info.value)


def test_ref_error_when_perception_relation_not_declared() -> None:
    """perception.include_relations 引用未声明的关系类型。"""
    payload = {
        **MIN_VALID_WORLD,
        "entity_types": {
            "Company": {
                "decision_mode": "llm",
                "perception": {
                    "scope": "relation",
                    "include_relations": ["alliance"],  # 未声明
                },
                "attributes": {"cash": {"type": "number"}},
                "actions": ["do_nothing"],
            }
        },
    }
    with pytest.raises(WorldDefinitionReferenceError) as exc_info:
        load_world_definition_from_dict(payload)
    assert "alliance" in str(exc_info.value)


def test_ref_error_when_environment_trigger_field_not_declared() -> None:
    """activation.environment_triggers.field 不是已声明的环境变量。"""
    payload = {
        **MIN_VALID_WORLD,
        "entity_types": {
            "Company": {
                "decision_mode": "llm",
                "activation": {
                    "environment_triggers": [
                        {"field": "unknown_var", "gte_delta": 10}
                    ]
                },
                "attributes": {"cash": {"type": "number"}},
                "actions": ["do_nothing"],
            }
        },
        # 不声明任何 environment 变量
    }
    with pytest.raises(WorldDefinitionReferenceError) as exc_info:
        load_world_definition_from_dict(payload)
    assert "unknown_var" in str(exc_info.value)


def test_ref_error_when_attribute_trigger_field_not_declared() -> None:
    """activation.attribute_triggers.field 不是实体自身的属性。"""
    payload = {
        **MIN_VALID_WORLD,
        "entity_types": {
            "Company": {
                "decision_mode": "llm",
                "activation": {
                    "attribute_triggers": [
                        {"field": "ghost_attr", "lte": 10}
                    ]
                },
                "attributes": {"cash": {"type": "number"}},
                "actions": ["do_nothing"],
            }
        },
    }
    with pytest.raises(WorldDefinitionReferenceError) as exc_info:
        load_world_definition_from_dict(payload)
    assert "ghost_attr" in str(exc_info.value)


# ---------- 属性 schema 语义 ----------


def test_ref_error_when_enum_without_values() -> None:
    """type=enum 但未提供 values → WorldDefinitionReferenceError。"""
    payload = {
        **MIN_VALID_WORLD,
        "entity_types": {
            "Company": {
                "decision_mode": "llm",
                "attributes": {
                    "strategy_bias": {"type": "enum"}
                },
                "actions": ["do_nothing"],
            }
        },
    }
    with pytest.raises(WorldDefinitionReferenceError) as exc_info:
        load_world_definition_from_dict(payload)
    assert "values" in str(exc_info.value)


def test_ref_error_when_enum_default_not_in_values() -> None:
    """type=enum 时 default 不在 values 中 → WorldDefinitionReferenceError。"""
    payload = {
        **MIN_VALID_WORLD,
        "entity_types": {
            "Company": {
                "decision_mode": "llm",
                "attributes": {
                    "strategy_bias": {
                        "type": "enum",
                        "values": ["aggressive", "balanced"],
                        "default": "neutral",  # 不在 values 中
                    }
                },
                "actions": ["do_nothing"],
            }
        },
    }
    with pytest.raises(WorldDefinitionReferenceError) as exc_info:
        load_world_definition_from_dict(payload)
    assert "neutral" in str(exc_info.value)


def test_ref_error_when_non_enum_attribute_has_values() -> None:
    """非 enum 类型不应提供 values。"""
    payload = {
        **MIN_VALID_WORLD,
        "entity_types": {
            "Company": {
                "decision_mode": "llm",
                "attributes": {
                    "cash": {
                        "type": "number",
                        "values": ["100", "200"],  # 非法
                    }
                },
                "actions": ["do_nothing"],
            }
        },
    }
    with pytest.raises(WorldDefinitionReferenceError) as exc_info:
        load_world_definition_from_dict(payload)
    assert "values" in str(exc_info.value)


def test_ref_error_when_min_greater_than_max() -> None:
    """属性 min > max → WorldDefinitionReferenceError。"""
    payload = {
        **MIN_VALID_WORLD,
        "entity_types": {
            "Company": {
                "decision_mode": "llm",
                "attributes": {
                    "cash": {"type": "number", "min": 100, "max": 50}
                },
                "actions": ["do_nothing"],
            }
        },
    }
    with pytest.raises(WorldDefinitionReferenceError) as exc_info:
        load_world_definition_from_dict(payload)
    assert "min" in str(exc_info.value) and "max" in str(exc_info.value)


def test_environment_variable_schema_is_also_validated() -> None:
    """environment.variables 下的 AttributeSchema 同样受语义校验约束。"""
    payload = {
        **MIN_VALID_WORLD,
        "environment": {
            "variables": {
                "risk_level": {"type": "number", "min": 10, "max": 5}
            }
        },
    }
    with pytest.raises(WorldDefinitionReferenceError) as exc_info:
        load_world_definition_from_dict(payload)
    assert "risk_level" in str(exc_info.value)


# ---------- 多错误聚合 ----------


def test_multiple_reference_errors_reported_together() -> None:
    """多个跨字段错误应该一次性全部报告，不是遇错即停。"""
    payload = {
        **MIN_VALID_WORLD,
        "entity_types": {
            "Company": {
                "decision_mode": "llm",
                "attributes": {"cash": {"type": "number"}},
                "actions": ["ghost_action_1", "ghost_action_2"],  # 2 个未声明
            }
        },
        "defaults": {"fallback_action": "ghost_action_3"},  # 再 1 个
    }
    with pytest.raises(WorldDefinitionReferenceError) as exc_info:
        load_world_definition_from_dict(payload)
    msg = str(exc_info.value)
    assert "ghost_action_1" in msg
    assert "ghost_action_2" in msg
    assert "ghost_action_3" in msg


# ---------- schema 文件本身 ----------


def test_schema_file_is_valid_json() -> None:
    """schemas/world_definition.schema.json 本身必须是可读的 JSON。"""
    schema_path = (
        Path(__file__).resolve().parents[1]
        / "schemas"
        / "world_definition.schema.json"
    )
    assert schema_path.exists()
    with schema_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("title") == "WorldDefinition"
