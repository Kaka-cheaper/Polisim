"""server/api/v1/errors.py —— SimEngineError → HTTP 错误响应映射（D-017 第五节）。

**核心契约**（D-017 第 2.4 节）：

1. 所有非 2xx 响应**必须**统一为 `ErrorResponse` 形态——前端单点解析
2. `ErrorResponse.error.code` 是结构化字符串——前端按此分支处理
3. `ErrorResponse.error.message` 是中文友好提示——可直接展示
4. `ErrorResponse.error.issues` 是可选结构化条目——`SemanticValidationError` 用，
   供 LLM 辅助建模"自我修复循环"消费

**禁止**：把 Python traceback / 堆栈直接暴露给前端。

**异常映射表**（ERROR_MAP）：

| Python 异常类           | HTTP 状态 | error.code              |
|-------------------------|-----------|-------------------------|
| InvalidStateError       | 400       | INVALID_STATE           |
| ValueError              | 400       | INVALID_REQUEST         |
| FileNotFoundError       | 404       | RESOURCE_NOT_FOUND      |
| PausedError             | 409       | RUNTIME_PAUSED          |
| TerminatedError         | 410       | RUNTIME_TERMINATED      |
| SemanticValidationError | 422       | SEMANTIC_VALIDATION_FAILED |
| RulesError              | 500       | RULES_ERROR             |
| RulesLoadError          | 500       | RULES_LOAD_FAILED       |
| ProviderError           | 502       | LLM_PROVIDER_ERROR      |
| LLMProtocolError        | 502       | LLM_PROTOCOL_ERROR      |
| SimEngineError（基类）  | 500       | UNKNOWN_ENGINE_ERROR    |

未列出的 Python 内置异常（如 RuntimeError）→ FastAPI 默认 500，前端按 5xx 处理。
"""

from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

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


# =============================================================================
# 响应 schema
# =============================================================================


class ErrorIssue(BaseModel):
    """单条结构化错误条目（SemanticValidationError.issues 用）。

    字段语义对齐 `core/semantic_validator.SemanticIssue`，但避免反向依赖
    （issues 在 SimEngineError 基类中只声明为 list，元素结构由生产侧约定）。
    """

    model_config = ConfigDict(extra="allow")

    field_path: str = Field(..., description="出错字段在配置树中的路径")
    kind: str = Field(..., description="错误种类标识符（机器可分支）")
    detail: str = Field(..., description="人类可读的细节信息")


class ErrorBody(BaseModel):
    """错误响应主体——D-017 第 2.4 节定义的统一形态。"""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., description="错误码——前端可分支处理")
    message: str = Field(..., description="人类可读消息——可直接展示")
    issues: list[ErrorIssue] | None = Field(
        default=None,
        description="可选结构化错误条目（SemanticValidationError 等用）",
    )


class ErrorResponse(BaseModel):
    """ErrorResponse 顶层包装。

    设计意图：前端识别"任意非 2xx → 解析这一种形态"，无需按 endpoint 区分。
    """

    model_config = ConfigDict(extra="forbid")

    error: ErrorBody = Field(..., description="错误体")


# =============================================================================
# 异常 → HTTP 映射表
# =============================================================================


ERROR_MAP: dict[type[BaseException], tuple[int, str]] = {
    # 4xx 客户端错误
    InvalidStateError: (400, "INVALID_STATE"),
    ValueError: (400, "INVALID_REQUEST"),
    FileNotFoundError: (404, "RESOURCE_NOT_FOUND"),
    PausedError: (409, "RUNTIME_PAUSED"),
    TerminatedError: (410, "RUNTIME_TERMINATED"),
    SemanticValidationError: (422, "SEMANTIC_VALIDATION_FAILED"),
    # 5xx 服务端错误
    RulesError: (500, "RULES_ERROR"),
    RulesLoadError: (500, "RULES_LOAD_FAILED"),
    ProviderError: (502, "LLM_PROVIDER_ERROR"),
    LLMProtocolError: (502, "LLM_PROTOCOL_ERROR"),
}


