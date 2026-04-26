"""场景加载器。

职责：

1. 从 YAML 文件或 dict 加载场景数据
2. 用 JSON Schema（`schemas/scenario.schema.json`）做结构校验
3. 用 Pydantic（`models/scenario_models.py`）做类型校验
4. 执行跨字段与跨文件引用校验——这一层需要同时访问 `WorldDefinition` 与 `Scenario`

跨文件校验清单（对齐 `docs/02-design/场景文件格式设计.md` 第六节）：

- `world_id` 与加载的 `WorldDefinition.world.id` 一致
- 所有实体 `id` 唯一
- 所有实体 `type` 必须是世界定义中声明的实体类型
- 实体属性 override 的 key 必须在对应 entity_type 的 attributes schema 中
- 关系 `type` 必须是世界定义中声明的关系类型
- 关系的 `source` / `target` 必须引用已声明的实体
- 环境变量必须在世界定义的 `environment.variables` 中声明
- `max_ticks >= total_ticks`
- 断点 `entity.id` / `entity.attribute` 必须合法；`environment` 变量必须已声明；
  两者至少配置一项；条件至少提供一个阈值（`gte` / `lte`）
- `scheduled_events` 按 `type` 与 `payload` / `message` 的一致性：
  `environment_event` 走 `payload`，`message_injection` 走 `message`，
  且 `message.type` 必须在世界定义中声明

不负责：

1. 推进仿真（属 Runtime）
2. 解释动作效果、冲突处理（属 Rules）
3. 校验世界定义本身（属 `core/definition_loader.py`）
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from jsonschema import validate as jsonschema_validate

from models.scenario_models import Scenario
from models.world_models import WorldDefinition


class ScenarioReferenceError(ValueError):
    """场景的跨字段引用或跨文件一致性校验失败。"""


_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "schemas" / "scenario.schema.json"
)

_schema_cache: dict[str, Any] | None = None


def _get_scenario_schema() -> dict[str, Any]:
    """加载并缓存 JSON Schema。"""
    global _schema_cache
    if _schema_cache is None:
        with _SCHEMA_PATH.open("r", encoding="utf-8") as f:
            _schema_cache = json.load(f)
    return _schema_cache


def load_scenario_from_dict(
    data: dict[str, Any],
    world_definition: WorldDefinition,
) -> Scenario:
    """从 dict 加载并校验场景。

    三道校验：JSON Schema（结构）→ Pydantic（类型）→ loader（跨字段/跨文件引用）。
    """
    jsonschema_validate(instance=data, schema=_get_scenario_schema())
    scenario = Scenario.model_validate(data)
    _validate_cross_references(scenario, world_definition)
    return scenario


def load_scenario(
    path: str | Path,
    world_definition: WorldDefinition,
) -> Scenario:
    """从 YAML 文件加载并校验场景。"""
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ScenarioReferenceError(
            f"场景文件顶层必须是对象（dict），实际为 "
            f"{type(data).__name__}: {file_path}"
        )
    return load_scenario_from_dict(data, world_definition)


def _validate_cross_references(
    scenario: Scenario,
    wd: WorldDefinition,
) -> None:
    """执行跨字段/跨文件引用与语义一致性校验。

    所有错误一次性收集后抛出，便于用户一次修复。
    """
    errors: list[str] = []

    # --- 预计算集合 ---
    entity_ids_list = [e.id for e in scenario.entities]
    entity_ids = set(entity_ids_list)
    entity_type_of: dict[str, str] = {e.id: e.type for e in scenario.entities}

    world_entity_type_names = set(wd.entity_types.keys())
    world_relation_type_names = set(
        wd.relation_types.keys() if wd.relation_types else []
    )
    world_message_type_names = set(
        wd.message_types.keys() if wd.message_types else []
    )
    world_env_var_names = set(
        wd.environment.variables.keys() if wd.environment else []
    )

    # --- 1. world_id 一致性 ---
    if scenario.world_id != wd.world.id:
        errors.append(
            f"world_id '{scenario.world_id}' 与加载的世界定义 id "
            f"'{wd.world.id}' 不一致"
        )

    # --- 2. 实体 id 唯一性 ---
    seen: set[str] = set()
    dup: set[str] = set()
    for eid in entity_ids_list:
        if eid in seen:
            dup.add(eid)
        seen.add(eid)
    for d in sorted(dup):
        errors.append(f"entities 中实体 id '{d}' 重复声明")

    # --- 3. 实体 type 合法性 ---
    for ent in scenario.entities:
        if ent.type not in world_entity_type_names:
            errors.append(
                f"entities[id={ent.id}].type '{ent.type}' "
                f"未在世界定义 entity_types 中声明"
            )

    # --- 4. 实体属性 override 必须在对应 entity_type 的 attributes schema 中 ---
    for ent in scenario.entities:
        if ent.type not in wd.entity_types:
            continue  # 已在 #3 报错
        declared = set(wd.entity_types[ent.type].attributes.keys())
        for key in ent.attributes.keys():
            if key not in declared:
                errors.append(
                    f"entities[id={ent.id}].attributes 包含未在 "
                    f"entity_types.{ent.type}.attributes 中声明的属性 '{key}'"
                )

    # --- 5. 关系 type 合法性 ---
    for idx, rel in enumerate(scenario.relations):
        if rel.type not in world_relation_type_names:
            errors.append(
                f"relations[{idx}].type '{rel.type}' "
                f"未在世界定义 relation_types 中声明"
            )

    # --- 6. 关系 source/target 指向已声明的实体 ---
    for idx, rel in enumerate(scenario.relations):
        if rel.source not in entity_ids:
            errors.append(
                f"relations[{idx}].source '{rel.source}' 未在 entities 中声明"
            )
        if rel.target not in entity_ids:
            errors.append(
                f"relations[{idx}].target '{rel.target}' 未在 entities 中声明"
            )

    # --- 7. 环境变量在世界定义中声明 ---
    for var_name in scenario.environment.keys():
        if var_name not in world_env_var_names:
            errors.append(
                f"environment 包含未在世界定义中声明的变量 '{var_name}'"
            )

    # --- 8. max_ticks >= total_ticks ---
    if (
        scenario.config.max_ticks is not None
        and scenario.config.max_ticks < scenario.config.total_ticks
    ):
        errors.append(
            f"config.max_ticks ({scenario.config.max_ticks}) 必须大于等于 "
            f"total_ticks ({scenario.config.total_ticks})"
        )

    # --- 9. 断点校验 ---
    for bp in scenario.breakpoints:
        errors.extend(
            _validate_breakpoint(bp, entity_ids, entity_type_of, wd, world_env_var_names)
        )

    # --- 10. scheduled_events 的 payload/message 与 type 一致 ---
    for idx, ev in enumerate(scenario.scheduled_events):
        if ev.type == "environment_event":
            if ev.payload is None:
                errors.append(
                    f"scheduled_events[{idx}] type=environment_event 必须提供 payload"
                )
            if ev.message is not None:
                errors.append(
                    f"scheduled_events[{idx}] type=environment_event 不应提供 message"
                )
        elif ev.type == "message_injection":
            if ev.message is None:
                errors.append(
                    f"scheduled_events[{idx}] type=message_injection 必须提供 message"
                )
            if ev.payload is not None:
                errors.append(
                    f"scheduled_events[{idx}] type=message_injection 不应提供 payload"
                )
            if ev.message is not None:
                msg_type = ev.message.get("type")
                if msg_type is not None and msg_type not in world_message_type_names:
                    errors.append(
                        f"scheduled_events[{idx}].message.type '{msg_type}' "
                        f"未在世界定义 message_types 中声明"
                    )

    if errors:
        raise ScenarioReferenceError(
            f"场景存在 {len(errors)} 项跨字段/跨文件引用错误:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )


def _validate_breakpoint(
    bp: Any,
    entity_ids: set[str],
    entity_type_of: dict[str, str],
    wd: WorldDefinition,
    world_env_var_names: set[str],
) -> list[str]:
    """校验单个断点配置，返回错误列表（可能为空）。"""
    errors: list[str] = []

    # 至少配置 entity 或 environment 其中一项
    if bp.when.entity is None and not bp.when.environment:
        errors.append(
            f"breakpoints[id={bp.id}].when 必须至少配置 entity 或 environment 其中一项"
        )

    # entity 条件
    if bp.when.entity is not None:
        ec = bp.when.entity
        if ec.id not in entity_ids:
            errors.append(
                f"breakpoints[id={bp.id}].when.entity.id '{ec.id}' "
                f"未在 entities 中声明"
            )
        elif ec.id in entity_type_of:
            et_name = entity_type_of[ec.id]
            if et_name in wd.entity_types:
                declared = set(wd.entity_types[et_name].attributes.keys())
                if ec.attribute not in declared:
                    errors.append(
                        f"breakpoints[id={bp.id}].when.entity.attribute "
                        f"'{ec.attribute}' 未在 entity_types.{et_name}.attributes 中声明"
                    )

        if ec.gte is None and ec.lte is None:
            errors.append(
                f"breakpoints[id={bp.id}].when.entity 必须至少设置一个阈值"
                f"（gte 或 lte）"
            )

    # environment 条件
    for var_name, cond in bp.when.environment.items():
        if var_name not in world_env_var_names:
            errors.append(
                f"breakpoints[id={bp.id}].when.environment 引用了未声明的环境变量 "
                f"'{var_name}'"
            )
        if cond.gte is None and cond.lte is None:
            errors.append(
                f"breakpoints[id={bp.id}].when.environment['{var_name}'] "
                f"必须至少设置一个阈值（gte 或 lte）"
            )

    return errors
