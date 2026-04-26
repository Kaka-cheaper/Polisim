"""MockProvider：可复现的假 LLM provider，用于测试与 CI（D-005）。

对应 `docs/02-design/LLM决策协议设计.md` 12.3 节"MockProvider（第 2~4 步默认使用）"。

使用目的：

1. 第 2~4 步（Runtime / 规则 / walkthrough）不接真实 LLM API 就能跑 tick
2. 测试中避免网络依赖、API key 泄露与速率限制
3. 让 Runtime 测试的 "给定输入 → 预期动作" 关系完全确定

**两种工作模式**（构造时二选一）：

- **固定响应（fixed）**——无论 prompt 是什么，永远返回同一字符串
- **脚本响应（scripted）**——按调用顺序从列表中取；列表用尽后**循环**回到开头

不支持 "从 prompt 中智能挑动作" 的模式——那会耦合 prompt 格式，使 mock 变脆弱。
若测试需要按实体/场景定制不同输出，用 `scripted_responses` 显式排好序即可。

观测字段（供测试断言）：

- ``call_count``：累计调用次数
- ``last_prompt``：最后一次收到的 prompt
- ``last_kwargs``：最后一次收到的 kwargs（拷贝，防止外部修改影响内部状态）
"""

from __future__ import annotations

from typing import Any

from core.providers.base import LLMProvider


class MockProvider(LLMProvider):
    """确定性 LLM provider，适用于测试 / CI / 第 2~4 步 Runtime 跑通。

    构造参数（``fixed_response`` 与 ``scripted_responses`` **恰好**二选一）：

    - ``fixed_response: str``——每次调用都返回此字符串
    - ``scripted_responses: list[str]``——按顺序返回，耗尽后循环
    """

    def __init__(
        self,
        *,
        fixed_response: str | None = None,
        scripted_responses: list[str] | None = None,
    ) -> None:
        both_none = fixed_response is None and scripted_responses is None
        both_given = fixed_response is not None and scripted_responses is not None
        if both_none or both_given:
            raise ValueError(
                "MockProvider 需要且仅需要提供 fixed_response 或 "
                "scripted_responses 二选一"
            )
        if scripted_responses is not None and len(scripted_responses) == 0:
            raise ValueError("scripted_responses 不能为空列表")

        self._fixed = fixed_response
        self._scripted = scripted_responses
        self._call_count = 0
        self._last_prompt: str | None = None
        self._last_kwargs: dict[str, Any] = {}

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """返回预设响应；``ProviderError`` 永不抛出（mock 不访问外部资源）。"""
        self._last_prompt = prompt
        self._last_kwargs = dict(kwargs)
        idx = self._call_count
        self._call_count += 1

        if self._fixed is not None:
            return self._fixed

        # __init__ 已确保 scripted 非空
        assert self._scripted is not None
        return self._scripted[idx % len(self._scripted)]

    # ---------- 观测接口 ----------

    @property
    def call_count(self) -> int:
        """累计调用次数。"""
        return self._call_count

    @property
    def last_prompt(self) -> str | None:
        """最后一次 ``generate`` 收到的 prompt；未调用过时为 None。"""
        return self._last_prompt

    @property
    def last_kwargs(self) -> dict[str, Any]:
        """最后一次 ``generate`` 收到的 kwargs 拷贝。"""
        return dict(self._last_kwargs)
