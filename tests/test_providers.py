"""Provider 抽象层测试（D-005）。

对应 `docs/02-design/LLM决策协议设计.md` 十二节"Provider 抽象层"。

覆盖：

1. `LLMProvider` ABC 契约：未实现 ``generate`` 的子类不可实例化，实现了就可以
2. `ProviderError` 是 ``Exception`` 的合法子类，支持 ``raise ... from exc`` 语义
3. `MockProvider` 两种工作模式（fixed / scripted）各自正确
4. `MockProvider` 构造参数互斥性（必须二选一且非空）
5. `MockProvider` 观测字段（call_count / last_prompt / last_kwargs）正确且防篡改

不覆盖：

- 真实 provider（`openai.py` / `anthropic.py`）——第 5 步实装后再测
- `llm_policy.py` 的协议级重试 / 校验——属于上层测试
"""

from __future__ import annotations

from typing import Any

import pytest

from core.providers.base import LLMProvider, ProviderError
from core.providers.mock import MockProvider


# =============================================================================
# LLMProvider ABC 契约
# =============================================================================


def test_llm_provider_cannot_be_instantiated_directly() -> None:
    """抽象基类不能直接实例化——Python ABC 在缺少实现时抛 TypeError。"""
    with pytest.raises(TypeError):
        LLMProvider()  # type: ignore[abstract]


def test_llm_provider_subclass_missing_generate_cannot_instantiate() -> None:
    """子类若未实现 ``generate``，仍然不可实例化。"""

    class Incomplete(LLMProvider):
        pass

    with pytest.raises(TypeError):
        Incomplete()  # type: ignore[abstract]


def test_llm_provider_subclass_with_generate_works() -> None:
    """子类只要实现了 ``generate`` 就能实例化和调用。"""

    class Minimal(LLMProvider):
        def generate(self, prompt: str, **kwargs: Any) -> str:
            return f"echo:{prompt}"

    provider = Minimal()
    assert provider.generate("hello") == "echo:hello"


# =============================================================================
# ProviderError
# =============================================================================


def test_provider_error_is_exception_subclass() -> None:
    assert issubclass(ProviderError, Exception)


def test_provider_error_preserves_cause() -> None:
    """使用 ``raise ProviderError(...) from exc`` 保留原始异常作为 __cause__。"""
    original = ConnectionError("底层网络断了")
    try:
        try:
            raise original
        except ConnectionError as exc:
            raise ProviderError("传输层失败") from exc
    except ProviderError as wrapped:
        assert wrapped.__cause__ is original
        assert str(wrapped) == "传输层失败"


# =============================================================================
# MockProvider 构造参数互斥性
# =============================================================================


def test_mock_provider_requires_one_mode() -> None:
    """既不给 fixed 也不给 scripted：ValueError。"""
    with pytest.raises(ValueError, match="二选一"):
        MockProvider()


def test_mock_provider_rejects_both_modes() -> None:
    """同时给 fixed 和 scripted：ValueError。"""
    with pytest.raises(ValueError, match="二选一"):
        MockProvider(fixed_response="a", scripted_responses=["b", "c"])


def test_mock_provider_rejects_empty_scripted_list() -> None:
    with pytest.raises(ValueError, match="不能为空"):
        MockProvider(scripted_responses=[])


# =============================================================================
# MockProvider fixed 模式
# =============================================================================


def test_mock_provider_fixed_returns_same_string_every_call() -> None:
    provider = MockProvider(fixed_response='{"action": "do_nothing", "params": {}}')
    r1 = provider.generate("prompt-1")
    r2 = provider.generate("prompt-2")
    r3 = provider.generate("prompt-3")
    assert r1 == r2 == r3 == '{"action": "do_nothing", "params": {}}'


def test_mock_provider_fixed_call_count_increments() -> None:
    provider = MockProvider(fixed_response="x")
    assert provider.call_count == 0
    provider.generate("a")
    provider.generate("b")
    assert provider.call_count == 2


# =============================================================================
# MockProvider scripted 模式
# =============================================================================


def test_mock_provider_scripted_returns_in_order() -> None:
    provider = MockProvider(scripted_responses=["first", "second", "third"])
    assert provider.generate("p") == "first"
    assert provider.generate("p") == "second"
    assert provider.generate("p") == "third"


def test_mock_provider_scripted_wraps_around_when_exhausted() -> None:
    """列表用尽后索引循环回开头，便于长时间跑 tick 不用手动扩长脚本。"""
    provider = MockProvider(scripted_responses=["a", "b"])
    assert provider.generate("p") == "a"
    assert provider.generate("p") == "b"
    assert provider.generate("p") == "a"
    assert provider.generate("p") == "b"
    assert provider.call_count == 4


def test_mock_provider_scripted_single_element() -> None:
    provider = MockProvider(scripted_responses=["only"])
    assert provider.generate("p") == "only"
    assert provider.generate("p") == "only"


# =============================================================================
# MockProvider 观测字段
# =============================================================================


def test_mock_provider_tracks_last_prompt() -> None:
    provider = MockProvider(fixed_response="x")
    assert provider.last_prompt is None
    provider.generate("第一个 prompt")
    assert provider.last_prompt == "第一个 prompt"
    provider.generate("第二个 prompt")
    assert provider.last_prompt == "第二个 prompt"


def test_mock_provider_tracks_last_kwargs() -> None:
    provider = MockProvider(fixed_response="x")
    provider.generate("p", temperature=0.5, max_tokens=100, timeout=10.0)
    kwargs = provider.last_kwargs
    assert kwargs == {"temperature": 0.5, "max_tokens": 100, "timeout": 10.0}


def test_mock_provider_last_kwargs_is_defensive_copy() -> None:
    """返回的 kwargs 是副本，外部修改不影响内部状态。"""
    provider = MockProvider(fixed_response="x")
    provider.generate("p", temperature=0.5)

    returned = provider.last_kwargs
    returned["temperature"] = 999
    returned["extra"] = "hack"

    # 内部状态不受影响
    assert provider.last_kwargs == {"temperature": 0.5}


def test_mock_provider_ignores_unknown_kwargs() -> None:
    """未识别的 kwargs 应被静默接受（记录但不影响输出）。"""
    provider = MockProvider(fixed_response="ok")
    result = provider.generate("p", weird_option=True, another=42)
    assert result == "ok"
    assert provider.last_kwargs == {"weird_option": True, "another": 42}
