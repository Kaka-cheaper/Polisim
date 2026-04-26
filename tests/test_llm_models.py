"""`models/llm_models.py` 的 PromptContext 模型直接单测（D-016）。

覆盖：

1. PromptContext 字段构造（最小 / 完整 / 默认值 / extra=forbid）
2. render() 输出语义
   - 默认（system_role=None + custom_segments={}）→ 与 D-014 时代 build_prompt
     字节级等价的"payload + language_instruction"两段格式
   - system_role 非 None → 前置
   - custom_segments 非空 → 尾部按 key 字母序拼
   - language_hint 不同 → 尾段语言变化
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from models.llm_models import PromptContext


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def minimal_kwargs() -> dict:
    """构造 PromptContext 所需的最小必填字段。"""
    return {
        "actor_view": {"id": "a", "type": "Agent", "attributes": {"x": 1}},
        "perception": {
            "tick": 1,
            "remaining_ticks": 4,
            "inbox": [],
            "environment": {},
        },
        "available_actions": [{"name": "noop", "params": {}}],
    }


# =============================================================================
# 字段构造
# =============================================================================


class TestPromptContextConstruction:
    def test_minimal_construction(self, minimal_kwargs: dict) -> None:
        """三个必填段就能构造；其余字段走默认值。"""
        ctx = PromptContext(**minimal_kwargs)
        assert ctx.system_role is None
        assert ctx.custom_segments == {}
        assert ctx.language_hint == "zh-CN"

    def test_full_construction(self, minimal_kwargs: dict) -> None:
        """完整字段构造——所有段全填。"""
        ctx = PromptContext(
            **minimal_kwargs,
            system_role="You are an Agent.",
            language_hint="en",
            custom_segments={"objective": "Win", "constraint": "Be honest"},
        )
        assert ctx.system_role == "You are an Agent."
        assert ctx.language_hint == "en"
        assert ctx.custom_segments == {"objective": "Win", "constraint": "Be honest"}

    def test_rejects_extra_field(self, minimal_kwargs: dict) -> None:
        """extra='forbid'：多余字段被拒。"""
        with pytest.raises(ValidationError):
            PromptContext(**minimal_kwargs, unknown_field="x")  # type: ignore[call-arg]

    def test_required_fields_must_be_provided(self) -> None:
        """actor_view / perception / available_actions 必填——缺一即抛。"""
        with pytest.raises(ValidationError):
            PromptContext(  # type: ignore[call-arg]
                actor_view={"id": "a", "type": "Agent"},
                perception={"tick": 1},
                # available_actions 缺
            )


# =============================================================================
# render() 输出语义
# =============================================================================


class TestPromptContextRender:
    def test_default_render_is_two_segments(self, minimal_kwargs: dict) -> None:
        """默认 render → "payload_json\\n\\nlanguage_instruction" 两段格式
        （system_role=None + custom_segments={}）。"""
        ctx = PromptContext(**minimal_kwargs)
        rendered = ctx.render()

        # 两段以 \n\n 分隔
        parts = rendered.split("\n\n")
        assert len(parts) == 2

        # 第一段必是合法 JSON，且是 build_prompt 时代的 payload 形态
        payload = json.loads(parts[0])
        assert payload["tick"] == 1
        assert payload["remaining_ticks"] == 4
        assert payload["actor"] == minimal_kwargs["actor_view"]
        assert payload["available_actions"] == minimal_kwargs["available_actions"]

        # 第二段是语言指令（默认 zh-CN）
        assert "zh-CN" in parts[1]
        assert "natural-language" in parts[1].lower()

    def test_system_role_prepended_when_present(self, minimal_kwargs: dict) -> None:
        """system_role 非 None → 出现在 prompt 最前。"""
        ctx = PromptContext(**minimal_kwargs, system_role="ROLE_X")
        rendered = ctx.render()
        # 三段：system_role / payload / language_instruction
        parts = rendered.split("\n\n")
        assert len(parts) == 3
        assert parts[0] == "ROLE_X"

    def test_custom_segments_appended_alphabetically(
        self, minimal_kwargs: dict
    ) -> None:
        """custom_segments 非空 → 按 key 字母序追加在尾部，每段独立块。"""
        ctx = PromptContext(
            **minimal_kwargs,
            custom_segments={
                "zebra": "ZZZ",
                "apple": "AAA",
                "banana": "BBB",
            },
        )
        rendered = ctx.render()
        # 字母序：apple / banana / zebra
        idx_apple = rendered.index("[apple]\nAAA")
        idx_banana = rendered.index("[banana]\nBBB")
        idx_zebra = rendered.index("[zebra]\nZZZ")
        assert idx_apple < idx_banana < idx_zebra

    def test_language_hint_appears_in_tail(self, minimal_kwargs: dict) -> None:
        """language_hint 注入语言指令尾段。"""
        ctx = PromptContext(**minimal_kwargs, language_hint="ja-JP")
        rendered = ctx.render()
        # 默认两段；最后一段是语言指令
        last = rendered.split("\n\n")[-1]
        assert "ja-JP" in last
        assert "zh-CN" not in last

    def test_render_is_deterministic(self, minimal_kwargs: dict) -> None:
        """同输入两次 render 输出**完全一致**——前端缓存与测试稳定的前提。"""
        ctx = PromptContext(
            **minimal_kwargs,
            system_role="X",
            custom_segments={"a": "1", "b": "2"},
        )
        assert ctx.render() == ctx.render()
