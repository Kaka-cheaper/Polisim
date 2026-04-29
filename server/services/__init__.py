"""server/services/ —— 业务编排层。

每个 service 类**与 FastAPI 解耦**——不接受 Request 对象，只接受裸数据：

- `RunService` —— Run CRUD + 控制 + 状态查询 + 事件查询
- `InterventionService` —— 3 类干预（inject_message / force_action / override_attribute）
- `AnalysisService` —— Phase A / Phase C 分析
- `StreamService`（推迟 session 32）—— WebSocket 推送广播

**设计动机**（D-017 第六节）：

未来加 mobile / 第三方 SDK / CLI 调用时，service 层可被复用，
**不必**重写一份业务逻辑。
"""
