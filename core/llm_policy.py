"""LLM 决策协议层（第 3 步 / Phase B）。

对应 `docs/02-design/LLM决策协议设计.md` 第四、五、七节。

**职责边界**（与相邻层的分工）：

- `core/providers/*`——**传输层**：只把 prompt 发出去、把原始文本拿回来；失败抛
  `ProviderError`
- `core/llm_policy`（本文件）——**协议层**：prompt 构造、JSON 输出校验、动作白
  名单校验、失败抛 `LLMProtocolError`；后续 Phase B.3 会在此加指数退避重试
- `core/runtime`——**编排层**：调 `llm_policy.decide` 拿到 `ActionProposal`，
  捕获 `ProviderError` / `LLMProtocolError` 后走 fallback；本层**不**知道 fallback
  是什么——那是 World 的 `defaults.fallback_action` 配置

**为什么把协议层独立出来**（session 19 Phase B.1 重构理由）：

1. Runtime 原本的 `_decide_via_llm` 把 prompt 构造 / 解析 / 校验 / fallback 混在
   一起，任何一处改动都要动 Runtime——违反单一职责
2. 未来接真实 LLM 后要加**协议级重试**（session 19 Phase B.3），重试循环不应
   写在 Runtime 里——Runtime 的 tick 主循环应该对 LLM 是否重试无感
3. Phase C LLM 增强分析（`core/analysis.enhance_with_llm`）也会调 provider——
   两者共享 `LLMProvider` ABC 与 `LLMProtocolError` 契约，各自维护自己的
   prompt / parse 逻辑（语义不同，不强行共享 prompt 模板）

**v1 不做**：

- 协议级重试（留给 Phase B.3）——本版 `decide` 调一次、失败即抛
- 结构化输出（OpenAI ``response_format=Pydantic``）——`generate` 返回 `str`
  是 `LLMProvider` ABC 的契约，本层用 ``json.loads`` 解析；未来可扩 ABC 再加
- 上下文压缩 / 记忆流（Stanford generative-agents 的 memory stream）——那是
  Phase C++ 的内容
"""

from __future__ import annotations

import json
import logging
from typing import Any

from core.errors import LLMProtocolError, ProviderError
from core.providers.base import LLMProvider
from models.config_models import RuntimeConfig
from models.runtime_models import ActionProposal, WorldState
from models.scenario_models import Scenario
from models.world_models import WorldDefinition

logger = logging.getLogger(__name__)


# =============================================================================
# Prompt 构造
# =============================================================================


def build_prompt(
    world: WorldDefinition,
    scenario: Scenario,
    state: WorldState,
    entity_id: str,
    tick: int,
    *,
    language: str = "zh-CN",
) -> str:
    """把 Runtime 当前上下文打成 LLM 可消费的 prompt 文本（v1 最简：JSON dump）。

    payload 字段：

    - ``tick`` / ``remaining_ticks``——时间维度
    - ``actor``——主体实体的 id / type / attributes
    - ``inbox``——本 tick 起点的所有已投递消息（去掉 tick_* 字段降噪）
    - ``environment``——当前环境变量
    - ``available_actions``——actor 允许的动作名及 param schema

    输出语言（session 19 追加）：

    - ``language`` 参数——LLM 在填写 ``reason`` 等自然语言字段时使用的语言
    - 通过在 payload JSON 后追加一行自然语言指令实现；**不**影响 JSON 结构字段
      （``action`` / ``params`` 等机器标识符永远保持原样）
    - LLM 自行理解 language 代码——支持 ``zh-CN`` / ``en`` / ``日本語`` / 任意字符串

    未来（Phase C++）会升级为结构化 prompt + 自然语言引导 + memory stream。
    v1 的 JSON dump 形式已经足够让 MockProvider 的 scripted 响应与 OpenAI 都跑通。

    Raises:
        KeyError: ``entity_id`` 未注册或实体类型未在 world 中声明（这些本应由
            Scenario loader 预检，到本层仍出错表示 Runtime 状态不一致）
    """
    entity = state.entities[entity_id]
    type_schema = world.entity_types[entity.type]
    inbox = state.mailboxes.get(entity_id, [])

    available_actions: list[dict[str, Any]] = []
    for action_name in type_schema.actions:
        action_schema = world.action_types.get(action_name)
        if action_schema is None:
            # 跨引用已由 loader 校验过；到本层仍缺失表示编排层异常，静默跳过
            continue
        available_actions.append(
            {
                "name": action_name,
                "params": {
                    p_name: {"type": p.type, "required": p.required}
                    for p_name, p in action_schema.params.items()
                },
            }
        )

    payload = {
        "tick": tick,
        "remaining_ticks": scenario.config.total_ticks - tick,
        "actor": {
            "id": entity.id,
            "type": entity.type,
            "attributes": entity.attributes,
        },
        "inbox": [
            {
                "message_type": m.message_type,
                "from": m.from_actor,
                "payload": m.payload,
            }
            for m in inbox
        ],
        "environment": state.environment,
        "available_actions": available_actions,
    }
    payload_json = json.dumps(payload, ensure_ascii=False)
    # 语言指令——让 LLM 的 reason 等自然语言字段遵从偏好语言。
    # 注意：指令**不**要求整条响应都用该语言（响应仍必须是合法 JSON），
    # 只要求 JSON 内部的**自然语言字段**使用。
    language_instruction = (
        f"\n\nWhen filling natural-language fields (e.g. `reason`), "
        f"respond in {language}. "
        f"Keep machine-readable fields (action names, parameter keys) unchanged."
    )
    return payload_json + language_instruction


