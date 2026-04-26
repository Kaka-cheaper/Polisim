"""运行时数据模型。

对应 `docs/02-design/运行时与事件轨迹设计.md` 第四节"运行时核心对象"与第九节
"事件轨迹设计"，以及 `docs/02-design/实现映射设计.md` 4.4 / 4.5 节的落点建议。

本文件只定义"状态容器"与"事件/快照条目"——**不承载任何业务逻辑**：

- LLM 决策协议由 `models/llm_models.py` 描述（本文件不依赖 LLM 层）
- 动作效果（effect）由 `rules/` 层定义并执行
- tick 主循环、消息投递、激活调度由 `core/runtime.py` 实现
- append-only log 的读写与快照存储由 `core/events.py` 实现

模型层约束：

1. 所有类型均使用 Pydantic v2 + ``ConfigDict(extra="forbid")``
   （与 `world_models.py` / `scenario_models.py` / `config_models.py` 风格一致）
2. 结构字段不做跨模型语义校验（例如 `ActionProposal.action_type` 是否在
   World Definition 中声明、`EventRecord.actor_id` 是否指向有效实体等）。
   这些校验属于 Runtime / Loader 职责
3. 字段下限与枚举值直接内嵌，使得错误值在"构造时刻"就被挡下，不污染后续层
4. 运行时模型默认是**可变**（Pydantic v2 默认 mutable），便于 tick 推进中就地更新
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# =============================================================================
# 类型别名
# =============================================================================

DecisionMode = Literal["llm", "rule", "random", "fallback"]
"""决策产生路径。

- ``llm`` / ``rule`` / ``random``：对齐 ``world.entity_types[*].decision_mode``
- ``fallback``：Runtime 在原决策失败/超时后使用降级动作生成的提议
"""

ProposalStatus = Literal["proposed", "rejected", "retried", "executed", "fallback"]
"""决策提议在单 tick 内的生命周期状态。

对应 `运行时与事件轨迹设计.md` 第九节列出的决策相关事件类型：
``decision_proposed / decision_rejected / decision_retried / fallback_used /
action_executed``。
"""

EventKind = Literal[
    "decision_proposed",
    "decision_rejected",
    "decision_retried",
    "fallback_used",
    "action_executed",
    "message_emitted",
    "relation_changed",
    "environment_changed",
    "scheduled_event_triggered",
    "intervention_applied",
    "breakpoint_triggered",
    "snapshot_saved",
]
"""事件轨迹支持的事件类型。

枚举值严格对齐 `运行时与事件轨迹设计.md` 第九节第一版事件清单；扩展需先更新设计文档。
"""


# =============================================================================
# 消息
# =============================================================================


class MessageEnvelope(BaseModel):
    """消息信封：代表一条"已发出或已投递"的消息实例。

    设计要点（对应 `运行时与事件轨迹设计.md` 第五节消息时序）：

    1. 消息在 tick T 被某动作产生 → ``tick_emitted = T``、``tick_delivered = None``
    2. 下一 tick 开始时 Runtime 投递到目标 mailbox → ``tick_delivered = T + 1``
    3. ``tick_delivered is None`` 表示消息还在 outbox，本 tick 内对其他实体不可见
    """

    model_config = ConfigDict(extra="forbid")

    tick_emitted: int = Field(..., ge=1, description="消息被发出的 tick")
    tick_delivered: int | None = Field(
        default=None,
        ge=1,
        description="消息被投递到收件箱的 tick；None 表示仍在 outbox",
    )
    message_type: str = Field(
        ..., min_length=1, description="消息类型名，必须在 World Definition.message_types 中声明"
    )
    from_actor: str | None = Field(
        default=None,
        description="发送方实体 id；为 None 表示来自 scheduled_event 注入",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict, description="消息载荷；字段形状由 World Definition.message_types 规定"
    )


# =============================================================================
# 实体 / 关系 运行时状态
# =============================================================================


class EntityRuntimeState(BaseModel):
    """单个实体在当前 tick 的运行时状态。

    与 `models/scenario_models.EntityInstance` 的区别：

    - EntityInstance 描述"场景文件里写的初始化覆盖值"，字段语义是 override
    - EntityRuntimeState 描述"跑到当前 tick 时该实体的全部当前属性值"，无 override 语义
    - 由 Runtime 初始化时从 World Definition 默认值 + Scenario 覆盖值合并生成
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, description="实体唯一标识")
    type: str = Field(..., min_length=1, description="实体类型名")
    name: str | None = Field(default=None, description="实体可读名称（可选）")
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="当前属性值；键集合应与 World Definition.entity_types[type].attributes 对齐",
    )


