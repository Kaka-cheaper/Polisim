"""server/api/v1/routes/runs.py —— /api/v1/runs/* 路由（D-017 第 3.1-3.4 节）。

包含的 endpoints：

- POST   /runs                          创建 run
- GET    /runs                          列出 run
- GET    /runs/{run_id}                 run 详情
- DELETE /runs/{run_id}                 删除 run（v0.2 简化：直接 shutdown registry）
- POST   /runs/{run_id}/step            推进一 tick
- POST   /runs/{run_id}/pause           暂停
- POST   /runs/{run_id}/resume          恢复
- GET    /runs/{run_id}/state           当前 WorldState
- GET    /runs/{run_id}/snapshots       已存的 tick 列表
- GET    /runs/{run_id}/snapshots/{tick} 指定 tick 快照
- GET    /runs/{run_id}/events          事件查询（分页 + 过滤）

**复用纪律**：

- response_model 直接用 `models/*` 与 `schemas.py`——不在此层重新声明
- 异常自然抛出——`server/api/v1/errors.py` 的 handler 统一映射 HTTP 状态
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from models.runtime_models import Snapshot, TickResult, WorldState

from server.api.deps import get_run_service
from server.api.v1.schemas import (
    CreateRunRequest,
    EventListResponse,
    PauseResumeResponse,
    RunDetail,
    RunSummary,
    SnapshotsListResponse,
)
from server.services.run_service import RunService


router = APIRouter(prefix="/runs", tags=["runs"])


# ---------- CRUD ----------


@router.post(
    "",
    response_model=RunDetail,
    status_code=status.HTTP_201_CREATED,
    summary="创建新 run",
)
def create_run(
    req: CreateRunRequest,
    svc: RunService = Depends(get_run_service),
) -> RunDetail:
    return svc.create_run(req)


@router.get(
    "",
    response_model=list[RunSummary],
    summary="列出 run",
)
def list_runs(
    status: str = Query("all", description="过滤 status：all / active / paused / finished / archived"),
    limit: int = Query(50, ge=1, le=1000, description="分页大小"),
    offset: int = Query(0, ge=0, description="分页偏移"),
    svc: RunService = Depends(get_run_service),
) -> list[RunSummary]:
    return svc.list_runs(status=status, limit=limit, offset=offset)


@router.get(
    "/{run_id}",
    response_model=RunDetail,
    summary="run 详情",
)
def get_run(
    run_id: str,
    svc: RunService = Depends(get_run_service),
) -> RunDetail:
    return svc.get_run(run_id)


@router.delete(
    "/{run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="关闭并移除 run（v0.2：从 registry 卸载）",
)
def delete_run(
    run_id: str,
    svc: RunService = Depends(get_run_service),
) -> None:
    svc.delete_run(run_id)


# ---------- 控制 ----------


@router.post(
    "/{run_id}/step",
    response_model=TickResult,
    summary="推进一 tick",
)
def step_run(
    run_id: str,
    svc: RunService = Depends(get_run_service),
) -> TickResult:
    return svc.step(run_id)


@router.post(
    "/{run_id}/pause",
    response_model=PauseResumeResponse,
    summary="暂停",
)
def pause_run(
    run_id: str,
    svc: RunService = Depends(get_run_service),
) -> PauseResumeResponse:
    return svc.pause(run_id)


@router.post(
    "/{run_id}/resume",
    response_model=PauseResumeResponse,
    summary="恢复",
)
def resume_run(
    run_id: str,
    svc: RunService = Depends(get_run_service),
) -> PauseResumeResponse:
    return svc.resume(run_id)


# ---------- 状态查询 ----------


@router.get(
    "/{run_id}/state",
    response_model=WorldState,
    summary="当前 WorldState",
)
def get_state(
    run_id: str,
    svc: RunService = Depends(get_run_service),
) -> WorldState:
    return svc.get_state(run_id)


@router.get(
    "/{run_id}/snapshots",
    response_model=SnapshotsListResponse,
    summary="已存的 tick 列表",
)
def list_snapshots(
    run_id: str,
    svc: RunService = Depends(get_run_service),
) -> SnapshotsListResponse:
    return svc.list_snapshots(run_id)


@router.get(
    "/{run_id}/snapshots/{tick}",
    response_model=Snapshot,
    summary="指定 tick 的 Snapshot",
)
def get_snapshot(
    run_id: str,
    tick: int,
    svc: RunService = Depends(get_run_service),
) -> Snapshot:
    return svc.get_snapshot(run_id, tick)


# ---------- 事件查询 ----------


@router.get(
    "/{run_id}/events",
    response_model=EventListResponse,
    summary="事件查询（分页 + 过滤）",
)
def query_events(
    run_id: str,
    tick: int | None = Query(None, ge=0, description="精确匹配某 tick"),
    kind: str | None = Query(None, description="按 EventKind 过滤"),
    actor_id: str | None = Query(None, description="按 actor_id 过滤"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    until_tick: int | None = Query(None, ge=0, description="返 tick<=until_tick 的事件"),
    svc: RunService = Depends(get_run_service),
) -> EventListResponse:
    return svc.query_events(
        run_id,
        tick=tick,
        kind=kind,
        actor_id=actor_id,
        limit=limit,
        offset=offset,
        until_tick=until_tick,
    )