# =============================================================================
# 响应解析 + 校验
# =============================================================================


def parse_response(raw: str, allowed_actions: list[str]) -> dict[str, Any]:
    """解析 LLM 原始文本，校验为合法的 action dict。

    协议约定（`LLM决策协议设计.md` 第四节）的最小子集：

    - 顶层必须是 object；否则 `LLMProtocolError`
    - ``action`` 字段必须是字符串且在 ``allowed_actions`` 中；否则 `LLMProtocolError`
    - ``params`` 字段若存在必须是 object；非 object 时归 0（取空 dict）——
      这是"宽容式降级"：LLM 可能把 params 写成 null / list，但核心是 action
      合法，宽容允许继续
    - ``reason`` 字段可选，字符串或 None——用于 `raw_reasoning_summary`

    Returns:
        标准化后的 dict：``{"action": str, "params": dict, "reason": str | None}``

    Raises:
        LLMProtocolError: 解析或校验失败；原始文本附在 ``__cause__`` 或 msg 中
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMProtocolError(
            f"LLM 响应不是合法 JSON：{exc.msg}；原始文本前 200 字符："
            f"{raw[:200]!r}"
        ) from exc
    except TypeError as exc:
        # raw 非 str/bytes——provider 实现违约；按协议错误处理（走 fallback）
        raise LLMProtocolError(
            f"LLM 响应类型非法（预期 str）：{type(raw).__name__}"
        ) from exc

    if not isinstance(data, dict):
        raise LLMProtocolError(
            f"LLM 响应顶层必须是 object，实际为 {type(data).__name__}"
        )

    action = data.get("action")
    if not isinstance(action, str):
        raise LLMProtocolError(
            f"LLM 响应 action 字段缺失或非字符串，实际为 {type(action).__name__}"
        )
    if action not in allowed_actions:
        raise LLMProtocolError(
            f"LLM 选择了不在白名单内的 action='{action}'；"
            f"允许: {sorted(allowed_actions)}"
        )

    params = data.get("params")
    if not isinstance(params, dict):
        # 宽容降级：params 非 object 时归 0
        params = {}

    reason = data.get("reason")
    if reason is not None and not isinstance(reason, str):
        reason = None

    return {"action": action, "params": params, "reason": reason}


# =============================================================================
# 决策编排——Runtime 的单点入口
# =============================================================================


def decide(
    provider: LLMProvider,
    world: WorldDefinition,
    scenario: Scenario,
    state: WorldState,
    entity_id: str,
    tick: int,
    *,
    config: RuntimeConfig,
) -> ActionProposal:
    """调 provider → 解析 → 校验 → 返回 `ActionProposal`。

    v1 单次调用；Phase B.3 会在此处加指数退避重试（`config.llm_request_timeout_sec`
    与 `LLMProviderConfig.max_retries` 联动）。

    Raises:
        ProviderError: 传输层失败（原样上抛给 Runtime）
        LLMProtocolError: 协议层失败——JSON 不合法 / action 不在白名单 / params 结构不合约

    Note:
        Fallback 不在本层做——那需要知道 ``world.defaults.fallback_action``，是 Runtime
        职责。本函数只负责"拿到一条合法的 LLM 提议"或"把失败原因抛上去"。
    """
    prompt = build_prompt(
        world,
        scenario,
        state,
        entity_id,
        tick,
        language=config.output_language,
    )
    entity = state.entities[entity_id]
    type_schema = world.entity_types[entity.type]
    allowed_actions = list(type_schema.actions)

    # ProviderError / LLMProtocolError 都向上自然冒泡——Runtime 在 _decide_via_llm
    # 一并捕获后走 fallback；本层不再做空 try/except 重抛
    raw = provider.generate(
        prompt,
        temperature=0.7,
        max_tokens=512,
        timeout=config.llm_request_timeout_sec,
    )
    parsed = parse_response(raw, allowed_actions)

    return ActionProposal(
        tick=tick,
        actor_id=entity_id,
        action_type=parsed["action"],
        params=parsed["params"],
        decision_mode="llm",
        raw_reasoning_summary=parsed["reason"],
        status="proposed",
    )