class RelationRuntimeState(BaseModel):
    """单个关系在当前 tick 的运行时状态。"""

    model_config = ConfigDict(extra="forbid")

    type: str = Field(..., min_length=1, description="关系类型名")
    source: str = Field(..., min_length=1, description="源实体 id")
    target: str = Field(..., min_length=1, description="目标实体 id")
    value: float | None = Field(default=None, description="关系强度或值（可选）")


# =============================================================================
# 世界状态聚合
# =============================================================================


class WorldState(BaseModel):
    """运行时世界状态聚合对象。

    对应 `运行时与事件轨迹设计.md` 4.1 节。每个 tick 结束后，Runtime 应该持有
    一份"该 tick 结束时刻"的完整 WorldState，供下一 tick 的决策基础以及
    快照生成使用。

    - ``tick = 0`` 代表"初始化完毕、尚未推进第 1 个 tick"的状态
    - ``tick = N (N >= 1)`` 代表"第 N 个 tick 执行完毕后的状态"
    """

    model_config = ConfigDict(extra="forbid")

    tick: int = Field(..., ge=0, description="当前 tick，0 表示初始状态")
    entities: dict[str, EntityRuntimeState] = Field(
        default_factory=dict, description="按实体 id 索引的当前状态字典"
    )
    relations: list[RelationRuntimeState] = Field(
        default_factory=list, description="当前生效的全部关系"
    )
    environment: dict[str, Any] = Field(
        default_factory=dict, description="当前环境变量值集合"
    )
    mailboxes: dict[str, list[MessageEnvelope]] = Field(
        default_factory=dict,
        description="按实体 id 索引的收件箱；未出现的实体视为空收件箱",
    )


# =============================================================================
# 决策提议
# =============================================================================


class ActionProposal(BaseModel):
    """单个实体在某 tick 的动作提议。

    对应 `运行时与事件轨迹设计.md` 4.2 节。每个被激活且完成决策流程的实体，
    在每个 tick 都会产生至少一条 ActionProposal 记录。同一实体若触发重试，
    可能产生多条 ActionProposal，通过 ``status`` 字段区分。
    """

    model_config = ConfigDict(extra="forbid")

    tick: int = Field(..., ge=1, description="产生该提议的 tick")
    actor_id: str = Field(..., min_length=1, description="提出动作的实体 id")
    action_type: str = Field(
        ..., min_length=1, description="动作类型名，必须在 World Definition.action_types 中声明"
    )
    params: dict[str, Any] = Field(
        default_factory=dict, description="动作参数，形状由 World Definition 对应 action 的 params 规定"
    )
    decision_mode: DecisionMode = Field(..., description="决策产生路径")
    raw_reasoning_summary: str | None = Field(
        default=None, description="LLM 思考过程的简要摘要（仅 llm 模式；可选）"
    )
    status: ProposalStatus = Field(..., description="生命周期状态")


# =============================================================================
# 事件记录
# =============================================================================


class EventRecord(BaseModel):
    """append-only 事件轨迹中的一条记录。

    对应 `运行时与事件轨迹设计.md` 4.3 节与第十节示例结构。事件一旦写入便不再修改，
    任何状态演化都通过"追加新事件"而非"改写旧事件"来表达。

    ``payload`` 字段形状因 ``kind`` 不同而不同，本模型不做 payload 结构校验，
    由 `core/events.py` 的 recorder 对具体 kind 负责封装。
    """

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(..., min_length=1, description="全局唯一事件 id")
    tick: int = Field(..., ge=0, description="事件发生时的 tick，0 表示初始化事件")
    kind: EventKind = Field(..., description="事件类型")
    actor_id: str | None = Field(
        default=None,
        description="事件主体实体 id；环境事件 / 快照事件 / 干预事件等可能为 None",
    )
    payload: dict[str, Any] = Field(
        default_factory=dict, description="事件载荷；形状由 kind 决定，本层不校验"
    )


