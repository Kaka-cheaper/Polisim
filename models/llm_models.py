"""LLM 决策协议数据模型（D-016）。

对应 `docs/02-design/decisions/D-016-prompt上下文规范化.md` 第二节，以及
`docs/02-design/实现映射设计.md` 第 56 行预留落点 `models/llm_models.py`。

本文件只定义 LLM 协议层的"输入输出 schema"，**不承载任何业务逻辑**：

- prompt 构造逻辑 / parse / decide 由 `core/llm_policy.py` 实现
- provider 传输由 `core/providers/*.py` 实现
- 场景特化 prompt 注入由 `rules/<world>.BaseRules.enrich_prompt` 实现

D-016 引入 `PromptContext` + `LLMDecisionResult` 的目的：

1. **可拆段可视化**——v0.2 前端"LLM 决策实时面板"可分别渲染 system_role /
   actor_view / perception / available_actions / custom_segments
2. **可注入场景人设**——`rules.enrich_prompt(ctx)` 可往 ``custom_segments``
   或 ``system_role`` 加场景特化提示，不动引擎事实段
3. **可序列化进 EventLog**——`LLMDecisionResult` 把 PromptContext 与
   ActionProposal 一起暴露给 Runtime，``decision_proposed`` 事件的
   ``prompt_context`` payload 由此而来

模型层约束（与项目其他 models 一致）：

1. Pydantic v2 + ``ConfigDict(extra="forbid")``
2. 字段类型严格、字段语义只在本文件 docstring 表达——结构字段不做跨模型语义校验
3. ``render()`` 方法把结构化容器拼为最终 prompt str，供 ``LLMProvider.generate``
   消费（v1 字符串契约不变，向后兼容）
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from models.runtime_models import ActionProposal


# =============================================================================
# PromptContext
# =============================================================================


class PromptContext(BaseModel):
    """LLM 决策 prompt 的结构化容器（D-016）。

    每段独立可序列化，前端可分别渲染。最终通过 :meth:`render` 拼成 ``str``
    供 ``LLMProvider.generate`` 消费——保持向后兼容。

    **字段语义边界**：

    - ``system_role`` / ``custom_segments``——**rules 模块可注入**
      （场景人设、目标、约束、历史叙事）
    - ``actor_view`` / ``perception`` / ``available_actions``——**引擎事实**
      （由 ``build_prompt`` 从 World / Scenario / WorldState / EventLog 推导，
      rules 模块**不应**修改这些段）

    **render 输出兼容性**：

    - 当 ``system_role=None`` 且 ``custom_segments={}`` 时，render 输出与
      D-014 时代的 ``build_prompt`` **字节级等价**——这是 D-016 第二步
      向后兼容回归测试的基线
    - 后续步骤补 ``actor_view.relations`` / ``actor_view.recent_decisions``
      时，render 输出会包含新字段，但 LLMProvider.generate 契约不变
    """

    model_config = ConfigDict(extra="forbid")

    # ── A. 角色与身份 ──
    system_role: str | None = Field(
        default=None,
        description='可选的 system 角色描述。例如 "You are entity \'company_a\' '
        'of type \'company\'"。rules.enrich_prompt 可替换为更场景化的角色描述。'
        "为 None 时 render 不输出此段。",
    )

    # ── B. Actor 自身视图 ──
    actor_view: dict[str, Any] = Field(
        ...,
        description="actor 自身的可见状态。最少包含 id / type / attributes；"
        "D-016 第 3-4 步将补 relations（actor 涉及的关系子集）与 "
        "recent_decisions（actor 最近 N 次决策）。",
    )

    # ── C. 外部感知 ──
    perception: dict[str, Any] = Field(
        ...,
        description="actor 看到的外部世界。包含 inbox（已投递消息）、"
        "environment（当前环境变量）、tick / remaining_ticks（时间维度）。",
    )

    # ── D. 可用动作（含 D-014 完整 ParamSchema）──
    available_actions: list[dict[str, Any]] = Field(
        ...,
        description="actor 当前 tick 允许采取的动作列表。每项含 name / params"
        "完整 schema（含 D-014 的 description / default / min / max / values / "
        "entity_type_filter）；可选 description。",
    )

    # ── E. 语言指令 ──
    language_hint: str = Field(
        default="zh-CN",
        description="LLM 在填写自然语言字段（如 ``reason``）时使用的语言。"
        "支持 ISO 639-1（如 zh-CN / en）或自然语言名（如 日本語）；"
        "render 时附加在 prompt 尾部。",
    )

    # ── F. 场景特化段（rules.enrich_prompt 注入）──
    custom_segments: dict[str, str] = Field(
        default_factory=dict,
        description="rules 模块通过 enrich_prompt 注入的场景特化段。"
        '示例：{"objective": "Reach trust=80 with at least one other party"}。'
        "render 时按 key 字母序拼接，避免随机化输出影响测试稳定性。",
    )

    # ------------------------------------------------------------------
    # 序列化为 prompt 字符串
    # ------------------------------------------------------------------

    def render(self) -> str:
        """把结构化容器拼为最终 prompt 字符串。

        **拼接顺序**（每段之间用 ``\\n\\n`` 分隔，缺省段省略）：

        1. ``system_role``（若非 None）
        2. payload JSON（含 actor_view / perception / available_actions——
           D-014 时代 build_prompt 的核心输出，字节级等价）
        3. ``language_hint`` 指令（永远输出，4 行尾段）
        4. ``custom_segments``（按 key 字母序，若非空）

        **向后兼容**：``system_role=None`` 且 ``custom_segments={}`` 时，
        输出 = ``payload_json + language_instruction``，与 D-014 时代的
        ``build_prompt`` 输出**字节级等价**——D-016 第 2 步重构后回归测
        试的基线。
        """
        parts: list[str] = []

        if self.system_role is not None:
            parts.append(self.system_role)

        # 主体 payload——与 D-014 时代 build_prompt 字段顺序保持一致
        payload = {
            "tick": self.perception.get("tick"),
            "remaining_ticks": self.perception.get("remaining_ticks"),
            "actor": self.actor_view,
            "inbox": self.perception.get("inbox", []),
            "environment": self.perception.get("environment", {}),
            "available_actions": self.available_actions,
        }
        payload_json = json.dumps(payload, ensure_ascii=False)
        parts.append(payload_json)

        # 语言指令（与 session 19 多语言机制一致）
        language_instruction = (
            f"When filling natural-language fields (e.g. `reason`), "
            f"respond in {self.language_hint}. "
            f"Keep machine-readable fields (action names, parameter keys) unchanged."
        )
        parts.append(language_instruction)

        # custom_segments：按 key 字母序拼接（避免随机化影响测试 + 前端展示稳定）
        if self.custom_segments:
            for key in sorted(self.custom_segments):
                parts.append(f"[{key}]\n{self.custom_segments[key]}")

        # **关键**：当 system_role=None + custom_segments={} 时，
        # parts = [payload_json, language_instruction]
        # 两段以 "\n\n" 拼接 → 与 D-014 时代 build_prompt 输出
        # `payload_json + "\n\n" + language_instruction` 字节级等价。
        return "\n\n".join(parts)


# =============================================================================
# LLMDecisionResult
# =============================================================================


class LLMDecisionResult(BaseModel):
    """LLM 决策完整结果（D-016 第 6 步）。

    由 :func:`core.llm_policy.decide` 返回，封装两个紧密关联的产物：

    - ``proposal``——动作提议（与 D-016 之前 ``decide`` 返回的对象同形）
    - ``prompt_context``——本次决策实际喂给 LLM 的结构化 prompt 上下文

    Runtime 拿到本对象后：

    1. 用 ``proposal`` 走原有动作执行链路（与之前完全相同）
    2. 用 ``prompt_context`` 序列化进 ``decision_proposed`` 事件的 payload，
       供前端"LLM 决策实时面板"事后回看 prompt 各段

    **为什么不是 dataclass / NamedTuple**：与项目其他模型（``ActionProposal`` /
    ``ValidationResult`` / ``Snapshot`` 等）一致用 Pydantic BaseModel——
    一致性 + 原生 JSON 序列化 + extra=forbid 防字段漂移。
    """

    model_config = ConfigDict(extra="forbid")

    proposal: ActionProposal = Field(
        ..., description="动作提议（与 D-016 前 ``decide`` 返回类型相同）"
    )
    prompt_context: PromptContext = Field(
        ..., description="本次决策实际喂给 LLM 的结构化 prompt 上下文"
    )
