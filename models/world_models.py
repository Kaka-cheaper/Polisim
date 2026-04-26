"""世界定义层的数据模型。

本文件只负责把 world_definition.schema.json 映射成 Pydantic 模型，
用于加载和校验世界定义的静态结构。

注意：
1. 这里只做结构校验，不做运行时行为推演。
2. 这里只描述“世界允许有什么”，不处理具体场景实例。
3. 业务规则如何执行，仍然由 Rules 层负责。
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class WorldInfo(BaseModel):
    """世界定义本身的元信息。"""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, description="世界唯一标识")
    name: str = Field(..., min_length=1, description="世界名称")
    description: str | None = Field(default=None, description="世界描述（可选）")


class AttributeSchema(BaseModel):
    """属性模板定义。

    用于描述实体属性或环境变量的类型、范围、默认值等静态约束。
    """

    model_config = ConfigDict(extra="allow")

    type: Literal["number", "string", "boolean", "enum", "entity_ref"] = Field(
        ..., description="属性类型"
    )
    min: float | None = Field(default=None, description="数值最小值（可选）")
    max: float | None = Field(default=None, description="数值最大值（可选）")
    default: Any = Field(default=None, description="默认值")
    values: list[str] | None = Field(default=None, description="枚举候选值列表")
    clamp: bool = Field(default=True, description="是否自动截断到 min/max 范围")


class ActivationEnvironmentTrigger(BaseModel):
    """环境变化触发条件。"""

    model_config = ConfigDict(extra="allow")

    field: str = Field(..., description="环境变量字段名")
    gte_delta: float | None = Field(default=None, description="变化量大于等于阈值时触发")
    lte_delta: float | None = Field(default=None, description="变化量小于等于阈值时触发")


class ActivationAttributeTrigger(BaseModel):
    """实体属性触发条件。"""

    model_config = ConfigDict(extra="allow")

    field: str = Field(..., description="实体属性字段名")
    gte: float | None = Field(default=None, description="属性值大于等于阈值时触发")
    lte: float | None = Field(default=None, description="属性值小于等于阈值时触发")


class ActivationSchema(BaseModel):
    """实体激活策略。

    Runtime 会读取这里的配置来决定某个实体在当前 tick 是否进入决策流程。
    """

    model_config = ConfigDict(extra="allow")

    on_message: bool = Field(default=True, description="收到消息时是否激活")
    decision_interval: int = Field(default=1, ge=1, description="最短决策间隔，单位为 tick")
    wake_on: list[Literal["environment_changed", "relation_changed", "action_finished"]] | None = Field(
        default=None, description="关键事件触发器"
    )
    environment_triggers: list[ActivationEnvironmentTrigger] | None = Field(
        default=None, description="环境变量变化触发条件"
    )
    attribute_triggers: list[ActivationAttributeTrigger] | None = Field(
        default=None, description="实体属性触发条件"
    )


class PerceptionSchema(BaseModel):
    """实体感知范围定义。"""

    model_config = ConfigDict(extra="forbid")

    scope: Literal["global", "relation", "attribute", "custom"] = Field(
        ..., description="感知范围类型"
    )
    include_relations: list[str] | None = Field(default=None, description="需要纳入感知的关系类型列表")


class EntityTypeSchema(BaseModel):
    """实体类型模板。"""

    model_config = ConfigDict(extra="forbid")

    description: str | None = Field(default=None, description="实体类型描述")
    decision_mode: Literal["llm", "rule", "random"] = Field(..., description="决策模式")
    activation: ActivationSchema | None = Field(default=None, description="激活策略")
    perception: PerceptionSchema | None = Field(default=None, description="感知范围")
    attributes: dict[str, AttributeSchema] = Field(..., description="属性模板定义")
    actions: list[str] = Field(..., min_length=1, description="该实体类型允许使用的动作列表")


class RelationTypeSchema(BaseModel):
    """关系类型模板。"""

    model_config = ConfigDict(extra="forbid")

    description: str | None = Field(default=None, description="关系描述")
    directed: bool = Field(..., description="是否有方向")
    transient: bool = Field(..., description="是否允许在运行时动态变化")


class MessagePayloadFieldSchema(BaseModel):
    """消息载荷字段定义。"""

    model_config = ConfigDict(extra="allow")

    type: Literal["string", "number", "boolean"] = Field(..., description="消息字段类型")


class MessageTypeSchema(BaseModel):
    """消息类型模板。"""

    model_config = ConfigDict(extra="forbid")

    description: str | None = Field(default=None, description="消息类型描述")
    delivery: Literal["direct", "broadcast", "by_relation"] = Field(
        ..., description="消息路由方式"
    )
    payload: dict[str, MessagePayloadFieldSchema] | None = Field(
        default=None, description="消息载荷字段定义"
    )


class ActionParamSchema(BaseModel):
    """动作参数定义。"""

    model_config = ConfigDict(extra="forbid")

    type: Literal["number", "string", "boolean", "entity_ref"] = Field(..., description="参数类型")
    required: bool = Field(default=False, description="是否必填")


class ActionEffectSchema(BaseModel):
    """动作效果类型定义。"""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["self_attribute", "relation", "message", "environment"] = Field(
        ..., description="效果类别"
    )


class ActionTypeSchema(BaseModel):
    """动作类型模板。"""

    model_config = ConfigDict(extra="forbid")

    description: str | None = Field(default=None, description="动作描述")
    actor_types: list[str] = Field(..., min_length=1, description="允许执行该动作的实体类型列表")
    params: dict[str, ActionParamSchema] = Field(..., description="动作参数定义")
    effects: list[ActionEffectSchema] = Field(..., description="动作效果类型列表")


class EnvironmentSchema(BaseModel):
    """环境变量模板集合。"""

    model_config = ConfigDict(extra="forbid")

    variables: dict[str, AttributeSchema] = Field(..., description="环境变量定义")


class DefaultsSchema(BaseModel):
    """运行默认参数。

    这些参数是世界级默认值，不等同于规则实现本身。
    """

    model_config = ConfigDict(extra="forbid")

    conflict_resolution: Literal["both", "priority", "random"] = Field(
        default="both", description="默认冲突解决策略"
    )
    max_messages_per_tick: int = Field(default=100, ge=1, description="单 tick 消息上限")
    fallback_action: str | None = Field(default=None, description="决策失败时的降级动作")
    action_effect_order: list[Literal["self_attribute", "relation", "environment", "message"]] = Field(
        default_factory=lambda: ["self_attribute", "relation", "environment", "message"],
        description="动作效果的默认执行顺序",
    )


class WorldDefinition(BaseModel):
    """世界定义顶层模型。

    这是整个世界定义文件在 Python 中的结构化表示。
    它只描述静态结构，不描述一次具体仿真。
    """

    model_config = ConfigDict(extra="forbid")

    version: Literal["0.1"] = Field(..., description="世界定义格式版本")
    world: WorldInfo = Field(..., description="世界元信息")
    entity_types: dict[str, EntityTypeSchema] = Field(..., description="实体类型定义")
    relation_types: dict[str, RelationTypeSchema] | None = Field(default=None, description="关系类型定义")
    message_types: dict[str, MessageTypeSchema] | None = Field(default=None, description="消息类型定义")
    action_types: dict[str, ActionTypeSchema] = Field(..., description="动作类型定义")
    environment: EnvironmentSchema | None = Field(default=None, description="环境变量模板")
    defaults: DefaultsSchema | None = Field(default=None, description="运行默认参数")
