"""world_models 的结构校验测试。

对应 `docs/01-requirements/验收标准.md` 6.1 节 "World Definition 验收"。

本测试只校验 Pydantic 层的结构约束，不覆盖：

1. JSON Schema 层的额外约束（`jsonschema` 校验由 loader 执行）
2. 跨字段引用校验（如 `entity_types.actions` 是否都在 `action_types` 中声明、
   `defaults.fallback_action` 是否存在等）——这些属于 `core/definition_loader.py`
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from models.world_models import WorldDefinition


# ---------- fixtures ----------

WALKTHROUGH_MIN_WORLD: dict = {
    "version": "0.1",
    "world": {"id": "walkthrough-min", "name": "最小 walkthrough 世界"},
    "entity_types": {
        "Company": {
            "decision_mode": "llm",
            "attributes": {"cash": {"type": "number", "default": 100}},
            "actions": ["promote", "do_nothing"],
        },
        "Regulator": {
            "decision_mode": "rule",
            "attributes": {"strictness": {"type": "number", "default": 50}},
            "actions": ["do_nothing"],
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
}


# ---------- 合法路径 ----------


def test_walkthrough_minimal_world_parses() -> None:
    """walkthrough 描述的最小世界定义能被加载。"""
    w = WorldDefinition.model_validate(WALKTHROUGH_MIN_WORLD)
    assert w.world.id == "walkthrough-min"
    assert set(w.entity_types.keys()) == {"Company", "Regulator"}
    assert set(w.action_types.keys()) == {"promote", "do_nothing"}


def test_optional_top_level_fields_can_be_omitted() -> None:
    """relation_types / message_types / environment / defaults 皆可缺省。"""
    w = WorldDefinition.model_validate(WALKTHROUGH_MIN_WORLD)
    assert w.relation_types is None
    assert w.message_types is None
    assert w.environment is None
    assert w.defaults is None


def test_defaults_schema_fills_sensible_defaults() -> None:
    """DefaultsSchema 在缺省字段时填入默认值。"""
    payload = {
        **WALKTHROUGH_MIN_WORLD,
        "defaults": {},
    }
    w = WorldDefinition.model_validate(payload)
    assert w.defaults is not None
    assert w.defaults.conflict_resolution == "both"
    assert w.defaults.max_messages_per_tick == 100
    assert w.defaults.action_effect_order == [
        "self_attribute",
        "relation",
        "environment",
        "message",
    ]


def test_full_world_definition_with_all_sections() -> None:
    """一份涵盖全部字段的世界定义能被正确加载。"""
    payload = {
        "version": "0.1",
        "world": {
            "id": "market-competition",
            "name": "多组织竞争世界",
            "description": "MVP 场景骨架",
        },
        "entity_types": {
            "Company": {
                "description": "企业主体",
                "decision_mode": "llm",
                "activation": {
                    "on_message": True,
                    "decision_interval": 2,
                    "wake_on": ["environment_changed", "action_finished"],
                    "environment_triggers": [
                        {"field": "policy_pressure", "gte_delta": 10}
                    ],
                    "attribute_triggers": [{"field": "reputation", "lte": 20}],
                },
                "perception": {
                    "scope": "relation",
                    "include_relations": ["competition", "alliance"],
                },
                "attributes": {
                    "market_share": {
                        "type": "number",
                        "min": 0,
                        "max": 100,
                        "default": 10,
                    },
                    "strategy_bias": {
                        "type": "enum",
                        "values": ["aggressive", "balanced"],
                        "default": "balanced",
                    },
                },
                "actions": ["promote", "do_nothing"],
            }
        },
        "relation_types": {
            "competition": {"directed": False, "transient": False},
            "alliance": {"directed": False, "transient": True},
        },
        "message_types": {
            "policy_signal": {
                "delivery": "broadcast",
                "payload": {
                    "signal": {"type": "string"},
                    "strength": {"type": "number"},
                },
            }
        },
        "action_types": {
            "promote": {
                "actor_types": ["Company"],
                "params": {"budget": {"type": "number", "required": True}},
                "effects": [{"kind": "self_attribute"}, {"kind": "message"}],
            },
            "do_nothing": {
                "actor_types": ["Company"],
                "params": {},
                "effects": [],
            },
        },
        "environment": {
            "variables": {
                "market_demand": {"type": "number", "min": 0, "max": 100, "default": 50}
            }
        },
        "defaults": {
            "conflict_resolution": "priority",
            "max_messages_per_tick": 50,
            "fallback_action": "do_nothing",
            "action_effect_order": ["self_attribute", "message"],
        },
    }
    w = WorldDefinition.model_validate(payload)
    assert w.entity_types["Company"].activation is not None
    assert w.entity_types["Company"].activation.decision_interval == 2
    assert w.entity_types["Company"].perception is not None
    assert w.entity_types["Company"].perception.scope == "relation"
    assert w.relation_types is not None
    assert w.message_types is not None
    assert w.environment is not None
    assert w.defaults is not None
    assert w.defaults.conflict_resolution == "priority"


# ---------- 必填字段 ----------


def test_missing_version_is_rejected() -> None:
    payload = {k: v for k, v in WALKTHROUGH_MIN_WORLD.items() if k != "version"}
    with pytest.raises(ValidationError):
        WorldDefinition.model_validate(payload)


def test_missing_world_is_rejected() -> None:
    payload = {k: v for k, v in WALKTHROUGH_MIN_WORLD.items() if k != "world"}
    with pytest.raises(ValidationError):
        WorldDefinition.model_validate(payload)


def test_missing_entity_types_is_rejected() -> None:
    payload = {k: v for k, v in WALKTHROUGH_MIN_WORLD.items() if k != "entity_types"}
    with pytest.raises(ValidationError):
        WorldDefinition.model_validate(payload)


def test_missing_action_types_is_rejected() -> None:
    payload = {k: v for k, v in WALKTHROUGH_MIN_WORLD.items() if k != "action_types"}
    with pytest.raises(ValidationError):
        WorldDefinition.model_validate(payload)


# ---------- 枚举与下限 ----------


def test_invalid_decision_mode_is_rejected() -> None:
    """`decision_mode` 只能是 llm / rule / random。"""
    payload = {
        **WALKTHROUGH_MIN_WORLD,
        "entity_types": {
            **WALKTHROUGH_MIN_WORLD["entity_types"],
            "Rogue": {
                "decision_mode": "custom",  # 非法
                "attributes": {"x": {"type": "number"}},
                "actions": ["do_nothing"],
            },
        },
    }
    with pytest.raises(ValidationError):
        WorldDefinition.model_validate(payload)


def test_decision_interval_must_be_ge_1() -> None:
    payload = {
        **WALKTHROUGH_MIN_WORLD,
        "entity_types": {
            "Company": {
                "decision_mode": "llm",
                "activation": {"decision_interval": 0},
                "attributes": {"cash": {"type": "number"}},
                "actions": ["do_nothing"],
            }
        },
    }
    with pytest.raises(ValidationError):
        WorldDefinition.model_validate(payload)


def test_invalid_wake_on_value_is_rejected() -> None:
    """`wake_on` 只允许 environment_changed / relation_changed / action_finished。"""
    payload = {
        **WALKTHROUGH_MIN_WORLD,
        "entity_types": {
            "Company": {
                "decision_mode": "llm",
                "activation": {"wake_on": ["random_trigger"]},
                "attributes": {"cash": {"type": "number"}},
                "actions": ["do_nothing"],
            }
        },
    }
    with pytest.raises(ValidationError):
        WorldDefinition.model_validate(payload)


def test_invalid_conflict_resolution_is_rejected() -> None:
    payload = {
        **WALKTHROUGH_MIN_WORLD,
        "defaults": {"conflict_resolution": "majority"},  # 非法
    }
    with pytest.raises(ValidationError):
        WorldDefinition.model_validate(payload)


def test_max_messages_per_tick_must_be_ge_1() -> None:
    payload = {
        **WALKTHROUGH_MIN_WORLD,
        "defaults": {"max_messages_per_tick": 0},
    }
    with pytest.raises(ValidationError):
        WorldDefinition.model_validate(payload)


def test_entity_actions_must_be_non_empty() -> None:
    """实体类型的 actions 列表不得为空。"""
    payload = {
        **WALKTHROUGH_MIN_WORLD,
        "entity_types": {
            "Company": {
                "decision_mode": "llm",
                "attributes": {"cash": {"type": "number"}},
                "actions": [],  # 非法
            }
        },
    }
    with pytest.raises(ValidationError):
        WorldDefinition.model_validate(payload)


def test_action_types_actor_types_must_be_non_empty() -> None:
    """动作的 actor_types 列表不得为空。"""
    payload = {
        **WALKTHROUGH_MIN_WORLD,
        "action_types": {
            "broken": {
                "actor_types": [],  # 非法
                "params": {},
                "effects": [],
            }
        },
    }
    with pytest.raises(ValidationError):
        WorldDefinition.model_validate(payload)


# ---------- extra="forbid" ----------


def test_unknown_top_level_field_is_rejected() -> None:
    payload = {**WALKTHROUGH_MIN_WORLD, "unknown_section": {}}
    with pytest.raises(ValidationError):
        WorldDefinition.model_validate(payload)


def test_unknown_field_in_perception_is_rejected() -> None:
    """PerceptionSchema 是 extra='forbid'，不得出现未知字段。"""
    payload = {
        **WALKTHROUGH_MIN_WORLD,
        "entity_types": {
            "Company": {
                "decision_mode": "llm",
                "perception": {"scope": "relation", "mystery_field": 1},
                "attributes": {"cash": {"type": "number"}},
                "actions": ["do_nothing"],
            }
        },
    }
    with pytest.raises(ValidationError):
        WorldDefinition.model_validate(payload)


# ---------- 跨层边界固化 ----------


def test_cross_reference_of_actions_is_not_checked_here() -> None:
    """实体类型的 actions 引用了未在 action_types 中声明的动作，在模型层不校验。

    该校验属于 `core/definition_loader.py` 的跨字段校验职责。
    """
    payload = {
        **WALKTHROUGH_MIN_WORLD,
        "entity_types": {
            "Company": {
                "decision_mode": "llm",
                "attributes": {"cash": {"type": "number"}},
                "actions": ["undefined_action"],  # 未声明，但模型层应放行
            }
        },
    }
    # 模型层应通过
    w = WorldDefinition.model_validate(payload)
    assert "undefined_action" in w.entity_types["Company"].actions


# ---------- D-014 ActionParamSchema 扩充字段 ----------
#
# 对应 `docs/02-design/decisions/D-014-动作参数强Schema化.md` 第二节
# 测试覆盖：合法路径 + 6 项 cross-validation 约束的全分支


from models.world_models import ActionParamSchema  # noqa: E402  分组导入便于阅读


def test_action_param_minimal_valid() -> None:
    """D-014：只含必填 type 字段的 ActionParamSchema 能加载（向后兼容）。

    新加 6 个字段（description / default / min / max / values / entity_type_filter）
    全部默认 None，已有 YAML 不需要任何改动即可继续工作。
    """
    p = ActionParamSchema.model_validate({"type": "number"})
    assert p.type == "number"
    assert p.required is False
    assert p.description is None
    assert p.default is None
    assert p.min is None
    assert p.max is None
    assert p.values is None
    assert p.entity_type_filter is None


def test_action_param_full_number_valid() -> None:
    """D-014：number 类型 + 全部相关字段（description / default / min / max）合法。"""
    p = ActionParamSchema.model_validate(
        {
            "type": "number",
            "required": True,
            "description": "推广预算",
            "default": 50,
            "min": 10,
            "max": 1000,
        }
    )
    assert p.description == "推广预算"
    assert p.default == 50
    assert p.min == 10.0
    assert p.max == 1000.0


def test_action_param_full_string_with_values_valid() -> None:
    """D-014：string 类型 + values 枚举 + default in values 合法。"""
    p = ActionParamSchema.model_validate(
        {
            "type": "string",
            "values": ["aggressive", "balanced", "conservative"],
            "default": "balanced",
        }
    )
    assert p.values == ["aggressive", "balanced", "conservative"]
    assert p.default == "balanced"


def test_action_param_full_entity_ref_with_filter_valid() -> None:
    """D-014：entity_ref 类型 + entity_type_filter 合法。"""
    p = ActionParamSchema.model_validate(
        {
            "type": "entity_ref",
            "entity_type_filter": ["Company", "Regulator"],
        }
    )
    assert p.entity_type_filter == ["Company", "Regulator"]


def test_action_param_boolean_default_true_valid() -> None:
    """D-014：boolean 类型 + default=True 合法（确认 bool 不被误识别为 number）。"""
    p = ActionParamSchema.model_validate({"type": "boolean", "default": True})
    assert p.default is True


# --- 约束 1：default 类型与 type 必须一致 ---


def test_action_param_default_type_mismatch_number_with_string() -> None:
    """约束 1：type=number 但 default 是字符串 → 拒绝。"""
    with pytest.raises(ValidationError, match="number"):
        ActionParamSchema.model_validate({"type": "number", "default": "abc"})


def test_action_param_default_bool_for_number_is_rejected() -> None:
    """约束 1：bool 是 int 子类陷阱——type=number 但 default=True 必须被拒。"""
    with pytest.raises(ValidationError, match="number"):
        ActionParamSchema.model_validate({"type": "number", "default": True})


def test_action_param_default_type_mismatch_boolean_with_int() -> None:
    """约束 1：type=boolean 但 default 是 int → 拒绝。"""
    with pytest.raises(ValidationError, match="boolean"):
        ActionParamSchema.model_validate({"type": "boolean", "default": 1})


def test_action_param_default_type_mismatch_string_with_int() -> None:
    """约束 1：type=string 但 default 是 int → 拒绝。"""
    with pytest.raises(ValidationError, match="string"):
        ActionParamSchema.model_validate({"type": "string", "default": 42})


def test_action_param_default_type_mismatch_entity_ref_with_int() -> None:
    """约束 1：type=entity_ref 但 default 是 int → 拒绝。"""
    with pytest.raises(ValidationError, match="entity_ref"):
        ActionParamSchema.model_validate({"type": "entity_ref", "default": 42})


# --- 约束 2：min / max 仅 type=number 时有意义 ---


def test_action_param_min_on_string_is_rejected() -> None:
    with pytest.raises(ValidationError, match="min"):
        ActionParamSchema.model_validate({"type": "string", "min": 0})


def test_action_param_max_on_boolean_is_rejected() -> None:
    with pytest.raises(ValidationError, match="max"):
        ActionParamSchema.model_validate({"type": "boolean", "max": 1})


# --- 约束 3：values 仅 type=string 时有意义 ---


def test_action_param_values_on_number_is_rejected() -> None:
    with pytest.raises(ValidationError, match="values"):
        ActionParamSchema.model_validate({"type": "number", "values": ["a", "b"]})


# --- 约束 4：entity_type_filter 仅 type=entity_ref 时有意义 ---


def test_action_param_entity_type_filter_on_string_is_rejected() -> None:
    with pytest.raises(ValidationError, match="entity_type_filter"):
        ActionParamSchema.model_validate(
            {"type": "string", "entity_type_filter": ["Company"]}
        )


# --- 约束 5：min <= max ---


def test_action_param_min_greater_than_max_is_rejected() -> None:
    with pytest.raises(ValidationError, match="min.*max"):
        ActionParamSchema.model_validate({"type": "number", "min": 100, "max": 10})


# --- 约束 6：default in values ---


def test_action_param_default_not_in_values_is_rejected() -> None:
    with pytest.raises(ValidationError, match="values"):
        ActionParamSchema.model_validate(
            {
                "type": "string",
                "values": ["a", "b"],
                "default": "c",  # 不在 values 列表中
            }
        )
