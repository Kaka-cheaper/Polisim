"""三人谈判场景规则（D-009 路线 1 的第二份具体兑现）。

对应 `scenarios/three_party_negotiation/world.yaml` + `scenario.yaml`。

**与 minimal_market 的差异**——本文件是为了**主动覆盖 minimal_market 没演示的
架构特性**：

- ``propose`` 产生 ``MessageEffect``（direct 投递，target_id 路由）
- ``accept`` 同时产生**三种** Effect：``RelationEffect`` (trust update_value)
  + ``AttributeEffect`` (max_trust delta) + ``MessageEffect`` (agreement broadcast)
- ``reject`` 产生 ``RelationEffect`` (trust 减少)
- ``trust`` 关系的 update_value 操作（minimal_market 完全没用 RelationEffect）

**业务前置条件**（在 `BaseRules.validate_action` 通用校验之上追加）：

- ``propose``：``target_id`` 必须存在且不是自己；``price`` ≥ 0
- ``accept`` / ``reject``：``offer_from`` 必须存在且不是自己

**v1 简化**：

- ``accept`` 不真实扣 cash——v1 演示 trust 演化，不演示资金结算
- ``reject`` 不发消息——对方下 tick 看不到拒绝原因（节省消息体量）
- 不区分 ``offer`` 是否真有过——LLM 可以在没 offer 时也调 accept；rules
  仅按"声明的 offer_from 是有效 negotiator"校验，不查 inbox
"""

from __future__ import annotations

from models.runtime_models import (
    ActionProposal,
    AttributeEffect,
    Effect,
    MessageEffect,
    MessageEnvelope,
    RelationEffect,
    ValidationResult,
    WorldState,
)
from models.world_models import WorldDefinition
from rules.base import BaseRules


# 业务常量（与 docstring / 测试同步）
_TRUST_DELTA_ON_ACCEPT = 20.0
_TRUST_DELTA_ON_REJECT = -10.0
_TRUST_MIN = 0.0
_TRUST_MAX = 100.0