# =============================================================================
# Effect（规则层产出，运行时消费）
# =============================================================================


class AttributeEffect(BaseModel):
    """对某实体的某属性施加的效果——**支持数值增量（delta）或绝对值赋值（new_value）**。

    **D-015 缩限版**（2026-04 落地）：本模型新增 ``new_value: Any`` 字段，与
    ``delta`` 二选一（model_validator 强制）。这部分解除了 v1 仅能改数值属性
    的限制——现在也能表达：

    - 把 enum 属性从 ``"balanced"`` 改到 ``"aggressive"``（用 ``new_value``）
    - 把 boolean 属性翻转（用 ``new_value=True/False``）
    - 把 string 属性重写（用 ``new_value="xxx"``）

    数值属性既可用 ``delta``（增量）也可用 ``new_value``（绝对值赋值）。

    **下游适配**：``BaseRules.apply_constraints`` 对 ``new_value`` 形式的
    AttributeEffect 当前**透传不裁剪**——后续若需要绝对值版本的 clamp，
    在该 helper 内追加分支即可，不影响本模型契约。

    ⚠️ **历史背景**（D-015 之前的限制，现已部分结清）：

    - 旧版本只能表达 numeric 属性的 delta（加减数值），**不能**表达：
      - 把 enum 属性从 ``"balanced"`` 改到 ``"aggressive"``
      - 把 boolean 属性翻转
      - 把 string 属性重写
    - **D-015 缩限版**已用 ``new_value`` 字段填补该缺口（见上）；
      `Intervention.override_attribute` 仍保留为"人工干预"路径，会写
      `intervention_applied` 事件——两者职责不同，不冲突

    ``kind`` 是 Literal 常量，供上层做 discriminated union 分发。
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["self_attribute"] = Field(
        default="self_attribute", description="效果类别常量"
    )
    actor_id: str = Field(..., min_length=1, description="目标实体 id")
    attribute: str = Field(..., min_length=1, description="目标属性名")
    delta: float | None = Field(
        default=None, description="数值增量；正数增加、负数减少。与 new_value 二选一"
    )
    new_value: Any = Field(
        default=None,
        description="绝对值赋值（适用于 enum/string/bool 或数值绝对值）。"
        "与 delta 二选一。**注意**：v1 用 None 兼任 sentinel——无法把属性显式赋为 None",
    )

    @model_validator(mode="after")
    def _check_delta_xor_new_value(self) -> "AttributeEffect":
        """D-015：``delta`` 与 ``new_value`` 必须二选一（不能都给也不能都不给）。"""
        if self.delta is None and self.new_value is None:
            raise ValueError(
                "AttributeEffect 必须给 delta 或 new_value 之一（不能都为 None）"
            )
        if self.delta is not None and self.new_value is not None:
            raise ValueError(
                "AttributeEffect 的 delta 与 new_value 不能同时给——二选一"
            )
        return self


class RelationEffect(BaseModel):
    """对关系的变更效果。

    v1 支持三种操作：

    - ``add``——创建一条新关系（同三元组已存在时由 Runtime 决定是否覆盖）
    - ``update_value``——更新既有关系的 value
    - ``remove``——删除一条关系
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["relation"] = Field(default="relation", description="效果类别常量")
    operation: Literal["add", "update_value", "remove"] = Field(
        ..., description="对关系的操作类型"
    )
    relation_type: str = Field(..., min_length=1, description="关系类型名")
    source: str = Field(..., min_length=1, description="源实体 id")
    target: str = Field(..., min_length=1, description="目标实体 id")
    value: float | None = Field(
        default=None, description="add / update_value 时必需；remove 时忽略"
    )

    @model_validator(mode="after")
    def _value_required_for_add_update(self) -> "RelationEffect":
        if self.operation in ("add", "update_value") and self.value is None:
            raise ValueError(
                f"operation='{self.operation}' 必须提供 value 字段"
            )
        return self


