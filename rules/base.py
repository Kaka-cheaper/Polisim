"""规则层基类（D-009 路线 1）。

对应 `docs/02-design/规则层设计.md` 全章与 `docs/02-design/实现映射设计.md` 4.3 节。

**分层约束**：

- 本模块只依赖 `models/world_models` 与 `models/runtime_models`——**不**导入
  `core/events.py` / `core/runtime.py` / `core/providers/`，保证规则层可独立测试
- 运行时调用规则、规则不知道运行时；规则通过返回 `Effect` 列表与 `ValidationResult`
  表达意图，由运行时执行副作用
- `resolve_effects` 是**抽象方法**——每个世界写一个子类实现自己的公式
- 其余 3 个方法有**通用默认实现**：`validate_action` / `apply_constraints` /
  `resolve_conflicts`，均可由任意合法的 `WorldDefinition` 数据驱动

**v1 约定**（来自 D-009）：

1. 公式不在世界 schema 中表达——`ActionEffectSchema` 只声明效果 `kind`，不带
   formula。未来若走路线 2 扩展 schema，本类的默认 `resolve_effects` 可升级为
   "从 schema 公式字段推导"，接口不变
2. 规则层不感知 LLM / 消息投递时机 / 激活调度——那些都是 Runtime 的职责
3. 对 v1 超出范围的冲突场景（例如关系冲突）直接 flatten，不报错；走到踩坑时再决策
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from random import Random
from typing import Any

from models.runtime_models import (
    ActionProposal,
    AttributeEffect,
    Effect,
    EnvironmentEffect,
    ValidationResult,
    WorldState,
)
from models.world_models import WorldDefinition


class BaseRules(ABC):
    """规则模块的抽象基类。

    所有具体规则模块（例如 `rules/minimal_market.py`）都应继承本类并**只覆写
    `resolve_effects`**。其他 3 个方法的默认实现已基于 `WorldDefinition` 推导，
    对任意合法世界都成立。

    构造参数：

    - ``random_seed``：用于 `resolve_conflicts` 的 ``random`` 策略，可复现选择。
      为 None 时行为不确定（每次运行随机种子不同）
    """

    def __init__(self, *, random_seed: int | None = None) -> None:
        self._rng = Random(random_seed)

    # =========================================================================
    # 抽象：每个世界必须实现
    # =========================================================================

    @abstractmethod
    def resolve_effects(
        self,
        world: WorldDefinition,
        state: WorldState,
        proposal: ActionProposal,
    ) -> list[Effect]:
        """将一个（已通过 `validate_action` 校验的）动作提议映射为具体效果列表。

        v1 必须由子类实现——`ActionEffectSchema` 只声明 ``kind``，不携带公式。
        第二阶段（D-009 路线 2）扩展 schema 后，本方法可提供默认实现。

        参数：
            world: 静态世界定义
            state: 当前 tick 的完整运行时状态
            proposal: 一条**合法**的动作提议（已过 `validate_action`）

        返回：
            与本动作语义等价的 `Effect` 列表；空列表表示"无副作用"（如 do_nothing）
        """

    # =========================================================================
    # 可选钩子：actions_handled（D-013 语义校验消费）
    # =========================================================================

    def actions_handled(self) -> set[str] | None:
        """声明本规则模块能 resolve 的 ``action_type`` 集合。

        **D-013 用途**——`core/semantic_validator.validate_semantics` 用此集合
        校验两件事：

        1. ``world.defaults.fallback_action`` 必须 ∈ ``actions_handled()``
           （否则首次 fallback 触发时崩在运行期，详见 `pitfalls.md` P1）
        2. ``actions_handled()`` 必须 ⊆ ``world.action_types``
           （rules 不应声明 resolve 了 world 未定义的动作；防拼写错）

        **默认返回 ``None``**——表示子类未实现本钩子，D-013 跳过这两项检查（向后
        兼容）。具体规则模块若想被 D-013 严格校验，覆写本方法返回明确集合即可。

        Returns:
            set[str] | None: 能 resolve 的 action_type 集合，或 None（不声明）。
        """
        return None

    # =========================================================================
    # 通用实现：validate_action
    # =========================================================================

    def validate_action(
        self,
        world: WorldDefinition,
        state: WorldState,
        proposal: ActionProposal,
    ) -> ValidationResult:
        """判断一条动作提议是否合法。

        聚合所有可独立发现的错误一次性返回，便于 Runtime / UI 一次展示所有问题。
        仅当 ``action_type`` 未声明时短路（因为后续校验都依赖它的 schema）。

        校验维度：

        1. ``action_type`` 必须在 ``world.action_types`` 中声明
        2. ``actor_id`` 必须存在于 ``state.entities``
        3. 该实体的 ``type`` 必须在动作的 ``actor_types`` 允许列表中
        4. 动作的 ``required=True`` 参数必须出现在 ``proposal.params``
        5. ``proposal.params`` 中不得有未声明的参数
        6. 每个参数的值类型应匹配其声明（number / string / boolean / entity_ref）
        """
        errors: list[str] = []

        # 1. action_type declared
        if proposal.action_type not in world.action_types:
            errors.append(
                f"action_type '{proposal.action_type}' 未在 World Definition 中声明"
            )
            # 后续校验都依赖 action_schema，直接短路
            return ValidationResult(valid=False, errors=errors)

        action_schema = world.action_types[proposal.action_type]

        # 2/3. actor existence + type
        actor = state.entities.get(proposal.actor_id)
        if actor is None:
            errors.append(
                f"actor_id '{proposal.actor_id}' 未在当前世界状态中"
            )
        elif actor.type not in action_schema.actor_types:
            errors.append(
                f"实体 '{proposal.actor_id}' 类型 '{actor.type}' 不在动作 "
                f"'{proposal.action_type}' 的允许 actor_types "
                f"{action_schema.actor_types} 中"
            )

        # 4. required params present
        declared_params = action_schema.params
        given_params = proposal.params
        for param_name, param_schema in declared_params.items():
            if param_schema.required and param_name not in given_params:
                errors.append(f"必填参数 '{param_name}' 缺失")

        # 5/6. given params: each declared + type match
        for param_name, value in given_params.items():
            if param_name not in declared_params:
                errors.append(
                    f"参数 '{param_name}' 未在动作 '{proposal.action_type}' 中声明"
                )
                continue
            expected_type = declared_params[param_name].type
            if not self._matches_param_type(value, expected_type):
                errors.append(
                    f"参数 '{param_name}' 类型不匹配："
                    f"期望 {expected_type}，实际 {type(value).__name__}"
                )

        return ValidationResult(valid=len(errors) == 0, errors=errors)

    @staticmethod
    def _matches_param_type(value: Any, expected: str) -> bool:
        """检查 Python 值是否匹配参数类型字符串。

        Python 的 ``bool`` 是 ``int`` 的子类，``number`` 检查需显式排除 bool。
        ``entity_ref`` 在 v1 等同于 string（id）。
        """
        if expected == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if expected in ("string", "entity_ref"):
            return isinstance(value, str)
        if expected == "boolean":
            return isinstance(value, bool)
        # 未知类型：放行（防御式），避免挡住未来扩展
        return True

    # =========================================================================
    # 通用实现：apply_constraints
    # =========================================================================

    def apply_constraints(
        self,
        world: WorldDefinition,
        state: WorldState,
        effects: list[Effect],
    ) -> list[Effect]:
        """把数值类效果的 delta 裁剪到属性 / 环境变量声明的 min/max 内。

        - `AttributeEffect`：按实体类型的属性 schema 裁剪
        - `EnvironmentEffect`：按环境变量 schema 裁剪
        - `RelationEffect` / `MessageEffect`：原样透传（v1 不约束）

        **不修改入参**：返回全新列表；若某效果无需调整则引用原对象。
        """
        return [self._clamp_single(world, state, eff) for eff in effects]

    def _clamp_single(
        self, world: WorldDefinition, state: WorldState, effect: Effect
    ) -> Effect:
        if isinstance(effect, AttributeEffect):
            return self._clamp_attribute(world, state, effect)
        if isinstance(effect, EnvironmentEffect):
            return self._clamp_environment(world, state, effect)
        return effect

    def _clamp_attribute(
        self,
        world: WorldDefinition,
        state: WorldState,
        effect: AttributeEffect,
    ) -> AttributeEffect:
        actor = state.entities.get(effect.actor_id)
        if actor is None:
            return effect  # 未知实体：留给 Runtime 处理
        actor_type_schema = world.entity_types.get(actor.type)
        if actor_type_schema is None:
            return effect
        attr_schema = actor_type_schema.attributes.get(effect.attribute)
        if attr_schema is None or attr_schema.type != "number":
            return effect  # 非数值属性或未声明：不在本层约束
        current = actor.attributes.get(effect.attribute, 0)
        if not isinstance(current, (int, float)) or isinstance(current, bool):
            return effect  # 状态里塞了非数值——留给 Runtime 报错
        target = current + effect.delta
        clamped = self._clamp_range(target, attr_schema.min, attr_schema.max)
        if clamped == target:
            return effect
        return AttributeEffect(
            actor_id=effect.actor_id,
            attribute=effect.attribute,
            delta=clamped - current,
        )

    def _clamp_environment(
        self,
        world: WorldDefinition,
        state: WorldState,
        effect: EnvironmentEffect,
    ) -> EnvironmentEffect:
        env_schema = world.environment
        if env_schema is None:
            return effect
        var_schema = env_schema.variables.get(effect.variable)
        if var_schema is None or var_schema.type != "number":
            return effect
        current = state.environment.get(effect.variable, 0)
        if not isinstance(current, (int, float)) or isinstance(current, bool):
            return effect
        target = current + effect.delta
        clamped = self._clamp_range(target, var_schema.min, var_schema.max)
        if clamped == target:
            return effect
        return EnvironmentEffect(
            variable=effect.variable,
            delta=clamped - current,
        )

    @staticmethod
    def _clamp_range(
        value: float, lo: float | None, hi: float | None
    ) -> float:
        if lo is not None:
            value = max(value, lo)
        if hi is not None:
            value = min(value, hi)
        return value

    # =========================================================================
    # 通用实现：resolve_conflicts
    # =========================================================================

    def resolve_conflicts(
        self,
        world: WorldDefinition,
        state: WorldState,
        effect_groups: list[list[Effect]],
    ) -> list[Effect]:
        """按 ``world.defaults.conflict_resolution`` 合并多个动作的效果。

        输入：每个动作产出的效果列表的列表；顺序即 actor 被调度的顺序。

        策略：

        - ``both``：全部保留（默认；无冲突检测）
        - ``priority``：同 key 冲突时**第一个**胜出（insertion order = actor 顺序）
        - ``random``：同 key 冲突时随机选一，由 ``self._rng`` 决定（注入 seed 保证可复现）

        v1 只对 ``AttributeEffect`` 的 (actor_id, attribute) 与 ``EnvironmentEffect``
        的 variable 做冲突检测。关系 / 消息不做检测（即便多次 add 也会串行叠加）。
        """
        strategy: str = "both"
        if world.defaults is not None:
            strategy = world.defaults.conflict_resolution

        flattened: list[Effect] = [
            eff for group in effect_groups for eff in group
        ]

        if strategy == "both":
            return flattened

        # 分桶：同 key 的放一起，None key 直通
        buckets: dict[tuple, list[Effect]] = {}
        non_conflicting: list[Effect] = []
        for eff in flattened:
            key = self._conflict_key(eff)
            if key is None:
                non_conflicting.append(eff)
            else:
                buckets.setdefault(key, []).append(eff)

        resolved: list[Effect] = list(non_conflicting)
        for group in buckets.values():
            if len(group) == 1:
                resolved.extend(group)
            elif strategy == "priority":
                resolved.append(group[0])  # 第一个（insertion order）胜出
            elif strategy == "random":
                resolved.append(self._rng.choice(group))
            else:
                # 未知策略：防御式退化到 both
                resolved.extend(group)
        return resolved

    @staticmethod
    def _conflict_key(effect: Effect) -> tuple | None:
        """返回可哈希的冲突键；None 表示本层不做冲突检测。"""
        if isinstance(effect, AttributeEffect):
            return ("self_attribute", effect.actor_id, effect.attribute)
        if isinstance(effect, EnvironmentEffect):
            return ("environment", effect.variable)
        # RelationEffect / MessageEffect：v1 不做冲突检测
        return None
