"""server/api/deps.py —— FastAPI Depends 依赖注入入口（D-017 第八节）。

**目的**：把 server.app 中初始化的全局对象（registry / services）通过
FastAPI 的 Depends 体系暴露给路由函数，避免路由内部硬编码"全局变量"。

**关键模式**：

1. `server.app` lifespan 时构造 `RuntimeRegistry` + 各 Service 实例
2. 把它们存到 `app.state.registry` / `app.state.run_service` / ...
3. 路由通过 `Depends(get_run_service)` 拿到对应实例
4. 测试时可以 `app.dependency_overrides[get_run_service] = lambda: mock_service`

**为何不用全局单例**：

- 全局单例不利于测试隔离（每个测试用例需要独立 registry）
- FastAPI 的 lifespan + app.state 是官方推荐做法

未来 v0.3+ 加 user 鉴权时，本文件会增加 `get_current_user` 等 deps。
"""

from __future__ import annotations

from fastapi import Depends, Request

from server.runtime_registry import RuntimeRegistry
from server.services.analysis_service import AnalysisService
from server.services.intervention_service import InterventionService
from server.services.run_service import RunService


def get_registry(request: Request) -> RuntimeRegistry:
    """从 ``app.state.registry`` 取 RuntimeRegistry 单例。

    server 启动时（lifespan）已经初始化；测试时可通过 ``dependency_overrides`` 替换。
    """
    return request.app.state.registry


def get_run_service(request: Request) -> RunService:
    return request.app.state.run_service


def get_intervention_service(request: Request) -> InterventionService:
    return request.app.state.intervention_service


def get_analysis_service(request: Request) -> AnalysisService:
    return request.app.state.analysis_service


# 类型别名——路由文件可写 `RunServiceDep = Annotated[RunService, Depends(get_run_service)]`
# 但 v0.2 简化为直接 Depends——避免依赖 Annotated 复杂度
__all__ = [
    "Depends",
    "get_registry",
    "get_run_service",
    "get_intervention_service",
    "get_analysis_service",
]
