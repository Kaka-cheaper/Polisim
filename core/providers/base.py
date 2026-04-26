"""LLM Provider 抽象层基类（D-005）。

对应 `docs/02-design/LLM决策协议设计.md` 十二节"Provider 抽象层"。

**分层约束**：

1. 本模块定义 `LLMProvider` ABC 与统一异常 `ProviderError`
2. 所有具体 provider（`mock.py` / `openai.py` / `anthropic.py`）都必须继承 `LLMProvider`
3. `core/llm_policy.py` 与 `core/runtime.py` **只**依赖本文件的 ABC，
   禁止直接 `import openai` / `import anthropic`
4. 具体 SDK 的异常必须由 provider 实现封装为 `ProviderError`，保证上层重试逻辑
   不感知底层差异
5. 可用 provider 的枚举与 `models/config_models.LLMProviderConfig.provider` 的
   ``Literal["openai", "anthropic", "mock"]`` 一一对应

**职责边界**：

本层只做"传输"——把 prompt 发出去、把原始文本拿回来。
协议级校验（输出 JSON 合法性）、协议级重试、降级等都在 `core/llm_policy.py`。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

# D-011：`ProviderError` 权威定义搬到 `core/errors.py`（继承 `SimEngineError`）。
# 本文件保留 re-export 以兼容既有 ``from core.providers.base import ProviderError``
# 的调用点——无需改动现有测试与 Runtime 代码。
from core.errors import ProviderError  # noqa: F401 re-export


class LLMProvider(ABC):
    """LLM Provider 抽象基类（D-005）。

    所有真实或假的 LLM 调用路径都必须实现这个接口。

    **约定**：

    - 同步接口优先。异步版本（`async_generate`）留到 `RuntimeConfig.max_concurrent_decisions`
      真正 > 1 时再加，第一版保守为 1
    - ``generate`` 返回**原始文本**，不做 JSON 解析——解析归 `llm_policy.py`
    - 失败只能抛 `ProviderError`，禁止外泄具体 SDK 的异常类型

    **kwargs 约定**（所有实现必须接受，未知 kwarg 应忽略而非报错）：

    - ``temperature: float``——采样温度，对齐 `LLMProviderConfig.temperature`
    - ``max_tokens: int``——输出 token 上限
    - ``timeout: float``——单次请求超时秒数
    - ``system_prompt: str``——覆盖 provider 构造期默认 system prompt；
      让同一 provider 实例服务多种消费者（决策层 / 分析增强层）时各自维持
      合适的角色定位。识别此 kwarg 的实现（如 `OpenAIProvider`）会用它替换
      默认值；不识别的实现（如 `MockProvider`）按通用规则静默忽略
    """

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> str:
        """发送 prompt 到 LLM，返回原始文本。

        参数：
            prompt: 已由 `llm_policy.py` 组织好的完整 prompt 文本
            **kwargs: 至少接受 ``temperature`` / ``max_tokens`` / ``timeout``；
                未识别字段应静默忽略

        返回：
            LLM 返回的**原始文本**。JSON 解析 / 合法性校验不在本层

        抛出：
            ProviderError: 传输层失败时（网络 / 鉴权 / 速率限制 / 超时 / SDK 异常）
        """
