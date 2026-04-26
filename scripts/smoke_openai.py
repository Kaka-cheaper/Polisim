"""真实 OpenAI API 的端到端烟雾脚本（Phase B + Phase C 手动验收）。

**不进 CI**——需要真实 API key 与网络；仅供开发者手工确认 OpenAIProvider
在当前依赖矩阵与模型下工作。

用法：

    # 1. 设置环境变量
    export OPENAI_API_KEY="sk-..."           # macOS / Linux
    $env:OPENAI_API_KEY = "sk-..."           # PowerShell

    # 2. 复制并编辑 config
    cp config/llm.yaml.example config/llm.yaml
    # （如需改 model / base_url，编辑 config/llm.yaml）

    # 3. 跑
    python scripts/smoke_openai.py

预期产出（两段）：

1. **Phase B 决策烟雾**——单次 ``llm_policy.decide`` 调用：
   - 默认 system prompt（决策导向，"decision-making agent"）
   - 期望 LLM 返回 ``{action, params, reason}`` 形状
2. **Phase C 增强烟雾**——单次 ``analysis.enhance_with_llm`` 调用：
   - 显式 ``system_prompt=_ANALYSIS_SYSTEM_PROMPT``（分析导向，覆盖默认）
   - 期望 LLM 返回 ``{narrative_summary, situation_judgement, next_action_suggestions}``

第二段是 session 21 F1 修复的关键验证——**同一个 OpenAIProvider 实例**先后服务
两种角色，必须不出现 system prompt 冲突。

**费用提示**：默认用 ``gpt-4o-mini``——两次调用合计约 $0.00005 量级（忽略不计）。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# 让本脚本能 `python scripts/smoke_openai.py` 直接运行（无需 pip install -e .）
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from core import llm_policy
from core.analysis import enhance_with_llm
from core.definition_loader import load_world_definition
from core.errors import LLMProtocolError, ProviderError, SimEngineError
from core.providers.openai import OpenAIProvider
from core.scenario_loader import load_scenario
from models.analysis_models import AnalysisResult, TrajectorySummary
from models.config_models import RuntimeConfig, load_llm_config


def _resolve_provider() -> tuple[OpenAIProvider, str] | int:
    """加载 config/llm.yaml + 解析环境变量 + 构造 OpenAIProvider。

    成功返 ``(provider, key)``；失败返非 0 退出码。
    """
    config_path = _REPO_ROOT / "config" / "llm.yaml"
    if not config_path.exists():
        print(
            f"[error] {config_path} 不存在。"
            f"先 `cp config/llm.yaml.example config/llm.yaml`",
            file=sys.stderr,
        )
        return 2

    try:
        llm_config = load_llm_config(config_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[error] 加载 {config_path} 失败：{exc}", file=sys.stderr)
        return 2

    key = llm_config.default_provider
    prov_cfg = llm_config.providers.get(key)
    if prov_cfg is None or prov_cfg.provider != "openai":
        for candidate_key, candidate_cfg in llm_config.providers.items():
            if candidate_cfg.provider == "openai":
                key, prov_cfg = candidate_key, candidate_cfg
                break
        else:
            print(
                "[error] 没在 config/llm.yaml 找到 provider='openai' 的条目",
                file=sys.stderr,
            )
            return 2

    print(f"[info] 使用 provider key = '{key}'")
    print(f"[info]       model      = {prov_cfg.model}")
    print(
        f"[info]       base_url   = "
        f"{prov_cfg.base_url or '(官方 api.openai.com)'}"
    )
    print(f"[info]       api_key_env= {prov_cfg.api_key_env}")

    if not os.environ.get(prov_cfg.api_key_env or ""):
        print(
            f"[error] 环境变量 ${prov_cfg.api_key_env} 未设置",
            file=sys.stderr,
        )
        return 2

    try:
        provider = OpenAIProvider(prov_cfg)
    except ProviderError as exc:
        print(f"[error] OpenAIProvider 构造失败：{exc}", file=sys.stderr)
        return 2

    return provider, key


def _phase_b_smoke(provider: OpenAIProvider) -> int:
    """Phase B：单次 ``llm_policy.decide`` smoke——验证决策导向 prompt 链路。"""
    print("\n========== Phase B：决策层 smoke ==========")

    world = load_world_definition(
        _REPO_ROOT / "scenarios" / "minimal_market" / "world.yaml"
    )
    scenario = load_scenario(
        _REPO_ROOT / "scenarios" / "minimal_market" / "scenario.yaml",
        world,
    )

    from models.runtime_models import EntityRuntimeState, WorldState

    entities: dict[str, EntityRuntimeState] = {}
    for inst in scenario.entities:
        type_schema = world.entity_types[inst.type]
        merged = {
            name: attr.default for name, attr in type_schema.attributes.items()
        }
        merged.update(inst.attributes)
        entities[inst.id] = EntityRuntimeState(
            id=inst.id, type=inst.type, attributes=merged
        )
    state = WorldState(tick=0, entities=entities, mailboxes={})

    print("[info] 发起单次 LLM 决策：company_a @ tick=1")
    try:
        proposal = llm_policy.decide(
            provider,
            world,
            scenario,
            state,
            "company_a",
            tick=1,
            config=RuntimeConfig(version="0.1"),
        )
    except ProviderError as exc:
        print(f"[FAIL][provider] {exc}", file=sys.stderr)
        return 1
    except LLMProtocolError as exc:
        print(f"[FAIL][protocol] {exc}", file=sys.stderr)
        return 1
    except SimEngineError as exc:
        print(f"[FAIL][sim-engine] {exc}", file=sys.stderr)
        return 1

    print("[ok] LLM 返回合法 ActionProposal：")
    print(f"  action_type : {proposal.action_type}")
    print(f"  params      : {proposal.params}")
    print(f"  reason      : {proposal.raw_reasoning_summary}")
    return 0


def _phase_c_smoke(provider: OpenAIProvider) -> int:
    """Phase C：单次 ``analysis.enhance_with_llm`` smoke——验证 F1 修复后的
    分析导向 prompt 覆盖链路。

    构造一个紧凑的内存 ``AnalysisResult`` 充当 Phase A 产物，调 enhance；
    LLM 必须返三段叙事 JSON。这是 F1 修复后第一次让真实 OpenAI 看到
    分析导向 system prompt——验证 system + user 角色不冲突。
    """
    print("\n========== Phase C：分析增强 smoke ==========")

    minimal_result = AnalysisResult(
        version="0.1",
        run_id="smoke-phase-c",
        summary=TrajectorySummary(
            total_ticks=3,
            total_events=8,
            events_by_kind=[],
            events_by_actor=[],
            paused_ticks=[],
            breakpoints_triggered=[],
        ),
        turning_points=[],
        entity_comparisons=[],
        environment_trajectory=[],
    )

    print("[info] 发起单次 LLM 分析增强（构造 in-memory Phase A 产物）")
    try:
        enhanced = enhance_with_llm(
            minimal_result, provider, RuntimeConfig(version="0.1")
        )
    except ProviderError as exc:
        print(f"[FAIL][provider] {exc}", file=sys.stderr)
        return 1
    except LLMProtocolError as exc:
        print(f"[FAIL][protocol] {exc}", file=sys.stderr)
        return 1
    except SimEngineError as exc:
        print(f"[FAIL][sim-engine] {exc}", file=sys.stderr)
        return 1

    print("[ok] LLM 返回合法分析增强：")
    print(f"  narrative_summary       : {enhanced.narrative_summary}")
    print(f"  situation_judgement     : {enhanced.situation_judgement}")
    print(f"  next_action_suggestions :")
    for i, sug in enumerate(enhanced.next_action_suggestions or [], 1):
        print(f"    {i}. {sug}")
    return 0


def main() -> int:
    resolved = _resolve_provider()
    if isinstance(resolved, int):
        return resolved
    provider, _key = resolved

    code_b = _phase_b_smoke(provider)
    code_c = _phase_c_smoke(provider)

    print("\n========== 总结 ==========")
    print(f"Phase B 决策 smoke    : {'[ok]' if code_b == 0 else '[FAIL]'}")
    print(f"Phase C 增强 smoke    : {'[ok]' if code_c == 0 else '[FAIL]'}")

    # 任何一段失败整体非 0
    return code_b or code_c


if __name__ == "__main__":
    raise SystemExit(main())