class NegotiationRules(BaseRules):
    """三人谈判场景的规则实现。

    所有动作的语义详见模块 docstring。本类只覆写 `validate_action` 与
    `resolve_effects`；`apply_constraints` / `resolve_conflicts` 沿用基类。
    """

    # ------------------------------------------------------------------
    # actions_handled：D-013 语义校验消费的钩子
    # ------------------------------------------------------------------

    def actions_handled(self) -> set[str]:
        """声明本规则可 resolve 的 action 集合（D-013）。

        与 `resolve_effects` 的 4 路分发（propose / accept / reject / do_nothing）
        保持同步。
        """
        return {"propose", "accept", "reject", "do_nothing"}

    # ------------------------------------------------------------------
    # validate_action：业务前置条件
    # ------------------------------------------------------------------

    def validate_action(
        self,
        world: WorldDefinition,
        state: WorldState,
        proposal: ActionProposal,
    ) -> ValidationResult:
        base_result = super().validate_action(world, state, proposal)
        if not base_result.valid:
            return base_result

        errors: list[str] = []

        if proposal.action_type == "propose":
            target_id = proposal.params.get("target_id")
            price = proposal.params.get("price", 0)
            if target_id == proposal.actor_id:
                errors.append(
                    f"propose 的 target_id 不能是自己（actor='{proposal.actor_id}'）"
                )
            elif target_id not in state.entities:
                errors.append(
                    f"propose 的 target_id='{target_id}' 不是有效 negotiator"
                )
            if price < 0:
                errors.append(f"propose 的 price={price} 不能为负")

        elif proposal.action_type in ("accept", "reject"):
            offer_from = proposal.params.get("offer_from")
            if offer_from == proposal.actor_id:
                errors.append(
                    f"{proposal.action_type} 的 offer_from 不能是自己"
                )
            elif offer_from not in state.entities:
                errors.append(
                    f"{proposal.action_type} 的 offer_from='{offer_from}' "
                    f"不是有效 negotiator"
                )

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    # ------------------------------------------------------------------
    # resolve_effects：动作 → 效果列表
    # ------------------------------------------------------------------

    def resolve_effects(
        self,
        world: WorldDefinition,
        state: WorldState,
        proposal: ActionProposal,
    ) -> list[Effect]:
        if proposal.action_type == "do_nothing":
            return []

        if proposal.action_type == "propose":
            return self._resolve_propose(state, proposal)

        if proposal.action_type == "accept":
            return self._resolve_accept(state, proposal)

        if proposal.action_type == "reject":
            return self._resolve_reject(state, proposal)

        return []

    # ------------------------------------------------------------------
    # 各动作的具体效果生成
    # ------------------------------------------------------------------

    def _resolve_propose(
        self, state: WorldState, proposal: ActionProposal
    ) -> list[Effect]:
        """propose → 一条 direct offer 消息。"""
        target_id = proposal.params["target_id"]
        price = float(proposal.params["price"])
        envelope = MessageEnvelope(
            tick_emitted=proposal.tick,
            tick_delivered=None,
            message_type="offer",
            from_actor=proposal.actor_id,
            payload={
                "target_id": target_id,
                "price": price,
                "from_negotiator": proposal.actor_id,
            },
        )
        return [MessageEffect(envelope=envelope)]

    def _resolve_accept(
        self, state: WorldState, proposal: ActionProposal
    ) -> list[Effect]:
        """accept → 同时产生 RelationEffect / AttributeEffect / MessageEffect 三种。

        三种 Effect 同时发出是 minimal_market 没演示的——验证 BaseRules
        / Runtime 的 effect 流水线对混合 effect 的处理。
        """
        actor_id = proposal.actor_id
        offer_from = proposal.params["offer_from"]
        price = float(proposal.params.get("price", 0))

        actor = state.entities[actor_id]

        # 1. 计算新 trust 值（基类 update_value 是 set 新值，不是 delta；
        #    所以这里要先读 current 再算 new）
        current_trust = self._get_trust(state, actor_id, offer_from)
        new_trust = max(
            _TRUST_MIN,
            min(_TRUST_MAX, current_trust + _TRUST_DELTA_ON_ACCEPT),
        )

        # 2. 计算 max_trust 的增量——如果新 trust 超过历史 max，差值进 AttributeEffect
        old_max = float(actor.attributes.get("max_trust", 0))
        new_max = max(old_max, new_trust)
        max_delta = new_max - old_max  # 0 或正

        # 3. agreement broadcast 广播
        agreement_envelope = MessageEnvelope(
            tick_emitted=proposal.tick,
            tick_delivered=None,
            message_type="agreement",
            from_actor=actor_id,
            payload={
                "acceptor": actor_id,
                "counterparty": offer_from,
                "price": price,
            },
        )

        effects: list[Effect] = [
            RelationEffect(
                operation="update_value",
                relation_type="trust",
                source=actor_id,
                target=offer_from,
                value=new_trust,
            ),
        ]
        # 只在 max_trust 真要刷新时才发 AttributeEffect——避免 0 delta 噪声事件
        if max_delta > 0:
            effects.append(
                AttributeEffect(
                    actor_id=actor_id,
                    attribute="max_trust",
                    delta=max_delta,
                )
            )
        effects.append(MessageEffect(envelope=agreement_envelope))
        return effects

    def _resolve_reject(
        self, state: WorldState, proposal: ActionProposal
    ) -> list[Effect]:
        """reject → 单条 RelationEffect（trust 下调）。"""
        actor_id = proposal.actor_id
        offer_from = proposal.params["offer_from"]

        current_trust = self._get_trust(state, actor_id, offer_from)
        new_trust = max(
            _TRUST_MIN,
            min(_TRUST_MAX, current_trust + _TRUST_DELTA_ON_REJECT),
        )

        return [
            RelationEffect(
                operation="update_value",
                relation_type="trust",
                source=actor_id,
                target=offer_from,
                value=new_trust,
            )
        ]

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _get_trust(state: WorldState, source: str, target: str) -> float:
        """读 state.relations 中 trust(source → target) 的当前值；缺失视作 0。

        scenario.yaml 已在初始化时声明 6 条双向 trust 关系，运行期不应缺。
        但 v1 防御式：缺失返 0，让 update_value 仍能给出合理的新值。
        """
        for rel in state.relations:
            if (
                rel.type == "trust"
                and rel.source == source
                and rel.target == target
            ):
                return float(rel.value or 0)
        return 0.0
