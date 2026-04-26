"""OpenAI Provider 实现（Phase B.2）。

对应 `docs/02-design/LLM决策协议设计.md` 十二节"Provider 抽象层"。

**设计原则**：

- 继承 `LLMProvider` ABC，实现唯一抽象方法 `generate(prompt, **kwargs) -> str`
- 包装 `openai` SDK 的 `Client.chat.completions.create` 调用
- 捕获所有底层 SDK 异常，统一抛 `ProviderError`（D-005 / D-011）——
  上层 `core/llm_policy` 只需 ``except ProviderError`` 一条路径
- 使用 ``response_format={"type": "json_object"}``——OpenAI JSON 模式，强制
  模型返回合法 JSON，降低 `LLMProtocolError` 概率
- **不**做协议级重试——那是 `core/llm_policy` 的职责（Phase B.3 补）；
  `openai.OpenAI(max_retries=N)` 仅处理传输层的 429 / 5xx 自动退避

**API key 解析**：

- 来源：`LLMProviderConfig.api_key_env`（环境变量名）+ `os.environ`
- **禁止**把 API key 直接写进 `LLMProviderConfig.api_key` 这种字段——
  `config_models.LLMProviderConfig` 只有 ``api_key_env``，没有 ``api_key``
- 构造期解析；环境变量未设时立即抛 `ProviderError`，防止延迟到首次调用才报错

**兼容性**：

- 通过 ``base_url`` 可指向 Azure OpenAI / OpenRouter / 本地 vLLM 等 OpenAI 兼容端点
- **模型名透传**——`LLMProviderConfig.model` 不做枚举校验，允许任意字符串
"""

from __future__ import annotations

import os
from typing import Any

from core.errors import ProviderError
from core.providers.base import LLMProvider
from models.config_models import LLMProviderConfig


# =============================================================================
# 常量
# =============================================================================


_DEFAULT_SYSTEM_PROMPT = (
    "You are a decision-making agent in a multi-entity simulation. "
    "The user message contains the current tick context as JSON, including "
    "the actor's state, inbox messages, environment variables, and a list "
    "of available_actions with their parameter schemas. "
    "Your response MUST be a valid JSON object with EXACTLY this shape:\n"
    '{"action": "<one of available_actions>", "params": {...}, "reason": "<optional string>"}\n'
    "Rules:\n"
    "1. `action` must be the `name` field of one of the available_actions.\n"
    "2. `params` must match the parameter schema of the chosen action.\n"
    "3. `reason` is optional—a brief explanation of why you chose this action.\n"
    "4. Do NOT include any prose, markdown, or explanation outside the JSON object."
)
"""Phase B.2 最简 system prompt。

- 明确用户输入格式（当前 tick context JSON）
- 明确响应形状（匹配 `core/llm_policy.parse_response` 的期望）
- 含 "JSON" 关键词——这是 ``response_format={"type":"json_object"}`` 的硬性要求
  （OpenAI API 会校验 prompt 中必须至少出现一次 "json"）
- 后续 Phase B.3+ 可升级为多段式、含历史摘要、memory stream 等
"""


# =============================================================================
# OpenAIProvider
# =============================================================================


class OpenAIProvider(LLMProvider):
    """OpenAI（及兼容端点）的 `LLMProvider` 实现。

    构造：

    >>> from models.config_models import LLMProviderConfig
    >>> cfg = LLMProviderConfig(
    ...     provider="openai",
    ...     model="gpt-4o-mini",
    ...     api_key_env="OPENAI_API_KEY",
    ... )
    >>> provider = OpenAIProvider(cfg)  # 从 os.environ["OPENAI_API_KEY"] 读 key

    Raises:
        ProviderError: 构造期——``api_key_env`` 未提供或环境变量未设
    """

    def __init__(
        self,
        config: LLMProviderConfig,
        *,
        system_prompt: str = _DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        if config.provider != "openai":
            raise ProviderError(
                f"OpenAIProvider 只接受 provider='openai'，实际 "
                f"'{config.provider}'"
            )
        if not config.api_key_env:
            raise ProviderError(
                "OpenAIProvider 需要 LLMProviderConfig.api_key_env（环境变量名）"
            )
        api_key = os.environ.get(config.api_key_env)
        if not api_key:
            raise ProviderError(
                f"环境变量 '{config.api_key_env}' 未设置或为空，"
                f"无法初始化 OpenAIProvider"
            )

        # 延迟 import 避免未装 openai 时其他 provider 仍可工作
        from openai import OpenAI

        # OpenAI SDK 的 max_retries 处理传输层的 429 / 5xx 自动退避——
        # 协议级重试（不合法 JSON）走 core/llm_policy（Phase B.3）
        self._client = OpenAI(
            api_key=api_key,
            base_url=config.base_url,  # None 时走默认 api.openai.com
            max_retries=config.max_retries,
            timeout=config.timeout_sec,
        )
        self._config = config
        self._system_prompt = system_prompt

    def generate(self, prompt: str, **kwargs: Any) -> str:
        """调 chat.completions.create；失败统一抛 `ProviderError`。

        kwargs 识别：
        - ``temperature``——覆盖 config.temperature
        - ``max_tokens``——输出 token 上限（默认 512）
        - ``timeout``——覆盖 config.timeout_sec（本次调用）
        - ``system_prompt``——覆盖构造期默认 system prompt（用于不同消费者
          需要不同角色定位时，例如 ``analysis.enhance_with_llm`` 用分析导向，
          ``llm_policy.decide`` 用决策导向）
        未识别 kwargs 静默忽略（LLMProvider ABC 约定）。
        """
        # 延迟 import——与构造函数一致
        from openai import (
            APIConnectionError,
            APIError,
            APITimeoutError,
            AuthenticationError,
            BadRequestError,
            RateLimitError,
        )

        temperature = kwargs.get("temperature", self._config.temperature)
        max_tokens = kwargs.get("max_tokens", 512)
        timeout = kwargs.get("timeout", self._config.timeout_sec)
        system_prompt = kwargs.get("system_prompt") or self._system_prompt

        try:
            response = self._client.chat.completions.create(
                model=self._config.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                response_format={"type": "json_object"},
            )
        except AuthenticationError as exc:
            raise ProviderError(
                f"OpenAI 鉴权失败（401）；检查 "
                f"${self._config.api_key_env} 是否正确"
            ) from exc
        except RateLimitError as exc:
            raise ProviderError(
                f"OpenAI 速率限制（429）；详情：{exc}"
            ) from exc
        except APITimeoutError as exc:
            raise ProviderError(
                f"OpenAI 请求超时（>{timeout}s）"
            ) from exc
        except APIConnectionError as exc:
            raise ProviderError(f"OpenAI 连接失败：{exc}") from exc
        except BadRequestError as exc:
            # 400——通常是模型名错 / 参数不合法。构造层问题，但用 ProviderError
            # 统一上抛，由 llm_policy / cli 暴露给用户
            raise ProviderError(
                f"OpenAI 请求被拒（400）：{exc}"
            ) from exc
        except APIError as exc:
            # 5xx / 其他未归类
            raise ProviderError(
                f"OpenAI API 错误（{type(exc).__name__}）：{exc}"
            ) from exc

        content = response.choices[0].message.content
        if content is None:
            # 极端情况：模型触发 content_filter，content 会是 None
            raise ProviderError(
                "OpenAI 响应内容为空（可能被 content filter 拦截）"
            )
        return content
