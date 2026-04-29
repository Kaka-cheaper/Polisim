"""server/app.py —— FastAPI 应用工厂（D-017 第八节）。

**入口**：`create_app(config: AppConfig | None = None) -> FastAPI`

- 工厂模式而非全局单例——便于测试时构造独立 app 实例（每个测试 fixture 一个）
- lifespan 内构造 RuntimeRegistry / 各 Service，绑到 ``app.state``——
  路由通过 `Depends(get_xxx)` 拉取
- 注册 SimEngineError / ValueError / FileNotFoundError 全局 handler
- 注册 `RegistryFullError` → 503 的小 handler（不进 D-011 异常树，单独处理）
- 挂载 v1 路由（runs / interventions / analysis / meta）到 ``/api/v1``

**run 启动**：

- 命令行：``polisim serve [--scenarios-root ...] [--runs-root ...]``（cli/serve.py）
- Python 内：``uvicorn.run(create_app(), host="127.0.0.1", port=8000)``

**测试**：见 ``tests/test_server_*.py``——用 `TestClient(create_app(...))` 即可。
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from server.api.v1.errors import (
    ErrorBody,
    ErrorResponse,
    register_exception_handlers,
)
from server.api.v1.routes import analysis as analysis_routes
from server.api.v1.routes import interventions as intervention_routes
from server.api.v1.routes import meta as meta_routes
from server.api.v1.routes import runs as run_routes
from server.api.v1.routes import ws as ws_routes
from server.runtime_registry import RegistryFullError, RuntimeRegistry
from server.services.analysis_service import AnalysisService
from server.services.intervention_service import InterventionService
from server.services.run_service import RunService
from server.services.stream_service import StreamService


@dataclass
class AppConfig:
    """server 启动配置。

    与 `RuntimeConfig` / `StorageConfig` 不同——后者是 v1 内核配置，
    AppConfig 是 server 平台配置。所有路径在此层解析为绝对路径。
    """

    runs_root: Path = field(default_factory=lambda: Path("./runs").resolve())
    """runs/ 根目录——RunService 落盘 events.jsonl + snapshots/ 用。"""

    scenarios_root: Path = field(
        default_factory=lambda: Path("./scenarios").resolve()
    )
    """scenarios/ 根目录——GET /scenarios 扫描的目录。"""

    max_concurrent_runs: int = 10
    """RuntimeRegistry 并发上限。"""

    enable_cors: bool = True
    """是否开启 CORS（前端开发时需要；v0.2 默认开放，绑 127.0.0.1 也安全）。"""

    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    """允许的 origin 列表；`*` 表示任意（v0.2 单用户本地默认）。"""


# =============================================================================
# Lifespan：app 启动 / 关闭时初始化和清理资源
# =============================================================================


@asynccontextmanager
async def _lifespan(app: FastAPI) -> Any:  # noqa: ANN401 fastapi 接受 AsyncIterator[Any]
    """构造 RuntimeRegistry + 各 Service + StreamService，存到 ``app.state``。

    StreamService 必须在 lifespan 里 attach 当前事件循环——broadcast (sync 调用)
    通过 loop.call_soon_threadsafe 把消息投递到 WebSocket 协程的 queue。

    关闭阶段调 ``registry.shutdown_all()`` + ``stream_service.detach()`` ——
    清理活跃 Runtime 与订阅者表。
    """
    import asyncio

    config: AppConfig = app.state.config
    # runs/ 与 scenarios/ 应该存在（runs 自动创建；scenarios 用户应保证）
    config.runs_root.mkdir(parents=True, exist_ok=True)

    registry = RuntimeRegistry(max_concurrent=config.max_concurrent_runs)
    stream_service = StreamService()
    stream_service.attach_loop(asyncio.get_running_loop())

    app.state.registry = registry
    app.state.stream_service = stream_service
    app.state.run_service = RunService(
        registry, config.runs_root, stream_service=stream_service
    )
    app.state.intervention_service = InterventionService(registry)
    app.state.analysis_service = AnalysisService(registry)
    app.state.scenarios_root = config.scenarios_root

    try:
        yield
    finally:
        registry.shutdown_all()
        stream_service.detach()


# =============================================================================
# 工厂
# =============================================================================


def create_app(config: AppConfig | None = None) -> FastAPI:
    """构造 FastAPI 应用实例。

    Args:
        config: AppConfig；None 时用默认（cwd/runs + cwd/scenarios + 10 并发）

    Returns:
        已注册全部路由 / 异常 handler / CORS middleware 的 FastAPI 实例
    """
    if config is None:
        config = AppConfig()

    app = FastAPI(
        title="Polisim API",
        description=(
            "v0.2 server (D-017) —— 把 v1 仿真引擎暴露为 REST + WebSocket API。"
            "WebSocket 在 session 32 加入。"
        ),
        version="0.2.0",
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
        lifespan=_lifespan,
    )
    app.state.config = config

    # CORS——前端开发与生产都需要
    if config.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # 全局异常 handler——SimEngineError / ValueError / FileNotFoundError
    register_exception_handlers(app)

    # RegistryFullError → 503（不在 SimEngineError 树里，单独注册）
    @app.exception_handler(RegistryFullError)
    async def _registry_full_handler(
        request: Request, exc: RegistryFullError
    ) -> JSONResponse:
        body = ErrorBody(code="REGISTRY_FULL", message=str(exc))
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(error=body).model_dump(exclude_none=True),
        )

    # 注册 v1 路由——全部挂在 /api/v1 前缀下
    api_v1 = "/api/v1"
    app.include_router(run_routes.router, prefix=api_v1)
    app.include_router(intervention_routes.router, prefix=api_v1)
    app.include_router(analysis_routes.router, prefix=api_v1)
    app.include_router(meta_routes.router, prefix=api_v1)
    # WebSocket 路由（D-017 第四节）—— ws_routes 暴露 GET /runs/{id}/stream
    app.include_router(ws_routes.router, prefix=api_v1)

    return app


# =============================================================================
# 顶层默认 app（uvicorn 用）
# =============================================================================


def _default_app() -> FastAPI:
    """uvicorn 入口模式：``uvicorn server.app:app`` 时使用此 callable。

    包裹一层是因为直接顶层 ``app = create_app()`` 会在 import server.app 时就跑
    lifespan——某些工具（如 pytest 收集）会受影响。这样让 uvicorn 显式构造。
    """
    return create_app()


# 给 uvicorn / cli/serve.py 用
app = _default_app()
