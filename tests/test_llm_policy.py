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

    # --- D-014 扩充字段在 prompt payload 中的渲染 ---

    def test_available_actions_includes_d014_param_fields(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        """D-014：build_prompt 让 available_actions 输出完整 ParamSchema 字段。

        构造法：替换已加载 world 的 promote.budget 为含 D-014 字段的新版本，
        再调 build_prompt，断言 payload['available_actions'] 含 description /
        default / min / max 等字段。
        """
        from models.world_models import ActionParamSchema

        world.action_types["promote"].params["budget"] = ActionParamSchema(
            type="number",
            required=True,
            description="推广预算（货币单位）",
            default=50.0,
            min=10.0,
            max=1000.0,
        )

        raw = llm_policy.build_prompt(
            world, scenario, initial_state, "company_a", tick=1
        )
        data = _extract_payload(raw)

        promote_entry = next(
            a for a in data["available_actions"] if a["name"] == "promote"
        )
        budget_payload = promote_entry["params"]["budget"]
        assert budget_payload["type"] == "number"
        assert budget_payload["required"] is True
        assert budget_payload["description"] == "推广预算（货币单位）"
        assert budget_payload["default"] == 50.0
        assert budget_payload["min"] == 10.0
        assert budget_payload["max"] == 1000.0

    def test_available_actions_omits_none_d014_fields(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        """D-014：未声明的字段（None）不应出现在 payload——保持 prompt 简洁。

        构造法：替换 budget 为无 D-014 字段的极简版本（所有可选字段 None），
        断言 payload 不含 description / default / min / max / values 等键。
        """
        from models.world_models import ActionParamSchema

        world.action_types["promote"].params["budget"] = ActionParamSchema(
            type="number",
            required=True,
            # 其他 6 个 D-014 字段全部走默认 None
        )

        raw = llm_policy.build_prompt(
            world, scenario, initial_state, "company_a", tick=1
        )
        data = _extract_payload(raw)
        promote_entry = next(
            a for a in data["available_actions"] if a["name"] == "promote"
        )
        budget_payload = promote_entry["params"]["budget"]
        # 必有字段
        assert "type" in budget_payload
        assert "required" in budget_payload
        # 未声明字段应被过滤
        for omitted in ("description", "default", "min", "max", "values", "entity_type_filter"):
            assert omitted not in budget_payload, f"{omitted} 不应出现在 payload"

    def test_action_description_in_payload_when_provided(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        """D-014：action_types[name].description 应进入 available_actions 条目。"""
        from models.world_models import ActionTypeSchema

        original = world.action_types["promote"]
        world.action_types["promote"] = ActionTypeSchema(
            description="推广产品提升声誉",
            actor_types=original.actor_types,
            params=original.params,
            effects=original.effects,
        )

        raw = llm_policy.build_prompt(
            world, scenario, initial_state, "company_a", tick=1
        )
        data = _extract_payload(raw)
        promote_entry = next(
            a for a in data["available_actions"] if a["name"] == "promote"
        )
        assert promote_entry.get("description") == "推广产品提升声誉"


# =============================================================================
# 1.5 build_prompt_context（D-016 第 2 步——新增结构化入口）
# =============================================================================


class TestBuildPromptContext:
    """D-016 重构后 ``build_prompt`` 是 ``build_prompt_context + render`` 的薄壳。

    本组测试验证：

    1. ``build_prompt_context`` 返 PromptContext 实例
    2. **字节级等价**——``build_prompt(...) == build_prompt_context(...).render()``
       （向后兼容回归基线，OpenAI smoke / 现有 mock provider 无感）
    3. 结构字段对齐 D-016 spec 第 2.1 节
    """

    def test_returns_prompt_context(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        """build_prompt_context 返 PromptContext 类实例。"""
        from models.llm_models import PromptContext

        ctx = llm_policy.build_prompt_context(
            world, scenario, initial_state, "company_a", tick=1
        )
        assert isinstance(ctx, PromptContext)

    def test_byte_equivalent_to_legacy_build_prompt(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        """**关键回归**：build_prompt 输出 == build_prompt_context().render()
        字节级等价——D-016 第 2 步对 LLMProvider.generate 完全无感的硬证据。"""
        prompt_str = llm_policy.build_prompt(
            world, scenario, initial_state, "company_a", tick=1
        )
        ctx = llm_policy.build_prompt_context(
            world, scenario, initial_state, "company_a", tick=1
        )
        assert prompt_str == ctx.render()

    def test_byte_equivalent_with_custom_language(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        """language 参数透传——非默认语言下仍字节级等价。"""
        prompt_str = llm_policy.build_prompt(
            world, scenario, initial_state, "company_a", tick=1, language="en"
        )
        ctx = llm_policy.build_prompt_context(
            world, scenario, initial_state, "company_a", tick=1, language="en"
        )
        assert prompt_str == ctx.render()
        assert ctx.language_hint == "en"

    def test_actor_view_contains_minimal_fields(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        """D-016 第 1-2 步：actor_view 仅含 id / type / attributes（与 D-014 时代等价）。
        第 3-4 步会补 relations / recent_decisions——届时本测试需更新。"""
        ctx = llm_policy.build_prompt_context(
            world, scenario, initial_state, "company_a", tick=1
        )
        assert ctx.actor_view["id"] == "company_a"
        assert ctx.actor_view["type"] == "Company"
        assert "attributes" in ctx.actor_view
        # D-016 第 1-2 步暂不含 relations / recent_decisions
        assert "relations" not in ctx.actor_view
        assert "recent_decisions" not in ctx.actor_view

    def test_perception_contains_time_inbox_environment(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        """perception 含时间维度 + 收件箱 + 环境变量。"""
        ctx = llm_policy.build_prompt_context(
            world, scenario, initial_state, "company_a", tick=2
        )
        assert ctx.perception["tick"] == 2
        assert ctx.perception["remaining_ticks"] == scenario.config.total_ticks - 2
        assert "inbox" in ctx.perception
        assert "environment" in ctx.perception

    def test_default_system_role_and_custom_segments_empty(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        """D-016 第 1-2 步基线：不传 rules 时 system_role / custom_segments 留默认值。"""
        ctx = llm_policy.build_prompt_context(
            world, scenario, initial_state, "company_a", tick=1
        )
        assert ctx.system_role is None
        assert ctx.custom_segments == {}


# =============================================================================
# 1.6 D-016 第 3-5 步：relations / recent_decisions / enrich_prompt
# =============================================================================


class TestActorViewRelations:
    """D-016 第 3 步：actor_view.relations 抽取（outgoing/incoming）。"""

    def test_extract_actor_relations_empty_when_no_relations(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        """actor 不涉及任何关系时——actor_view 不含 'relations' 键（保字节级等价）。"""
        ctx = llm_policy.build_prompt_context(
            world, scenario, initial_state, "company_a", tick=1
        )
        assert "relations" not in ctx.actor_view

    def test_relations_outgoing_uses_to_key(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        """outgoing 关系按 D-016 spec 用 'to' 键标识对端。"""
        from models.runtime_models import RelationRuntimeState

        # 注入一条 company_a → regulator_main 的关系
        initial_state.relations.append(
            RelationRuntimeState(
                type="oversees",
                source="regulator_main",
                target="company_a",
                value=0.5,
            )
        )
        initial_state.relations.append(
            RelationRuntimeState(
                type="trusts",
                source="company_a",
                target="regulator_main",
                value=0.7,
            )
        )
        ctx = llm_policy.build_prompt_context(
            world, scenario, initial_state, "company_a", tick=1
        )
        assert "relations" in ctx.actor_view
        rels = ctx.actor_view["relations"]
        # outgoing：source==company_a 的 trusts 关系
        assert len(rels["outgoing"]) == 1
        assert rels["outgoing"][0] == {
            "type": "trusts",
            "to": "regulator_main",
            "value": 0.7,
        }
        # incoming：target==company_a 的 oversees 关系
        assert len(rels["incoming"]) == 1
        assert rels["incoming"][0] == {
            "type": "oversees",
            "from": "regulator_main",
            "value": 0.5,
        }


class TestActorViewRecentDecisions:
    """D-016 第 4 步：actor_view.recent_decisions 从 EventLog 抽取最近 N 条。"""

    def test_no_event_log_means_no_recent_decisions(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        """不传 event_log → actor_view 不含 'recent_decisions'（保字节级等价）。"""
        ctx = llm_policy.build_prompt_context(
            world, scenario, initial_state, "company_a", tick=2
        )
        assert "recent_decisions" not in ctx.actor_view

    def test_history_size_zero_means_no_recent_decisions(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        """history_size=0 → 不抽取（即使提供了 event_log）。"""
        from core.events import EventLog
        from models.config_models import StorageConfig

        log = EventLog("test_run", StorageConfig(version="0.1", persist=False))
        ctx = llm_policy.build_prompt_context(
            world,
            scenario,
            initial_state,
            "company_a",
            tick=2,
            event_log=log,
            history_size=0,
        )
        assert "recent_decisions" not in ctx.actor_view

    def test_recent_decisions_extracted_descending(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        """recent_decisions 按 tick 降序——最新在最前。"""
        from core.events import EventLog
        from models.config_models import StorageConfig
        from models.runtime_models import EventRecord

        log = EventLog("test_run2", StorageConfig(version="0.1", persist=False))
        # 写两条 decision_proposed（tick=1, tick=2）
        for t in (1, 2):
            log.append(
                EventRecord(
                    event_id=f"evt_{t:06d}",
                    tick=t,
                    kind="decision_proposed",
                    actor_id="company_a",
                    payload={
                        "action_type": "promote",
                        "params": {"budget": 10 * t},
                        "decision_mode": "llm",
                    },
                )
            )
        ctx = llm_policy.build_prompt_context(
            world,
            scenario,
            initial_state,
            "company_a",
            tick=3,
            event_log=log,
            history_size=3,
        )
        recent = ctx.actor_view["recent_decisions"]
        assert len(recent) == 2
        # 最新（tick=2）在前
        assert recent[0]["tick"] == 2
        assert recent[0]["action"] == "promote"
        assert recent[0]["params"] == {"budget": 20}
        assert recent[1]["tick"] == 1
        assert recent[1]["params"] == {"budget": 10}

    def test_recent_decisions_filters_by_actor(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        """只抽 entity_id 自己的决策——不掺杂其他 actor。"""
        from core.events import EventLog
        from models.config_models import StorageConfig
        from models.runtime_models import EventRecord

        log = EventLog("test_run3", StorageConfig(version="0.1", persist=False))
        log.append(
            EventRecord(
                event_id="evt_000001",
                tick=1,
                kind="decision_proposed",
                actor_id="company_a",
                payload={"action_type": "promote", "params": {}, "decision_mode": "llm"},
            )
        )
        log.append(
            EventRecord(
                event_id="evt_000002",
                tick=1,
                kind="decision_proposed",
                actor_id="regulator_main",  # 别人
                payload={"action_type": "do_nothing", "params": {}, "decision_mode": "rule"},
            )
        )
        ctx = llm_policy.build_prompt_context(
            world,
            scenario,
            initial_state,
            "company_a",
            tick=2,
            event_log=log,
            history_size=5,
        )
        recent = ctx.actor_view["recent_decisions"]
        assert len(recent) == 1
        assert recent[0]["action"] == "promote"


class TestEnrichPromptHook:
    """D-016 第 5 步：rules.enrich_prompt 钩子被调用 + 注入 custom_segments。"""

    def test_default_base_rules_enrich_is_noop(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        """BaseRules 默认 enrich_prompt 不动 ctx——返回原 ctx。"""
        from models.llm_models import PromptContext
        from rules.base import BaseRules

        class DummyRules(BaseRules):
            def resolve_effects(self, world, state, proposal):
                return []

        rules = DummyRules()
        ctx_before = llm_policy.build_prompt_context(
            world, scenario, initial_state, "company_a", tick=1
        )
        ctx_after = llm_policy.build_prompt_context(
            world, scenario, initial_state, "company_a", tick=1, rules=rules
        )
        # 默认 no-op：两份 ctx 字段等价
        assert ctx_after.system_role == ctx_before.system_role
        assert ctx_after.custom_segments == ctx_before.custom_segments
        assert isinstance(ctx_after, PromptContext)

    def test_minimal_market_rules_inject_objective(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        """MinimalMarketRules.enrich_prompt 给 Company 注入 objective + constraint。"""
        from rules.minimal_market import MinimalMarketRules

        rules = MinimalMarketRules()
        ctx = llm_policy.build_prompt_context(
            world, scenario, initial_state, "company_a", tick=1, rules=rules
        )
        assert ctx.system_role is not None
        assert "Company" in ctx.system_role
        assert "objective" in ctx.custom_segments
        assert "constraint" in ctx.custom_segments

    def test_enrich_prompt_skips_non_target_entity(
        self,
        world: WorldDefinition,
        scenario: Scenario,
        initial_state: WorldState,
    ) -> None:
        """MinimalMarketRules.enrich_prompt 对非 Company（如 Regulator）不注入——
        ctx 保持基础形态（system_role=None, custom_segments={}）。"""
        from rules.minimal_market import MinimalMarketRules

        rules = MinimalMarketRules()
        ctx = llm_policy.build_prompt_context(
            world,
            scenario,
            initial_state,
            "regulator_main",
            tick=1,
            rules=rules,
        )
        assert ctx.system_role is None
        assert ctx.custom_segments == {}


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
        # D-016 第 6 步：decide 返 LLMDecisionResult
        result = llm_policy.decide(
            provider,
            world,
            scenario,
            initial_state,
            "company_a",
            tick=1,
            config=runtime_config,
        )
        from models.llm_models import LLMDecisionResult, PromptContext

        assert isinstance(result, LLMDecisionResult)
        proposal = result.proposal
        assert isinstance(proposal, ActionProposal)
        assert proposal.action_type == "promote"
        assert proposal.params == {"budget": 30}
        assert proposal.decision_mode == "llm"
        assert proposal.status == "proposed"
        assert proposal.raw_reasoning_summary == "x"
        # prompt_context 伴随返回，供 Runtime 塑进 EventLog
        assert isinstance(result.prompt_context, PromptContext)

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
