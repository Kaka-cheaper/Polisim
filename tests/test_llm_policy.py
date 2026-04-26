"""`core/llm_policy.py` 的直接单测（Phase B.1 重构后）。

三组公开 API：

1. `build_prompt(world, scenario, state, entity_id, tick) -> str`
2. `parse_response(raw, allowed_actions) -> dict`
3. `decide(provider, world, scenario, state, entity_id, tick, *, config) -> ActionProposal`

策略：用 walkthrough 的 world + scenario 做 fixture；用 `MockProvider` 的
fixed/scripted 两种模式覆盖 decide 的各种路径。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core import llm_policy
from core.definition_loader import load_world_definition
from core.errors import LLMProtocolError, ProviderError
from core.providers.base import LLMProvider
from core.providers.mock import MockProvider
from core.scenario_loader import load_scenario
from models.config_models import RuntimeConfig
from models.runtime_models import (
    ActionProposal,
    EntityRuntimeState,
    MessageEnvelope,
    WorldState,
)
from models.scenario_models import Scenario
from models.world_models import WorldDefinition


# =============================================================================
# Fixtures
# =============================================================================


WALKTHROUGH = Path(__file__).resolve().parent.parent / "scenarios" / "minimal_market"


@pytest.fixture
def world() -> WorldDefinition:
    return load_world_definition(WALKTHROUGH / "world.yaml")


@pytest.fixture
def scenario(world: WorldDefinition) -> Scenario:
    return load_scenario(WALKTHROUGH / "scenario.yaml", world)


@pytest.fixture
def initial_state(world: WorldDefinition, scenario: Scenario) -> WorldState:
    """构造一个最小的 tick=0 初态，company_a 和 regulator_main 各一份。"""
    entities: dict[str, EntityRuntimeState] = {}
    for inst in scenario.entities:
        type_schema = world.entity_types[inst.type]
        merged: dict = {
            name: attr.default for name, attr in type_schema.attributes.items()
        }
        merged.update(inst.attributes)
        entities[inst.id] = EntityRuntimeState(
            id=inst.id, type=inst.type, attributes=merged
        )
    return WorldState(tick=0, entities=entities, mailboxes={})


@pytest.fixture
def runtime_config() -> RuntimeConfig:
    return RuntimeConfig(version="0.1")


# =============================================================================
# 1. build_prompt
# =============================================================================


def _extract_payload(raw: str) -> dict:
    """从 build_prompt 返回值里抽取 JSON payload 部分。

    build_prompt 的格式约定（session 19 Phase B 末 + 多语言支持）：
    ``<json_payload>\\n\\n<language_instruction>``
    测试只需校验 payload 结构时，用本 helper 抽取前缀 JSON。
    """
    head = raw.split("\n\n", 1)[0]
    return json.loads(head)


class TestBuildPrompt:
    def test_returns_valid_json_payload(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        raw = llm_policy.build_prompt(
            world, scenario, initial_state, "company_a", tick=1
        )
        data = _extract_payload(raw)
        assert isinstance(data, dict)

    def test_includes_core_sections(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        raw = llm_policy.build_prompt(
            world, scenario, initial_state, "company_a", tick=1
        )
        data = _extract_payload(raw)
        assert data["tick"] == 1
        assert data["remaining_ticks"] == scenario.config.total_ticks - 1
        assert data["actor"]["id"] == "company_a"
        assert data["actor"]["type"] == "Company"
        assert "attributes" in data["actor"]
        assert "inbox" in data
        assert "environment" in data
        assert "available_actions" in data

    def test_available_actions_match_type_schema(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        raw = llm_policy.build_prompt(
            world, scenario, initial_state, "company_a", tick=1
        )
        data = _extract_payload(raw)
        names = [a["name"] for a in data["available_actions"]]
        assert set(names) == {"promote", "do_nothing"}

    def test_inbox_renders_messages(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        msg = MessageEnvelope(
            tick_emitted=1,
            tick_delivered=2,
            message_type="policy_signal",
            from_actor=None,
            payload={"pressure": "high"},
        )
        initial_state.mailboxes["company_a"] = [msg]
        raw = llm_policy.build_prompt(
            world, scenario, initial_state, "company_a", tick=2
        )
        data = _extract_payload(raw)
        assert len(data["inbox"]) == 1
        assert data["inbox"][0]["message_type"] == "policy_signal"

    def test_missing_entity_raises_keyerror(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        with pytest.raises(KeyError):
            llm_policy.build_prompt(
                world, scenario, initial_state, "nonexistent", tick=1
            )

    # --- 多语言支持（session 19 追加） --------------------------------------

    def test_default_language_is_zh_cn(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        """默认参数：language 不传时 prompt 尾部应含 'zh-CN' 指令。"""
        raw = llm_policy.build_prompt(
            world, scenario, initial_state, "company_a", tick=1
        )
        # payload 后面应有语言指令段
        assert "\n\n" in raw
        tail = raw.split("\n\n", 1)[1]
        assert "zh-CN" in tail
        assert "reason" in tail.lower()

    def test_custom_language_injected(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        """传 language='en' 时 prompt 尾部应含 'en' 而非 'zh-CN'。"""
        raw = llm_policy.build_prompt(
            world, scenario, initial_state, "company_a", tick=1, language="en"
        )
        tail = raw.split("\n\n", 1)[1]
        assert "en" in tail
        assert "zh-CN" not in tail

    def test_language_does_not_affect_payload(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        """不同 language 下 payload JSON 结构必须完全一致——只影响尾部指令。"""
        raw_zh = llm_policy.build_prompt(
            world, scenario, initial_state, "company_a", tick=1, language="zh-CN"
        )
        raw_en = llm_policy.build_prompt(
            world, scenario, initial_state, "company_a", tick=1, language="en"
        )
        assert _extract_payload(raw_zh) == _extract_payload(raw_en)


# =============================================================================
# 2. parse_response
# =============================================================================


class TestParseResponse:
    def test_valid_minimum(self) -> None:
        raw = json.dumps({"action": "promote", "params": {"budget": 20}})
        parsed = llm_policy.parse_response(raw, ["promote", "do_nothing"])
        assert parsed["action"] == "promote"
        assert parsed["params"] == {"budget": 20}
        assert parsed["reason"] is None

    def test_reason_string_preserved(self) -> None:
        raw = json.dumps(
            {"action": "promote", "params": {}, "reason": "boost cash"}
        )
        parsed = llm_policy.parse_response(raw, ["promote"])
        assert parsed["reason"] == "boost cash"

    def test_reason_non_string_dropped(self) -> None:
        """reason 非 str 时降级为 None——不抛错。"""
        raw = json.dumps({"action": "promote", "params": {}, "reason": 42})
        parsed = llm_policy.parse_response(raw, ["promote"])
        assert parsed["reason"] is None

    def test_params_null_becomes_empty_dict(self) -> None:
        """params=null 时归 0 为空 dict（宽容降级）。"""
        raw = json.dumps({"action": "promote", "params": None})
        parsed = llm_policy.parse_response(raw, ["promote"])
        assert parsed["params"] == {}

    def test_params_missing_becomes_empty_dict(self) -> None:
        raw = json.dumps({"action": "promote"})
        parsed = llm_policy.parse_response(raw, ["promote"])
        assert parsed["params"] == {}

    def test_params_list_becomes_empty_dict(self) -> None:
        """params 类型非法时宽容降级。"""
        raw = json.dumps({"action": "promote", "params": [1, 2]})
        parsed = llm_policy.parse_response(raw, ["promote"])
        assert parsed["params"] == {}

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(LLMProtocolError, match="合法 JSON"):
            llm_policy.parse_response("{not json}", ["promote"])

    def test_top_level_array_raises(self) -> None:
        with pytest.raises(LLMProtocolError, match="object"):
            llm_policy.parse_response("[1,2,3]", ["promote"])

    def test_action_missing_raises(self) -> None:
        with pytest.raises(LLMProtocolError, match="action"):
            llm_policy.parse_response('{"params": {}}', ["promote"])

    def test_action_not_string_raises(self) -> None:
        with pytest.raises(LLMProtocolError, match="action"):
            llm_policy.parse_response('{"action": 42}', ["promote"])

    def test_action_not_in_whitelist_raises(self) -> None:
        raw = json.dumps({"action": "explode", "params": {}})
        with pytest.raises(LLMProtocolError, match="explode"):
            llm_policy.parse_response(raw, ["promote", "do_nothing"])

    def test_non_string_input_raises(self) -> None:
        """provider 违约回了 non-str。应被协议错捕获而不是 TypeError 逃逸。"""
        with pytest.raises(LLMProtocolError, match="str"):
            llm_policy.parse_response(
                123,  # type: ignore[arg-type]
                ["promote"],
            )


# =============================================================================
# 3. decide —— 完整编排
# =============================================================================


class TestDecide:
    def test_happy_path(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
        runtime_config: RuntimeConfig,
    ) -> None:
        provider = MockProvider(
            fixed_response=json.dumps(
                {"action": "promote", "params": {"budget": 30}, "reason": "x"}
            )
        )
        proposal = llm_policy.decide(
            provider,
            world,
            scenario,
            initial_state,
            "company_a",
            tick=1,
            config=runtime_config,
        )
        assert isinstance(proposal, ActionProposal)
        assert proposal.action_type == "promote"
        assert proposal.params == {"budget": 30}
        assert proposal.decision_mode == "llm"
        assert proposal.status == "proposed"
        assert proposal.raw_reasoning_summary == "x"

    def test_provider_error_propagates(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
        runtime_config: RuntimeConfig,
    ) -> None:
        """ProviderError 原样上抛（不由 decide 降级）。"""

        class FailingProvider(LLMProvider):
            def generate(self, prompt: str, **kwargs):  # type: ignore[override]
                raise ProviderError("network dead")

        with pytest.raises(ProviderError, match="network dead"):
            llm_policy.decide(
                FailingProvider(),
                world,
                scenario,
                initial_state,
                "company_a",
                tick=1,
                config=runtime_config,
            )

    def test_invalid_action_raises_protocol_error(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
        runtime_config: RuntimeConfig,
    ) -> None:
        provider = MockProvider(
            fixed_response=json.dumps(
                {"action": "nonexistent_action", "params": {}}
            )
        )
        with pytest.raises(LLMProtocolError, match="nonexistent_action"):
            llm_policy.decide(
                provider,
                world,
                scenario,
                initial_state,
                "company_a",
                tick=1,
                config=runtime_config,
            )

    def test_unparseable_output_raises_protocol_error(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
        runtime_config: RuntimeConfig,
    ) -> None:
        provider = MockProvider(fixed_response="not valid json")
        with pytest.raises(LLMProtocolError, match="合法 JSON"):
            llm_policy.decide(
                provider,
                world,
                scenario,
                initial_state,
                "company_a",
                tick=1,
                config=runtime_config,
            )

    def test_passes_timeout_to_provider(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        """RuntimeConfig.llm_request_timeout_sec 要透传到 provider.generate kwargs。"""
        captured: dict = {}

        class TracingProvider(LLMProvider):
            def generate(self, prompt: str, **kwargs):  # type: ignore[override]
                captured.update(kwargs)
                return json.dumps({"action": "do_nothing", "params": {}})

        config = RuntimeConfig(version="0.1", llm_request_timeout_sec=15.0)
        llm_policy.decide(
            TracingProvider(),
            world,
            scenario,
            initial_state,
            "company_a",
            tick=1,
            config=config,
        )
        assert captured["timeout"] == 15.0
        assert "temperature" in captured
        assert "max_tokens" in captured

    def test_passes_output_language_to_prompt(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        """RuntimeConfig.output_language 必须注入到 prompt 尾部（多语言链路闭合）。"""
        captured_prompts: list[str] = []

        class PromptCapturingProvider(LLMProvider):
            def generate(self, prompt: str, **kwargs):  # type: ignore[override]
                captured_prompts.append(prompt)
                return json.dumps({"action": "do_nothing", "params": {}})

        config = RuntimeConfig(version="0.1", output_language="fr-FR")
        llm_policy.decide(
            PromptCapturingProvider(),
            world,
            scenario,
            initial_state,
            "company_a",
            tick=1,
            config=config,
        )
        assert len(captured_prompts) == 1
        assert "fr-FR" in captured_prompts[0]
        # 默认语言必须**不**出现——防止有两条指令互相冲突
        assert "zh-CN" not in captured_prompts[0]
