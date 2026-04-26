"""分析层产出物的结构化模型（Phase A——纯规则核心）。

对应 `docs/02-design/实现映射设计.md` 第五步之后的"补分析层"阶段，以及
`docs/01-requirements/MVP场景定义.md` 10.3 节"最终输出"条款。

**本模块只负责数据结构定义**——Phase A 的聚合、渲染逻辑与 Phase C 的 LLM
增强都在 `core/analysis.py`（后者通过 `enhance_with_llm` 公开 API 填充三个
叙事字段）。

**分层约束**：

- 本文件**不**依赖 `core/*`——仅依赖 Pydantic 与 stdlib
- `AnalysisResult` 顶层三个可选字段（`narrative_summary` / `situation_judgement` /
  `next_action_suggestions`）预留给 Phase C；Phase A 渲染时发现为 None 会省略对应段
- 所有字段使用 `extra="forbid"`——对齐其他 models 模块的严格纪律

**JSON 往返设计**：

- 所有嵌套模型都是 Pydantic BaseModel，可直接 `model_dump_json(indent=2)` 落盘
- 环境变量与属性值用 `Any`——因为仿真允许任意 JSON 兼容类型；渲染层自行格式化
- 不使用 `dict[int, ...]`——JSON 会把 int key 序列化为字符串，反序列化会歧义；
  改用 `list[TickValuePoint]` 风格的显式条目列表，UI 消费也更顺手

**版本化**：

- `AnalysisResult.version` 与 `StorageConfig` 等保持同一风格（`Literal["0.1"]`）
- 未来 schema 变化时必须升版本号 + 写迁移逻辑（不在本文件范围）
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# 统计原子
# =============================================================================


class KindStat(BaseModel):
    """按 `EventKind` 的计数条目。"""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(..., min_length=1, description="EventKind 字面量")
    count: int = Field(..., ge=0, description="该 kind 出现的事件总数")


class ActorStat(BaseModel):
    """按 `actor_id` 的行为统计条目。

    只统计两类有业务含义的事件：
    - `action_executed`——真正落地的动作
    - `decision_rejected`——被规则层拒绝的决策提议
    其他事件（如 `decision_proposed`）每次都会写，信噪比低，不计入。
    """

    model_config = ConfigDict(extra="forbid")

    actor_id: str = Field(..., min_length=1, description="实体 id")
    action_count: int = Field(..., ge=0, description="action_executed 事件数")
    decision_rejected_count: int = Field(
        ..., ge=0, description="decision_rejected 事件数"
    )


# =============================================================================
# 属性变化 / 关键转折点
# =============================================================================


class AttributeChange(BaseModel):
    """实体某属性从 `before` 变到 `after` 的单条记录。

    用于 `EntityComparison.changes`——只收录实际变化过的属性；未变化的
    属性不进此列表（避免渲染时噪声）。

    - `before is None`：该属性在 initial snapshot 中**不存在**（实体中途新增或
      v1 不会出现，保留 Nullable 以兼容未来）
    - `after` 永远非 None（因为 final snapshot 里有这条属性才会进这个列表）
    """

    model_config = ConfigDict(extra="forbid")

    attribute: str = Field(..., min_length=1, description="属性名")
    before: Any = Field(
        default=None, description="初始值；None 表示属性在初始快照中缺失"
    )
    after: Any = Field(..., description="终态值")


class TurningPoint(BaseModel):
    """tick-by-tick 扫描发现的显著属性变化。

    定义：对于每对相邻快照 `snap_{t-1}` 与 `snap_t`，对每个实体的每个属性，
    若值发生变化，记作一条候选；按 `|delta|` 降序取前 K 条作为 turning points。

    - `delta` 为 None：属性是非数值型（或 before/after 有一方非数值），
      无法计算差值；仍可能被保留为 turning point（按 0 排序，排在数值型之后）
    - `actor_id` 借用 `actor` 语义：指**实体 id**，不是事件发起者
    """

    model_config = ConfigDict(extra="forbid")

    tick: int = Field(
        ..., ge=1, description="属性变化发生的 tick（≥1；tick 0 是初始态）"
    )
    actor_id: str = Field(..., min_length=1, description="发生变化的实体 id")
    attribute: str = Field(..., min_length=1, description="变化的属性名")
    before: Any = Field(default=None, description="变化前的值")
    after: Any = Field(..., description="变化后的值")
    delta: float | None = Field(
        default=None,
        description="数值差（after - before）；非数值属性为 None",
    )


# =============================================================================
# 环境变量轨迹
# =============================================================================


class TickValuePoint(BaseModel):
    """`(tick, value)` 对——某变量在某 tick 的取值。"""

    model_config = ConfigDict(extra="forbid")

    tick: int = Field(..., ge=0, description="tick；0 表示初始态")
    value: Any = Field(..., description="该 tick 的变量值")


class EnvironmentChange(BaseModel):
    """单个环境变量在整个仿真过程中的取值序列。

    只收录"值发生变化"的 tick（含初始 tick）——未变化的 tick 省略，
    避免无意义膨胀。举例：若 `market_demand` 整个仿真保持 100 不变，
    `values` 只有一条 `(tick=0, value=100)`。
    """

    model_config = ConfigDict(extra="forbid")

    variable: str = Field(..., min_length=1, description="环境变量名")
    values: list[TickValuePoint] = Field(
        default_factory=list,
        description="按 tick 升序的取值序列；只收录值变化过的 tick",
    )


# =============================================================================
# 实体对比（initial vs final）
# =============================================================================


class EntityComparison(BaseModel):
    """单个实体的初态与终态对比——对应 MVP 10.3 #3"各实体最终状态比较"。

    - `initial_attributes` / `final_attributes` 是两份完整快照（所有属性）
    - `changes` 只列出实际变化的属性——渲染 markdown 时先看 `changes` 找重点，
      需要完整对比表时再走 `initial_/final_attributes`
    """

    model_config = ConfigDict(extra="forbid")

    entity_id: str = Field(..., min_length=1, description="实体 id")
    initial_attributes: dict[str, Any] = Field(
        default_factory=dict, description="初始 snapshot 的全部属性快照"
    )
    final_attributes: dict[str, Any] = Field(
        default_factory=dict, description="最终 snapshot 的全部属性快照"
    )
    changes: list[AttributeChange] = Field(
        default_factory=list,
        description="实际变化的属性列表（空列表表示该实体整个仿真没变化）",
    )


# =============================================================================
# 全轨迹总览
# =============================================================================


class TrajectorySummary(BaseModel):
    """整次仿真的事件与节奏总览——对应 MVP 10.3 #1"全轨迹总结"。"""

    model_config = ConfigDict(extra="forbid")

    total_ticks: int = Field(
        ...,
        ge=0,
        description="整个仿真实际推进的 tick 数（= 事件中的最大 tick）",
    )
    total_events: int = Field(
        ..., ge=0, description="events.jsonl 中的事件总数"
    )
    events_by_kind: list[KindStat] = Field(
        default_factory=list,
        description="按 kind 分组的计数；按 kind 字典序排序",
    )
    events_by_actor: list[ActorStat] = Field(
        default_factory=list,
        description="按实体 id 分组的行为计数；按 actor_id 字典序排序",
    )
    paused_ticks: list[int] = Field(
        default_factory=list,
        description="触发了 breakpoint_triggered 事件的 tick 集合（升序去重）",
    )
    breakpoints_triggered: list[str] = Field(
        default_factory=list,
        description="命中的 breakpoint id 列表（按事件顺序，可能重复）",
    )


