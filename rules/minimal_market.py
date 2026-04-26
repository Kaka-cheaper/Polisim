"""Walkthrough 最小市场规则（D-009 路线 1 的具体兑现）。

对应 `docs/01-requirements/最小示例Walkthrough.md` 第七节"规则层真正让动作生效"
与 `scenarios/minimal_market/world.yaml` + `scenario.yaml`。

**本模块只做两件事**：

1. 覆写 `validate_action`——在 `BaseRules` 通用校验之上追加"`cash >= budget`"前置条件
2. 覆写 `resolve_effects`——把 `promote(budget=B)` 映射为两条 `AttributeEffect`：
   ``cash -B`` 与 ``reputation +5``；`do_nothing` 映射为空列表

**不做**：

- 冲突解决（继承 `BaseRules.resolve_conflicts`，按 `defaults.conflict_resolution` 走）
- 属性 clamp（继承 `BaseRules.apply_constraints`，按 `min/max` 走）
- 消息路由 / 激活调度（Runtime 的职责，与本模块无关）

**设计约定**（D-009）：

- 每个世界写一个 `rules/<world>.py` 模块；本模块仅对 `world.id = "minimal-market"` 有意义
- 但本模块**不**显式检查 `world.id`——因为 Runtime 的 validate_action 已确保 action_type
  合法（`promote` / `do_nothing`），公式就是对这些 action_type 的语义解释
- 未来走 D-009 路线 2（schema 数据化）时，本模块可退化成零代码——公式从 world 数据推出
"""

from __future__ import annotations

from models.runtime_models import (
    ActionProposal,
    AttributeEffect,
    Effect,
    ValidationResult,
    WorldState,
)
from models.world_models import WorldDefinition
from rules.base import BaseRules


class MinimalMarketRules(BaseRules):
    """Walkthrough 最小市场场景的规则实现。

    动作公式：

    - ``promote(budget=B)`` → ``cash -B`` + ``reputation +5``，前置条件 ``cash >= B``
    - ``do_nothing`` → 无效果

    其余通用逻辑（action 存在性、参数类型、min/max clamp、冲突策略）沿用 `BaseRules`。
    """

    # ------------------------------------------------------------------
    # actions_handled：D-013 语义校验消费的钩子
    # ------------------------------------------------------------------

    def actions_handled(self) -> set[str]:
        """声明本规则可 resolve 的 action 集合（D-013）。

        与 `resolve_effects` 的 if/elif 分发分支保持同步——两者必须一致，否则 D-013
        会拒绝该 world+rules 组合（"声明的 actions_handled 与 world.action_types
        不一致" 或 "fallback_action 不在 actions_handled 内"）。
        """
        return {"promote", "do_nothing"}

    # ------------------------------------------------------------------
    # 在通用 validate_action 之上追加业务前置条件
    # ------------------------------------------------------------------

    def validate_action(
        self,
        world: WorldDefinition,
        state: WorldState,
        proposal: ActionProposal,
    ) -> ValidationResult:
        """继承通用校验 + 追加 walkthrough 专属前置条件。

        前置条件清单（第一版只有 1 条）：

        - ``promote``：要求 actor 的 ``cash >= budget``

        若基础校验已不通过，直接返回其结果（不累加业务错误，避免"基础错 + 业务错"
        一起输出让用户困惑）。
        """
        base_result = super().validate_action(world, state, proposal)
        if not base_result.valid:
            return base_result

        # base_result.valid=True 已保证 base_result.errors 为空——
        # 业务前置条件错误从空列表起步累积
        errors: list[str] = []

        if proposal.action_type == "promote":
            actor = state.entities.get(proposal.actor_id)
            budget = proposal.params.get("budget", 0)
            # 此时 actor 一定存在（base 已校验），budget 也一定是 number（base 已校验）
            assert actor is not None
            current_cash = actor.attributes.get("cash", 0)
            if current_cash < budget:
                errors.append(
                    f"promote 前置条件不满足：actor '{proposal.actor_id}' 的 "
                    f"cash={current_cash} 小于 budget={budget}"
                )

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    # ------------------------------------------------------------------
    # resolve_effects：D-009 路线 1 要求每世界自己实现
    # ------------------------------------------------------------------

    def resolve_effects(
        self,
        world: WorldDefinition,
        state: WorldState,
        proposal: ActionProposal,
    ) -> list[Effect]:
        """按 walkthrough 第七节映射动作为效果列表。

        Runtime 应确保在调用本方法前 proposal 已通过 `validate_action`；
        因此本方法对未知动作返回空列表，不重复校验。
        """
        if proposal.action_type == "do_nothing":
            return []

        if proposal.action_type == "promote":
            budget = float(proposal.params.get("budget", 0))
            return [
                AttributeEffect(
                    actor_id=proposal.actor_id,
                    attribute="cash",
                    delta=-budget,
                ),
                AttributeEffect(
                    actor_id=proposal.actor_id,
                    attribute="reputation",
                    delta=5.0,
                ),
            ]

        # 未覆盖的 action_type：防御式返回空；正常流程不应走到这里
        return []
