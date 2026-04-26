"""世界定义加载器。

职责：

1. 从 YAML 文件或 dict 加载世界定义数据
2. 用 JSON Schema（`schemas/world_definition.schema.json`）做结构校验
3. 用 Pydantic（`models/world_models.py`）做类型校验
4. 执行跨字段引用校验（同一文件内的字段互相引用是否完整一致）

不负责：

1. 定义规则执行逻辑（属 Rules 层）
2. 推进仿真（属 Runtime）
3. 与 Scenario 的交叉校验（如 `world_id` 一致性、场景实体 type 合法性——属 scenario_loader）
4. 业务层面的合法性判断（如某个动作的效果是否合理——属 Rules）

接口：

- `load_world_definition_from_dict(data)` → `WorldDefinition`
- `load_world_definition(path)` → `WorldDefinition`

失败时抛出：

- `jsonschema.ValidationError`：结构校验失败
- `pydantic.ValidationError`：类型校验失败
- `WorldDefinitionReferenceError`：跨字段引用失败
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import validate as jsonschema_validate

from models.world_models import WorldDefinition


class WorldDefinitionReferenceError(ValueError):
    """世界定义的跨字段引用或语义校验失败。

    与 `jsonschema.ValidationError`（结构）和 `pydantic.ValidationError`（类型）
    不同，这个错误代表"结构和类型都对，但字段之间引用/语义不一致"。
    """


_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "schemas" / "world_definition.schema.json"
)

_schema_cache: dict[str, Any] | None = None


def _get_world_schema() -> dict[str, Any]:
    """加载并缓存 JSON Schema。"""
    global _schema_cache
    if _schema_cache is None:
        with _SCHEMA_PATH.open("r", encoding="utf-8") as f:
            _schema_cache = json.load(f)
    return _schema_cache


def load_world_definition_from_dict(data: dict[str, Any]) -> WorldDefinition:
    """从 dict 加载并校验世界定义。

    先做 JSON Schema 校验，再做 Pydantic 类型校验，最后做跨字段引用校验。
    三道校验各司其职，失败时抛出对应层的异常类型。
    """
    jsonschema_validate(instance=data, schema=_get_world_schema())
    wd = WorldDefinition.model_validate(data)
    _validate_cross_references(wd)
    return wd


def load_world_definition(path: str | Path) -> WorldDefinition:
    """从 YAML 文件加载并校验世界定义。"""
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise WorldDefinitionReferenceError(
            f"世界定义文件顶层必须是对象（dict），实际为 "
            f"{type(data).__name__}: {file_path}"
        )
    return load_world_definition_from_dict(data)


def _validate_cross_references(wd: WorldDefinition) -> None:
    """执行跨字段引用与语义一致性校验。

    所有错误一次性收集后抛出，避免用户改一条报一条。
    """
    errors: list[str] = []

    action_names = set(wd.action_types.keys())
    entity_type_names = set(wd.entity_types.keys())
    relation_type_names = set(
        wd.relation_types.keys() if wd.relation_types else []
    )
    environment_var_names = set(
        wd.environment.variables.keys() if wd.environment else []
    )

    # 1. 每个 entity_type 的 actions 必须都在 action_types 中声明
    for ent_name, ent in wd.entity_types.items():
        for act in ent.actions:
            if act not in action_names:
                errors.append(
                    f"entity_types.{ent_name}.actions 引用了未声明的动作 '{act}'"
                )

    # 2. 每个 action_type 的 actor_types 必须都在 entity_types 中声明
    for act_name, act in wd.action_types.items():
        for actor in act.actor_types:
            if actor not in entity_type_names:
                errors.append(
                    f"action_types.{act_name}.actor_types 引用了未声明的实体类型 "
                    f"'{actor}'"
                )

    # 3. defaults.fallback_action 必须存在
    if (
        wd.defaults is not None
        and wd.defaults.fallback_action is not None
        and wd.defaults.fallback_action not in action_names
    ):
        errors.append(
            f"defaults.fallback_action '{wd.defaults.fallback_action}' "
            f"未在 action_types 中声明"
        )

    # 4. perception.include_relations 必须都在 relation_types 中声明
    for ent_name, ent in wd.entity_types.items():
        if ent.perception is None or not ent.perception.include_relations:
            continue
        for rel in ent.perception.include_relations:
            if rel not in relation_type_names:
                errors.append(
                    f"entity_types.{ent_name}.perception.include_relations "
                    f"引用了未声明的关系类型 '{rel}'"
                )

    # 5. activation.environment_triggers.field 必须是已声明的环境变量
    for ent_name, ent in wd.entity_types.items():
        if ent.activation is None or not ent.activation.environment_triggers:
            continue
        for trig in ent.activation.environment_triggers:
            if trig.field not in environment_var_names:
                errors.append(
                    f"entity_types.{ent_name}.activation.environment_triggers "
                    f"引用了未声明的环境变量 '{trig.field}'"
                )

    # 6. activation.attribute_triggers.field 必须是该实体自身已声明的属性
    for ent_name, ent in wd.entity_types.items():
        if ent.activation is None or not ent.activation.attribute_triggers:
            continue
        attr_names = set(ent.attributes.keys())
        for trig in ent.activation.attribute_triggers:
            if trig.field not in attr_names:
                errors.append(
                    f"entity_types.{ent_name}.activation.attribute_triggers "
                    f"引用了未声明的属性 '{trig.field}'"
                )

    # 7. 属性若声明 enum，则必须提供 values；否则不允许出现 values
    for ent_name, ent in wd.entity_types.items():
        for attr_name, attr in ent.attributes.items():
            errors.extend(_validate_attribute_schema(
                f"entity_types.{ent_name}.attributes.{attr_name}", attr
            ))
    if wd.environment is not None:
        for var_name, var in wd.environment.variables.items():
            errors.extend(_validate_attribute_schema(
                f"environment.variables.{var_name}", var
            ))

    if errors:
        raise WorldDefinitionReferenceError(
            f"世界定义存在 {len(errors)} 项跨字段引用/语义错误:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )


def _validate_attribute_schema(path: str, attr: Any) -> list[str]:
    """校验单个 AttributeSchema 的语义一致性，返回错误列表（可能为空）。

    包含：

    - enum 类型必须提供 values；非 enum 类型不得提供 values
    - min/max 的大小关系
    - enum 类型的 default（若提供）必须在 values 中
    """
    errors: list[str] = []

    # enum 类型必须提供 values；非 enum 类型不得提供 values
    if attr.type == "enum":
        if not attr.values:
            errors.append(f"{path}: type=enum 时必须提供非空 values 列表")
        elif attr.default is not None and attr.default not in attr.values:
            errors.append(
                f"{path}: default '{attr.default}' 不在 values {attr.values} 中"
            )
    else:
        if attr.values is not None:
            errors.append(
                f"{path}: 非 enum 类型不应提供 values（type={attr.type}）"
            )

    # min <= max
    if attr.min is not None and attr.max is not None and attr.min > attr.max:
        errors.append(f"{path}: min ({attr.min}) 大于 max ({attr.max})")

    return errors
