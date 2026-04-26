"""config_models 的结构与跨字段校验测试。

对应 `docs/01-requirements/验收标准.md` 第 6 节——虽然该节未明确列出 config，
但决策 D-004 把第一版 config schema 固化在 `models/config_models.py`，
本测试就是 D-004 的验收载体。

测试组织：

1. 合法路径（每类 config 的最小合法构造 + YAML 加载）
2. 必填字段
3. 枚举与数值下限
4. extra='forbid'
5. 跨字段：`LLMConfig.default_provider ∈ providers`、
          `LoggingConfig` 在 `output ∈ {file, both}` 时必须提供 `file_path`
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from models.config_models import (
    LLMConfig,
    LLMProviderConfig,
    LoggingConfig,
    RuntimeConfig,
    StorageConfig,
    load_llm_config,
    load_logging_config,
    load_runtime_config,
    load_storage_config,
)


# =============================================================================
# LLMConfig
# =============================================================================


def _min_llm_config_dict() -> dict:
    return {
        "version": "0.1",
        "default_provider": "mock",
        "providers": {
            "mock": {"provider": "mock", "model": "mock-model-v1"}
        },
    }


def test_llm_config_minimal_valid() -> None:
    cfg = LLMConfig.model_validate(_min_llm_config_dict())
    assert cfg.default_provider == "mock"
    assert cfg.providers["mock"].provider == "mock"
    # 默认值生效
    assert cfg.providers["mock"].timeout_sec == 30.0
    assert cfg.providers["mock"].max_retries == 2
    assert cfg.providers["mock"].temperature == 0.7


def test_llm_config_multi_provider_valid() -> None:
    payload = {
        "version": "0.1",
        "default_provider": "openai_main",
        "providers": {
            "openai_main": {
                "provider": "openai",
                "model": "gpt-4o",
                "api_key_env": "OPENAI_API_KEY",
                "timeout_sec": 60,
                "max_retries": 3,
                "temperature": 0.3,
            },
            "mock": {"provider": "mock", "model": "mock-v1"},
        },
    }
    cfg = LLMConfig.model_validate(payload)
    assert cfg.providers["openai_main"].model == "gpt-4o"
    assert cfg.providers["openai_main"].api_key_env == "OPENAI_API_KEY"
    assert cfg.providers["openai_main"].max_retries == 3


def test_llm_config_default_provider_must_exist_in_providers() -> None:
    """D-004 跨字段校验：`default_provider` 必须在 providers 中声明。"""
    payload = {
        "version": "0.1",
        "default_provider": "ghost",
        "providers": {
            "mock": {"provider": "mock", "model": "mock-v1"}
        },
    }
    with pytest.raises(ValidationError) as exc_info:
        LLMConfig.model_validate(payload)
    assert "ghost" in str(exc_info.value)


def test_llm_config_empty_providers_rejected() -> None:
    payload = {
        "version": "0.1",
        "default_provider": "mock",
        "providers": {},
    }
    with pytest.raises(ValidationError):
        LLMConfig.model_validate(payload)


def test_llm_provider_invalid_enum_rejected() -> None:
    payload = {
        "version": "0.1",
        "default_provider": "x",
        "providers": {
            "x": {"provider": "palm", "model": "palm-1"}
        },
    }
    with pytest.raises(ValidationError):
        LLMConfig.model_validate(payload)


def test_llm_provider_negative_timeout_rejected() -> None:
    payload = {
        "version": "0.1",
        "default_provider": "mock",
        "providers": {
            "mock": {"provider": "mock", "model": "mock", "timeout_sec": 0}
        },
    }
    with pytest.raises(ValidationError):
        LLMConfig.model_validate(payload)


def test_llm_provider_temperature_out_of_range_rejected() -> None:
    payload = {
        "version": "0.1",
        "default_provider": "mock",
        "providers": {
            "mock": {"provider": "mock", "model": "mock", "temperature": 2.5}
        },
    }
    with pytest.raises(ValidationError):
        LLMConfig.model_validate(payload)


def test_llm_config_extra_field_rejected() -> None:
    payload = {**_min_llm_config_dict(), "extra_section": 1}
    with pytest.raises(ValidationError):
        LLMConfig.model_validate(payload)


def test_llm_provider_extra_field_rejected() -> None:
    payload = {
        "version": "0.1",
        "default_provider": "mock",
        "providers": {
            "mock": {
                "provider": "mock",
                "model": "mock",
                "mystery": "field",
            }
        },
    }
    with pytest.raises(ValidationError):
        LLMConfig.model_validate(payload)


# =============================================================================
# RuntimeConfig
# =============================================================================


def test_runtime_config_defaults() -> None:
    cfg = RuntimeConfig.model_validate({"version": "0.1"})
    assert cfg.random_seed is None
    assert cfg.max_concurrent_decisions == 1
    assert cfg.llm_request_timeout_sec == 30.0
    # 多语言支持（session 19 追加）：默认中文
    assert cfg.output_language == "zh-CN"


def test_runtime_config_custom_values() -> None:
    cfg = RuntimeConfig.model_validate(
        {
            "version": "0.1",
            "random_seed": 42,
            "max_concurrent_decisions": 4,
            "llm_request_timeout_sec": 60,
        }
    )
    assert cfg.random_seed == 42
    assert cfg.max_concurrent_decisions == 4


def test_runtime_config_max_concurrent_must_be_ge_1() -> None:
    with pytest.raises(ValidationError):
        RuntimeConfig.model_validate(
            {"version": "0.1", "max_concurrent_decisions": 0}
        )


def test_runtime_config_missing_version_rejected() -> None:
    with pytest.raises(ValidationError):
        RuntimeConfig.model_validate({})


def test_runtime_config_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        RuntimeConfig.model_validate({"version": "0.1", "unknown": 1})


def test_runtime_config_custom_output_language() -> None:
    """output_language 接受任意非空字符串（ISO 639-1 / 自然语言名都可）。"""
    cfg = RuntimeConfig.model_validate(
        {"version": "0.1", "output_language": "en"}
    )
    assert cfg.output_language == "en"

    cfg_jp = RuntimeConfig.model_validate(
        {"version": "0.1", "output_language": "日本語"}
    )
    assert cfg_jp.output_language == "日本語"


def test_runtime_config_empty_output_language_rejected() -> None:
    """空字符串被 min_length=1 拒绝——空语言名对 LLM 无效。"""
    with pytest.raises(ValidationError):
        RuntimeConfig.model_validate(
            {"version": "0.1", "output_language": ""}
        )


# =============================================================================
# StorageConfig
# =============================================================================


def test_storage_config_defaults() -> None:
    """D-007 默认值：runs_root='./runs'，其余默认对齐 UI-ready 要求。"""
    cfg = StorageConfig.model_validate({"version": "0.1"})
    assert cfg.persist is True
    assert cfg.runs_root == "./runs"
    assert cfg.event_log_format == "jsonl"


def test_storage_config_custom_values() -> None:
    """v1 event_log_format 仅支持 jsonl（见 StorageConfig 文档）。此测试覆盖
    persist / runs_root 的自定义，event_log_format 保持默认。"""
    cfg = StorageConfig.model_validate(
        {
            "version": "0.1",
            "persist": False,
            "runs_root": "/tmp/polisim_runs",
        }
    )
    assert cfg.persist is False
    assert cfg.runs_root == "/tmp/polisim_runs"
    assert cfg.event_log_format == "jsonl"  # default


def test_storage_config_rejects_legacy_fields() -> None:
    """D-007 后已移除的字段（event_log_dir / snapshot_dir）应被 extra='forbid' 挡下。

    这条测试是为了防止外部配置文件仍沿用旧字段名时悄悄失效。
    """
    with pytest.raises(ValidationError):
        StorageConfig.model_validate(
            {"version": "0.1", "event_log_dir": "./old"}
        )
    with pytest.raises(ValidationError):
        StorageConfig.model_validate(
            {"version": "0.1", "snapshot_dir": "./old"}
        )


def test_storage_config_invalid_format_rejected() -> None:
    with pytest.raises(ValidationError):
        StorageConfig.model_validate(
            {"version": "0.1", "event_log_format": "csv"}
        )


# =============================================================================
# LoggingConfig
# =============================================================================


def test_logging_config_defaults() -> None:
    cfg = LoggingConfig.model_validate({"version": "0.1"})
    assert cfg.level == "INFO"
    assert cfg.output == "stdout"
    assert cfg.file_path is None


def test_logging_config_file_output_requires_path() -> None:
    """output=file 时必须提供 file_path。"""
    with pytest.raises(ValidationError) as exc_info:
        LoggingConfig.model_validate(
            {"version": "0.1", "output": "file"}
        )
    assert "file_path" in str(exc_info.value)


def test_logging_config_both_output_requires_path() -> None:
    """output=both 时同样必须提供 file_path。"""
    with pytest.raises(ValidationError):
        LoggingConfig.model_validate(
            {"version": "0.1", "output": "both"}
        )


def test_logging_config_with_file_path_valid() -> None:
    cfg = LoggingConfig.model_validate(
        {
            "version": "0.1",
            "level": "DEBUG",
            "output": "both",
            "file_path": "./runs/log.txt",
        }
    )
    assert cfg.level == "DEBUG"
    assert cfg.output == "both"
    assert cfg.file_path == "./runs/log.txt"


def test_logging_config_invalid_level_rejected() -> None:
    with pytest.raises(ValidationError):
        LoggingConfig.model_validate(
            {"version": "0.1", "level": "TRACE"}
        )


# =============================================================================
# YAML 加载器
# =============================================================================


def test_load_llm_config_from_yaml(tmp_path: Path) -> None:
    path = tmp_path / "llm.yaml"
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(_min_llm_config_dict(), f, allow_unicode=True)
    cfg = load_llm_config(path)
    assert cfg.default_provider == "mock"


def test_load_runtime_config_from_yaml(tmp_path: Path) -> None:
    path = tmp_path / "runtime.yaml"
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump({"version": "0.1", "random_seed": 7}, f)
    cfg = load_runtime_config(path)
    assert cfg.random_seed == 7


def test_load_storage_config_from_yaml(tmp_path: Path) -> None:
    path = tmp_path / "storage.yaml"
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            {"version": "0.1", "persist": False},
            f,
        )
    cfg = load_storage_config(path)
    assert cfg.persist is False


def test_load_logging_config_from_yaml(tmp_path: Path) -> None:
    path = tmp_path / "logging.yaml"
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            {"version": "0.1", "level": "WARNING"}, f
        )
    cfg = load_logging_config(path)
    assert cfg.level == "WARNING"


def test_yaml_top_level_non_dict_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_llm_config(path)
