"""server/api/v1/middlewares/auth.py —— 鉴权中间件（v0.2 占位）。

**v0.2 状态**：no-op pass-through 中间件——本文件存在的唯一原因是

1. 占据"鉴权层"位置——将来 v0.3+ 加鉴权时，结构稳定不大改
2. 文档化决策（D-017 第 2.5 节）——v0.2 不鉴权是有意为之，绑本机 127.0.0.1

**v0.3+ 设计**（不在本 session 落地）：

- 从 header 读 `Authorization: Bearer <token>`
- 与环境变量 `POLISIM_API_TOKEN` 比对
- 不匹配 → 401

**v0.4+ 设计**：

- OAuth + 多用户隔离（每 user 独立 runs/）
- run_id 改为 (user_id, run_id) 复合键

未启用——`server/app.py` 当前**不**注册本中间件。改为日后启用时直接
`app.add_middleware(AuthMiddleware)` 就行。
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class AuthMiddleware(BaseHTTPMiddleware):
    """鉴权中间件占位。

    v0.2 调用 `await call_next(request)` 直接放行——所有请求无鉴权检查。
    """

    async def dispatch(
        self, request: Request, call_next
    ) -> Response:
        # v0.2：no-op，直接放行
        return await call_next(request)
