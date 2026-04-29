"""server/services/intervention_service.py —— 干预的业务层（D-017 第 6.2 节）。

3 类 Intervention（kind）：
- ``inject_message``——给某个 actor 投递消息
- ``force_action``——强制 actor 下一 tick 执行某动作
- ``override_attribute``——直接修改 actor 属性

实现就是包装 `Runtime.intervene`——它已经处理 3 类的具体逻辑 + 写
``intervention_applied`` 事件。本 service 层只做：

1. 通过 RuntimeRegistry 找 Runtime；不存在 → 404（FileNotFoundError）
2. 调 runtime.intervene(intervention) → 让内核去校验 + 应用
3. 把返回的 EventRecord 透传给路由层
"""

from __future__ import annotations

from models.runtime_models import EventRecord, Intervention

from server.runtime_registry import RuntimeRegistry


class InterventionService:
    """3 类干预的业务编排层。

    与 RunService 的关系：

    - 共享同一 ``RuntimeRegistry``——它们对同一 run 的并发调用线程安全
      （Runtime 内部用 register 锁保护，但 step 与 intervene 之间是顺序的）
    - v0.2 不做"干预排队"——若用户在 step 进行中调用 intervene，
      会等到 step 完成后才进入 intervene；这是 v1 内核的天然顺序模型
    """

    def __init__(self, registry: RuntimeRegistry) -> None:
        self._registry = registry

    def apply(self, run_id: str, intervention: Intervention) -> EventRecord:
        """应用干预并返写入的 EventRecord。

        Runtime.intervene 自然抛 ValueError（target_actor 不存在 / kind
        不合规等）—— server 全局 handler 映射为 400。
        """
        runtime = self._registry.get(run_id)
        if runtime is None:
            raise FileNotFoundError(f"run_id={run_id!r} 不存在或已归档")
        return runtime.intervene(intervention)
