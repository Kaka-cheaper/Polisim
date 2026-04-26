"""`models/analysis_models.py` 的单元测试。

每个结构型至少覆盖：

1. 最小构造（必填字段 + 默认值）
2. JSON 往返（model_dump_json + model_validate_json）
3. ``extra="forbid"`` 拒绝未知字段
4. 约束字段的下界（ge=0、min_length=1 等）

本层**不**测业务逻辑——业务逻辑聚合规则在 `tests/test_analysis.py`。
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from models.analysis_models import (
    ActorStat,
    AnalysisResult,
    AttributeChange,
    EntityComparison,
    EnvironmentChange,
    KindStat,
    TickValuePoint,
    TrajectorySummary,
    TurningPoint,
)


# =============================================================================
# KindStat / ActorStat 计数原子
# =============================================================================


class TestKindStat:
    def test_minimal(self) -> None:
        stat = KindStat(kind="action_executed", count=5)
        assert stat.kind == "action_executed"
        assert stat.count == 5

    def test_round_trip(self) -> None:
        original = KindStat(kind="action_executed", count=5)
        decoded = KindStat.model_validate_json(original.model_dump_json())
        assert decoded == original

    def test_count_must_be_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            KindStat(kind="x", count=-1)

    def test_kind_cannot_be_empty(self) -> None:
        with pytest.raises(ValidationError):
            KindStat(kind="", count=0)

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            KindStat(kind="x", count=0, extra_field="hi")  # type: ignore[call-arg]


class TestActorStat:
    def test_minimal(self) -> None:
        stat = ActorStat(
            actor_id="company_a", action_count=3, decision_rejected_count=0
        )
        assert stat.actor_id == "company_a"
        assert stat.action_count == 3

    def test_counts_must_be_non_negative(self) -> None:
        with pytest.raises(ValidationError):
            ActorStat(actor_id="x", action_count=-1, decision_rejected_count=0)
        with pytest.raises(ValidationError):
            ActorStat(actor_id="x", action_count=0, decision_rejected_count=-1)

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ActorStat(
                actor_id="x",
                action_count=0,
                decision_rejected_count=0,
                bonus=1,  # type: ignore[call-arg]
            )


# =============================================================================
# AttributeChange / TurningPoint
# =============================================================================


class TestAttributeChange:
    def test_minimal(self) -> None:
        ch = AttributeChange(attribute="cash", before=100, after=80)
        assert ch.before == 100
        assert ch.after == 80

    def test_before_can_be_none(self) -> None:
        """属性在初始快照中缺失时 before=None 合法。"""
        ch = AttributeChange(attribute="new_attr", after=42)
        assert ch.before is None

    def test_attribute_required(self) -> None:
        with pytest.raises(ValidationError):
            AttributeChange(attribute="", after=1)

    def test_round_trip_non_numeric(self) -> None:
        ch = AttributeChange(
            attribute="strategy", before="defensive", after="aggressive"
        )
        decoded = AttributeChange.model_validate_json(ch.model_dump_json())
        assert decoded == ch


class TestTurningPoint:
    def test_numeric(self) -> None:
        tp = TurningPoint(
            tick=3,
            actor_id="company_a",
            attribute="cash",
            before=100,
            after=80,
            delta=-20.0,
        )
        assert tp.delta == -20.0

    def test_non_numeric_delta_is_none(self) -> None:
        tp = TurningPoint(
            tick=3,
            actor_id="company_a",
            attribute="mood",
            before="neutral",
            after="angry",
        )
        assert tp.delta is None

    def test_tick_must_be_ge_one(self) -> None:
        """tick 0 不算转折点——是初始态。"""
        with pytest.raises(ValidationError):
            TurningPoint(
                tick=0, actor_id="x", attribute="y", before=0, after=1
            )

    def test_round_trip(self) -> None:
        original = TurningPoint(
            tick=5,
            actor_id="c",
            attribute="cash",
            before=100,
            after=50,
            delta=-50.0,
        )
        decoded = TurningPoint.model_validate_json(original.model_dump_json())
        assert decoded == original


# =============================================================================
# EnvironmentChange / TickValuePoint
# =============================================================================


class TestTickValuePoint:
    def test_tick_zero_allowed(self) -> None:
        p = TickValuePoint(tick=0, value=42)
        assert p.tick == 0

    def test_tick_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TickValuePoint(tick=-1, value=0)


class TestEnvironmentChange:
    def test_empty_values_allowed(self) -> None:
        """全程未变的变量也可以建——上层会给一个初始点即可。"""
        env = EnvironmentChange(variable="market_demand")
        assert env.values == []

    def test_round_trip(self) -> None:
        env = EnvironmentChange(
            variable="market_demand",
            values=[
                TickValuePoint(tick=0, value=100),
                TickValuePoint(tick=2, value=120),
                TickValuePoint(tick=5, value=90),
            ],
        )
        decoded = EnvironmentChange.model_validate_json(env.model_dump_json())
        assert decoded == env


# =============================================================================
# EntityComparison
# =============================================================================


class TestEntityComparison:
    def test_no_changes(self) -> None:
        comp = EntityComparison(
            entity_id="company_a",
            initial_attributes={"cash": 100},
            final_attributes={"cash": 100},
            changes=[],
        )
        assert comp.changes == []

    def test_with_changes(self) -> None:
        comp = EntityComparison(
            entity_id="company_a",
            initial_attributes={"cash": 100, "rep": 50},
            final_attributes={"cash": 60, "rep": 65},
            changes=[
                AttributeChange(attribute="cash", before=100, after=60),
                AttributeChange(attribute="rep", before=50, after=65),
            ],
        )
        assert len(comp.changes) == 2

    def test_round_trip(self) -> None:
        comp = EntityComparison(
            entity_id="x",
            initial_attributes={"a": 1},
            final_attributes={"a": 2},
            changes=[AttributeChange(attribute="a", before=1, after=2)],
        )
        decoded = EntityComparison.model_validate_json(comp.model_dump_json())
        assert decoded == comp


# =============================================================================
# TrajectorySummary
# =============================================================================


class TestTrajectorySummary:
    def test_minimal(self) -> None:
        s = TrajectorySummary(total_ticks=0, total_events=0)
        assert s.events_by_kind == []
        assert s.paused_ticks == []

    def test_total_ticks_cannot_be_negative(self) -> None:
        with pytest.raises(ValidationError):
            TrajectorySummary(total_ticks=-1, total_events=0)


# =============================================================================
# AnalysisResult 顶层
# =============================================================================


class TestAnalysisResult:
    def test_phase_a_minimal(self) -> None:
        """Phase A 的最小产物：所有 LLM 字段 None，summary 可空。"""
        res = AnalysisResult(
            run_id="20260424_abc",
            summary=TrajectorySummary(total_ticks=0, total_events=0),
        )
        assert res.version == "0.1"
        assert res.narrative_summary is None
        assert res.situation_judgement is None
        assert res.next_action_suggestions is None

    def test_version_locked(self) -> None:
        """version 是 Literal["0.1"]——不能写别的值。"""
        with pytest.raises(ValidationError):
            AnalysisResult(
                version="0.2",  # type: ignore[arg-type]
                run_id="x",
                summary=TrajectorySummary(total_ticks=0, total_events=0),
            )

    def test_llm_fields_accept_strings(self) -> None:
        """Phase C 增强字段：accept 字符串与列表。"""
        res = AnalysisResult(
            run_id="x",
            summary=TrajectorySummary(total_ticks=1, total_events=1),
            narrative_summary="company_a 保持稳定",
            situation_judgement="整体平衡",
            next_action_suggestions=["建议 1", "建议 2"],
        )
        assert res.narrative_summary == "company_a 保持稳定"
        assert len(res.next_action_suggestions or []) == 2

    def test_round_trip(self) -> None:
        original = AnalysisResult(
            run_id="20260424_abc",
            summary=TrajectorySummary(
                total_ticks=5,
                total_events=25,
                events_by_kind=[KindStat(kind="action_executed", count=10)],
            ),
            turning_points=[
                TurningPoint(
                    tick=3,
                    actor_id="x",
                    attribute="cash",
                    before=100,
                    after=80,
                    delta=-20.0,
                )
            ],
            entity_comparisons=[
                EntityComparison(
                    entity_id="x",
                    initial_attributes={"cash": 100},
                    final_attributes={"cash": 80},
                    changes=[
                        AttributeChange(
                            attribute="cash", before=100, after=80
                        )
                    ],
                )
            ],
            environment_trajectory=[
                EnvironmentChange(
                    variable="demand",
                    values=[TickValuePoint(tick=0, value=100)],
                )
            ],
            narrative_summary="概要",
        )
        decoded = AnalysisResult.model_validate_json(original.model_dump_json())
        assert decoded == original

    def test_run_id_cannot_be_empty(self) -> None:
        with pytest.raises(ValidationError):
            AnalysisResult(
                run_id="",
                summary=TrajectorySummary(total_ticks=0, total_events=0),
            )

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            AnalysisResult(
                run_id="x",
                summary=TrajectorySummary(total_ticks=0, total_events=0),
                extra_stuff=42,  # type: ignore[call-arg]
            )
