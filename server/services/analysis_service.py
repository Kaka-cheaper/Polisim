"""server/services/analysis_service.py —— 分析层的业务编排（D-017 第 6.4 节）。

包装 `core.analysis`：
- `analyze_run(run_dir)` —— Phase A 纯规则分析
- `enhance_with_llm(result, provider, config, *, world, scenario)` —— Phase C LLM 增强

**v0.2 入口**：
- GET /runs/:id/analysis?enhance=false → 返 Phase A 结果
- GET /runs/:id/analysis?enhance=true → 跑 Phase A + Phase C
- POST /runs/:id/analyze → 重新跑（前端"重跑增强"按钮）

**LLM provider 策略**：

session 31 简化——AnalysisService 在调用 enhance_with_llm 时**复用 Runtime 自身
的 provider**（``runtime.provider`` 只读 @property）。这意味着：

- 跑 run 时如果用了 mock，分析增强**会被跳过**（session 45 防御）——MockProvider
  无法产出 4 段叙事 JSON，强行调 enhance_with_llm 必抛 LLMProtocolError → 502。
  本服务前置检查 ``isinstance(runtime.provider, MockProvider)``，命中则直接返
  Phase A 结果（log 一条 INFO，不报错）。
- 跑 run 时用 openai，分析增强走 openai——正常流程。

未来可能加 server 配置允许"跑 mock 但增强走 openai"——但 v0.2 不做。
"""

from __future__ import annotations

import logging

from core.analysis import analyze_run, enhance_with_llm, write_analysis
from core.providers.mock import MockProvider
from models.analysis_models import AnalysisResult

from server.runtime_registry import RuntimeRegistry

_logger = logging.getLogger(__name__)


class AnalysisService:
    """分析的业务编排。

    持有 ``RuntimeRegistry`` 是为了：

    1. 找到指定 run 的 ``run_dir``——`analyze_run` 需要它读 events.jsonl
    2. 找到 run 的 ``provider`` / ``world`` / ``scenario`` / ``runtime_config``——
       `enhance_with_llm` 需要它们做证据援引

    **v0.2 限制**：仅支持**活跃** run 的分析（registry 里还在）；
    已 GC 的 run 推迟到 v0.3+ 加"归档分析"功能。
    """

    def __init__(self, registry: RuntimeRegistry) -> None:
        self._registry = registry

    def analyze(
        self, run_id: str, llm_enhance: bool = False
    ) -> AnalysisResult:
        """跑分析。

        - 必须 run_dir 存在——v0.2 不做内存模式分析
        - llm_enhance=True 时跑 Phase C；失败抛 SimEngineError 子类，
          server 层映射为 502（具体由 errors.ERROR_MAP 决定）
        """
        runtime = self._registry.get(run_id)
        if runtime is None:
            raise FileNotFoundError(f"run_id={run_id!r} 不存在或已归档")
        if runtime.run_dir is None:
            raise ValueError(
                f"run_id={run_id!r} 走内存模式（persist=False），"
                f"无法生成分析；请 persist=True 重新创建"
            )
        result = analyze_run(runtime.run_dir)
        if llm_enhance:
            # session 45：mock provider 无法产出 4 段叙事 JSON
            # （MockProvider 默认返回 `{"action":"do_nothing"}`），
            # enhance_with_llm 必抛 LLMProtocolError → server 502。
            # 这里前置检查降级：跳过 enhance 返 Phase A，避免误报错。
            if isinstance(runtime.provider, MockProvider):
                _logger.info(
                    "run_id=%s provider 为 MockProvider，跳过 LLM 增强（仅返 Phase A）",
                    run_id,
                )
            else:
                # v0.2 直接复用 Runtime 自身的 provider 与 runtime_config——
                # 通过 @property 只读暴露（D-017 反向校验产物，session 33 收敛）。
                result = enhance_with_llm(
                    result,
                    runtime.provider,
                    runtime.runtime_config,
                    world=runtime.world,
                    scenario=runtime.scenario,
                )
        # 落盘——与 CLI cmd_run 保持一致行为；后续 GET /analysis 也可读到结果
        write_analysis(runtime.run_dir, result)
        return result