class MessageEffect(BaseModel):
    """产生一条消息的效果。

    封装一个已组装好的 ``MessageEnvelope``，由 Runtime 在动作执行后投入 outbox，
    下一 tick 才投递到目标 mailbox（遵循"同时决策、延迟可见"）。
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["message"] = Field(default="message", description="效果类别常量")
    envelope: "MessageEnvelope" = Field(..., description="待投递的消息信封")


class EnvironmentEffect(BaseModel):
    """对全局环境变量的数值增量。"""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["environment"] = Field(
        default="environment", description="效果类别常量"
    )
    variable: str = Field(..., min_length=1, description="环境变量名")
    delta: float = Field(..., description="数值增量")


Effect = AttributeEffect | RelationEffect | MessageEffect | EnvironmentEffect
"""规则层产出的一条具体效果。

由 ``kind`` 字段做 discriminated union 分发；所有 4 个子类已对齐
``ActionEffectSchema.kind`` 的 Literal 枚举。
"""


# =============================================================================
# 校验结果
# =============================================================================


class ValidationResult(BaseModel):
    """`BaseRules.validate_action` 的返回类型。

    - ``valid=True`` 时 ``errors`` 应为空列表
    - ``valid=False`` 时 ``errors`` 至少有 1 条可读的中文错误描述
    - 多条错误一次性返回，便于 Runtime 日志 / UI 一次展示所有问题
    """

    model_config = ConfigDict(extra="forbid")

    valid: bool = Field(..., description="动作提议是否合法")
    errors: list[str] = Field(
        default_factory=list, description="不合法时的原因清单；合法时为空"
    )


# =============================================================================
# 快照
# =============================================================================


class MessageSummary(BaseModel):
    """单 tick 消息统计。

    第一版只维护最粗粒度的两个计数，不保存完整消息轨迹（完整轨迹走 EventRecord）。
    对应 `运行时与事件轨迹设计.md` 第十一节示例。
    """

    model_config = ConfigDict(extra="forbid")

    emitted: int = Field(default=0, ge=0, description="本 tick 产生的消息数")
    delivered_next_tick: int = Field(
        default=0, ge=0, description="将在下一 tick 被投递的消息数"
    )


class Intervention(BaseModel):
    """人工干预记录。

    对齐 `需求分析.md` 8.3 节"人工干预三级"，以及 D-008 对 Runtime 步进式接口的要求
    （`Runtime.intervene(intervention)`）：

    1. ``inject_message``——向某实体（或广播）注入一条消息，绕过正常动作产出路径
    2. ``force_action``——强制某实体在指定 tick 执行一个动作，覆盖其 LLM/规则决策
    3. ``override_attribute``——直接修改实体属性，绕过规则层

    所有 Intervention 经 Runtime 处理后会**同时**写入一条
    ``EventRecord(kind='intervention_applied')``，确保 `需求分析.md` 8.3 要求的
    "所有干预必须可追溯"。Intervention 对象本身是**输入**（通常来自 CLI / UI），
    不是 Event Log 的直接条目。

    字段约束由 `model_validator` 强制：

    - ``inject_message`` 必须提供 ``message``；``target_actor=None`` 表示广播
    - ``force_action`` 必须提供 ``action`` 与 ``target_actor``
    - ``override_attribute`` 必须提供 ``attribute_changes`` 与 ``target_actor``
    """

    model_config = ConfigDict(extra="forbid")

    tick: int = Field(..., ge=1, description="生效 tick；干预在该 tick 开始前应用")
    kind: Literal["inject_message", "force_action", "override_attribute"] = Field(
        ..., description="干预类型，对应需求分析 8.3 的三级"
    )
    target_actor: str | None = Field(
        default=None,
        description="目标实体 id；inject_message 可为 None（广播）；其余两类必需",
    )
    message: dict[str, Any] | None = Field(
        default=None,
        description="inject_message 时使用；至少包含 message_type 与 payload",
    )
    action: dict[str, Any] | None = Field(
        default=None,
        description="force_action 时使用；至少包含 action_type 与 params",
    )
    attribute_changes: dict[str, Any] | None = Field(
        default=None,
        description="override_attribute 时使用；键为属性名，值为新值",
    )
    reason: str | None = Field(
        default=None, description="操作者的说明/理由；可选，用于审计追溯"
    )

    @model_validator(mode="after")
    def _payload_matches_kind(self) -> "Intervention":
        if self.kind == "inject_message":
            if self.message is None:
                raise ValueError(
                    "kind='inject_message' 必须提供 message 字段"
                )
        elif self.kind == "force_action":
            if self.action is None:
                raise ValueError(
                    "kind='force_action' 必须提供 action 字段"
                )
            if not self.target_actor:
                raise ValueError(
                    "kind='force_action' 必须提供 target_actor"
                )
        elif self.kind == "override_attribute":
            if self.attribute_changes is None:
                raise ValueError(
                    "kind='override_attribute' 必须提供 attribute_changes 字段"
                )
            if not self.target_actor:
                raise ValueError(
                    "kind='override_attribute' 必须提供 target_actor"
                )
        return self


# =============================================================================
# 快照
# =============================================================================


class Snapshot(BaseModel):
    """某个 tick 结束后的全局快照。

    对应 `运行时与事件轨迹设计.md` 4.4 节与第十一节示例。快照是**分析层**
    的主要输入源之一，要求能从任意一份快照 + 事件轨迹复原该 tick 的全貌。

    - ``tick = 0`` 对应"场景加载完成、第 1 tick 开始前"的初始快照
    - 保存频率由 ``Scenario.config.snapshot_mode`` 决定，Runtime 按配置触发
    """

    model_config = ConfigDict(extra="forbid")

    tick: int = Field(..., ge=0, description="快照对应的 tick")
    entity_state_summary: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="按实体 id 映射到属性快照（通常是当前 attributes 的拷贝）",
    )
    relation_state_summary: list[dict[str, Any]] = Field(
        default_factory=list,
        description="当前关系状态列表，每项至少包含 type / source / target",
    )
    environment_state: dict[str, Any] = Field(
        default_factory=dict, description="环境变量快照"
    )
    message_summary: MessageSummary = Field(
        default_factory=MessageSummary, description="消息统计（emitted / delivered_next_tick）"
    )


# =============================================================================
# TickResult（D-008：Runtime.step() 的返回对象）
# =============================================================================


class TickResult(BaseModel):
    """单次 tick 执行结果。

    对应 `运行时与事件轨迹设计.md` 13.2 节约定——每次 `Runtime.step()` 返回
    一个本对象，包含：

    - 本 tick 产生的**新增**事件列表（Runtime 已将它们 append 到 EventLog）
    - 本 tick 结束后的快照（``snapshot_mode`` 决定是否保存；未保存时为 None）
    - 本 tick 结束时是否应当暂停（``paused_after``）与触发的断点 id 列表
    - 是否达到 ``total_ticks`` 边界（``reached_total_ticks``）

    **调用方契约**：

    - ``events`` 是本 tick 新产生的记录——已经被 Runtime append 到 EventLog；
      TickResult 内的拷贝只是方便调用方同步消费（如 UI 实时刷新）
    - ``snapshot`` 为 None 表示本 tick 按 ``snapshot_mode`` 未保存，可通过
      `Runtime.get_snapshot(tick)` 随时补查（若运行时仍在内存中）
    - ``reached_total_ticks=True`` 时**不得**再调用 `step()`——Runtime 会拒绝
    """

    model_config = ConfigDict(extra="forbid")

    tick: int = Field(..., ge=1, description="本次 step 完成后的 tick（从 1 起）")
    events: list[EventRecord] = Field(
        default_factory=list, description="本 tick 产生的事件记录；可能为空"
    )
    snapshot: Snapshot | None = Field(
        default=None,
        description="本 tick 结束后的快照；按 snapshot_mode 决定是否存在",
    )
    paused_after: bool = Field(
        default=False,
        description="本 tick 结束后是否应进入 paused 状态（每轮暂停 / 断点命中 / 手动 pause）",
    )
    triggered_breakpoints: list[str] = Field(
        default_factory=list, description="本 tick 命中的断点 id 列表（可能为空）"
    )
    reached_total_ticks: bool = Field(
        default=False,
        description="本 tick 是否已到 scenario.config.total_ticks——到达后不应再 step",
    )
