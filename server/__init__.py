"""Polisim v0.2 server 层（D-017）。

本包只做"把 v1 内核暴露为 HTTP / WebSocket API"——

- **routes**（`server/api/v1/routes/*`）：HTTP 协议解析与响应序列化
- **services**（`server/services/*`）：业务编排，可被 CLI / SDK / 第三方复用
- **registry**（`server/runtime_registry.py`）：多并发 Runtime 内存生命周期

**分层纪律**（D-017 第 2 节）：

1. routes 不持有业务逻辑——只做参数解析、调 service、序列化响应
2. services 不接触 FastAPI 类型——纯业务接口，可独立单测
3. response_model 直接复用 `models/*` Pydantic——**不**新建翻译层
4. 平台专有 schema（CreateRunRequest / RunSummary / ErrorResponse 等）
   落点 `server/api/v1/schemas.py`，**不**侵入 v1 核心 `models/*`

**与 v1 内核的关系**：

- 不动 `core/` / `models/` / `rules/` —— 它们是 v0.2 stable contract
- D-016 PromptContext / D-014 ParamSchema / D-015 EntityCreate 等能力
  都通过 `models/*` 的 Pydantic 模型自然透传到前端
"""
