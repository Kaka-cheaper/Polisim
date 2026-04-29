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
   - decide 现返 ``LLMDecisionResult``（D-016 第 6 步），通过 ``.proposal`` 取 ActionProposal
2. **Phase C 增强烟雾**——**真跑** minimal_market 3 ticks → ``analyze_run`` →
   ``enhance_with_llm``（含 ``world / scenario`` 必填 kwargs，session 26 升级）：
   - 显式 ``system_prompt=_ANALYSIS_SYSTEM_PROMPT``（分析导向，覆盖默认）
   - 期望 LLM 返回 ``{world_overview, narrative_summary, situation_judgement,
     next_action_suggestions}`` 四段
   - 真跑产生真实 turning_points / entity_comparisons / environment_trajectory，
     让 LLM 在 situation_judgement 与 next_action_suggestions 中能援引具体证据

第二段是 session 21 F1 修复（双 system prompt 不冲突）+ session 26 升级（4 段 LLM 输出）+
session 27 架构审查（F1 改 LLMDecisionResult 解构 / F2 加 world+scenario kwargs /
F10 真跑取代空骨架）的综合验证。

**费用提示**：默认用 ``gpt-4o-mini``——决策 3 次 + 分析 1 次共约 4 次调用，
合计 $0.0001 量级（忽略不计）。
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# 让本脚本能 `python scripts/smoke_openai.py` 直接运行（无需 pip install -e .）
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from core import llm_policy
from core.analysis import analyze_run, enhance_with_llm
from core.definition_loader import load_world_definition
from core.errors import LLMProtocolError, ProviderError, SimEngineError
from core.providers.openai import OpenAIProvider
from core.runtime import Runtime
from core.scenario_loader import load_scenario
from models.config_models import RuntimeConfig, StorageConfig, load_llm_config


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
    """Phase B：单次 ``llm_policy.decide`` smoke——验证决策导向 prompt 链路。

    **F1（session 27）**：``decide`` 现返 ``LLMDecisionResult``（D-016 第 6 步
    破坏性变更），通过 ``.proposal`` 取 ``ActionProposal``。
    """
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
        result = llm_policy.decide(
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

    proposal = result.proposal  # F1：解构 LLMDecisionResult
    print("[ok] LLM 返回合法 ActionProposal：")
    print(f"  action_type : {proposal.action_type}")
    print(f"  params      : {proposal.params}")
    print(f"  reason      : {proposal.raw_reasoning_summary}")
    return 0


def _phase_c_smoke(provider: OpenAIProvider) -> int:
    """Phase C：**真跑** minimal_market 3 ticks → ``analyze_run`` →
    ``enhance_with_llm`` smoke——验证 F1（双 system prompt 不冲突）+
    session 26 升级（4 段叙事）+ F2/F10（真实 Phase A 数据 + world/scenario kwargs）。

    **F2（session 27）**：``enhance_with_llm`` 必填 ``world`` + ``scenario`` kwargs
    （session 26 破坏性变更——LLM 据此先解释初始世界，再援引具体证据）。

    **F10（session 27）**：原版用空骨架 ``AnalysisResult`` 让 LLM"没数据可说"；
    本版真跑 minimal_market 3 ticks（含 LLM 决策路径），让 LLM 看到真实
    turning_points / entity_comparisons / environment_trajectory 后再 enhance。
    """
    print("\n========== Phase C：分析增强 smoke（真跑 minimal_market） ==========")

    world = load_world_definition(
        _REPO_ROOT / "scenarios" / "minimal_market" / "world.yaml"
    )
    scenario = load_scenario(
        _REPO_ROOT / "scenarios" / "minimal_market" / "scenario.yaml",
        world,
    )

    # 限制到 3 ticks 节省 API 调用——足够产生 turning_points 与 environment 变化
    scenario.config.total_ticks = 3
    runtime_config = RuntimeConfig(version="0.1", random_seed=42)

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_config = StorageConfig(
            version="0.1", persist=True, runs_root=tmpdir
        )

        print(f"[info] 真跑 minimal_market（{scenario.config.total_ticks} ticks，含 LLM 决策）")
        try:
            with Runtime(
                world,
                scenario,
                provider,
                runtime_config=runtime_config,
                storage_config=storage_config,
            ) as rt:
                print(f"[info] run_id = {rt.run_id}")
                for _ in range(scenario.config.total_ticks):
                    rt.step()
                run_dir = rt.run_dir
        except SimEngineError as exc:
            print(f"[FAIL][sim-engine] {exc}", file=sys.stderr)
            return 1

        if run_dir is None:
            print("[FAIL] run_dir 为 None（persist 配置异常）", file=sys.stderr)
            return 1

        # Phase A 分析（纯规则）
        try:
            phase_a_result = analyze_run(run_dir)
        except (FileNotFoundError, ValueError) as exc:
            print(f"[FAIL][phase-a] {exc}", file=sys.stderr)
            return 1

        print(
            f"[info] Phase A：{phase_a_result.summary.total_events} 事件 / "
            f"{len(phase_a_result.turning_points)} 转折点 / "
            f"{len(phase_a_result.entity_comparisons)} 实体对比"
        )

        # Phase C 增强——F2：必填 world + scenario kwargs
        print("[info] 发起 LLM 分析增强（含真实 Phase A 数据 + World + Scenario）")
        try:
            enhanced = enhance_with_llm(
                phase_a_result,
                provider,
                runtime_config,
                world=world,
                scenario=scenario,
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

    # 打印 4 段（session 26 升级后的完整产物；F10 验证 world_overview 段已生成）
    print("[ok] LLM 返回完整四段叙事：")
    if enhanced.world_overview:
        print(f"  world_overview          : {enhanced.world_overview[:160]}...")
    print(f"  narrative_summary       : {(enhanced.narrative_summary or '')[:160]}...")
    print(f"  situation_judgement     : {(enhanced.situation_judgement or '')[:160]}...")
    print("  next_action_suggestions :")
    for i, sug in enumerate(enhanced.next_action_suggestions or [], 1):
        print(f"    {i}. {sug[:160]}")
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
