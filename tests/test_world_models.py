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
