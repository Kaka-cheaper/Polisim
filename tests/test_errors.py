"""`core/errors.py` 的单元测试（D-011 部分落地）。

覆盖要点：

1. `SimEngineError` 继承自 `Exception` 但**不**继承 `RuntimeError` / `ValueError`
   ——D-011 核心动机是让这两条路径正交
2. 所有子类继承自 `SimEngineError`——上层一条 ``except SimEngineError``可捕获全部
3. ``ProviderError`` re-export from `core.providers.base` 必须是**同一个对象**
   （不是两份定义）——保证既有测试与 Runtime 代码无需改动
4. chained exception（``raise X() from Y``）的 ``__cause__`` 可正确保留
"""

from __future__ import annotations

import pytest

from core.errors import (
    InvalidStateError,
    LLMProtocolError,
    PausedError,
    ProviderError,
    RulesError,
    SimEngineError,
    TerminatedError,
)


class TestInheritanceTree:
    """继承关系——D-011 的核心契约。"""

    @pytest.mark.parametrize(
        "subclass",
        [
            ProviderError,
            LLMProtocolError,
            RulesError,
            InvalidStateError,
            PausedError,
            TerminatedError,
        ],
    )
    def test_subclass_inherits_sim_engine_error(
        self, subclass: type[Exception]
    ) -> None:
        assert issubclass(subclass, SimEngineError)
        assert issubclass(subclass, Exception)

    def test_sim_engine_error_does_not_inherit_runtime_error(self) -> None:
        """D-011 动机：``except RuntimeError`` 与 ``except SimEngineError`` 正交。"""
        assert not issubclass(SimEngineError, RuntimeError)
        assert not issubclass(SimEngineError, ValueError)

    def test_catches_all_subclasses_with_base(self) -> None:
        """一条 ``except SimEngineError`` 拦全部业务错误。"""
        for subclass in (
            ProviderError,
            LLMProtocolError,
            RulesError,
            InvalidStateError,
            PausedError,
            TerminatedError,
        ):
            try:
                raise subclass("test")
            except SimEngineError:
                pass  # 期望
            else:
                pytest.fail(f"{subclass.__name__} 没被 SimEngineError 拦到")


class TestReExport:
    """`core.providers.base.ProviderError` 必须是 `core.errors.ProviderError` 同一对象。"""

    def test_same_object_across_modules(self) -> None:
        from core.providers.base import ProviderError as ReExported

        assert ReExported is ProviderError

    def test_isinstance_cross_module(self) -> None:
        from core.providers.base import ProviderError as ReExported

        exc = ReExported("boom")
        assert isinstance(exc, ProviderError)
        assert isinstance(exc, SimEngineError)


class TestChainedException:
    """``raise X() from Y`` 保留 ``__cause__``——用于调试。"""

    def test_cause_preserved(self) -> None:
        inner = ValueError("original")
        try:
            raise ProviderError("wrapped") from inner
        except ProviderError as exc:
            assert exc.__cause__ is inner

    def test_llm_protocol_error_with_cause(self) -> None:
        inner = ValueError("bad json")
        try:
            raise LLMProtocolError("parse fail") from inner
        except LLMProtocolError as exc:
            assert exc.__cause__ is inner


class TestConstruction:
    """全部异常应接受单字符串参数并复现到 ``str(exc)``。"""

    @pytest.mark.parametrize(
        "cls",
        [
            SimEngineError,
            ProviderError,
            LLMProtocolError,
            RulesError,
            InvalidStateError,
            PausedError,
            TerminatedError,
        ],
    )
    def test_str_roundtrip(self, cls: type[Exception]) -> None:
        exc = cls("message body")
        assert str(exc) == "message body"
