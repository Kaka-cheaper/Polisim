"""`core/providers/openai.py` 的单元测试（Phase B.2）。

测试策略：

- **全 mock**——不发任何真实 OpenAI 请求；CI 无需 `OPENAI_API_KEY`
- 验证构造期参数校验：provider 类型 / api_key_env 缺失 / env 未设
- 验证 ``generate`` 的五条异常分支映射到 `ProviderError`
- 验证 kwargs 透传（temperature / max_tokens / timeout）
- 验证 ``response_format={"type":"json_object"}`` 始终被设置
- 验证 base_url 透传到 `OpenAI` 构造函数

真实 API 连通测试放在 `scripts/smoke_openai.py`（手动执行，不进 CI）。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from core.errors import ProviderError
from core.providers.openai import OpenAIProvider, _DEFAULT_SYSTEM_PROMPT
from models.config_models import LLMProviderConfig


# =============================================================================
# Helpers——构造 openai SDK 异常
# =============================================================================


def _dummy_http_response(status: int) -> httpx.Response:
    return httpx.Response(
        status, request=httpx.Request("POST", "https://api.openai.com/v1/x")
    )


def _make_rate_limit_error() -> Exception:
    from openai import RateLimitError

    return RateLimitError(
        "rate limited", response=_dummy_http_response(429), body={}
    )


def _make_auth_error() -> Exception:
    from openai import AuthenticationError

    return AuthenticationError(
        "bad key", response=_dummy_http_response(401), body={}
    )


def _make_bad_request_error() -> Exception:
    from openai import BadRequestError

    return BadRequestError(
        "invalid model", response=_dummy_http_response(400), body={}
    )


def _make_timeout_error() -> Exception:
    from openai import APITimeoutError

    # APITimeoutError 需要 request 参数
    return APITimeoutError(
        request=httpx.Request("POST", "https://api.openai.com/v1/x")
    )


def _make_connection_error() -> Exception:
    from openai import APIConnectionError

    return APIConnectionError(
        request=httpx.Request("POST", "https://api.openai.com/v1/x")
    )


def _make_generic_api_error() -> Exception:
    from openai import APIError

    return APIError(
        "server error",
        request=httpx.Request("POST", "https://api.openai.com/v1/x"),
        body={},
    )


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def provider_config() -> LLMProviderConfig:
    return LLMProviderConfig(
        provider="openai",
        model="gpt-4o-mini",
        api_key_env="FAKE_OPENAI_KEY",
        temperature=0.5,
        max_retries=2,
        timeout_sec=10.0,
    )


@pytest.fixture
def env_with_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FAKE_OPENAI_KEY", "sk-test-placeholder")


def _build_mock_completion(content: str) -> MagicMock:
    """构造 chat.completions.create 的返回值 mock。"""
    completion = MagicMock()
    completion.choices = [MagicMock()]
    completion.choices[0].message.content = content
    return completion


# =============================================================================
# 1. 构造
# =============================================================================


class TestConstruction:
    def test_happy_path(
        self, provider_config: LLMProviderConfig, env_with_key: None
    ) -> None:
        with patch("openai.OpenAI") as mock_openai:
            provider = OpenAIProvider(provider_config)
            mock_openai.assert_called_once()
            kwargs = mock_openai.call_args.kwargs
            assert kwargs["api_key"] == "sk-test-placeholder"
            assert kwargs["max_retries"] == 2
            assert kwargs["timeout"] == 10.0

    def test_rejects_non_openai_provider(
        self, env_with_key: None
    ) -> None:
        cfg = LLMProviderConfig(
            provider="mock",
            model="foo",
            api_key_env="FAKE_OPENAI_KEY",
        )
        with pytest.raises(ProviderError, match="provider='openai'"):
            OpenAIProvider(cfg)

    def test_rejects_missing_api_key_env(self) -> None:
        cfg = LLMProviderConfig(
            provider="openai",
            model="gpt-4o-mini",
            api_key_env=None,
        )
        with pytest.raises(ProviderError, match="api_key_env"):
            OpenAIProvider(cfg)

    def test_rejects_env_var_not_set(
        self,
        provider_config: LLMProviderConfig,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("FAKE_OPENAI_KEY", raising=False)
        with pytest.raises(ProviderError, match="未设置"):
            OpenAIProvider(provider_config)

    def test_rejects_env_var_empty_string(
        self,
        provider_config: LLMProviderConfig,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("FAKE_OPENAI_KEY", "")
        with pytest.raises(ProviderError, match="未设置或为空"):
            OpenAIProvider(provider_config)

    def test_base_url_propagated(
        self, env_with_key: None
    ) -> None:
        cfg = LLMProviderConfig(
            provider="openai",
            model="gpt-4o-mini",
            api_key_env="FAKE_OPENAI_KEY",
            base_url="https://proxy.example.com/v1",
        )
        with patch("openai.OpenAI") as mock_openai:
            OpenAIProvider(cfg)
            kwargs = mock_openai.call_args.kwargs
            assert kwargs["base_url"] == "https://proxy.example.com/v1"


# =============================================================================
# 2. generate() happy path
# =============================================================================


class TestGenerateHappyPath:
    def test_returns_message_content(
        self, provider_config: LLMProviderConfig, env_with_key: None
    ) -> None:
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = (
                _build_mock_completion('{"action": "promote"}')
            )
            mock_openai.return_value = mock_client

            provider = OpenAIProvider(provider_config)
            result = provider.generate("dummy prompt")
            assert result == '{"action": "promote"}'

    def test_system_and_user_messages_sent(
        self, provider_config: LLMProviderConfig, env_with_key: None
    ) -> None:
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = (
                _build_mock_completion('{"action": "do_nothing"}')
            )
            mock_openai.return_value = mock_client

            provider = OpenAIProvider(provider_config)
            provider.generate("CONTEXT")

            kwargs = mock_client.chat.completions.create.call_args.kwargs
            messages = kwargs["messages"]
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == _DEFAULT_SYSTEM_PROMPT
            assert messages[1]["role"] == "user"
            assert messages[1]["content"] == "CONTEXT"

    def test_forces_json_response_format(
        self, provider_config: LLMProviderConfig, env_with_key: None
    ) -> None:
        """response_format 必须指定 json_object——否则 OpenAI 可能加 prose。"""
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = (
                _build_mock_completion("{}")
            )
            mock_openai.return_value = mock_client
            OpenAIProvider(provider_config).generate("x")

            kwargs = mock_client.chat.completions.create.call_args.kwargs
            assert kwargs["response_format"] == {"type": "json_object"}

    def test_kwargs_override_config(
        self, provider_config: LLMProviderConfig, env_with_key: None
    ) -> None:
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = (
                _build_mock_completion("{}")
            )
            mock_openai.return_value = mock_client
            OpenAIProvider(provider_config).generate(
                "x", temperature=0.9, max_tokens=256, timeout=5.0
            )

            kwargs = mock_client.chat.completions.create.call_args.kwargs
            assert kwargs["temperature"] == 0.9
            assert kwargs["max_tokens"] == 256
            assert kwargs["timeout"] == 5.0

    def test_unknown_kwargs_ignored(
        self, provider_config: LLMProviderConfig, env_with_key: None
    ) -> None:
        """ABC 约定：未知 kwarg 应静默忽略，不 crash。"""
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = (
                _build_mock_completion("{}")
            )
            mock_openai.return_value = mock_client
            provider = OpenAIProvider(provider_config)
            # 不应抛 TypeError
            provider.generate("x", some_unknown_kwarg="value")

    def test_system_prompt_kwarg_overrides_default(
        self, provider_config: LLMProviderConfig, env_with_key: None
    ) -> None:
        """F1：传 system_prompt kwarg 时覆盖构造期默认——避免角色冲突。"""
        custom_system = (
            "You are a JSON-only trajectory analyst; respond with JSON object."
        )
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = (
                _build_mock_completion("{}")
            )
            mock_openai.return_value = mock_client

            OpenAIProvider(provider_config).generate(
                "context", system_prompt=custom_system
            )

            kwargs = mock_client.chat.completions.create.call_args.kwargs
            messages = kwargs["messages"]
            assert messages[0]["role"] == "system"
            assert messages[0]["content"] == custom_system
            # 默认 system prompt 不再出现
            assert messages[0]["content"] != _DEFAULT_SYSTEM_PROMPT
            # user 消息原样透传
            assert messages[1]["role"] == "user"
            assert messages[1]["content"] == "context"

    def test_system_prompt_default_used_when_kwarg_absent(
        self, provider_config: LLMProviderConfig, env_with_key: None
    ) -> None:
        """不传 system_prompt 时，回退到构造期默认值（决策导向）。"""
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = (
                _build_mock_completion("{}")
            )
            mock_openai.return_value = mock_client

            OpenAIProvider(provider_config).generate("context")

            kwargs = mock_client.chat.completions.create.call_args.kwargs
            assert kwargs["messages"][0]["content"] == _DEFAULT_SYSTEM_PROMPT


# =============================================================================
# 3. generate() 异常映射
# =============================================================================


class TestGenerateExceptionMapping:
    @pytest.mark.parametrize(
        "make_error,expected_pattern",
        [
            (_make_auth_error, "鉴权失败"),
            (_make_rate_limit_error, "速率限制"),
            (_make_timeout_error, "请求超时"),
            (_make_connection_error, "连接失败"),
            (_make_bad_request_error, "请求被拒"),
            (_make_generic_api_error, "API 错误"),
        ],
    )
    def test_maps_to_provider_error(
        self,
        provider_config: LLMProviderConfig,
        env_with_key: None,
        make_error,
        expected_pattern: str,
    ) -> None:
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = make_error()
            mock_openai.return_value = mock_client

            provider = OpenAIProvider(provider_config)
            with pytest.raises(ProviderError, match=expected_pattern):
                provider.generate("x")

    def test_preserves_cause(
        self, provider_config: LLMProviderConfig, env_with_key: None
    ) -> None:
        original = _make_rate_limit_error()
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = original
            mock_openai.return_value = mock_client

            provider = OpenAIProvider(provider_config)
            with pytest.raises(ProviderError) as exc_info:
                provider.generate("x")
            assert exc_info.value.__cause__ is original

    def test_none_content_raises_provider_error(
        self, provider_config: LLMProviderConfig, env_with_key: None
    ) -> None:
        """content_filter 拦截时 content=None——包装为 ProviderError。"""
        with patch("openai.OpenAI") as mock_openai:
            mock_client = MagicMock()
            completion = MagicMock()
            completion.choices = [MagicMock()]
            completion.choices[0].message.content = None
            mock_client.chat.completions.create.return_value = completion
            mock_openai.return_value = mock_client

            provider = OpenAIProvider(provider_config)
            with pytest.raises(ProviderError, match="内容为空"):
                provider.generate("x")
