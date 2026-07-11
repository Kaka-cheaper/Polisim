"""server/api/v1/schemas.py —— v0.2 平台专有 Pydantic schema（D-017）。

**复用纪律**（D-017 第 2.2 节）：

- 状态相关数据（`EventRecord` / `Snapshot` / `TickResult` / `WorldState` /
  `WorldDefinition` / `Scenario` / `AnalysisResult` / `Intervention` / `PromptContext`）
  **直接从 `models/*` import，不在此文件重新声明**——避免 session 27 F3 漂移教训
- 仅以下"平台专有"模型在本文件定义：
  - **请求体**：`CreateRunRequest` / `AnalyzeRequest`
  - **响应包装**：`RunSummary` / `RunDetail` / `EventListResponse` / `ScenarioSummary` /
    `HealthResponse` / `PauseResumeResponse` / `SnapshotsListResponse`

它们都是 v0.2 server 层的协议产物——v1 内核不需要也不该知道。
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from models.config_models import RuntimeConfig
from models.runtime_models import EventRecord
from models.scenario_models import Scenario
from models.world_models import WorldDefinition


# =============================================================================
# 请求体（POST 入参）
# =============================================================================


class CreateRunRequest(BaseModel):
    """创建 run 的请求体（POST /api/v1/runs）。

    字段语义对齐 `cli/run.py cmd_run` 的命令行参数——v0.2 server 是 CLI 的网络化等价物。
    """

    model_config = ConfigDict(extra="forbid")

    scenario_path: str = Field(
        ...,
        min_length=1,
        description="scenario.yaml 相对仓库根的路径（或绝对路径）",
    )
    world_path: str | None = Field(
        default=None,
        description="world.yaml 路径；默认 <scenario_dir>/world.yaml",
    )
    runtime_config: RuntimeConfig | None = Field(
        default=None,
        description="可选 runtime 配置覆盖；省略时用模型默认值",
    )
    llm_provider: Literal["mock", "openai"] = Field(
        default="mock",
        description=(
            "LLM provider 类型——v0.2 默认 mock 离线；openai 需配 provider_key"
        ),
    )
    provider_key: str | None = Field(
        default=None,
        description=(
            "config/llm.yaml 的 providers 字典 key；省略时用 default_provider"
        ),
    )
    config_llm_path: str | None = Field(
        default=None,
        description="LLM 配置文件路径；默认 config/llm.yaml；仅 llm_provider=openai 用",
    )
    ticks_override: int | None = Field(
        default=None,
        ge=1,
        description="覆盖 scenario.config.total_ticks；省略走 scenario 声明",
    )
    run_id: str | None = Field(
        default=None,
        description="显式 run_id；None 时由 EventLog.generate_run_id 自动生成",
    )


class AnalyzeRequest(BaseModel):
    """显式触发分析的请求体（POST /api/v1/runs/:id/analyze）。

    与 GET /analysis 的差别：POST 表达"重新生成"语义——前端"重跑增强"按钮调它。
    """

    model_config = ConfigDict(extra="forbid")

    llm_enhance: bool = Field(
        default=False,
        description="是否触发 Phase C LLM 增强（4 段叙事报告）",
    )


# =============================================================================
# Run 元信息（响应）
# =============================================================================


class RunSummary(BaseModel):
    """run 摘要信息——列表场景使用（GET /runs 返回）。

    `RunDetail` 进一步携带完整 world / scenario 配置。
    """

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(..., description="run 唯一标识")
    world_id: str = Field(..., description="World Definition.id")
    scenario_id: str = Field(..., description="Scenario.scenario.id")
    status: Literal["active", "paused", "finished", "archived"] = Field(
        ..., description="run 当前状态——active：在跑；paused：暂停；finished：达 total_ticks；archived：已 GC 出内存"
    )
    current_tick: int = Field(..., ge=0, description="当前 tick（0 表示未开始）")
    total_ticks: int = Field(..., ge=1, description="本次仿真总轮次")
    created_at: datetime = Field(..., description="run 创建时间（UTC）")


class RunDetail(BaseModel):
    """run 完整详情——单 run 视图使用（POST /runs / GET /runs/:id 返回）。

    含完整 world + scenario + runtime_config——前端可用作"创建后立即展示"
    与"刷新页面恢复跑前阶段配置"的数据源。
    """

    model_config = ConfigDict(extra="forbid")

    summary: RunSummary = Field(..., description="run 摘要")
    world: WorldDefinition = Field(..., description="完整 World Definition")
    scenario: Scenario = Field(..., description="完整 Scenario（含 ui_layout）")
    runtime_config: RuntimeConfig = Field(..., description="生效的 runtime 配置")


# =============================================================================
# 控制响应
# =============================================================================


class PauseResumeResponse(BaseModel):
    """pause / resume endpoint 的响应（D-017 第 3.2 节）。"""

    model_config = ConfigDict(extra="forbid")

    status: Literal["paused", "running"] = Field(
        ..., description="操作后的状态"
    )
    tick: int = Field(..., ge=0, description="当前 tick")


# =============================================================================
# 事件查询响应
# =============================================================================


class EventListResponse(BaseModel):
    """事件查询的响应——含分页元信息。"""

    model_config = ConfigDict(extra="forbid")

    events: list[EventRecord] = Field(
        default_factory=list,
        description="EventRecord 列表（按发生顺序）",
    )
    total: int = Field(..., ge=0, description="过滤后命中的总条数（不分页）")
    has_more: bool = Field(..., description="是否还有下一页")


class SnapshotsListResponse(BaseModel):
    """已保存的快照 tick 列表（GET /runs/:id/snapshots）。"""

    model_config = ConfigDict(extra="forbid")

    ticks: list[int] = Field(
        default_factory=list,
        description="存在快照的 tick 编号列表（升序）",
    )


# =============================================================================
# 元信息响应
# =============================================================================


class ScenarioSummary(BaseModel):
    """场景画廊卡片数据源（GET /api/v1/scenarios）。

    D-017 反向校验产物：`ui_layout` 字段直接透传 `Scenario.ui_layout`——
    前端依据它选 entity_card / relation_graph / event_stream 三种主区 layout。
    """

    model_config = ConfigDict(extra="forbid")

    path: str = Field(..., description="scenario.yaml 仓库相对路径")
    id: str = Field(..., description="Scenario.scenario.id")
    name: str = Field(..., description="Scenario.scenario.name")
    description: str = Field(default="", description="Scenario.scenario.description")
    total_ticks: int = Field(..., ge=1, description="Scenario.config.total_ticks")
    ui_layout: Literal["entity_card", "relation_graph", "event_stream"] = Field(
        default="entity_card",
        description=(
            "v0.2 前端跑中主区 layout 风格选择"
            "（D-017 反向校验产物，详见 v0.2-前端-UI-mockup.md 第 7 节）"
        ),
    )
    world_id: str = Field(..., description="Scenario.world_id（前端可对齐 world 信息）")


class HealthResponse(BaseModel):
    """健康检查响应（GET /api/v1/health）。"""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = Field(default="ok", description="server 状态")
    version: str = Field(..., description="Polisim 版本号")
    active_runs: int = Field(..., ge=0, description="活跃 run 数")