# =============================================================================
# 顶层结果
# =============================================================================


class AnalysisResult(BaseModel):
    """分析层的顶层产物——一次 `analyze_run` 调用的完整结果。

    **分层**：
    - 前五个字段是 Phase A 纯规则核心填——100% 确定性
    - 后三个字段（`narrative_summary` / `situation_judgement` /
      `next_action_suggestions`）是 Phase C LLM 增强层填；Phase A 默认 None
    - 渲染 markdown 时 Phase A 产物总有，LLM 增强段发现 None 会省略对应 section
    """

    model_config = ConfigDict(extra="forbid")

    version: Literal["0.1"] = Field(
        default="0.1", description="AnalysisResult schema 版本号"
    )
    run_id: str = Field(..., min_length=1, description="对应的 run_id")
    summary: TrajectorySummary = Field(
        ..., description="全轨迹总览（对应 MVP 10.3 #1）"
    )
    turning_points: list[TurningPoint] = Field(
        default_factory=list,
        description="关键转折点列表（对应 MVP 10.3 #2），按 |delta| 降序",
    )
    entity_comparisons: list[EntityComparison] = Field(
        default_factory=list,
        description="各实体初态 vs 终态对比（对应 MVP 10.3 #3）",
    )
    environment_trajectory: list[EnvironmentChange] = Field(
        default_factory=list,
        description="环境变量轨迹；未变化变量保留单点初态",
    )

    # ---- Phase C LLM 增强字段（Phase A 默认不填） ----
    narrative_summary: str | None = Field(
        default=None,
        description="LLM 生成的自然语言总览（Phase C 填；对应 MVP 10.3 #4 前半）",
    )
    situation_judgement: str | None = Field(
        default=None,
        description="LLM 生成的局势判断（Phase C 填；对应 MVP 10.3 #4 后半）",
    )
    next_action_suggestions: list[str] | None = Field(
        default=None,
        description="LLM 生成的面向用户建议条目（Phase C 填；对应 MVP 10.3 #5）",
    )
