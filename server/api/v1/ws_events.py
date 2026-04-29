"""server/api/v1/ws_events.py —— WebSocket 服务端推送事件 typed schema（D-017 第四节）。

**设计契约**：

1. **discriminated union**——每条消息的 `event` 字段是 Literal 字符串，前端按此分支
2. **server → client 单向**——所有控制走 REST endpoints；WebSocket 仅用于事件推送
3. **复用 v1 模型作 data**——`TickResult` / `AnalysisResult` / `ErrorBody` 直接嵌入

**前端解析模式**（伪 TS）：

```typescript
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  switch (msg.event) {
    case "tick_advanced": handleTick(msg.data); break;
    case "paused":        handlePaused(msg.data); break;
    case "run_finished":  handleFinished(msg.data); break;
    case "error":         handleError(msg.data); break;
    case "ping":          ws.send(JSON.stringify({event: "pong"})); break;
  }
};
```

**WebSocket 关闭码**（D-017 第 4.1 / 4.5 节）：

| Code | 含义 |
|------|------|
| 1000 | 正常关闭（run finished + 推完 run_finished 后） |
| 4004 | run 不存在或已归档 |
| 4500 | 推送过程中发生 SimEngineError |

由 `routes/ws.py` 决定发什么 code；本文件只定义消息体。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from models.analysis_models import AnalysisResult
from models.runtime_models import TickResult

from server.api.v1.errors import ErrorBody


# =============================================================================
# 基类
# =============================================================================


class WSEventBase(BaseModel):
    """所有 WebSocket 服务端推送消息的基类。

    每个具体事件用 Literal 覆写 `event` 字段——形成 discriminated union，
    前端可通过 `msg.event` 分支处理。
    """

    model_config = ConfigDict(extra="forbid")

    event: str = Field(..., description="事件类型 discriminator")


# =============================================================================
# 推送事件（server → client）
# =============================================================================


class TickAdvancedEvent(WSEventBase):
    """每次 ``runtime.step()`` 完成后立即推送。

    `data` 直接复用 `models.runtime_models.TickResult`——含 events / paused_after /
    reached_total_ticks / snapshot 等完整字段。前端可拿来更新主时间线 + 实体卡片 +
    LLM 决策气泡。
    """

    event: Literal["tick_advanced"] = Field(
        default="tick_advanced", description="事件类型常量"
    )
    data: TickResult = Field(..., description="本次 step 的 TickResult")


class PausedPayload(BaseModel):
    """`PausedEvent.data` 的载荷（D-017 第 4.2 节）。"""

    model_config = ConfigDict(extra="forbid")

    tick: int = Field(..., ge=0, description="发生暂停时的 tick 编号")
    breakpoint_ids: list[str] = Field(
        default_factory=list,
        description="触发暂停的断点 id 列表；reason 非 breakpoint 时为空",
    )
    reason: Literal["manual", "every_tick", "breakpoint", "total_ticks"] = Field(
        ..., description="暂停原因"
    )


class PausedEvent(WSEventBase):
    """暂停事件——客户端 POST /pause 或 step 后触发暂停条件时推送。

    与 ``TickAdvancedEvent`` 的关系：
    - 自动暂停（every_tick / breakpoint）由 step 触发，**先推 tick_advanced 再推 paused**
    - 手动暂停（manual）由 POST /pause 触发，独立推 paused
    - 达到 total_ticks 时**不推 paused**——直接推 `RunFinishedEvent`
    """

    event: Literal["paused"] = Field(
        default="paused", description="事件类型常量"
    )
    data: PausedPayload = Field(..., description="暂停信息")


class RunFinishedEvent(WSEventBase):
    """run 跑到 total_ticks 时推送（最后一条消息）。

    `data` 是 Phase A 分析结果——server 自动跑 ``analyze_run`` 后推送，避免前端
    再调一次 GET /analysis。前端可显示后选择是否手动 enhance（避免每个 run 都走 LLM）。

    推送后 server **主动 close(1000)** —— 客户端无需再处理后续消息。
    """

    event: Literal["run_finished"] = Field(
        default="run_finished", description="事件类型常量"
    )
    data: AnalysisResult = Field(..., description="Phase A 分析结果（不含 LLM 增强）")


class ErrorEvent(WSEventBase):
    """推送过程中发生 SimEngineError 时推送（异常路径）。

    与 REST 错误响应的区别：
    - REST：异常 handler 序列化为 HTTP 4xx/5xx + ErrorResponse body
    - WS：把同一个 ErrorBody 包成 ErrorEvent 推送，紧接着 close(4500)

    前端按 `data.code` 分支处理；与 REST 的 `error.code` 完全一致。

    **v0.2 状态**（session 33 架构审查记录）：本事件 schema 已预留，但**当前 server
    实施未触发**——`RunService.step` 抛出的 SimEngineError 由 REST 异常 handler
    映射成 4xx/5xx 直接返给 step 调用方；WebSocket 路由层只在自身 `_send_loop` 异常
    时 close(4500)，不发 ErrorEvent。v0.3+ 加"异步任务推送"或"后台 step 自动跑"时
    会启用此事件。
    """

    event: Literal["error"] = Field(
        default="error", description="事件类型常量"
    )
    data: ErrorBody = Field(..., description="错误体（与 REST ErrorResponse.error 同结构）")


# =============================================================================
# 心跳（双向；客户端**仅** Ping/Pong 这一种"上行消息"——见 D-017 第 4.4 节）
# =============================================================================


class PingEvent(WSEventBase):
    """server → client 心跳（30s 周期由 server 主动发）。

    **v0.2 状态**（session 33 架构审查记录）：心跳 schema 已预留，但**当前 server
    未实施**主动推送 ping。v0.2 单进程本机部署，连接断开靠 `_receive_loop`
    捕获 `WebSocketDisconnect` 自然检测——不需要 ping 探活。v0.3+ 跨网络 / 长闲置
    场景启用 30s 周期 ping。
    """

    event: Literal["ping"] = Field(default="ping", description="事件类型常量")
    data: dict = Field(default_factory=dict, description="预留载荷；v0.2 为空")


class PongEvent(WSEventBase):
    """client → server 心跳响应。

    v0.2 的**唯一上行消息**——server 收到 pong 即视为客户端在线，
    无 pong 超过 60s 视为客户端断开（lazy 检测，由 send 失败触发清理）。

    **v0.2 状态**（session 33 架构审查记录）：因 server 不主动发 ping，前端无需发 pong；
    `_receive_loop` 接受任意客户端消息但不验证（不强制 schema，避免误关 ws）。
    v0.3+ 启用 ping/pong 双向心跳。
    """

    event: Literal["pong"] = Field(default="pong", description="事件类型常量")
    data: dict = Field(default_factory=dict, description="预留载荷；v0.2 为空")


# =============================================================================
# 联合类型（供路由 / 测试做类型注解）
# =============================================================================


WSServerEvent = (
    TickAdvancedEvent
    | PausedEvent
    | RunFinishedEvent
    | ErrorEvent
    | PingEvent
)
"""server → client 推送的所有事件类型联合。"""

WSClientEvent = PongEvent
"""client → server 上行消息——v0.2 仅 PongEvent。"""
