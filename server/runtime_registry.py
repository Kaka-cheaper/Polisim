"""server/runtime_registry.py —— 多并发 Runtime 实例的内存注册表（D-017 第七节）。

**职责**：
- 维护 `run_id -> Runtime` 的映射
- 提供 `register / get / shutdown / shutdown_all / active_count / list_summaries` 接口
- 限制并发 run 数量（默认 10）—— 超限时拒绝新建（后续映射为 503）

**线程模型**：
- v0.2 单进程 + asyncio——FastAPI 的标准部署形态
- 共享 dict 用 `threading.Lock` 保护——FastAPI 在 sync 路由里可能跑在 thread pool；
  asyncio.Lock 不能跨同步/异步使用
- 上层 service 层不该直接修改 dict——只通过本类方法

**演进路径**（D-017 第 7.2 节）：

| 演进方向 | 触发条件 | 实现思路 |
|---|---|---|
| Redis 共享 | 集群部署 | `RuntimeRegistry` 替换为 `RedisRegistry` |
| 重启持久化 | server 重启不丢未跑完的 run | SQLite 存暂停点；启动时从 EventLog 重放 |
| 多用户隔离 | v0.4 SaaS | run_id 改为 `(user_id, run_id)` 复合键 |
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Literal

from core.runtime import Runtime

from server.api.v1.schemas import RunSummary


class RegistryFullError(Exception):
    """活跃 run 数已达 max_concurrent 上限。

    继承自 Python 内置 `Exception`——不进 D-011 异常树（这是平台运维错，
    不是 v1 引擎语义错）；server.app 的全局 handler 把它映射为 503。
    """


class RuntimeRegistry:
    """活跃 Runtime 实例的内存注册表。

    使用方式：
    - server 启动时构造一个全局 registry（lifespan）
    - service 通过 FastAPI Depends 注入它
    - WebSocket 推送（session 32）也复用同一 registry 找 Runtime
    - server 关闭时 `shutdown_all()` 关闭所有活跃 run，触发各 EventLog 的最后 flush

    **关键约定**：

    1. `register` 后 Runtime 的所有权归 registry——直到 `shutdown(run_id)` 才放
    2. `get(run_id)` 返回的引用调用方**不应** `close()`——交给 registry 管
    3. `shutdown_all()` 顺序遍历所有活跃 run，单个失败不影响其他
    """

    def __init__(self, max_concurrent: int = 10) -> None:
        if max_concurrent < 1:
            raise ValueError(
                f"max_concurrent 必须 ≥ 1，收到 {max_concurrent}"
            )
        self._max_concurrent = max_concurrent
        self._runtimes: dict[str, Runtime] = {}
        self._created_at: dict[str, datetime] = {}
        self._lock = threading.Lock()

    @property
    def max_concurrent(self) -> int:
        """允许的最大并发 run 数。"""
        return self._max_concurrent

    def register(self, run_id: str, runtime: Runtime) -> None:
        """注册新 Runtime。

        前置条件：
        - run_id 未被占用
        - 当前活跃数 < max_concurrent

        失败抛异常：
        - `ValueError`——run_id 已存在
        - `RegistryFullError`——超出并发上限

        v1 内核已经在 EventLog 层保证 run_id 唯一（generate_run_id 含时间戳）；
        此处再加一道防御以防上层重复注册。
        """
        with self._lock:
            if run_id in self._runtimes:
                raise ValueError(
                    f"run_id={run_id!r} 已注册——重复 register 是上层 bug"
                )
            if len(self._runtimes) >= self._max_concurrent:
                raise RegistryFullError(
                    f"活跃 run 数 {len(self._runtimes)} 已达上限 "
                    f"{self._max_concurrent}；请等待已有 run 完成或调高 max_concurrent"
                )
            self._runtimes[run_id] = runtime
            self._created_at[run_id] = datetime.now(timezone.utc)

    def get(self, run_id: str) -> Runtime | None:
        """获取活跃 Runtime；不存在返 None。

        调用方负责处理 None 情况（路由层映射为 404）。
        """
        with self._lock:
            return self._runtimes.get(run_id)

    def get_created_at(self, run_id: str) -> datetime | None:
        """获取注册时间——给 RunSummary.created_at 用。"""
        with self._lock:
            return self._created_at.get(run_id)

    def shutdown(self, run_id: str) -> bool:
        """关闭并移除指定 run。

        返回是否实际移除（True：成功；False：run_id 不存在）。
        失败 close() 不抛异常——日志降级，继续清理 dict。
        """
        with self._lock:
            runtime = self._runtimes.pop(run_id, None)
            self._created_at.pop(run_id, None)
        if runtime is None:
            return False
        try:
            runtime.close()
        except Exception:
            # 关闭失败不该阻断 registry 清理；防止 close 异常吞掉 server lifecycle
            pass
        return True

    def shutdown_all(self) -> int:
        """关闭所有活跃 run。

        返回成功关闭的数量。供 server lifespan 关闭时使用。
        """
        with self._lock:
            run_ids = list(self._runtimes.keys())
        closed = 0
        for run_id in run_ids:
            if self.shutdown(run_id):
                closed += 1
        return closed

    def active_count(self) -> int:
        """当前活跃 run 数。"""
        with self._lock:
            return len(self._runtimes)

    def list_summaries(self) -> list[RunSummary]:
        """枚举所有活跃 run 的摘要（GET /runs 用）。

        返回的 RunSummary.status 取自 Runtime 的实时状态：

        - `paused`——`runtime.is_paused()` True
        - `finished`——`runtime.current_tick() >= scenario.config.total_ticks`
        - `active`——其余（在跑或刚创建未跑）

        快照取在锁内——保证迭代过程中 dict 不变；快照外的 Runtime 调用不持锁
        以免 step 操作长时间阻塞列表查询。
        """
        with self._lock:
            snapshot = list(self._runtimes.items())
            created_snapshot = dict(self._created_at)
        result: list[RunSummary] = []
        for run_id, runtime in snapshot:
            current = runtime.current_tick()
            total = runtime.scenario.config.total_ticks
            # 用 Literal 注解局部变量，让类型检查器自然推断（去掉 session 33 F5）
            status: Literal["active", "paused", "finished"]
            if current >= total:
                status = "finished"
            elif runtime.is_paused():
                status = "paused"
            else:
                status = "active"
            result.append(
                RunSummary(
                    run_id=run_id,
                    world_id=runtime.scenario.world_id,
                    scenario_id=runtime.scenario.scenario.id,
                    status=status,
                    current_tick=current,
                    total_ticks=total,
                    created_at=created_snapshot.get(
                        run_id, datetime.now(timezone.utc)
                    ),
                )
            )
        return result
