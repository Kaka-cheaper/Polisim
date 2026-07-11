"""server/services/stream_service.py —— WebSocket 推送服务（D-017 第 6.3 节）。

**核心职责**：

1. 维护 `run_id -> set[asyncio.Queue]` 订阅者表
2. 提供 **sync `broadcast`**——FastAPI sync 路由（如 RunService.step）能直接调
3. 提供 **async `subscribe / unsubscribe`**——给 WebSocket 协程用

**线程模型**：

- FastAPI sync 路由可能跑在 starlette 的 thread pool 里
- broadcast 是 sync 接口；通过 `loop.call_soon_threadsafe` 安全地把消息塞进
  asyncio.Queue（每个连接独立队列）
- WebSocket 协程在主 event loop 里 `await queue.get()`

**反压策略**：

- 每个 queue 有 `maxsize=100`——上限保护
- broadcast 时 queue 已满 → **静默丢弃**（不让慢客户端拖慢主流程）
- 这是 v0.2 简化策略；v0.3+ 可加"丢失数计数 + 客户端追赶"机制

**所有权**：

- v0.2 单 server 进程——一个全局 StreamService 由 app.lifespan 构造
- v0.3+ 集群：StreamService 替换为 RedisStreamService（共享发布订阅）
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections import defaultdict
from typing import Any

from server.api.v1.ws_events import WSEventBase


logger = logging.getLogger(__name__)


# 单连接 queue 上限——超出丢弃以保护慢客户端不拖累 server
_QUEUE_MAXSIZE = 100


class StreamService:
    """WebSocket 订阅广播服务。

    使用模式：

    ```python
    # WebSocket 协程
    async def ws_endpoint(ws, run_id):
        queue = await stream_service.subscribe(run_id)
        try:
            while True:
                msg = await queue.get()
                await ws.send_json(msg)
        finally:
            await stream_service.unsubscribe(run_id, queue)

    # FastAPI sync 路由（如 RunService.step）
    def step(self, run_id):
        result = runtime.step()
        stream_service.broadcast(run_id, TickAdvancedEvent(data=result))
        return result
    ```
    """

    def __init__(self) -> None:
        # run_id -> set[asyncio.Queue]
        # 用 list 而非 set 是因为 asyncio.Queue 不是 hashable（v0.2 暂用 set 也可，
        # CPython 默认 Queue 实例可哈希——身份比较——这里仍稳）
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
        # 主 event loop 引用——broadcast 用 call_soon_threadsafe 必须知道目标 loop
        self._loop: asyncio.AbstractEventLoop | None = None
        # 保护 _subscribers 的锁——broadcast (任意线程) 与 subscribe/unsubscribe (主 loop) 并发
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # 启动 / 关闭
    # ------------------------------------------------------------------

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """记录主 event loop——必须在 app.lifespan 启动时调用一次。

        broadcast 用 ``loop.call_soon_threadsafe`` 安全跨线程投递消息。
        未 attach 时 broadcast 是 no-op（避免启动期意外抛错）。
        """
        self._loop = loop

    def detach(self) -> None:
        """app.lifespan 关闭时调用——释放 loop 引用 + 清空订阅者。"""
        with self._lock:
            self._subscribers.clear()
        self._loop = None

    # ------------------------------------------------------------------
    # 订阅 / 取消订阅（async，给 WebSocket 协程用）
    # ------------------------------------------------------------------

    async def subscribe(self, run_id: str) -> asyncio.Queue:
        """注册新订阅者——返回它的 queue。

        WebSocket 协程拿到 queue 后 ``await queue.get()`` 读取消息。
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=_QUEUE_MAXSIZE)
        with self._lock:
            self._subscribers[run_id].add(queue)
        return queue

    async def unsubscribe(self, run_id: str, queue: asyncio.Queue) -> None:
        """注销订阅——WebSocket 关闭时调用。

        清空队列并丢弃——避免 queue 滞留在内存里。
        """
        with self._lock:
            self._subscribers.get(run_id, set()).discard(queue)
            # 如果该 run 没有订阅者了，移除 key 防止字典无限增长
            if run_id in self._subscribers and not self._subscribers[run_id]:
                del self._subscribers[run_id]

    def subscriber_count(self, run_id: str) -> int:
        """订阅者数（测试 / 监控用）。"""
        with self._lock:
            return len(self._subscribers.get(run_id, set()))

    # ------------------------------------------------------------------
    # 推送（sync，FastAPI sync 路由可调）
    # ------------------------------------------------------------------

    def broadcast(self, run_id: str, event: WSEventBase) -> None:
        """把事件推送给该 run 的所有订阅者。

        线程安全——任何线程都能调（FastAPI sync 路由跑在 thread pool 里）。

        实现：用 ``loop.call_soon_threadsafe`` 把 ``queue.put_nowait`` 安排到
        主 event loop 执行；若 queue 满则丢弃（QueueFull 静默吞）。

        **健壮性保证**（session 33 架构审查 F2）：整个推送用 try/except 包裹——
        Pydantic 序列化报错 / loop 关闭 / queue 赋值异常都不能阻断调用者
        （典型场景：RunService.step）主流程。仅 log warning，让 server 永远能返 200。

        **race fix**（session 45 F8）：原本 ``self._loop is None`` 检查与
        后续 ``call_soon_threadsafe`` 之间存在 TOCTOU 窗口——如果 detach()
        在两者之间把 loop 设为 None，会触发 NoneType.call_soon_threadsafe。
        改为持锁同时读 loop + 订阅者快照。
        """
        try:
            # 序列化为 dict（一次性，避免每个订阅者重复 dump）
            message = event.model_dump(mode="json")
        except Exception:  # noqa: BLE001 顶层守护——任何序列化报错都不能拖垄 step
            logger.warning(
                "stream_service.broadcast: event serialization failed; "
                "dropping message run_id=%s event_type=%s",
                run_id,
                type(event).__name__,
                exc_info=True,
            )
            return
        # F8：把 loop 引用与订阅者快照一同在锁内读取，闭合 TOCTOU 窗口
        with self._lock:
            loop = self._loop
            queues = list(self._subscribers.get(run_id, ()))
        if loop is None:
            # server 还未启动 attach_loop 或已 detach——丢弃消息（不阻断 broadcaster）
            return
        if not queues:
            return
        for queue in queues:
            try:
                loop.call_soon_threadsafe(self._safe_put, queue, message)
            except RuntimeError:
                # loop 已关闭——server 正在 shutdown；忽略
                logger.debug(
                    "stream_service.broadcast: loop closed, dropping message"
                )

    @staticmethod
    def _safe_put(queue: asyncio.Queue, message: Any) -> None:
        """在主 loop 里安全地 put_nowait；queue 满则丢弃。"""
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            # 慢客户端追不上——丢弃这条消息保 server 可用
            logger.debug(
                "stream_service: queue full, dropping message for slow client"
            )

    # ------------------------------------------------------------------
    # 关闭某 run 所有订阅者（run finished / GC 时用）
    # ------------------------------------------------------------------

    def close_run(self, run_id: str) -> None:
        """通知该 run 所有订阅者结束——通过特殊 sentinel `None` put 到 queue。

        WebSocket 协程读到 None → break 循环 + close ws + unsubscribe。

        **race fix**（session 45 F8）：与 broadcast 同模式——loop 引用 + 订阅者
        快照在锁内同时读，闭合与 detach() 的 TOCTOU 窗口。
        """
        with self._lock:
            loop = self._loop
            queues = list(self._subscribers.get(run_id, ()))
        if loop is None:
            return
        for queue in queues:
            try:
                loop.call_soon_threadsafe(self._safe_put, queue, None)
            except RuntimeError:
                pass
