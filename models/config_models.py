"""系统级配置的数据模型。

对应 `docs/02-design/实现映射设计.md` 4.8 节——此类配置独立于
`World Definition / Scenario / Rules` 三层业务建模文件，不随场景变化。

四类配置：

- `LLMConfig`——对应 `config/llm.yaml`：LLM provider、模型、超时、重试、采样等
- `RuntimeConfig`——对应 `config/runtime.yaml`：并发决策数、随机种子、LLM 请求超时
- `StorageConfig`——对应 `config/storage.yaml`：事件轨迹、快照的存储路径与格式
- `LoggingConfig`——对应 `config/logging.yaml`：日志级别、格式、输出位置

**注意（D-004）**：设计文档只给出了这四份配置的职责边界，未给出具体字段定义。
本文件的字段清单是第一版由实现层自定的最小集合，所有字段都给了合理默认值，
以便首次运行时不强制用户提供任何 `config/*.yaml`。未来若运行时或 LLM 协议
演进，相关字段应回滚到此文件修改，而不是散落在代码各处。

校验分工：

1. 结构/类型——Pydantic（本文件）
2. 跨字段（例如 `LLMConfig.default_provider` 必须在 `providers` 中存在）——
   用 `model_validator` 内联校验，失败时抛 `pydantic.ValidationError`
3. 此处不引入独立的 `config_loader.py`，因为这些配置：
   - 没有跨文件引用（不需要与 World / Scenario 互校验）
   - 没有语义复杂度（不像 World 里的 enum values / min/max / 引用链）
   - Pydantic 自身已足够
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


# =============================================================================
# LLM 配置
# =============================================================================


class LLMProviderConfig(BaseModel):
    """单个 LLM provider 的配置条目。

    `provider` 限制为枚举：

    - `openai`——OpenAI 协议兼容 provider（含 Azure / 任何 OpenAI 兼容 endpoint）
    - `anthropic`——Anthropic Claude
    - `mock`——本地可复现的假 provider，用于测试与 CI，无需真实 API key
    """

    model_config = ConfigDict(extra="forbid")

    provider: Literal["openai", "anthropic", "mock"] = Field(
        ..., description="provider 类型"
    )
    model: str = Field(..., min_length=1, description="模型名")
    api_key_env: str | None = Field(
        default=None,
        description="从哪个环境变量读取 API key；mock provider 不需要",
    )
    base_url: str | None = Field(
        default=None, description="API base URL；自托管或代理时使用"
    )
    timeout_sec: float = Field(
        default=30.0, gt=0, description="单次请求超时秒数"
    )
    max_retries: int = Field(
        default=2,
        ge=0,
        description="重试次数上限，对齐 LLM决策协议设计 第七节的协议默认值",
    )
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="采样温度"
    )


class LLMConfig(BaseModel):
    """`config/llm.yaml` 的顶层模型。"""

    model_config = ConfigDict(extra="forbid")

    version: Literal["0.1"] = Field(..., description="配置文件版本")
    default_provider: str = Field(
        ...,
        min_length=1,
        description="默认使用的 provider 名称，必须是 providers 的 key 之一",
    )
    providers: dict[str, LLMProviderConfig] = Field(
        ..., min_length=1, description="至少声明一个 provider"
    )

    @model_validator(mode="after")
    def _default_provider_must_exist(self) -> "LLMConfig":
        if self.default_provider not in self.providers:
            raise ValueError(
                f"default_provider '{self.default_provider}' 未在 providers "
                f"{sorted(self.providers.keys())} 中声明"
            )
        return self


# =============================================================================
# Runtime 配置
# =============================================================================


class RuntimeConfig(BaseModel):
    """`config/runtime.yaml` 的顶层模型。

    此处字段只涉及"如何运行"，不涉及"世界是什么"或"场景如何配置"。
    业务默认值（`conflict_resolution` / `max_messages_per_tick` /
    `action_effect_order` 等）属于 World Definition 的 `defaults` 段，
    与本文件职责无关。
    """

    model_config = ConfigDict(extra="forbid")

    version: Literal["0.1"] = Field(..., description="配置文件版本")
    random_seed: int | None = Field(
        default=None, description="全局随机种子；None 表示不固定"
    )
    max_concurrent_decisions: int = Field(
        default=1,
        ge=1,
        description="单 tick 内并行采集决策的并发数；第一版保守为 1",
    )
    llm_request_timeout_sec: float = Field(
        default=30.0,
        gt=0,
        description="LLM 请求的整体超时秒数；与 LLMProviderConfig.timeout_sec "
        "叠加（取较小值）",
    )
    output_language: str = Field(
        default="zh-CN",
        min_length=1,
        description=(
            "LLM 输出自然语言字段时使用的语言（ISO 639-1 或自然语言名；LLM 会"
            "自行理解）。影响范围：决策层的 reason 字段、Phase C 分析层的叙事/"
            "判断/建议段落。**不**影响 JSON 结构字段（action / params 等）——"
            "那些是机器标识符，与语言无关。通过 prompt 注入生效，provider 层"
            "不关心。默认 zh-CN（简体中文）。"
        ),
    )


# =============================================================================
# Storage 配置
# =============================================================================


class StorageConfig(BaseModel):
    """`config/storage.yaml` 的顶层模型。

    控制事件轨迹与快照是否落盘、归到哪个根目录、用什么格式。

    **D-007 约定**：所有仿真产物统一落到 ``{runs_root}/<run_id>/`` 下，目录结构固定：

    - ``config.yaml``——本次合并后的 world + scenario + system config 快照（复现用）
    - ``events.jsonl``——一行一 ``EventRecord``（``event_log_format=jsonl`` 时）
    - ``snapshots/tick_<N>.json``——按 tick 切分的快照
    - ``analysis/interim_tick_<N>.{md,json}`` + ``analysis/final.{md,json}``

    Run 级子目录由 ``core/events.py`` / ``core/runtime.py`` 按约定拼接，
    **不**作为本配置的字段——避免配置层越俎代庖定义内部结构。

    **D-006 约定**：所有落盘格式必须是 UI-ready（JSONL / JSON / MD），以便第二阶段
    UI 项目可直接消费 ``{runs_root}/<run_id>/`` 目录而不改动内核。
    """

    model_config = ConfigDict(extra="forbid")

    version: Literal["0.1"] = Field(..., description="配置文件版本")
    persist: bool = Field(
        default=True,
        description="是否把事件与快照写入磁盘；False 时只保留在内存中",
    )
    runs_root: str = Field(
        default="./runs",
        description="所有运行产物的根目录；每次仿真归到 `{runs_root}/<run_id>/`",
    )
    event_log_format: Literal["jsonl"] = Field(
        default="jsonl",
        description="事件日志格式；v1 仅支持 jsonl（对齐 D-006 UI-ready 约定）。"
        "若未来需要人读格式，请在决策层先提 D-xxx 再扩展枚举，避免僵尸字段。",
    )


# =============================================================================
# Logging 配置
# =============================================================================


class LoggingConfig(BaseModel):
    """`config/logging.yaml` 的顶层模型。"""

    model_config = ConfigDict(extra="forbid")

    version: Literal["0.1"] = Field(..., description="配置文件版本")
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="日志级别"
    )
    format: str = Field(
        default="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        description="标准 logging 模块的格式串",
    )
    output: Literal["stdout", "file", "both"] = Field(
        default="stdout", description="日志输出位置"
    )
    file_path: str | None = Field(
        default=None,
        description="输出到文件时的路径；output 为 stdout 时忽略",
    )

    @model_validator(mode="after")
    def _file_path_required_when_output_uses_file(self) -> "LoggingConfig":
        if self.output in ("file", "both") and not self.file_path:
            raise ValueError(
                f"output='{self.output}' 时必须提供 file_path"
            )
        return self


# =============================================================================
# 通用加载器
# =============================================================================


def _load_yaml_as_dict(path: str | Path) -> dict[str, Any]:
    """把 YAML 文件读成 dict，非 dict 顶层抛 ValueError。"""
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(
            f"配置文件顶层必须是对象（dict），实际为 "
            f"{type(data).__name__}: {file_path}"
        )
    return data


def load_llm_config(path: str | Path) -> LLMConfig:
    """从 YAML 加载 `LLMConfig`。"""
    return LLMConfig.model_validate(_load_yaml_as_dict(path))


def load_runtime_config(path: str | Path) -> RuntimeConfig:
    """从 YAML 加载 `RuntimeConfig`。"""
    return RuntimeConfig.model_validate(_load_yaml_as_dict(path))


def load_storage_config(path: str | Path) -> StorageConfig:
    """从 YAML 加载 `StorageConfig`。"""
    return StorageConfig.model_validate(_load_yaml_as_dict(path))


def load_logging_config(path: str | Path) -> LoggingConfig:
    """从 YAML 加载 `LoggingConfig`。"""
    return LoggingConfig.model_validate(_load_yaml_as_dict(path))
