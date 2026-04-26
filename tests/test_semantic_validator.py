"""D-013 语义校验测试（session 22 落地）。

对应 `core/semantic_validator.py`。

**测试结构**：

1. **SemanticIssue 数据载体**——frozen / __str__ / 字段约束
2. **入口函数 validate_semantics**：
   - rules.actions_handled 返回 None：跳过两项检查（向后兼容）
   - 检查 1（fallback_action ∈ handled）：合法 / 不合法 / fallback 未配置
   - 检查 2（handled ⊆ world.action_types）：合法 / 多声明（拼写错样本）
   - 错误聚合：两项同时失败时 issues 含两条
3. **集成路径**：
   - Runtime 构造时自动调用——成功 / 失败链路
   - 真实场景（minimal_market + negotiation）确认两个产线场景都通过校验
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.definition_loader import load_world_definition
from core.errors import SemanticValidationError, SimEngineError
from core.providers.mock import MockProvider
from core.runtime import Runtime
from core.scenario_loader import load_scenario
from core.semantic_validator import (
    SemanticIssue,
    validate_semantics,
)
from models.config_models import StorageConfig
from rules.base import BaseRules
from rules.minimal_market import MinimalMarketRules
from rules.three_party_negotiation import NegotiationRules


# =============================================================================
# 1. SemanticIssue 数据载体
# =============================================================================


class TestSemanticIssue:
    def test_is_frozen(self) -> None:
        """SemanticIssue 是 frozen dataclass——不可变载体。"""
        issue = SemanticIssue(
            field_path="x.y", kind="some_kind", detail="..."
        )
        with pytest.raises(Exception):  # FrozenInstanceError 是 dataclasses 内部类型
            issue.kind = "changed"  # type: ignore[misc]

    def test_str_renders_kind_path_detail(self) -> None:
        issue = SemanticIssue(
            field_path="world.defaults.fallback_action",
            kind="fallback_action_not_handled",
            detail="ghost 不在 handled",
        )
        s = str(issue)
        assert "fallback_action_not_handled" in s
        assert "world.defaults.fallback_action" in s
        assert "ghost" in s


# =============================================================================
# 2. 自定义 BaseRules stub——便于精确控制 actions_handled 返回值
# =============================================================================


class _StubRules(BaseRules):
    """测试专用 stub——actions_handled 由构造参数指定。

    resolve_effects 返回空列表（本测试不关心），random_seed 默认 None。
    """

    def __init__(self, *, handled: set[str] | None) -> None:
        super().__init__(random_seed=42)
        self._handled = handled

    def resolve_effects(self, world, state, proposal):  # type: ignore[override]
        return []

    def actions_handled(self) -> set[str] | None:  # type: ignore[override]
        return self._handled


# =============================================================================
# 3. validate_semantics 单元
# =============================================================================


_MINIMAL_MARKET_DIR = Path("scenarios/minimal_market")
_NEGOTIATION_DIR = Path("scenarios/three_party_negotiation")


@pytest.fixture
def mm_world():
    return load_world_definition(_MINIMAL_MARKET_DIR / "world.yaml")


@pytest.fixture
def mm_scenario(mm_world):
    return load_scenario(_MINIMAL_MARKET_DIR / "scenario.yaml", mm_world)


@pytest.fixture
def neg_world():
    return load_world_definition(_NEGOTIATION_DIR / "world.yaml")


@pytest.fixture
def neg_scenario(neg_world):
    return load_scenario(_NEGOTIATION_DIR / "scenario.yaml", neg_world)


class TestValidateSemanticsSkipsWhenHookReturnsNone:
    """钩子返回 None 时——v1 向后兼容；不抛异常。"""

    def test_skip_both_checks(self, mm_world, mm_scenario) -> None:
        rules = _StubRules(handled=None)  # 等同于"未实现钩子"
        # 即便 fallback_action 是 ghost，也不抛——因为钩子未声明，跳过校验
        # （此处无需故意改 world；用真实 minimal_market world 即可）
        validate_semantics(mm_world, mm_scenario, rules)


class TestFallbackActionCheck:
    def test_fallback_in_handled_passes(self, mm_world, mm_scenario) -> None:
        rules = _StubRules(handled={"promote", "do_nothing"})
        # minimal_market world fallback_action='do_nothing' ∈ handled
        validate_semantics(mm_world, mm_scenario, rules)  # 不抛

    def test_fallback_not_in_handled_fails(
        self, mm_world, mm_scenario
    ) -> None:
        # rules 声明只能处理 do_nothing，但 world.fallback_action 也是 do_nothing
        # —— 这里改成 rules 不含 do_nothing，让 fallback 越界
        rules = _StubRules(handled={"promote"})
        with pytest.raises(SemanticValidationError) as exc_info:
            validate_semantics(mm_world, mm_scenario, rules)
        err = exc_info.value
        assert err.issues, "issues 必须非空"
        kinds = {i.kind for i in err.issues}
        assert "fallback_action_not_handled" in kinds
        # detail 中应明确指出违规的 action 名
        fb_issue = next(
            i for i in err.issues if i.kind == "fallback_action_not_handled"
        )
        assert "do_nothing" in fb_issue.detail
        assert fb_issue.field_path == "world.defaults.fallback_action"

    def test_fallback_unset_skips_check(
        self, mm_world, mm_scenario
    ) -> None:
        """world.defaults.fallback_action=None 时不应触发本项检查。"""
        # 用 model_copy 制造 fallback=None 的副本
        defaults_copy = mm_world.defaults.model_copy(
            update={"fallback_action": None}
        )
        world_copy = mm_world.model_copy(update={"defaults": defaults_copy})
        rules = _StubRules(handled={"promote"})  # 故意不含 do_nothing
        # fallback_action=None 时本项检查被跳过；handled ⊆ world.action_types
        # 仍然成立（promote 在 world.action_types 中），所以整体通过
        validate_semantics(world_copy, mm_scenario, rules)


class TestRulesActionsInWorldCheck:
    def test_handled_subset_of_world_passes(
        self, mm_world, mm_scenario
    ) -> None:
        rules = _StubRules(handled={"promote", "do_nothing"})
        validate_semantics(mm_world, mm_scenario, rules)  # 不抛

    def test_handled_extra_action_fails(
        self, mm_world, mm_scenario
    ) -> None:
        # rules 声明能处理 'promot'（typo）—— world 没有此动作
        rules = _StubRules(handled={"promote", "do_nothing", "promot"})
        with pytest.raises(SemanticValidationError) as exc_info:
            validate_semantics(mm_world, mm_scenario, rules)
        kinds = {i.kind for i in exc_info.value.issues}
        assert "rules_action_not_in_world" in kinds
        extra_issue = next(
            i
            for i in exc_info.value.issues
            if i.kind == "rules_action_not_in_world"
        )
        assert "promot" in extra_issue.detail
        assert extra_issue.field_path.startswith("rules.actions_handled[")


class TestErrorAggregation:
    def test_two_violations_aggregate_in_single_exception(
        self, mm_world, mm_scenario
    ) -> None:
        """两项同时违规——一次性抛出包含两条 issue 的异常。"""
        # 1. fallback_action='do_nothing' 不在 handled（违反检查 1）
        # 2. handled 含 'ghost'（违反检查 2）
        rules = _StubRules(handled={"promote", "ghost"})
        with pytest.raises(SemanticValidationError) as exc_info:
            validate_semantics(mm_world, mm_scenario, rules)
        kinds = [i.kind for i in exc_info.value.issues]
        assert "fallback_action_not_handled" in kinds
        assert "rules_action_not_in_world" in kinds
        # 异常 message 应同时含两项问题的提示
        msg = str(exc_info.value)
        assert "2 项问题" in msg or "2 项" in msg
        assert "do_nothing" in msg
        assert "ghost" in msg


# =============================================================================
# 4. 异常体系归属验证
# =============================================================================


class TestExceptionHierarchy:
    def test_inherits_from_polisim_error(self, mm_world, mm_scenario) -> None:
        """SemanticValidationError 必须继承 SimEngineError——CLI 顶层 except 才能兜。"""
        rules = _StubRules(handled={"promote"})  # 故意触发 fallback 不在 handled
        with pytest.raises(SimEngineError):
            validate_semantics(mm_world, mm_scenario, rules)

    def test_issues_attribute_is_list(self, mm_world, mm_scenario) -> None:
        rules = _StubRules(handled={"promote"})
        with pytest.raises(SemanticValidationError) as exc_info:
            validate_semantics(mm_world, mm_scenario, rules)
        assert isinstance(exc_info.value.issues, list)
        assert all(
            isinstance(i, SemanticIssue) for i in exc_info.value.issues
        )


# =============================================================================
# 5. 真实场景集成：两个生产场景必须通过校验
# =============================================================================


class TestRealScenariosPass:
    def test_minimal_market_passes(self, mm_world, mm_scenario) -> None:
        rules = MinimalMarketRules(random_seed=42)
        validate_semantics(mm_world, mm_scenario, rules)  # 不抛

    def test_three_party_negotiation_passes(
        self, neg_world, neg_scenario
    ) -> None:
        rules = NegotiationRules(random_seed=42)
        validate_semantics(neg_world, neg_scenario, rules)  # 不抛


# =============================================================================
# 6. Runtime 集成：构造期自动调用
# =============================================================================


class TestRuntimeIntegration:
    def test_runtime_construct_succeeds_for_real_scenario(
        self, mm_world, mm_scenario
    ) -> None:
        """真实 minimal_market 通过校验——Runtime 正常构造。"""
        rules = MinimalMarketRules(random_seed=42)
        provider = MockProvider(fixed_response='{"action":"do_nothing"}')
        with Runtime(
            mm_world,
            mm_scenario,
            provider,
            rules=rules,
            storage_config=StorageConfig(
                version="0.1", persist=False, runs_root="./runs"
            ),
        ) as rt:
            assert rt.current_tick() == 0  # 构造成功

    def test_runtime_construct_fails_when_rules_handled_invalid(
        self, mm_world, mm_scenario
    ) -> None:
        """rules 声明不一致时 Runtime 构造立即失败——不进入运行期。"""
        rules = _StubRules(handled={"promote"})  # fallback=do_nothing 越界
        provider = MockProvider(fixed_response='{"action":"do_nothing"}')
        with pytest.raises(SemanticValidationError):
            Runtime(
                mm_world,
                mm_scenario,
                provider,
                rules=rules,
                storage_config=StorageConfig(
                    version="0.1", persist=False, runs_root="./runs"
                ),
            )

    def test_runtime_construct_no_run_dir_left_when_validation_fails(
        self, mm_world, mm_scenario, tmp_path
    ) -> None:
        """语义校验失败时——不应在 runs_root 留下空 run 目录（D-013 集成位置正确性证据）。"""
        rules = _StubRules(handled={"promote"})  # fallback=do_nothing 越界
        provider = MockProvider(fixed_response='{"action":"do_nothing"}')
        with pytest.raises(SemanticValidationError):
            Runtime(
                mm_world,
                mm_scenario,
                provider,
                rules=rules,
                storage_config=StorageConfig(
                    version="0.1", persist=True, runs_root=str(tmp_path)
                ),
            )
        # tmp_path 下不应出现任何 run_id 子目录
        children = list(tmp_path.iterdir())
        assert children == [], (
            f"语义校验失败时不应落 run 目录，但发现：{children}"
        )
