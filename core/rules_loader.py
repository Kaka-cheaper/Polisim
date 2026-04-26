"""规则模块动态加载器（D-010 方案 A 落地）。

对应 `docs/02-design/实现映射设计.md` 4.3 节与 `docs/00-overview/progress.md`
D-010 已决策条目。

**职责边界**：

- 本模块**只**做一件事：把 ``"module.path:ClassName"`` 字符串解析为
  `BaseRules` 子类（不是实例）。实例化由 Runtime 根据 `RuntimeConfig` 决定
  构造参数（如 `random_seed`）
- **不**负责装载 scenario——那是 `core/scenario_loader.py`
- **不**负责实例化 Runtime——那是 `core/runtime.py`
- **不**感知哪套规则对应哪个世界——世界 → 规则的绑定由 `Scenario.rules_module`
  字段显式指定，本模块零语义耦合

**格式约定**（与 `scenarios/scenario.schema.json.pattern` 及
`models/scenario_models.Scenario.rules_module` 的 Pydantic pattern 三方同步）：

- 形如 ``"rules.minimal_market:MinimalMarketRules"``
- 冒号 **恰好一个**，冒号两侧都是合法 Python 标识符序列
- 模块路径可多级点号分隔（如 ``"my_pkg.rules.custom:CustomRules"``）
- 类名**不含**点号（类路径嵌套不在 v1 支持范围）

**失败模式**（全部抛 `RulesLoadError`）：

1. 格式非法（缺冒号 / 冒号过多 / 两侧为空）
2. 模块不存在或导入时出错
3. 指定名字不在模块中
4. 指定名字不是类，或不是 `BaseRules` 子类
5. 指定名字**就是** `BaseRules` 本身（抽象基类，无法实例化）

所有错误信息都带原始输入串，方便排错。
"""

from __future__ import annotations

import importlib
import inspect

from core.errors import SimEngineError
from rules.base import BaseRules


class RulesLoadError(SimEngineError):
    """Rules 模块加载失败时抛出的统一异常（D-011 体系）。

    上层（CLI / Runtime 构造阶段）应捕获本异常并以用户可读的方式提示；
    不应被 Runtime 主循环捕获——规则缺失是启动前就应发现的致命问题。

    继承 ``SimEngineError``：CLI 顶层 ``except SimEngineError`` 一并兜住，
    用户看到的是 ``[error] ...`` 友好提示而非 traceback。
    """


def load_rules_class(rules_module: str) -> type[BaseRules]:
    """把形如 ``"module.path:ClassName"`` 的字符串解析为 `BaseRules` 子类。

    返回**类对象**，不是实例——由调用方按需构造（例如注入 ``random_seed``）。

    Args:
        rules_module: 符合 D-010 约定的路径字符串

    Returns:
        `BaseRules` 的一个具体子类

    Raises:
        RulesLoadError: 任何一步解析或校验失败时抛出，带输入串与根因
    """
    # 1. 格式校验（防御式——scenario.schema.json 与 Pydantic 已做 pattern，
    #    但本 loader 必须对直接调用也稳健）
    if not isinstance(rules_module, str) or not rules_module.strip():
        raise RulesLoadError(
            f"rules_module 必须是非空字符串，实际收到 {rules_module!r}"
        )

    parts = rules_module.split(":")
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        raise RulesLoadError(
            f"rules_module '{rules_module}' 格式非法："
            f"应为 'module.path:ClassName'，恰好一个冒号且两侧非空"
        )
    module_path, class_name = parts[0].strip(), parts[1].strip()

    # 2. 动态导入模块
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise RulesLoadError(
            f"rules_module '{rules_module}' 的模块 '{module_path}' 无法导入："
            f"{exc}"
        ) from exc

    # 3. 取出类
    cls = getattr(module, class_name, None)
    if cls is None:
        raise RulesLoadError(
            f"rules_module '{rules_module}' 指定的类 '{class_name}' "
            f"未在模块 '{module_path}' 中找到"
        )

    # 4. 必须是类
    if not inspect.isclass(cls):
        raise RulesLoadError(
            f"rules_module '{rules_module}' 指向的 '{class_name}' 不是类，"
            f"实际类型是 {type(cls).__name__}"
        )

    # 5. 必须是 BaseRules 的**具体**子类（不是 BaseRules 本身，也不是无关类）
    if cls is BaseRules:
        raise RulesLoadError(
            f"rules_module '{rules_module}' 指向 BaseRules 本身，"
            f"但 BaseRules 是抽象基类——请指向一个具体子类"
        )
    if not issubclass(cls, BaseRules):
        raise RulesLoadError(
            f"rules_module '{rules_module}' 指向的 '{class_name}' "
            f"不是 BaseRules 的子类，无法用作规则模块"
        )

    return cls
