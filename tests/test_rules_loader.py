"""rules_loader 测试（D-010 方案 A 落地）。

对应 `docs/00-overview/progress.md` D-010 已决策条目与 `core/rules_loader.py`。

覆盖：

1. **合法路径** → 返回正确的 `BaseRules` 子类（类对象，不是实例）
2. **格式错误**：None / 空串 / 无冒号 / 多冒号 / 冒号两侧为空
3. **模块不存在** → `RulesLoadError` 带模块名
4. **类不存在** → `RulesLoadError` 带类名
5. **不是类**（例如模块级常量）→ `RulesLoadError`
6. **不是 `BaseRules` 子类** → `RulesLoadError`
7. **是 `BaseRules` 本身** → `RulesLoadError`（抽象基类不可作为具体规则）
8. **集成**：`rules.minimal_market:MinimalMarketRules` 真实可解析

本文件同时作为**测试夹具宿主**——文件尾部定义了几个供测试引用的类与常量，
pytest 自动把 `tests/` 加入 sys.path，因此可通过 ``"test_rules_loader:..."``
字符串被 `importlib.import_module` 解析。
"""

from __future__ import annotations

import pytest

from core.rules_loader import RulesLoadError, load_rules_class
from rules.base import BaseRules


# =============================================================================
# 合法路径
# =============================================================================


def test_load_rules_class_returns_concrete_subclass() -> None:
    """合法字符串返回具体的 `BaseRules` 子类（来自本文件尾部的 fixture）。"""
    cls = load_rules_class("test_rules_loader:_ValidTestRules")
    assert cls is _ValidTestRules
    assert issubclass(cls, BaseRules)
    assert cls is not BaseRules


def test_load_rules_class_returns_class_not_instance() -> None:
    """返回类对象——不是实例。调用方要自己实例化。"""
    cls = load_rules_class("test_rules_loader:_ValidTestRules")
    # 不能对 cls 调用实例方法（需先实例化）
    instance = cls()
    assert isinstance(instance, BaseRules)


def test_load_rules_class_integration_minimal_market() -> None:
    """端到端：真实的 rules/minimal_market.py 可以被加载。"""
    from rules.minimal_market import MinimalMarketRules

    cls = load_rules_class("rules.minimal_market:MinimalMarketRules")
    assert cls is MinimalMarketRules


def test_load_rules_class_strips_whitespace_around_path() -> None:
    """字符串两侧 / 冒号两侧有空白时，loader 应容忍。"""
    cls = load_rules_class("  test_rules_loader : _ValidTestRules  ")
    assert cls is _ValidTestRules


# =============================================================================
# D-011 异常体系一致性（F2 修复）
# =============================================================================


def test_rules_load_error_inherits_sim_engine_error() -> None:
    """F2：RulesLoadError 必须是 SimEngineError 子类——CLI 顶层兜底依赖。"""
    from core.errors import SimEngineError

    assert issubclass(RulesLoadError, SimEngineError)


def test_rules_load_error_caught_by_sim_engine_error_handler() -> None:
    """F2：``except SimEngineError`` 一并兜住 RulesLoadError——这是 CLI 的关键路径。"""
    from core.errors import SimEngineError

    try:
        load_rules_class("nonexistent.module:Foo")
    except SimEngineError:
        pass  # 期望
    else:
        pytest.fail("RulesLoadError 未被 SimEngineError 拦到")


# =============================================================================
# 格式错误（RulesLoadError）
# =============================================================================


def test_load_rules_class_rejects_non_string() -> None:
    with pytest.raises(RulesLoadError, match="非空字符串"):
        load_rules_class(None)  # type: ignore[arg-type]


def test_load_rules_class_rejects_empty_string() -> None:
    with pytest.raises(RulesLoadError, match="非空字符串"):
        load_rules_class("")


def test_load_rules_class_rejects_whitespace_only_string() -> None:
    with pytest.raises(RulesLoadError, match="非空字符串"):
        load_rules_class("   ")


def test_load_rules_class_rejects_missing_colon() -> None:
    with pytest.raises(RulesLoadError, match="恰好一个冒号"):
        load_rules_class("rules.minimal_market")


def test_load_rules_class_rejects_multiple_colons() -> None:
    with pytest.raises(RulesLoadError, match="恰好一个冒号"):
        load_rules_class("rules.minimal_market:Class:Extra")


def test_load_rules_class_rejects_empty_lhs() -> None:
    with pytest.raises(RulesLoadError, match="恰好一个冒号"):
        load_rules_class(":MinimalMarketRules")


def test_load_rules_class_rejects_empty_rhs() -> None:
    with pytest.raises(RulesLoadError, match="恰好一个冒号"):
        load_rules_class("rules.minimal_market:")


# =============================================================================
# 模块 / 类查找失败
# =============================================================================


def test_load_rules_class_rejects_nonexistent_module() -> None:
    with pytest.raises(RulesLoadError, match="无法导入"):
        load_rules_class("nonexistent_pkg.nonexistent_module:Foo")


def test_load_rules_class_rejects_missing_class_in_module() -> None:
    """模块存在，但类名不存在。"""
    with pytest.raises(RulesLoadError, match="未在模块"):
        load_rules_class("test_rules_loader:_DoesNotExist")


def test_load_rules_class_rejects_module_constant_not_class() -> None:
    """名字存在但不是类（例如模块级常量）。"""
    with pytest.raises(RulesLoadError, match="不是类"):
        load_rules_class("test_rules_loader:_A_CONSTANT")


# =============================================================================
# 类型不匹配
# =============================================================================


def test_load_rules_class_rejects_non_baserules_subclass() -> None:
    with pytest.raises(RulesLoadError, match="不是 BaseRules 的子类"):
        load_rules_class("test_rules_loader:_NotARulesClass")


def test_load_rules_class_rejects_baserules_itself() -> None:
    """BaseRules 是抽象基类，不能作为具体规则模块。"""
    with pytest.raises(RulesLoadError, match="抽象基类"):
        load_rules_class("rules.base:BaseRules")


# =============================================================================
# 测试夹具——放在文件尾，供 importlib 通过 'test_rules_loader:<name>' 拾取
# =============================================================================


class _ValidTestRules(BaseRules):
    """合法 fixture：`BaseRules` 的具体子类，覆写了 `resolve_effects`。"""

    def resolve_effects(self, world, state, proposal):  # type: ignore[override]
        return []


class _NotARulesClass:
    """反例 fixture：与 `BaseRules` 无继承关系。"""

    pass


_A_CONSTANT = 42
"""反例 fixture：模块级常量，不是类。"""
