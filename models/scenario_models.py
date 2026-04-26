"""场景层的数据模型。

本文件只负责把 scenario.schema.json 映射成 Pydantic 模型，
用于加载和校验一次仿真的实例化内容。

注意：
1. 这里只做结构校验，不做跨文件校验。以下校验统一交给 scenario_loader：
   - `world_id` 是否与加载的 World Definition 一致
   - 实体 `type` 是否在 World Definition 中声明
   - 关系引用的实体 id 是否存在
   - 环境变量是否在 World Definition 中声明
   - `max_ticks >= total_ticks`
2. 这里只描述"本次仿真是什么"，不描述世界的静态结构。
3. 业务规则（动作效果、冲突解决）仍属于 Rules 层。

本文件遵循两条已决策：

1. D-001：`relations / environment / scheduled_events / breakpoints` 为可选字段。
   消费端拿到的 Scenario 对象永远具备对应容器，不会出现 `None`，由 `default_factory`
   保证。详见 `docs/02-design/场景文件格式设计.md` 6.1 节。
2. D-003：`entities` 至少包含一个元素（`min_length=1`），空场景在结构层就挡下。
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ScenarioInfo(BaseModel):
    """场景元信息。"""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, description="场景唯一标识")
    name: str = Field(..., min_length=1, description="场景名称")
    description: str | None = Field(default=None, description="场景描述（可选）")


class EntityInstance(BaseModel):
    """实体实例。"""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, description="实体唯一标识")
    type: str = Field(..., min_length=1, description="实体类型名，必须在 World Definition 中声明")
    name: str | None = Field(default=None, description="实体可读名称（可选）")
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="实体实例属性覆盖值；未提供的属性由 loader 回填 World Definition 默认值",
    )


class RelationInstance(BaseModel):
    """关系实例。"""

    model_config = ConfigDict(extra="forbid")

    type: str = Field(..., description="关系类型，必须在 World Definition 中声明")
    source: str = Field(..., description="源实体 id")
    target: str = Field(..., description="目标实体 id")
    value: float | None = Field(default=None, description="关系强度或值（可选）")


class ScheduledEvent(BaseModel):
    """预设事件。

    根据 `type` 的不同，`payload` 或 `message` 二者应至少一个被使用：

    - `environment_event` → 使用 `payload` 描述环境变化
    - `message_injection` → 使用 `message` 描述注入的消息
    """

    model_config = ConfigDict(extra="forbid")

    tick: int = Field(..., ge=1, description="触发 tick，最小值 1")
    type: Literal["environment_event", "message_injection"] = Field(..., description="事件类型")
    name: str | None = Field(default=None, description="事件名称（可选）")
    payload: dict[str, Any] | None = Field(
        default=None, description="事件载荷；`environment_event` 时使用"
    )
    message: dict[str, Any] | None = Field(
        default=None, description="注入的消息内容；`message_injection` 时使用"
    )


class BreakpointEnvironmentCondition(BaseModel):
    """针对单个环境变量的断点触发条件。"""

    model_config = ConfigDict(extra="forbid")

    gte: float | None = Field(default=None, description="大于等于阈值时触发")
    lte: float | None = Field(default=None, description="小于等于阈值时触发")


class BreakpointEntityCondition(BaseModel):
    """针对某个实体某个属性的断点触发条件。"""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="目标实体 id")
    attribute: str = Field(..., description="目标属性名")
    gte: float | None = Field(default=None, description="大于等于阈值时触发")
    lte: float | None = Field(default=None, description="小于等于阈值时触发")


class BreakpointWhen(BaseModel):
    """断点触发条件容器。

    第一版只支持简单条件组合，不支持复杂布尔表达式。
    `environment` 与 `entity` 至少配置一项才有意义，这条语义检查由 loader 负责。
    """

    model_config = ConfigDict(extra="forbid")

    environment: dict[str, BreakpointEnvironmentCondition] = Field(
        default_factory=dict,
        description="按环境变量名映射到触发条件；未配置时视为空",
    )
    entity: BreakpointEntityCondition | None = Field(
        default=None, description="单个实体属性触发条件（可选）"
    )


class Breakpoint(BaseModel):
    """断点定义。"""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="断点唯一标识")
    when: BreakpointWhen = Field(..., description="断点触发条件")


class PauseMode(BaseModel):
    """暂停策略。"""

    model_config = ConfigDict(extra="forbid")

    manual: bool = Field(default=True, description="是否允许手动暂停")
    every_tick: bool = Field(default=False, description="是否每 tick 自动暂停")


class AnalysisConfig(BaseModel):
    """分析相关配置。

    第一版只定义"需要保留哪些字段"，不定义"如何分析"。
    分析算法本身属于分析层，不属于场景配置。
    """

    model_config = ConfigDict(extra="forbid")

    snapshot_fields: list[Literal["entities", "relations", "environment", "messages"]] | None = Field(
        default=None, description="需要保留的快照字段集合（可选）"
    )


class ScenarioConfig(BaseModel):
    """场景运行参数。"""

    model_config = ConfigDict(extra="forbid")

    total_ticks: int = Field(..., ge=1, description="本次仿真的总轮次")
    max_ticks: int | None = Field(
        default=None,
        ge=1,
        description="安全上限；scenario_loader 需校验 `max_ticks >= total_ticks`",
    )
    pause_mode: PauseMode | None = Field(default=None, description="暂停策略（可选）")
    snapshot_mode: Literal["every_tick", "on_pause", "on_end"] | None = Field(
        default=None, description="快照保存频率（可选）"
    )
    analysis: AnalysisConfig | None = Field(default=None, description="分析配置（可选）")


class Scenario(BaseModel):
    """场景顶层模型。

    这是一次具体仿真实例在 Python 中的结构化表示。
    它描述"本次仿真里具体是什么"，不描述世界的静态结构，
    也不定义动作如何生效。
    """

    model_config = ConfigDict(extra="forbid")

    version: Literal["0.1"] = Field(..., description="场景文件格式版本")
    world_id: str = Field(..., min_length=1, description="引用的世界定义 id")
    rules_module: str | None = Field(
        default=None,
        min_length=1,
        pattern=r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*:[A-Za-z_][A-Za-z0-9_]*$",
        description=(
            "可选；规则模块导入路径（D-010），格式 'module.path:ClassName'。"
            "由 `core/rules_loader.load_rules_class` 解析为 `BaseRules` 子类。"
            "未声明时，Runtime 需由调用方显式传入 rules 实例。"
            "注：pattern 与 `schemas/scenario.schema.json` 保持同步。"
        ),
    )
    scenario: ScenarioInfo = Field(..., description="场景元信息")
    entities: list[EntityInstance] = Field(
        ..., min_length=1, description="实体实例列表，至少包含一个（D-003）"
    )
    relations: list[RelationInstance] = Field(
        default_factory=list, description="初始关系列表；未提供则为空（D-001）"
    )
    environment: dict[str, Any] = Field(
        default_factory=dict,
        description="环境初始值；未提供的变量由 loader 回填 World Definition 默认值",
    )
    scheduled_events: list[ScheduledEvent] = Field(
        default_factory=list, description="预设事件列表；未提供则为空（D-001）"
    )
    breakpoints: list[Breakpoint] = Field(
        default_factory=list, description="断点列表；未提供则为空（D-001）"
    )
    config: ScenarioConfig = Field(..., description="场景运行参数")
