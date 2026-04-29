"""server/api/v1/routes/ws.py —— GET /api/v1/runs/:run_id/stream WebSocket 路由（D-017 第四节）。

**协议**：

- 升级 WebSocket，订阅 stream_service
- server → client 推送 typed 事件（ws_events.py）
- client → server 仅发 PongEvent（v0.2 唯一上行）
- 关闭码：1000 正常 / 4004 run 不存在或已归档 / 4500 内部错误

**实现要点**：

- 每个连接起 2 个并发任务：`_send_loop`（消费 queue → ws.send_json）+
  `_receive_loop`（接收 client pong / 检测断开）；任一结束都终止另一个
- 用 ``asyncio.wait`` + FIRST_COMPLETED 等待两个任务
- finally 必须 unsubscribe + close ws，避免泄露 queue
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from server.runtime_registry import RuntimeRegistry
from server.services.stream_service import StreamService


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/runs", tags=["websocket"])


# WebSocket 关闭码（D-017 第 4.1 / 4.5 节）
_WS_CLOSE_NORMAL = 1000
_WS_CLOSE_RUN_NOT_FOUND = 4004
_WS_CLOSE_INTERNAL_ERROR = 4500


@router.websocket("/{run_id}/stream")
async def stream_run(websocket: WebSocket, run_id: str) -> None:
    """订阅指定 run 的实时事件流。

    生命周期：

    1. 接受 WebSocket 连接
    2. 检查 run_id 是否在 registry 里——不在则 close(4004)
    3. subscribe stream_service，拿到 queue
    4. 启动 send_loop 与 receive_loop 两个任务
    5. 等任一结束或异常 → 取消另一个 → unsubscribe → close
    """
    # FastAPI 把 app 实例绑在 websocket.app 上（同样的 state）
    app_state = websocket.app.state
    registry: RuntimeRegistry = app_state.registry
    stream_service: StreamService = app_state.stream_service

    # 必须先 accept；之后 close 才能带 close code 给客户端
    await websocket.accept()

    # 校验 run 存在
    if registry.get(run_id) is None:
        await websocket.close(
            code=_WS_CLOSE_RUN_NOT_FOUND, reason="run not found"
        )
        return

    # 订阅
    queue = await stream_service.subscribe(run_id)
    logger.info(
        "ws stream connected: run_id=%s subscribers=%d",
        run_id,
        stream_service.subscriber_count(run_id),
    )

    # 起两个任务并发跑
    send_task = asyncio.create_task(_send_loop(websocket, queue))
    recv_task = asyncio.create_task(_receive_loop(websocket))

    try:
        done, pending = await asyncio.wait(
            {send_task, recv_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        # 收集异常用于决定关闭码
        for task in done:
            exc = task.exception()
            if exc is not None and not isinstance(exc, WebSocketDisconnect):
                logger.exception(
                    "ws stream task error: run_id=%s",
                    run_id,
                    exc_info=exc,
                )
                # 试图发 close(4500)
                if websocket.client_state == WebSocketState.CONNECTED:
                    try:
                        await websocket.close(
                            code=_WS_CLOSE_INTERNAL_ERROR,
                            reason="internal server error",
                        )
                    except Exception:
                        pass
                return
    finally:
        await stream_service.unsubscribe(run_id, queue)
        # 正常关闭——若还在连接里
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.close(code=_WS_CLOSE_NORMAL)
            except Exception:
                pass
        logger.info("ws stream closed: run_id=%s", run_id)


async def _send_loop(websocket: WebSocket, queue: asyncio.Queue) -> None:
    """主推送循环——从 queue 拿消息发给客户端。

    收到 ``None`` 表示 server 主动关闭该 run（run finished + close_run），
    跳出循环让外层流程走 close。
    """
    while True:
        msg = await queue.get()
        if msg is None:
            # server 主动 close 信号
            return
        await websocket.send_json(msg)


async def _receive_loop(websocket: WebSocket) -> None:
    """接收循环——v0.2 仅 PongEvent；其他消息忽略。

    主要功能：检测客户端断开（receive_text 抛 WebSocketDisconnect）→
    让外层 wait FIRST_COMPLETED 醒来 → 走清理逻辑。
    """
    while True:
        # 任何 client 消息都接受；v0.2 不强制 schema 验证（避免 TypeError 误关 ws）
        await websocket.receive_text()
