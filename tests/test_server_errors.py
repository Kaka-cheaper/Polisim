"""tests/test_server_errors.py —— D-017 ERROR_MAP + handler 测试。

覆盖 D-017 第九节"错误映射（参数化）"：每种 SimEngineError 子类必须映射到
正确的 (status_code, code) 二元组。
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.errors import (
    InvalidStateError,
    LLMProtocolError,
    PausedError,
    ProviderError,
    RulesError,
    SemanticValidationError,
    SimEngineError,
    TerminatedError,
)
from core.rules_loader import RulesLoadError

from server.api.v1.errors import (
    ERROR_MAP,
    ErrorBody,
    ErrorIssue,
    ErrorResponse,
    get_error_map_for_exception,
    register_exception_handlers,
)


# =============================================================================
# 模型测试
# =============================================================================


class TestErrorSchemas:
    """ErrorBody / ErrorResponse / ErrorIssue 模型形状。"""

    def test_error_body_basic(self) -> None:
        body = ErrorBody(code="X", message="msg")
        assert body.code == "X"
        assert body.issues is None

    def test_error_body_with_issues(self) -> None:
        body = ErrorBody(
            code="SEMANTIC_VALIDATION_FAILED",
            message="2 项问题",
            issues=[
                ErrorIssue(
                    field_path="world.x", kind="not_found", detail="..."
                )
            ],
        )
        assert len(body.issues) == 1
        assert body.issues[0].field_path == "world.x"

    def test_error_response_serializable(self) -> None:
        resp = ErrorResponse(error=ErrorBody(code="X", message="m"))
        # exclude_none：issues=None 时不出现在序列化结果里
        d = resp.model_dump(exclude_none=True)
        assert d == {"error": {"code": "X", "message": "m"}}


# =============================================================================
# ERROR_MAP 完整性
# =============================================================================


@pytest.mark.parametrize(
    "exc_cls, expected_status, expected_code",
    [
        (InvalidStateError, 400, "INVALID_STATE"),
        (PausedError, 409, "RUNTIME_PAUSED"),
        (TerminatedError, 410, "RUNTIME_TERMINATED"),
        (SemanticValidationError, 422, "SEMANTIC_VALIDATION_FAILED"),
        (RulesError, 500, "RULES_ERROR"),
        (RulesLoadError, 500, "RULES_LOAD_FAILED"),
        (ProviderError, 502, "LLM_PROVIDER_ERROR"),
        (LLMProtocolError, 502, "LLM_PROTOCOL_ERROR"),
        (ValueError, 400, "INVALID_REQUEST"),
        (FileNotFoundError, 404, "RESOURCE_NOT_FOUND"),
    ],
)
def test_error_map_complete(
    exc_cls: type[Exception], expected_status: int, expected_code: str
) -> None:
    """每种已登记异常映射到设计的 (status, code) 二元组。"""
    assert exc_cls in ERROR_MAP, f"{exc_cls.__name__} 未在 ERROR_MAP 中登记"
    status, code = ERROR_MAP[exc_cls]
    assert status == expected_status
    assert code == expected_code


def test_get_error_map_walks_mro() -> None:
    """子类异常按 mro 走继承链找最近映射。"""

    class CustomProviderError(ProviderError):
        pass

    exc = CustomProviderError("x")
    status, code = get_error_map_for_exception(exc)
    assert status == 502
    assert code == "LLM_PROVIDER_ERROR"


def test_get_error_map_unknown_simengine_falls_back() -> None:
    """未知 SimEngineError 子类降级到 (500, "UNKNOWN_ENGINE_ERROR")。"""

    class CustomEngineError(SimEngineError):
        pass

    status, code = get_error_map_for_exception(CustomEngineError("x"))
    assert status == 500
    assert code == "UNKNOWN_ENGINE_ERROR"


# =============================================================================
# Handler 集成测试（用最小 app + raise 路由）
# =============================================================================


def _build_test_app() -> FastAPI:
    """构造最小 FastAPI app 含触发各类异常的路由——给 handler 集成测试用。"""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/raise/invalid-state")
    def _r1() -> None:
        raise InvalidStateError("invalid")

    @app.get("/raise/paused")
    def _r2() -> None:
        raise PausedError("paused")

    @app.get("/raise/terminated")
    def _r3() -> None:
        raise TerminatedError("done")

    @app.get("/raise/semantic")
    def _r4() -> None:
        raise SemanticValidationError("2 issues", issues=[])

    @app.get("/raise/rules")
    def _r5() -> None:
        raise RulesError("rules bug")

    @app.get("/raise/rules-load")
    def _r6() -> None:
        raise RulesLoadError("load bug")

    @app.get("/raise/provider")
    def _r7() -> None:
        raise ProviderError("provider bug")

    @app.get("/raise/protocol")
    def _r8() -> None:
        raise LLMProtocolError("protocol bug")

    @app.get("/raise/value")
    def _r9() -> None:
        raise ValueError("bad input")

    @app.get("/raise/notfound")
    def _r10() -> None:
        raise FileNotFoundError("missing.yaml")

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(_build_test_app())


@pytest.mark.parametrize(
    "endpoint, expected_status, expected_code",
    [
        ("/raise/invalid-state", 400, "INVALID_STATE"),
        ("/raise/paused", 409, "RUNTIME_PAUSED"),
        ("/raise/terminated", 410, "RUNTIME_TERMINATED"),
        ("/raise/semantic", 422, "SEMANTIC_VALIDATION_FAILED"),
        ("/raise/rules", 500, "RULES_ERROR"),
        ("/raise/rules-load", 500, "RULES_LOAD_FAILED"),
        ("/raise/provider", 502, "LLM_PROVIDER_ERROR"),
        ("/raise/protocol", 502, "LLM_PROTOCOL_ERROR"),
        ("/raise/value", 400, "INVALID_REQUEST"),
        ("/raise/notfound", 404, "RESOURCE_NOT_FOUND"),
    ],
)
def test_handler_returns_correct_status(
    client: TestClient,
    endpoint: str,
    expected_status: int,
    expected_code: str,
) -> None:
    """从路由抛异常 → handler 返正确 status_code + code。"""
    resp = client.get(endpoint)
    assert resp.status_code == expected_status
    body = resp.json()
    assert "error" in body
    assert body["error"]["code"] == expected_code
    assert body["error"]["message"]  # 非空


def test_handler_response_has_error_envelope(client: TestClient) -> None:
    """所有错误响应必有 `error` 顶层包装（D-017 第 5.1 节契约）。"""
    resp = client.get("/raise/invalid-state")
    body = resp.json()
    assert "error" in body
    assert "code" in body["error"]
    assert "message" in body["error"]


def test_semantic_error_carries_issues(client: TestClient) -> None:
    """SemanticValidationError.issues 应序列化进 ErrorBody.issues。"""
    # 改造 _build_test_app 单点：直接用临时 app 验证
    app = FastAPI()
    register_exception_handlers(app)

    class _MockIssue:
        def __init__(self) -> None:
            self.field_path = "x.y.z"
            self.kind = "missing"
            self.detail = "field 'z' not found"

        def model_dump(self) -> dict:
            return {
                "field_path": self.field_path,
                "kind": self.kind,
                "detail": self.detail,
            }

    @app.get("/raise/semantic-with-issues")
    def _r() -> None:
        raise SemanticValidationError("1 issue", issues=[_MockIssue()])

    c = TestClient(app)
    resp = c.get("/raise/semantic-with-issues")
    assert resp.status_code == 422
    body = resp.json()
    assert "issues" in body["error"]
    assert len(body["error"]["issues"]) == 1
    issue = body["error"]["issues"][0]
    assert issue["field_path"] == "x.y.z"
    assert issue["kind"] == "missing"


def test_handler_does_not_leak_traceback(client: TestClient) -> None:
    """禁止把 Python traceback 暴露到响应体（D-017 第 2.4 节）。"""
    resp = client.get("/raise/rules")
    body = resp.json()
    body_str = str(body)
    # traceback 关键字不应出现
    assert "Traceback" not in body_str
    assert "File " not in body_str
    assert "  line " not in body_str
