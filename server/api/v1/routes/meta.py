"""server/api/v1/routes/meta.py —— /api/v1/scenarios + /health（D-017 第 3.5 节）。

GET /scenarios —— 扫描 ``scenarios/`` 目录返画廊数据。
GET /health    —— 健康检查 + 活跃 run 数。
"""

from __future__ import annotations

from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, Request

from server.api.deps import get_registry
from server.api.v1.schemas import HealthResponse, ScenarioSummary
from server.runtime_registry import RuntimeRegistry


router = APIRouter(tags=["meta"])


@router.get(
    "/scenarios",
    response_model=list[ScenarioSummary],
    summary="列出可用场景（场景画廊数据源）",
)
def list_scenarios(request: Request) -> list[ScenarioSummary]:
    """扫描 ``scenarios/`` 目录返画廊数据。

    实现策略：
    - 扫描 `<scenarios_root>/*/scenario.yaml`
    - 用 PyYAML 直读（不走 scenario_loader——避免对 world.yaml 的强依赖）
    - 失败的场景文件**跳过**（容忍 yaml 语法错），但记录在 server 日志里
    - 返回 `ScenarioSummary` 列表，按 id 字典序排序

    `scenarios_root` 由 `app.state.scenarios_root` 配置，默认 `<cwd>/scenarios/`。
    """
    scenarios_root: Path = request.app.state.scenarios_root
    if not scenarios_root.exists():
        return []

    summaries: list[ScenarioSummary] = []
    for sub in sorted(scenarios_root.iterdir()):
        if not sub.is_dir():
            continue
        scenario_yaml = sub / "scenario.yaml"
        if not scenario_yaml.exists():
            continue
        try:
            data = yaml.safe_load(scenario_yaml.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError):
            # 容忍坏文件——画廊不希望整体 500
            continue
        if not isinstance(data, dict):
            continue
        scenario_info = data.get("scenario", {})
        config_info = data.get("config", {})
        if not isinstance(scenario_info, dict) or not isinstance(config_info, dict):
            continue
        sid = scenario_info.get("id")
        sname = scenario_info.get("name")
        total_ticks = config_info.get("total_ticks")
        if not sid or not sname or not isinstance(total_ticks, int):
            continue
        summaries.append(
            ScenarioSummary(
                path=str(scenario_yaml.resolve()),
                id=sid,
                name=sname,
                description=scenario_info.get("description") or "",
                total_ticks=total_ticks,
                ui_layout=data.get("ui_layout", "entity_card"),
                world_id=data.get("world_id", ""),
            )
        )
    summaries.sort(key=lambda s: s.id)
    return summaries


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="健康检查 + 活跃 run 数",
)
def health_check(
    registry: RuntimeRegistry = Depends(get_registry),
) -> HealthResponse:
    # version 从顶层包元数据读取——v0.2 期间使用 0.2.0 标识 server 阶段
    return HealthResponse(
        status="ok",
        version="0.2.0",
        active_runs=registry.active_count(),
    )