# =============================================================================
# 异常处理器
# =============================================================================


def _build_error_response(
    exc: BaseException, status_code: int, code: str
) -> JSONResponse:
    """构造统一格式的 JSON 错误响应。

    `SemanticValidationError.issues` 携带结构化条目时一并塞进 `error.issues`；
    其它异常类型 issues 字段为 None。
    """
    issues: list[ErrorIssue] | None = None
    raw_issues = getattr(exc, "issues", None)
    if raw_issues:
        # SemanticValidationError 的 issues 是 list[SemanticIssue]——后者通过 Pydantic 持有
        # field_path / kind / detail 三字段，可直接 model_dump 兼容 ErrorIssue。
        # 防御式：万一 issues 项不是 BaseModel，做 dict 兜底。
        issues = []
        for item in raw_issues:
            if hasattr(item, "model_dump"):
                issues.append(ErrorIssue(**item.model_dump()))
            elif isinstance(item, dict):
                issues.append(ErrorIssue(**item))
            else:
                # 非预期类型——降级为字符串放进 detail，避免 500 处理器自身崩溃
                issues.append(
                    ErrorIssue(
                        field_path="<unknown>",
                        kind="malformed_issue",
                        detail=str(item),
                    )
                )
    body = ErrorBody(code=code, message=str(exc), issues=issues)
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(error=body).model_dump(exclude_none=True),
    )


async def simengine_error_handler(
    request: Request, exc: SimEngineError
) -> JSONResponse:
    """SimEngineError 系列的统一处理器。

    通过 `ERROR_MAP` 查具体子类的状态码与 code；未在表中的子类降级到
    `(500, "UNKNOWN_ENGINE_ERROR")`——只允许这一种"未识别的业务异常"形态。
    """
    status_code, code = ERROR_MAP.get(type(exc), (500, "UNKNOWN_ENGINE_ERROR"))
    return _build_error_response(exc, status_code, code)


async def value_error_handler(
    request: Request, exc: ValueError
) -> JSONResponse:
    """ValueError → 400 INVALID_REQUEST。

    Python 内置 `ValueError` 在 v1 内核里表达"用户输入错"——直接转 400。
    """
    return _build_error_response(exc, 400, "INVALID_REQUEST")


async def file_not_found_handler(
    request: Request, exc: FileNotFoundError
) -> JSONResponse:
    """FileNotFoundError → 404 RESOURCE_NOT_FOUND。

    场景配置文件 / world 文件路径不存在时，CLI 习惯抛 `FileNotFoundError`，
    server 把它映射为 4xx 状态。
    """
    return _build_error_response(exc, 404, "RESOURCE_NOT_FOUND")


def get_error_map_for_exception(exc: BaseException) -> tuple[int, str]:
    """便利函数——给定异常实例，返回（状态码，code）。

    供测试代码 / 文档生成使用；不在 handler 注册路径上。
    优先精确匹配；其次按 mro 找继承链上最近的命中；最后降级 (500, "UNKNOWN_ENGINE_ERROR")。
    """
    for cls in type(exc).__mro__:
        if cls in ERROR_MAP:
            return ERROR_MAP[cls]
    return (500, "UNKNOWN_ENGINE_ERROR")


def register_exception_handlers(app: Any) -> None:
    """把所有处理器注册到 FastAPI 应用。

    顺序：具体优先——`SimEngineError` 兜底业务异常；`ValueError` / `FileNotFoundError`
    单独走自己的 handler 不被 `SimEngineError` 吃掉（它们不是 SimEngineError 子类）。

    `app.add_exception_handler` 接受异常类作 key——FastAPI 内部按 mro 匹配。
    """
    app.add_exception_handler(SimEngineError, simengine_error_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(FileNotFoundError, file_not_found_handler)
