"""server/api/v1/ —— v0.2 API（D-017 第三节定义）。

子模块：

- `errors.py` —— `SimEngineError` → HTTP 状态码映射 + 全局异常处理器
- `schemas.py` —— 平台专有 Pydantic schema（CreateRunRequest 等；不侵入 models/）
- `routes/` —— REST endpoint 实现（runs / interventions / analysis / meta）
- `middlewares/` —— v0.2 鉴权占位（v0.3+ 加 token / OAuth）

session 31 实施范围：**不含 WebSocket**——`routes/ws.py` 与 `ws_events.py`
推迟到 session 32（AGENTS.md 3.4 节 v0.2 推进路径第 4 步）。
"""
