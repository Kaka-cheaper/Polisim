"""跨层语义校验模块（D-013，session 22 落地）。

**为什么需要这一层**

`core/scenario_loader._validate_cross_references` 已经覆盖了"World ↔ Scenario
引用一致性"的大部分情形：实体 type、关系 type、环境变量、scheduled_event 消息
类型、breakpoint 实体/属性引用等。但有一类语义错误**只有当 rules 实例可见时
才能发现**——它跨越 World、Rules 两层，loader 单独一边都看不到全貌：

- ``world.defaults.fallback_action`` 必须能被 ``rules.resolve_effects`` 处理
  （否则首次 fallback 触发时崩在运行期，详见 `pitfalls.md` P1 历史样本）
- rules 不应声明能 resolve world 未定义的 action（防开发者拼写错；同时让
  rules ↔ world 双向一致）

本模块就是这一缺口的补全。

**设计要点**

1. **入口纯函数 `validate_semantics(world, scenario, rules)`**——不依赖 Runtime、
   不依赖 EventLog、不依赖 LLM。只消费三件 Pydantic / BaseRules 对象，纯逻辑校验
2. **错误聚合**——发现的所有问题一次性收集，最后统一抛出 `SemanticValidationError`，
   便于 LLM 修复循环消费一份完整反馈（见 `LLM辅助建模方案.md` 5.2 节）
3. **结构化错误条目 `SemanticIssue`**——每条带 ``field_path / kind / detail``
   三元组，便于不同前端（YAML 行号 / DSL 源码位置 / 自然语言提示）渲染
4. **可选钩子语义**——如果 ``rules.actions_handled()`` 返回 ``None`` 表示子类未
   声明能力，本模块**跳过**两项 rules 相关的检查（向后兼容；现有未实现钩子的
   规则模块不会因为引入 D-013 突然失败）

**不消费 YAML**——和 Polisim 其他校验层一样，本模块只消费**已经 load 完毕的
Pydantic 对象**。这意味着无论输入格式是 YAML、未来的自创 DSL、LLM 直接生成的
dict、还是程序化构造，只要终点是合法的 `WorldDefinition` / `Scenario` /
`BaseRules`，本模块都能工作。这是 Polisim 架构的隐形纪律——**所有校验层都
基于内部模型而非外部输入格式**。

**与 loader 的分工**

- `core/scenario_loader._validate_cross_references`：World ↔ Scenario 跨文件
- `core/semantic_validator.validate_semantics`：World ↔ Rules 跨层（rules 实例可见）

两者**不重叠**——loader 在没有 rules 实例的情况下能跑（构造 Runtime 之前就 load
好 world+scenario）；本模块在有 rules 实例后做后续一层校验。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from core.errors import SemanticValidationError
from models.scenario_models import Scenario
from models.world_models import WorldDefinition
from rules.base import BaseRules


# =============================================================================
# 结构化错误条目
# =============================================================================


SemanticIssueKind = Literal[
    "fallback_action_not_handled",
    "rules_action_not_in_world",
]


@dataclass(frozen=True)
class SemanticIssue:
    """单条语义问题的结构化载体。

    `SemanticValidationError.issues` 列表中的每一项即本类型实例。
    LLM 修复循环 / IDE 错误高亮 / CLI 友好打印的格式器消费 ``field_path`` +
    ``kind`` + ``detail`` 三元组渲染各自的视图。

    Attributes:
        field_path: 出问题的字段路径（如 ``"world.defaults.fallback_action"``）。
            统一用点分路径，便于检索；不带行号——行号是 YAML / DSL 这类
            "外部输入格式"的事，不属于内部模型层。
        kind: 错误类别枚举（见 `SemanticIssueKind`）。便于程序按类型分流处理
            （例如 LLM 反馈循环可对不同 kind 给不同修复建议）。
        detail: 人类可读的错误描述，含具体值与期望——可直接显示给最终用户。
    """

    field_path: str
    kind: str  # SemanticIssueKind 之一；用 str 是为了 frozen dataclass 兼容
    detail: str

    def __str__(self) -> str:  # pragma: no cover - 便于 print 调试
        return f"[{self.kind}] {self.field_path}: {self.detail}"


# =============================================================================
# 入口函数
# =============================================================================


def validate_semantics(
    world: WorldDefinition,
    scenario: Scenario,
    rules: BaseRules,
) -> None:
    """跨层语义校验（D-013）。

    依次跑两项检查，所有错误聚合成 `SemanticValidationError.issues` 一次性抛出。

    1. ``world.defaults.fallback_action`` ∈ ``rules.actions_handled()``
       （仅当 rules 实现了 `actions_handled` 钩子；返回 None 时跳过）
    2. ``rules.actions_handled()`` ⊆ ``world.action_types``
       （同条件触发；防 rules 声明 resolve 了 world 未定义的 action）

    Args:
        world: 已加载的 `WorldDefinition`
        scenario: 已加载的 `Scenario`（v1 暂不消费，预留参数以备未来 scenario 维度
            校验扩展，例如 ``scheduled_event`` 注入消息时 ``from_actor`` 实体存在性等）
        rules: 已实例化的 `BaseRules` 子类

    Raises:
        SemanticValidationError: 至少一项校验失败时抛出；``issues`` 字段含所有
            发现的问题（可能多个）
    """
    issues: list[SemanticIssue] = []

    # rules 是否声明了能力——None 表示放弃两项检查
    handled = rules.actions_handled()

    if handled is not None:
        issues.extend(_check_fallback_action(world, handled))
        issues.extend(_check_rules_actions_in_world(world, handled))

    # （未来扩展槽位）：scenario 维度的语义校验可以加在此处
    # issues.extend(_check_xxx(scenario, world, rules))

    if issues:
        # 友好的人类可读消息：按 field_path 分行，前缀 issue 序号
        lines = [f"  {idx + 1}. {issue}" for idx, issue in enumerate(issues)]
        raise SemanticValidationError(
            f"语义校验失败，共 {len(issues)} 项问题:\n" + "\n".join(lines),
            issues=list(issues),
        )


# =============================================================================
# 内部检查函数
# =============================================================================


def _check_fallback_action(
    world: WorldDefinition,
    handled: set[str],
) -> list[SemanticIssue]:
    """检查 ``world.defaults.fallback_action`` 必须 ∈ ``handled``。

    若 ``defaults`` 或 ``fallback_action`` 未配置，跳过——它是可选字段，
    Runtime 在没有 fallback 时会用其他兜底策略，不强求声明。
    """
    if world.defaults is None:
        return []
    fallback = world.defaults.fallback_action
    if fallback is None:
        return []
    if fallback in handled:
        return []
    return [
        SemanticIssue(
            field_path="world.defaults.fallback_action",
            kind="fallback_action_not_handled",
            detail=(
                f"fallback_action='{fallback}' 不在 rules 声明的 "
                f"actions_handled={sorted(handled)} 内；首次 fallback "
                f"触发时将崩在运行期（pitfalls.md P1 典型样本）"
            ),
        )
    ]


def _check_rules_actions_in_world(
    world: WorldDefinition,
    handled: set[str],
) -> list[SemanticIssue]:
    """检查 ``handled`` ⊆ ``world.action_types``——rules 不应声明 world 未定义的动作。

    多余声明本身不会让运行期崩（resolve_effects 实际不会被未声明的 action 调用），
    但通常意味着开发者**拼写错** rules 那侧的 action 名，与 world 不一致。提早暴露
    比静默失配好。
    """
    declared_in_world = set(world.action_types.keys())
    extras = handled - declared_in_world
    if not extras:
        return []
    return [
        SemanticIssue(
            field_path=f"rules.actions_handled['{name}']",
            kind="rules_action_not_in_world",
            detail=(
                f"rules 声明能 resolve action='{name}'，但 world.action_types "
                f"未定义此动作；可用动作：{sorted(declared_in_world)}"
            ),
        )
        for name in sorted(extras)
    ]
