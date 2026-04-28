"""`core/analysis.py` 的单元 + 集成测试。

测试分组：

1. I/O: ``_load_events_from_file`` / ``_load_snapshots_from_dir``
2. 聚合子步骤: ``_summarize_events`` / ``_find_turning_points`` /
   ``_trace_environment`` / ``_compare_entities``
3. 公开入口: ``analyze_run`` / ``render_markdown`` / ``render_json`` /
   ``write_analysis``
4. 端到端: 用 Runtime 跑出 walkthrough 产物，再跑分析层对比

大部分测试直接手工构造事件与快照，不走 Runtime——快且不依赖其他层。
端到端测试用 MockProvider scripted 响应驱动 company_a 的 promote，让
turning_points 能真正出结果。
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from core.analysis import (
    _build_analysis_prompt,
    _compare_entities,
    _find_turning_points,
    _load_events_from_file,
    _load_snapshots_from_dir,
    _parse_analysis_response,
    _summarize_events,
    _trace_environment,
    analyze_run,
    enhance_with_llm,
    render_json,
    render_markdown,
    write_analysis,
)
from core.definition_loader import load_world_definition
from core.errors import LLMProtocolError, ProviderError
from core.providers.base import LLMProvider
from core.providers.mock import MockProvider
from core.scenario_loader import load_scenario
from models.analysis_models import (
    AnalysisResult,
    AttributeChange,
    EntityComparison,
    TickValuePoint,
    TrajectorySummary,
)
from models.config_models import RuntimeConfig
from models.runtime_models import EventRecord, MessageSummary, Snapshot
from models.scenario_models import Scenario
from models.world_models import WorldDefinition


# =============================================================================
# Fixtures
# =============================================================================


def _make_event(
    *,
    event_id: str = "e1",
    tick: int = 1,
    kind: str = "action_executed",
    actor_id: str | None = None,
    payload: dict | None = None,
) -> EventRecord:
    """构造 EventRecord 的紧凑工厂。"""
    return EventRecord(
        event_id=event_id,
        tick=tick,
        kind=kind,  # type: ignore[arg-type]
        actor_id=actor_id,
        payload=payload or {},
    )


def _make_snapshot(
    tick: int,
    entities: dict[str, dict] | None = None,
    environment: dict | None = None,
) -> Snapshot:
    return Snapshot(
        tick=tick,
        entity_state_summary=entities or {},
        relation_state_summary=[],
        environment_state=environment or {},
        message_summary=MessageSummary(),
    )


@pytest.fixture
def events_file(tmp_path: Path) -> Path:
    """写一份 3 条事件的 events.jsonl 到临时目录。"""
    path = tmp_path / "events.jsonl"
    events = [
        _make_event(event_id="e1", tick=1, kind="decision_proposed", actor_id="a"),
        _make_event(event_id="e2", tick=1, kind="action_executed", actor_id="a"),
        _make_event(event_id="e3", tick=2, kind="action_executed", actor_id="b"),
    ]
    path.write_text(
        "\n".join(ev.model_dump_json() for ev in events) + "\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def snapshots_dir(tmp_path: Path) -> Path:
    """写两份快照到临时 snapshots/ 目录。"""
    sdir = tmp_path / "snapshots"
    sdir.mkdir()
    s0 = _make_snapshot(0, entities={"a": {"cash": 100}}, environment={"demand": 50})
    s1 = _make_snapshot(1, entities={"a": {"cash": 80}}, environment={"demand": 60})
    (sdir / "tick_0.json").write_text(s0.model_dump_json(indent=2), encoding="utf-8")
    (sdir / "tick_1.json").write_text(s1.model_dump_json(indent=2), encoding="utf-8")
    return sdir


# =============================================================================
# 1. I/O
# =============================================================================


class TestLoadEventsFromFile:
    def test_happy_path(self, events_file: Path) -> None:
        events = _load_events_from_file(events_file)
        assert len(events) == 3
        assert events[0].event_id == "e1"

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            _load_events_from_file(tmp_path / "nonexistent.jsonl")

    def test_blank_lines_ignored(self, tmp_path: Path) -> None:
        path = tmp_path / "with_blanks.jsonl"
        ev = _make_event()
        path.write_text(
            f"\n{ev.model_dump_json()}\n\n", encoding="utf-8"
        )
        assert len(_load_events_from_file(path)) == 1

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.jsonl"
        path.write_text("{not json}\n", encoding="utf-8")
        with pytest.raises(ValueError, match="bad.jsonl:1"):
            _load_events_from_file(path)

    def test_invalid_schema_raises(self, tmp_path: Path) -> None:
        """合法 JSON 但字段不合 EventRecord schema。"""
        path = tmp_path / "bad_schema.jsonl"
        path.write_text('{"event_id": "x"}\n', encoding="utf-8")  # 缺 tick/kind
        with pytest.raises(ValueError):
            _load_events_from_file(path)


class TestLoadSnapshotsFromDir:
    def test_happy_path(self, snapshots_dir: Path) -> None:
        snaps = _load_snapshots_from_dir(snapshots_dir)
        assert set(snaps) == {0, 1}
        assert snaps[0].entity_state_summary["a"]["cash"] == 100

    def test_missing_dir(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            _load_snapshots_from_dir(tmp_path / "nonexistent")

    def test_empty_dir_returns_empty(self, tmp_path: Path) -> None:
        sdir = tmp_path / "empty_snaps"
        sdir.mkdir()
        assert _load_snapshots_from_dir(sdir) == {}

    def test_non_matching_files_ignored(self, tmp_path: Path) -> None:
        """只读 tick_*.json，其他文件名静默忽略。"""
        sdir = tmp_path / "mixed"
        sdir.mkdir()
        (sdir / "tick_5.json").write_text(
            _make_snapshot(5).model_dump_json(), encoding="utf-8"
        )
        (sdir / "README.txt").write_text("ignored", encoding="utf-8")
        snaps = _load_snapshots_from_dir(sdir)
        assert set(snaps) == {5}


# =============================================================================
# 2. 聚合子步骤
# =============================================================================


class TestSummarizeEvents:
    def test_empty(self) -> None:
        s = _summarize_events([])
        assert s.total_ticks == 0
        assert s.total_events == 0
        assert s.events_by_kind == []

    def test_kind_aggregation(self) -> None:
        events = [
            _make_event(event_id="1", tick=1, kind="action_executed", actor_id="a"),
            _make_event(event_id="2", tick=1, kind="action_executed", actor_id="b"),
            _make_event(event_id="3", tick=2, kind="message_emitted"),
        ]
        s = _summarize_events(events)
        assert s.total_events == 3
        assert s.total_ticks == 2
        by_kind = {k.kind: k.count for k in s.events_by_kind}
        assert by_kind == {"action_executed": 2, "message_emitted": 1}

    def test_actor_aggregation_counts_only_business_events(self) -> None:
        """decision_proposed 不计入 actor 统计（信噪比低）。"""
        events = [
            _make_event(
                event_id="1", tick=1, kind="decision_proposed", actor_id="a"
            ),
            _make_event(
                event_id="2", tick=1, kind="action_executed", actor_id="a"
            ),
            _make_event(
                event_id="3", tick=1, kind="decision_rejected", actor_id="b"
            ),
        ]
        s = _summarize_events(events)
        by_actor = {a.actor_id: a for a in s.events_by_actor}
        assert by_actor["a"].action_count == 1
        assert by_actor["a"].decision_rejected_count == 0
        assert by_actor["b"].action_count == 0
        assert by_actor["b"].decision_rejected_count == 1

    def test_breakpoints_collected(self) -> None:
        events = [
            _make_event(
                event_id="1",
                tick=3,
                kind="breakpoint_triggered",
                payload={"breakpoint_id": "low_cash"},
            ),
            _make_event(
                event_id="2",
                tick=5,
                kind="breakpoint_triggered",
                payload={"breakpoint_id": "high_rep"},
            ),
        ]
        s = _summarize_events(events)
        assert s.paused_ticks == [3, 5]
        assert s.breakpoints_triggered == ["low_cash", "high_rep"]


class TestFindTurningPoints:
    def test_empty_snapshots(self) -> None:
        assert _find_turning_points({}) == []

    def test_single_snapshot(self) -> None:
        assert _find_turning_points({0: _make_snapshot(0)}) == []

    def test_no_changes(self) -> None:
        snaps = {
            0: _make_snapshot(0, entities={"a": {"cash": 100}}),
            1: _make_snapshot(1, entities={"a": {"cash": 100}}),
        }
        assert _find_turning_points(snaps) == []

    def test_orders_by_abs_delta_desc(self) -> None:
        snaps = {
            0: _make_snapshot(0, entities={"a": {"cash": 100, "rep": 50}}),
            1: _make_snapshot(1, entities={"a": {"cash": 95, "rep": 80}}),
            2: _make_snapshot(2, entities={"a": {"cash": 40, "rep": 82}}),
        }
        tps = _find_turning_points(snaps)
        # cash 变化最大：100→95 (-5), 95→40 (-55)；rep 变化：50→80 (+30), 80→82 (+2)
        assert tps[0].attribute == "cash"
        assert tps[0].tick == 2
        assert tps[0].delta == -55.0
        assert tps[1].attribute == "rep"
        assert tps[1].delta == 30.0

    def test_top_k_cutoff(self) -> None:
        """超过 top_k=5 的候选只保留前 5。"""
        entities_by_tick = {}
        for i in range(7):
            entities_by_tick[i] = _make_snapshot(
                i, entities={"a": {"v": i * 10}}
            )
        tps = _find_turning_points(entities_by_tick, top_k=3)
        assert len(tps) == 3

    def test_non_numeric_delta_is_none(self) -> None:
        snaps = {
            0: _make_snapshot(0, entities={"a": {"mood": "neutral"}}),
            1: _make_snapshot(1, entities={"a": {"mood": "angry"}}),
        }
        tps = _find_turning_points(snaps)
        assert len(tps) == 1
        assert tps[0].delta is None


class TestTraceEnvironment:
    def test_empty(self) -> None:
        assert _trace_environment({}) == []

    def test_single_variable_no_change(self) -> None:
        snaps = {
            0: _make_snapshot(0, environment={"demand": 100}),
            1: _make_snapshot(1, environment={"demand": 100}),
            2: _make_snapshot(2, environment={"demand": 100}),
        }
        traj = _trace_environment(snaps)
        assert len(traj) == 1
        # 初始点保留，后续未变化
        assert traj[0].values == [TickValuePoint(tick=0, value=100)]

    def test_variable_changes_mid_run(self) -> None:
        snaps = {
            0: _make_snapshot(0, environment={"demand": 100}),
            1: _make_snapshot(1, environment={"demand": 100}),
            2: _make_snapshot(2, environment={"demand": 150}),
            3: _make_snapshot(3, environment={"demand": 150}),
            4: _make_snapshot(4, environment={"demand": 120}),
        }
        traj = _trace_environment(snaps)
        assert len(traj) == 1
        assert traj[0].variable == "demand"
        # 初始 + 2 次变化 = 3 个点
        values = [(p.tick, p.value) for p in traj[0].values]
        assert values == [(0, 100), (2, 150), (4, 120)]


class TestCompareEntities:
    def test_empty(self) -> None:
        assert _compare_entities({}) == []

    def test_no_changes(self) -> None:
        snaps = {
            0: _make_snapshot(0, entities={"a": {"cash": 100}}),
            1: _make_snapshot(1, entities={"a": {"cash": 100}}),
        }
        comps = _compare_entities(snaps)
        assert len(comps) == 1
        assert comps[0].entity_id == "a"
        assert comps[0].changes == []

    def test_with_changes(self) -> None:
        snaps = {
            0: _make_snapshot(
                0, entities={"a": {"cash": 100, "rep": 50}}
            ),
            1: _make_snapshot(
                1, entities={"a": {"cash": 80, "rep": 50}}
            ),
        }
        comps = _compare_entities(snaps)
        changed = {ch.attribute: ch for ch in comps[0].changes}
        assert "cash" in changed
        assert changed["cash"].before == 100
        assert changed["cash"].after == 80
        assert "rep" not in changed

    def test_entity_sorted_by_id(self) -> None:
        snaps = {
            0: _make_snapshot(
                0, entities={"b": {"x": 1}, "a": {"x": 2}, "c": {"x": 3}}
            ),
        }
        comps = _compare_entities(snaps)
        assert [c.entity_id for c in comps] == ["a", "b", "c"]


# =============================================================================
# 3. 公开入口
# =============================================================================


class TestAnalyzeRun:
    def test_missing_events_file(self, tmp_path: Path) -> None:
        """run_dir 里没 events.jsonl：FileNotFoundError。"""
        with pytest.raises(FileNotFoundError):
            analyze_run(tmp_path)

    def test_minimal_run(self, tmp_path: Path, events_file: Path) -> None:
        """run_dir 只有 events.jsonl（没 snapshots/）：仍能返回结果。"""
        # events_file 是 tmp_path/events.jsonl，tmp_path 本身就是 run_dir
        result = analyze_run(tmp_path)
        assert result.run_id == tmp_path.name
        assert result.summary.total_events == 3
        assert result.turning_points == []  # 没快照就没转折点

    def test_full_run_with_snapshots(
        self, tmp_path: Path, events_file: Path, snapshots_dir: Path
    ) -> None:
        result = analyze_run(tmp_path)
        assert result.summary.total_ticks == 2
        # snapshots 里 a 的 cash 从 100→80，环境 demand 从 50→60
        assert len(result.turning_points) == 1
        assert result.turning_points[0].attribute == "cash"
        assert result.environment_trajectory[0].variable == "demand"

    def test_run_id_derived_from_dirname(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "20260424_abc_world_scenario"
        run_dir.mkdir()
        (run_dir / "events.jsonl").write_text("", encoding="utf-8")
        result = analyze_run(run_dir)
        assert result.run_id == "20260424_abc_world_scenario"


class TestRenderMarkdown:
    def test_minimal_result(self) -> None:
        result = AnalysisResult(
            run_id="x",
            summary=TrajectorySummary(total_ticks=0, total_events=0),
        )
        md = render_markdown(result)
        assert "# 仿真分析报告" in md
        assert "run_id" in md
        # 空数据时应有 fallback 文案
        assert "无显著属性变化" in md
        assert "未发现任何实体快照" in md
        assert "无环境变量" in md

    def test_with_all_sections(self) -> None:
        result = AnalysisResult(
            run_id="x",
            summary=TrajectorySummary(
                total_ticks=3,
                total_events=10,
                events_by_kind=[],
            ),
            entity_comparisons=[
                EntityComparison(
                    entity_id="company_a",
                    initial_attributes={"cash": 100},
                    final_attributes={"cash": 80},
                    changes=[
                        AttributeChange(attribute="cash", before=100, after=80)
                    ],
                )
            ],
        )
        md = render_markdown(result)
        assert "`company_a`" in md
        assert "| `cash` | 100 | 80 |" in md

    def test_llm_sections_omitted_when_none(self) -> None:
        """LLM 增强字段为 None：对应 section 不出现。"""
        result = AnalysisResult(
            run_id="x",
            summary=TrajectorySummary(total_ticks=0, total_events=0),
        )
        md = render_markdown(result)
        assert "局势判断" not in md
        assert "自然语言总览" not in md
        assert "面向用户的建议" not in md

    def test_llm_sections_rendered_when_provided(self) -> None:
        """四个 LLM 增强字段都被填时，render_markdown 全部输出。"""
        result = AnalysisResult(
            run_id="x",
            summary=TrajectorySummary(total_ticks=0, total_events=0),
            world_overview="初始世界描述",
            narrative_summary="整体稳定",
            situation_judgement="当前平衡",
            next_action_suggestions=["建议A", "建议B"],
        )
        md = render_markdown(result)
        # v0.1.1 收官加 world_overview 节
        assert "世界概览" in md
        assert "初始世界描述" in md
        assert "局势判断" in md
        assert "当前平衡" in md
        assert "- 建议A" in md
        assert "- 建议B" in md
        assert "全过程叙事" in md  # v0.1.1 重命名
        assert "整体稳定" in md

    def test_ends_with_newline(self) -> None:
        """markdown 渲染产物以换行结尾——工具链友好。"""
        result = AnalysisResult(
            run_id="x",
            summary=TrajectorySummary(total_ticks=0, total_events=0),
        )
        assert render_markdown(result).endswith("\n")


class TestRenderJson:
    def test_round_trip(self) -> None:
        result = AnalysisResult(
            run_id="x",
            summary=TrajectorySummary(total_ticks=1, total_events=2),
        )
        rendered = render_json(result)
        decoded = AnalysisResult.model_validate_json(rendered)
        assert decoded == result

    def test_is_pretty_printed(self) -> None:
        """pretty JSON 有换行与缩进，便于人读。"""
        result = AnalysisResult(
            run_id="x",
            summary=TrajectorySummary(total_ticks=0, total_events=0),
        )
        rendered = render_json(result)
        assert "\n" in rendered
        assert "  " in rendered  # indent=2


class TestWriteAnalysis:
    def test_writes_both_files(self, tmp_path: Path) -> None:
        result = AnalysisResult(
            run_id="x",
            summary=TrajectorySummary(total_ticks=0, total_events=0),
        )
        md_path, json_path = write_analysis(tmp_path, result)
        assert md_path.exists()
        assert json_path.exists()
        assert md_path.name == "final.md"
        assert json_path.name == "final.json"
        assert md_path.parent.name == "analysis"

    def test_creates_analysis_dir(self, tmp_path: Path) -> None:
        """analysis/ 子目录不存在时自动建。"""
        assert not (tmp_path / "analysis").exists()
        result = AnalysisResult(
            run_id="x",
            summary=TrajectorySummary(total_ticks=0, total_events=0),
        )
        write_analysis(tmp_path, result)
        assert (tmp_path / "analysis").is_dir()

    def test_overwrites_existing(self, tmp_path: Path) -> None:
        """同名文件存在：直接覆盖，无需 append-only。"""
        result = AnalysisResult(
            run_id="first",
            summary=TrajectorySummary(total_ticks=0, total_events=0),
        )
        write_analysis(tmp_path, result)
        new_result = AnalysisResult(
            run_id="second",
            summary=TrajectorySummary(total_ticks=0, total_events=0),
        )
        md_path, _ = write_analysis(tmp_path, new_result)
        content = md_path.read_text(encoding="utf-8")
        assert "second" in content
        assert "first" not in content


# =============================================================================
# 4. 端到端：用 CLI 跑 walkthrough → 分析层读产物
# =============================================================================


class TestEndToEndWithCli:
    """通过 CLI 跑 walkthrough 产出 run_dir，验证分析层能读出来。

    这些测试依赖 `scenarios/minimal_market/` + `cli/run.py`——算 **集成测试**。
    """

    def test_analyze_walkthrough_with_promote(self, tmp_path: Path) -> None:
        """用 --llm-script 让 company_a 做 promote，turning_points 应非空。"""
        from cli.run import main

        script = tmp_path / "llm.jsonl"
        script.write_text(
            "\n".join(
                [
                    json.dumps({"action": "promote", "params": {"budget": 30}}),
                    json.dumps({"action": "do_nothing", "params": {}}),
                ]
            ),
            encoding="utf-8",
        )
        stdout = io.StringIO()
        exit_code = main(
            [
                "run",
                "scenarios/minimal_market/scenario.yaml",
                "--runs-root",
                str(tmp_path),
                "--ticks",
                "1",
                "--llm-script",
                str(script),
            ],
            stdin=io.StringIO(),
            stdout=stdout,
            stderr=io.StringIO(),
        )
        assert exit_code == 0
        # 找到生成的 run_dir
        run_dirs = [p for p in tmp_path.iterdir() if p.is_dir()]
        assert len(run_dirs) == 1
        result = analyze_run(run_dirs[0])
        # company_a 的 cash/reputation 应该有变化
        assert result.turning_points, "应至少识别 1 条 turning point"
        cash_tps = [
            tp
            for tp in result.turning_points
            if tp.actor_id == "company_a" and tp.attribute == "cash"
        ]
        assert cash_tps, "company_a 的 cash 变化应进入 turning_points"
        assert cash_tps[0].delta == -30.0

    def test_analyze_walkthrough_default_do_nothing(
        self, tmp_path: Path
    ) -> None:
        """默认 do_nothing：应无 turning points。"""
        from cli.run import main

        stdout = io.StringIO()
        exit_code = main(
            [
                "run",
                "scenarios/minimal_market/scenario.yaml",
                "--runs-root",
                str(tmp_path),
                "--ticks",
                "2",
            ],
            stdin=io.StringIO(),
            stdout=stdout,
            stderr=io.StringIO(),
        )
        assert exit_code == 0
        run_dir = next(tmp_path.iterdir())
        result = analyze_run(run_dir)
        assert result.turning_points == []
        assert result.summary.total_ticks == 2


# =============================================================================
# 4. Phase C——LLM 增强
# =============================================================================


@pytest.fixture
def phase_a_result() -> AnalysisResult:
    """最小合法 AnalysisResult——只含 Phase A 字段，三个增强字段都是 None。"""
    return AnalysisResult(
        version="0.1",
        run_id="run-phase-c-fixture",
        summary=TrajectorySummary(
            total_ticks=3,
            total_events=12,
            events_by_kind=[],
            events_by_actor=[],
            paused_ticks=[],
            breakpoints_triggered=[],
        ),
        turning_points=[],
        entity_comparisons=[],
        environment_trajectory=[],
    )


def _enhancement_json(
    *,
    overview: str = "本仿真包含一家公司与一名监管者，目标是观察双方互动。",
    narrative: str = "公司 A 缓慢积累资本。",
    judgement: str = "目前局势偏稳，风险可控。在 tick 1 公司 A 选择 promote。",
    suggestions: list[str] | None = None,
) -> str:
    """构造一条合法的 LLM 增强响应 JSON（测试辅助函数）。

    v0.1.1 收官扩展：增加 ``world_overview`` 字段——LLM 协议从三字段升为四字段。

    注意：suggestions 用 ``is None`` 判默认——显式传空 list `[]` 时保留空 list，
    这是"测边界错误"路径的必要行为（绕开 Python `or` 对 falsy 的折叠）。
    """
    if suggestions is None:
        suggestions = [
            "建议 1（援引 tick 1 的 promote 动作）",
            "建议 2（援引 cash 数值变化）",
        ]
    return json.dumps(
        {
            "world_overview": overview,
            "narrative_summary": narrative,
            "situation_judgement": judgement,
            "next_action_suggestions": suggestions,
        },
        ensure_ascii=False,
    )


_WALKTHROUGH_DIR = (
    Path(__file__).resolve().parent.parent / "scenarios" / "minimal_market"
)


@pytest.fixture
def world() -> WorldDefinition:
    """复用 minimal_market world——LLM 增强测试需要真实 world 喂 prompt。"""
    return load_world_definition(_WALKTHROUGH_DIR / "world.yaml")


@pytest.fixture
def scenario(world: WorldDefinition) -> Scenario:
    """复用 minimal_market scenario——同上。"""
    return load_scenario(_WALKTHROUGH_DIR / "scenario.yaml", world)


class TestBuildAnalysisPrompt:
    def test_contains_phase_a_payload_json(
        self,
        phase_a_result: AnalysisResult,
        world: WorldDefinition,
        scenario: Scenario,
    ) -> None:
        """prompt 必须内嵌 AnalysisResult 的 Phase A 部分 JSON。"""
        prompt = _build_analysis_prompt(phase_a_result, world, scenario)
        assert phase_a_result.run_id in prompt
        assert '"total_ticks": 3' in prompt
        assert '"total_events": 12' in prompt

    def test_excludes_llm_enhancement_fields(
        self, world: WorldDefinition, scenario: Scenario
    ) -> None:
        """若 result 已含增强字段，prompt 必须剔除——不让 LLM 看到自己的旧答案。"""
        result = AnalysisResult(
            version="0.1",
            run_id="r1",
            summary=TrajectorySummary(
                total_ticks=1,
                total_events=1,
                events_by_kind=[],
                events_by_actor=[],
                paused_ticks=[],
                breakpoints_triggered=[],
            ),
            world_overview="这是旧的世界概览，不应出现",
            narrative_summary="这是旧的叙事，不应出现",
            situation_judgement="这是旧的判断，不应出现",
            next_action_suggestions=["旧建议"],
        )
        prompt = _build_analysis_prompt(result, world, scenario)
        assert "旧的世界概览" not in prompt
        assert "旧的叙事" not in prompt
        assert "旧的判断" not in prompt
        assert "旧建议" not in prompt

    def test_default_language_is_zh_cn(
        self,
        phase_a_result: AnalysisResult,
        world: WorldDefinition,
        scenario: Scenario,
    ) -> None:
        """默认 language 注入为 zh-CN。"""
        prompt = _build_analysis_prompt(phase_a_result, world, scenario)
        assert "zh-CN" in prompt

    def test_custom_language_injected(
        self,
        phase_a_result: AnalysisResult,
        world: WorldDefinition,
        scenario: Scenario,
    ) -> None:
        """自定义 language 要出现在 prompt 里且 zh-CN 不应出现（避免冲突指令）。"""
        prompt = _build_analysis_prompt(
            phase_a_result, world, scenario, language="en"
        )
        assert "en" in prompt
        assert "zh-CN" not in prompt

    def test_language_does_not_affect_payload(
        self,
        phase_a_result: AnalysisResult,
        world: WorldDefinition,
        scenario: Scenario,
    ) -> None:
        """不同语言下 payload JSON 内容完全一致——只有尾部指令变。"""
        p_zh = _build_analysis_prompt(
            phase_a_result, world, scenario, language="zh-CN"
        )
        p_en = _build_analysis_prompt(
            phase_a_result, world, scenario, language="en"
        )
        # 抽取 Phase A 部分的 payload JSON（v0.1.1 收官改了 header 文案）
        header = "Phase A analysis result (JSON):\n"
        zh_body = p_zh.split(header, 1)[1].split("\n\n", 1)[0]
        en_body = p_en.split(header, 1)[1].split("\n\n", 1)[0]
        assert zh_body == en_body

    def test_includes_json_output_contract(
        self,
        phase_a_result: AnalysisResult,
        world: WorldDefinition,
        scenario: Scenario,
    ) -> None:
        """prompt 必须告知 LLM 返 JSON 四字段（v0.1.1 收官加 world_overview）。"""
        prompt = _build_analysis_prompt(phase_a_result, world, scenario)
        assert "world_overview" in prompt
        assert "narrative_summary" in prompt
        assert "situation_judgement" in prompt
        assert "next_action_suggestions" in prompt

    def test_contains_world_definition(
        self,
        phase_a_result: AnalysisResult,
        world: WorldDefinition,
        scenario: Scenario,
    ) -> None:
        """v0.1.1 收官：prompt 必须含 World Definition payload——LLM 据此解释世界。"""
        prompt = _build_analysis_prompt(phase_a_result, world, scenario)
        assert "World Definition (JSON):" in prompt
        # minimal_market world 含 Company / Regulator 实体类型
        assert "Company" in prompt
        assert "Regulator" in prompt

    def test_contains_scenario_payload(
        self,
        phase_a_result: AnalysisResult,
        world: WorldDefinition,
        scenario: Scenario,
    ) -> None:
        """v0.1.1 收官：prompt 必须含 Scenario payload——LLM 据此解释初始关系/目标。"""
        prompt = _build_analysis_prompt(phase_a_result, world, scenario)
        assert "Scenario (JSON):" in prompt
        # minimal_market scenario 含 company_a / regulator_main
        assert "company_a" in prompt
        assert "regulator_main" in prompt

    def test_evidence_requirement_in_instructions(
        self,
        phase_a_result: AnalysisResult,
        world: WorldDefinition,
        scenario: Scenario,
    ) -> None:
        """v0.1.1 收官：prompt 必须明文要求援引证据（tick / 属性 / 实体）。"""
        prompt = _build_analysis_prompt(phase_a_result, world, scenario)
        # CRITICAL 关键字 + 至少一处 evidence 词 + tick 字样
        assert "evidence" in prompt.lower()
        assert "tick" in prompt.lower()


class TestParseAnalysisResponse:
    def test_happy_path(self) -> None:
        raw = _enhancement_json(
            narrative="Sim went fine.",
            judgement="Stable.",
            suggestions=["Do X", "Try Y"],
        )
        parsed = _parse_analysis_response(raw)
        assert parsed["narrative_summary"] == "Sim went fine."
        assert parsed["situation_judgement"] == "Stable."
        assert parsed["next_action_suggestions"] == ["Do X", "Try Y"]

    def test_strips_whitespace(self) -> None:
        """四段自然语言字段的首尾空白要剥掉。"""
        raw = json.dumps(
            {
                "world_overview": "  世界  ",
                "narrative_summary": "  叙事  ",
                "situation_judgement": "  判断  ",
                "next_action_suggestions": ["  建议 1  "],
            },
            ensure_ascii=False,
        )
        parsed = _parse_analysis_response(raw)
        assert parsed["world_overview"] == "世界"
        assert parsed["narrative_summary"] == "叙事"
        assert parsed["situation_judgement"] == "判断"
        assert parsed["next_action_suggestions"] == ["建议 1"]

    def test_extra_keys_tolerated(self) -> None:
        """LLM 偶尔会加解释性 key——容忍但忽略。"""
        raw = json.dumps(
            {
                "world_overview": "世界",
                "narrative_summary": "叙事",
                "situation_judgement": "判断",
                "next_action_suggestions": ["S1"],
                "unexpected_key": "LLM meta",
                "_chain_of_thought": "some reasoning",
            },
            ensure_ascii=False,
        )
        parsed = _parse_analysis_response(raw)
        assert set(parsed.keys()) == {
            "world_overview",
            "narrative_summary",
            "situation_judgement",
            "next_action_suggestions",
        }

    def test_not_json_raises(self) -> None:
        with pytest.raises(LLMProtocolError, match="合法 JSON"):
            _parse_analysis_response("not json at all {{")

    def test_non_str_input_raises(self) -> None:
        with pytest.raises(LLMProtocolError, match="预期 str"):
            _parse_analysis_response(123)  # type: ignore[arg-type]

    def test_top_level_not_dict_raises(self) -> None:
        with pytest.raises(LLMProtocolError, match="object"):
            _parse_analysis_response(json.dumps(["a", "b"]))

    def test_missing_world_overview_raises(self) -> None:
        """v0.1.1 收官：world_overview 缺失 → LLMProtocolError。"""
        raw = json.dumps(
            {
                "narrative_summary": "叙事",
                "situation_judgement": "判断",
                "next_action_suggestions": ["s1"],
            }
        )
        with pytest.raises(LLMProtocolError, match="world_overview"):
            _parse_analysis_response(raw)

    def test_empty_world_overview_raises(self) -> None:
        """v0.1.1 收官：world_overview 为空白 → LLMProtocolError。"""
        raw = _enhancement_json(overview="   ")
        with pytest.raises(LLMProtocolError, match="world_overview"):
            _parse_analysis_response(raw)

    def test_missing_narrative_raises(self) -> None:
        raw = json.dumps(
            {
                "world_overview": "世界",
                "situation_judgement": "judgement",
                "next_action_suggestions": ["s1"],
            }
        )
        with pytest.raises(LLMProtocolError, match="narrative_summary"):
            _parse_analysis_response(raw)

    def test_empty_narrative_raises(self) -> None:
        raw = _enhancement_json(narrative="   ")
        with pytest.raises(LLMProtocolError, match="narrative_summary"):
            _parse_analysis_response(raw)

    def test_missing_judgement_raises(self) -> None:
        raw = json.dumps(
            {
                "world_overview": "世界",
                "narrative_summary": "叙事",
                "next_action_suggestions": ["s1"],
            }
        )
        with pytest.raises(LLMProtocolError, match="situation_judgement"):
            _parse_analysis_response(raw)

    def test_empty_judgement_raises(self) -> None:
        raw = _enhancement_json(judgement="")
        with pytest.raises(LLMProtocolError, match="situation_judgement"):
            _parse_analysis_response(raw)

    def test_suggestions_missing_raises(self) -> None:
        raw = json.dumps(
            {
                "world_overview": "w",
                "narrative_summary": "n",
                "situation_judgement": "j",
            }
        )
        with pytest.raises(LLMProtocolError, match="next_action_suggestions"):
            _parse_analysis_response(raw)

    def test_suggestions_not_list_raises(self) -> None:
        raw = json.dumps(
            {
                "world_overview": "w",
                "narrative_summary": "n",
                "situation_judgement": "j",
                "next_action_suggestions": "not a list",
            }
        )
        with pytest.raises(LLMProtocolError, match="非空数组"):
            _parse_analysis_response(raw)

    def test_suggestions_empty_list_raises(self) -> None:
        raw = _enhancement_json(suggestions=[])
        with pytest.raises(LLMProtocolError, match="非空数组"):
            _parse_analysis_response(raw)

    def test_suggestion_item_not_str_raises(self) -> None:
        raw = json.dumps(
            {
                "world_overview": "w",
                "narrative_summary": "n",
                "situation_judgement": "j",
                "next_action_suggestions": ["ok", 123],
            }
        )
        with pytest.raises(LLMProtocolError, match=r"\[1\]"):
            _parse_analysis_response(raw)

    def test_suggestion_item_empty_raises(self) -> None:
        raw = _enhancement_json(suggestions=["valid", "   "])
        with pytest.raises(LLMProtocolError, match=r"\[1\]"):
            _parse_analysis_response(raw)


class TestEnhanceWithLLM:
    def test_happy_path_fills_four_fields(
        self,
        phase_a_result: AnalysisResult,
        world: WorldDefinition,
        scenario: Scenario,
    ) -> None:
        """成功路径：provider 返合法 JSON → 返回新 result 四字段被填。"""
        provider = MockProvider(
            fixed_response=_enhancement_json(
                overview="世界概览文本。",
                narrative="全流程稳定。",
                judgement="A 略占优势。",
                suggestions=["S1", "S2", "S3"],
            )
        )
        config = RuntimeConfig(version="0.1")
        enhanced = enhance_with_llm(
            phase_a_result, provider, config, world=world, scenario=scenario
        )
        assert enhanced.world_overview == "世界概览文本。"
        assert enhanced.narrative_summary == "全流程稳定。"
        assert enhanced.situation_judgement == "A 略占优势。"
        assert enhanced.next_action_suggestions == ["S1", "S2", "S3"]

    def test_returns_new_object_does_not_mutate_input(
        self,
        phase_a_result: AnalysisResult,
        world: WorldDefinition,
        scenario: Scenario,
    ) -> None:
        """input result 必须不被修改——Pydantic v2 不可变性惯例。"""
        provider = MockProvider(fixed_response=_enhancement_json())
        config = RuntimeConfig(version="0.1")
        enhanced = enhance_with_llm(
            phase_a_result, provider, config, world=world, scenario=scenario
        )
        # 原对象四字段仍为 None
        assert phase_a_result.world_overview is None
        assert phase_a_result.narrative_summary is None
        assert phase_a_result.situation_judgement is None
        assert phase_a_result.next_action_suggestions is None
        # 新对象已填
        assert enhanced is not phase_a_result
        assert enhanced.world_overview is not None
        assert enhanced.narrative_summary is not None

    def test_phase_a_fields_preserved(
        self,
        phase_a_result: AnalysisResult,
        world: WorldDefinition,
        scenario: Scenario,
    ) -> None:
        """前五个 Phase A 字段原样保留，只增量填增强字段。"""
        provider = MockProvider(fixed_response=_enhancement_json())
        config = RuntimeConfig(version="0.1")
        enhanced = enhance_with_llm(
            phase_a_result, provider, config, world=world, scenario=scenario
        )
        assert enhanced.run_id == phase_a_result.run_id
        assert enhanced.version == phase_a_result.version
        assert enhanced.summary == phase_a_result.summary
        assert enhanced.turning_points == phase_a_result.turning_points

    def test_passes_output_language_to_prompt(
        self,
        phase_a_result: AnalysisResult,
        world: WorldDefinition,
        scenario: Scenario,
    ) -> None:
        """config.output_language 必须注入 prompt——多语言链路完整闭合。"""
        captured: list[str] = []

        class PromptCapturingProvider(LLMProvider):
            def generate(self, prompt: str, **kwargs):  # type: ignore[override]
                captured.append(prompt)
                return _enhancement_json()

        config = RuntimeConfig(version="0.1", output_language="fr-FR")
        enhance_with_llm(
            phase_a_result,
            PromptCapturingProvider(),
            config,
            world=world,
            scenario=scenario,
        )
        assert len(captured) == 1
        assert "fr-FR" in captured[0]
        assert "zh-CN" not in captured[0]

    def test_passes_timeout_to_provider(
        self,
        phase_a_result: AnalysisResult,
        world: WorldDefinition,
        scenario: Scenario,
    ) -> None:
        """config.llm_request_timeout_sec 必须透传到 provider.generate。"""
        captured_kwargs: dict = {}

        class TracingProvider(LLMProvider):
            def generate(self, prompt: str, **kwargs):  # type: ignore[override]
                captured_kwargs.update(kwargs)
                return _enhancement_json()

        config = RuntimeConfig(version="0.1", llm_request_timeout_sec=45.0)
        enhance_with_llm(
            phase_a_result,
            TracingProvider(),
            config,
            world=world,
            scenario=scenario,
        )
        assert captured_kwargs["timeout"] == 45.0
        assert "temperature" in captured_kwargs
        assert "max_tokens" in captured_kwargs

    def test_passes_analysis_system_prompt_to_provider(
        self,
        phase_a_result: AnalysisResult,
        world: WorldDefinition,
        scenario: Scenario,
    ) -> None:
        """F1：enhance_with_llm 必须把分析导向 system_prompt 透传给 provider。

        避免与 ``OpenAIProvider`` 构造期默认的决策导向 system prompt 角色冲突。
        """
        captured_kwargs: dict = {}

        class TracingProvider(LLMProvider):
            def generate(self, prompt: str, **kwargs):  # type: ignore[override]
                captured_kwargs.update(kwargs)
                return _enhancement_json()

        config = RuntimeConfig(version="0.1")
        enhance_with_llm(
            phase_a_result,
            TracingProvider(),
            config,
            world=world,
            scenario=scenario,
        )
        assert "system_prompt" in captured_kwargs
        sp = captured_kwargs["system_prompt"]
        # 分析导向——含四个分析字段名（v0.1.1 收官加 world_overview）
        assert "world_overview" in sp
        assert "narrative_summary" in sp
        assert "situation_judgement" in sp
        assert "next_action_suggestions" in sp
        # 不含决策导向字段（避免角色冲突的关键标志）
        assert "available_actions" not in sp
        # 含 "JSON" 关键词——OpenAI response_format=json_object 模式硬性要求
        assert "JSON" in sp
        # v0.1.1 收官：必须明文要求援引证据
        assert "evidence" in sp.lower()

    def test_provider_error_propagates(
        self,
        phase_a_result: AnalysisResult,
        world: WorldDefinition,
        scenario: Scenario,
    ) -> None:
        """ProviderError 原样上抛——由调用方（CLI）决定降级策略。"""

        class FailingProvider(LLMProvider):
            def generate(self, prompt: str, **kwargs):  # type: ignore[override]
                raise ProviderError("network down")

        config = RuntimeConfig(version="0.1")
        with pytest.raises(ProviderError, match="network down"):
            enhance_with_llm(
                phase_a_result,
                FailingProvider(),
                config,
                world=world,
                scenario=scenario,
            )

    def test_invalid_json_raises_protocol_error(
        self,
        phase_a_result: AnalysisResult,
        world: WorldDefinition,
        scenario: Scenario,
    ) -> None:
        """provider 返非 JSON → LLMProtocolError。"""
        provider = MockProvider(fixed_response="not valid json")
        config = RuntimeConfig(version="0.1")
        with pytest.raises(LLMProtocolError, match="合法 JSON"):
            enhance_with_llm(
                phase_a_result,
                provider,
                config,
                world=world,
                scenario=scenario,
            )

    def test_missing_field_raises_protocol_error(
        self,
        phase_a_result: AnalysisResult,
        world: WorldDefinition,
        scenario: Scenario,
    ) -> None:
        """provider 返字段不全 → LLMProtocolError。"""
        raw = json.dumps(
            {
                "world_overview": "w",
                "narrative_summary": "n",
                "situation_judgement": "j",
            }
        )
        provider = MockProvider(fixed_response=raw)
        config = RuntimeConfig(version="0.1")
        with pytest.raises(LLMProtocolError, match="next_action_suggestions"):
            enhance_with_llm(
                phase_a_result,
                provider,
                config,
                world=world,
                scenario=scenario,
            )

    def test_renders_enhanced_markdown(
        self,
        phase_a_result: AnalysisResult,
        world: WorldDefinition,
        scenario: Scenario,
    ) -> None:
        """enhance 后的 result 走 render_markdown 应展示四节新内容（v0.1.1 加世界概览）。"""
        provider = MockProvider(
            fixed_response=_enhancement_json(
                overview="世界概览内容文本",
                narrative="叙事段落内容",
                judgement="局势判断内容",
                suggestions=["建议一", "建议二"],
            )
        )
        config = RuntimeConfig(version="0.1")
        enhanced = enhance_with_llm(
            phase_a_result, provider, config, world=world, scenario=scenario
        )
        md = render_markdown(enhanced)
        # v0.1.1 收官：世界概览在最前
        assert "世界概览" in md
        assert "世界概览内容文本" in md
        assert "局势判断" in md
        assert "局势判断内容" in md
        assert "面向用户的建议" in md
        assert "建议一" in md
        assert "全过程叙事" in md  # v0.1.1 重命名：原“自然语言总览”
        assert "叙事段落内容" in md
        # 世界概览出现在局势判断之前（重排验证）
        assert md.index("世界概览") < md.index("全轨迹总结")
