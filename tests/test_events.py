"""EventLog 与 run_id 生成器测试（D-006 / D-007）。

对应 `docs/02-design/实现映射设计.md` 4.5 节 Event Log 章节与
`docs/01-requirements/验收标准.md` 9.1 / 9.2 节。

覆盖：

1. `generate_run_id` 格式、时钟注入、slug 清理
2. `EventLog` in-memory 模式（persist=False，不创建任何文件）
3. `EventLog` 持久化模式（events.jsonl 流式追加、snapshots/tick_N.json 幂等覆盖）
4. `get_events` 三维度过滤 + 副本语义
5. `get_snapshot` / `all_snapshots` 正确性
6. 上下文管理器自动关闭文件
7. append-only 语义：EventLog 不暴露 delete / update / remove API

不覆盖：

- `EventRecord` / `Snapshot` 的结构校验（已在 `test_runtime_models.py`）
- Runtime 何时调用 `append` / `save_snapshot`（属 `test_runtime.py`）
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from core.events import EventLog, generate_run_id
from models.config_models import StorageConfig
from models.runtime_models import (
    EventRecord,
    MessageSummary,
    Snapshot,
)


# =============================================================================
# fixtures
# =============================================================================


def _make_event(
    event_id: str,
    tick: int,
    kind: str = "action_executed",
    actor_id: str | None = "company_a",
    payload: dict | None = None,
) -> EventRecord:
    return EventRecord(
        event_id=event_id,
        tick=tick,
        kind=kind,  # type: ignore[arg-type]
        actor_id=actor_id,
        payload=payload or {},
    )


def _make_snapshot(tick: int) -> Snapshot:
    return Snapshot(
        tick=tick,
        entity_state_summary={"company_a": {"cash": 100 - tick}},
        environment_state={"demand": 50 + tick},
        message_summary=MessageSummary(emitted=tick, delivered_next_tick=tick),
    )


def _in_memory_config() -> StorageConfig:
    return StorageConfig(version="0.1", persist=False)


def _persist_config(tmp_path: Path) -> StorageConfig:
    return StorageConfig(version="0.1", persist=True, runs_root=str(tmp_path))


# =============================================================================
# generate_run_id
# =============================================================================


def test_generate_run_id_format_matches_spec() -> None:
    fixed_now = datetime(2026, 4, 24, 12, 56, 0)
    run_id = generate_run_id("market", "walkthrough_min", now=fixed_now)
    assert run_id == "20260424_125600_market_walkthrough_min"


def test_generate_run_id_without_clock_is_well_formed() -> None:
    """不注入时钟时，输出仍必须匹配形状（用正则粗验证）。"""
    run_id = generate_run_id("w", "s")
    parts = run_id.split("_")
    assert len(parts) >= 4
    assert len(parts[0]) == 8 and parts[0].isdigit()  # YYYYMMDD
    assert len(parts[1]) == 6 and parts[1].isdigit()  # HHMMSS


def test_generate_run_id_slugifies_special_chars() -> None:
    """中文、空格、斜杠都被替换为下划线以保证路径安全。"""
    fixed_now = datetime(2026, 4, 24, 0, 0, 0)
    run_id = generate_run_id("市场 v1", "路径/子路径", now=fixed_now)
    # 中文 / 空格 / 斜杠都变 _
    assert "市场" not in run_id
    assert " " not in run_id
    assert "/" not in run_id
    # 仍然以时间戳开头
    assert run_id.startswith("20260424_000000_")


def test_generate_run_id_preserves_underscore_and_hyphen() -> None:
    fixed_now = datetime(2026, 4, 24, 0, 0, 0)
    run_id = generate_run_id("my_world-v1", "scen_a-01", now=fixed_now)
    assert run_id == "20260424_000000_my_world-v1_scen_a-01"


def test_generate_run_id_empty_id_becomes_underscore() -> None:
    fixed_now = datetime(2026, 4, 24, 0, 0, 0)
    run_id = generate_run_id("   ", "scen", now=fixed_now)
    # 空白 slug 为单下划线
    assert run_id == "20260424_000000___scen"


# =============================================================================
# EventLog：in-memory 模式
# =============================================================================


def test_eventlog_in_memory_append_events_stored() -> None:
    log = EventLog(run_id="r1", storage_config=_in_memory_config())
    log.append(_make_event("e1", tick=1))
    log.append(_make_event("e2", tick=2))
    assert log.event_count() == 2


def test_eventlog_in_memory_no_files_created(tmp_path: Path) -> None:
    """persist=False：即使提供了 runs_root，也**不**创建任何磁盘文件。"""
    cfg = StorageConfig(version="0.1", persist=False, runs_root=str(tmp_path))
    log = EventLog(run_id="r1", storage_config=cfg)
    log.append(_make_event("e1", tick=1))
    log.save_snapshot(_make_snapshot(tick=1))

    # tmp_path 应保持干净（pytest 为每个 test 提供隔离 tmp_path）
    assert list(tmp_path.iterdir()) == []
    assert log.run_dir is None
    assert log.events_file is None
    assert log.snapshot_dir is None


# =============================================================================
# EventLog：get_events 过滤
# =============================================================================


def _seed_events() -> EventLog:
    log = EventLog(run_id="r1", storage_config=_in_memory_config())
    log.append(_make_event("e1", tick=1, kind="decision_proposed", actor_id="a"))
    log.append(_make_event("e2", tick=1, kind="action_executed", actor_id="a"))
    log.append(_make_event("e3", tick=2, kind="decision_proposed", actor_id="b"))
    log.append(_make_event("e4", tick=2, kind="action_executed", actor_id="a"))
    log.append(_make_event("e5", tick=3, kind="snapshot_saved", actor_id=None))
    return log


def test_eventlog_get_events_no_filter_returns_all() -> None:
    log = _seed_events()
    all_events = log.get_events()
    assert len(all_events) == 5
    assert [e.event_id for e in all_events] == ["e1", "e2", "e3", "e4", "e5"]


def test_eventlog_get_events_filter_by_tick() -> None:
    log = _seed_events()
    assert [e.event_id for e in log.get_events(tick=1)] == ["e1", "e2"]
    assert [e.event_id for e in log.get_events(tick=3)] == ["e5"]
    assert log.get_events(tick=999) == []


def test_eventlog_get_events_filter_by_kind() -> None:
    log = _seed_events()
    proposed = log.get_events(kind="decision_proposed")
    assert [e.event_id for e in proposed] == ["e1", "e3"]


def test_eventlog_get_events_filter_by_actor_id() -> None:
    log = _seed_events()
    actor_a = log.get_events(actor_id="a")
    assert [e.event_id for e in actor_a] == ["e1", "e2", "e4"]
    actor_none = log.get_events(actor_id=None)  # None 表示不过滤
    assert len(actor_none) == 5


def test_eventlog_get_events_combined_filters_are_and() -> None:
    log = _seed_events()
    # tick=2 且 kind=decision_proposed 且 actor=b → 只有 e3
    result = log.get_events(tick=2, kind="decision_proposed", actor_id="b")
    assert [e.event_id for e in result] == ["e3"]
    # tick=1 且 actor=a → e1, e2
    result = log.get_events(tick=1, actor_id="a")
    assert [e.event_id for e in result] == ["e1", "e2"]


def test_eventlog_get_events_returns_fresh_list() -> None:
    """返回列表是副本——外部修改不影响内部状态。"""
    log = _seed_events()
    result = log.get_events()
    result.clear()
    assert log.event_count() == 5
    assert len(log.get_events()) == 5


# =============================================================================
# EventLog：持久化模式
# =============================================================================


def test_eventlog_persist_creates_run_directory(tmp_path: Path) -> None:
    cfg = _persist_config(tmp_path)
    with EventLog(run_id="my_run", storage_config=cfg):
        pass

    run_dir = tmp_path / "my_run"
    assert run_dir.is_dir()
    assert (run_dir / "snapshots").is_dir()


def test_eventlog_persist_writes_jsonl_one_line_per_event(tmp_path: Path) -> None:
    cfg = _persist_config(tmp_path)
    with EventLog(run_id="r1", storage_config=cfg) as log:
        log.append(_make_event("e1", tick=1, kind="decision_proposed"))
        log.append(_make_event("e2", tick=2, kind="action_executed"))
        log.append(_make_event("e3", tick=3, kind="snapshot_saved", actor_id=None))

    jsonl = (tmp_path / "r1" / "events.jsonl").read_text(encoding="utf-8")
    lines = [line for line in jsonl.splitlines() if line]
    assert len(lines) == 3
    # 每行独立 JSON，字段对齐 EventRecord
    parsed = [json.loads(line) for line in lines]
    assert [p["event_id"] for p in parsed] == ["e1", "e2", "e3"]
    assert parsed[0]["kind"] == "decision_proposed"
    assert parsed[2]["actor_id"] is None


def test_eventlog_persist_flushes_after_each_append(tmp_path: Path) -> None:
    """流式追加：append 后立即 flush 到磁盘，UI 可实时消费。"""
    cfg = _persist_config(tmp_path)
    log = EventLog(run_id="r1", storage_config=cfg)
    try:
        log.append(_make_event("e1", tick=1))
        # 不 close，直接读磁盘——必须已经写入
        content = (tmp_path / "r1" / "events.jsonl").read_text(encoding="utf-8")
        assert "e1" in content
    finally:
        log.close()


def test_eventlog_persist_writes_snapshot_per_tick(tmp_path: Path) -> None:
    cfg = _persist_config(tmp_path)
    with EventLog(run_id="r1", storage_config=cfg) as log:
        log.save_snapshot(_make_snapshot(tick=0))
        log.save_snapshot(_make_snapshot(tick=1))
        log.save_snapshot(_make_snapshot(tick=5))

    snap_dir = tmp_path / "r1" / "snapshots"
    files = sorted(p.name for p in snap_dir.iterdir())
    assert files == ["tick_0.json", "tick_1.json", "tick_5.json"]

    # 内容是合法 JSON 且字段正确
    tick_5 = json.loads((snap_dir / "tick_5.json").read_text(encoding="utf-8"))
    assert tick_5["tick"] == 5
    assert tick_5["entity_state_summary"]["company_a"]["cash"] == 95


def test_eventlog_persist_save_snapshot_same_tick_overwrites(tmp_path: Path) -> None:
    """同 tick 再次保存——覆盖上次（幂等语义）。"""
    cfg = _persist_config(tmp_path)
    with EventLog(run_id="r1", storage_config=cfg) as log:
        log.save_snapshot(
            Snapshot(tick=1, entity_state_summary={"x": {"v": 100}})
        )
        log.save_snapshot(
            Snapshot(tick=1, entity_state_summary={"x": {"v": 200}})
        )

    content = json.loads(
        (tmp_path / "r1" / "snapshots" / "tick_1.json").read_text(encoding="utf-8")
    )
    assert content["entity_state_summary"]["x"]["v"] == 200


def test_eventlog_persist_reuses_existing_run_dir(tmp_path: Path) -> None:
    """run_dir 已存在时不报错，events.jsonl 续写。"""
    cfg = _persist_config(tmp_path)
    (tmp_path / "r1").mkdir()
    (tmp_path / "r1" / "snapshots").mkdir()
    (tmp_path / "r1" / "events.jsonl").write_text(
        '{"event_id":"old","tick":0,"kind":"snapshot_saved","actor_id":null,"payload":{}}\n',
        encoding="utf-8",
    )

    with EventLog(run_id="r1", storage_config=cfg) as log:
        log.append(_make_event("new", tick=1))

    content = (tmp_path / "r1" / "events.jsonl").read_text(encoding="utf-8")
    lines = [line for line in content.splitlines() if line]
    assert len(lines) == 2
    assert json.loads(lines[0])["event_id"] == "old"
    assert json.loads(lines[1])["event_id"] == "new"


# =============================================================================
# EventLog：快照查询
# =============================================================================


def test_eventlog_get_snapshot_returns_none_for_missing() -> None:
    log = EventLog(run_id="r1", storage_config=_in_memory_config())
    assert log.get_snapshot(0) is None
    assert log.get_snapshot(999) is None


def test_eventlog_all_snapshots_sorted_by_tick() -> None:
    log = EventLog(run_id="r1", storage_config=_in_memory_config())
    log.save_snapshot(_make_snapshot(tick=5))
    log.save_snapshot(_make_snapshot(tick=1))
    log.save_snapshot(_make_snapshot(tick=3))

    snaps = log.all_snapshots()
    assert [s.tick for s in snaps] == [1, 3, 5]


# =============================================================================
# EventLog：上下文管理器 / close
# =============================================================================


def test_eventlog_context_manager_closes_file(tmp_path: Path) -> None:
    cfg = _persist_config(tmp_path)
    log = EventLog(run_id="r1", storage_config=cfg)
    assert log._events_fh is not None  # type: ignore[attr-defined]
    with log:
        log.append(_make_event("e1", tick=1))
    # 退出 with 后句柄被关
    assert log._events_fh is None  # type: ignore[attr-defined]


def test_eventlog_close_is_idempotent(tmp_path: Path) -> None:
    cfg = _persist_config(tmp_path)
    log = EventLog(run_id="r1", storage_config=cfg)
    log.close()
    log.close()  # 第二次不应抛


# =============================================================================
# EventLog：append-only 语义
# =============================================================================


def test_eventlog_has_no_mutation_api() -> None:
    """append-only 语义要求：类上不得暴露 delete / update / remove / clear。

    这是一条防御性测试——如果未来有人误加了写后修改接口，这里会立刻红。
    """
    forbidden = {"delete", "update", "remove", "clear", "pop", "replace"}
    public_methods = {m for m in dir(EventLog) if not m.startswith("_")}
    leaked = forbidden & public_methods
    assert not leaked, f"EventLog 不应暴露变更接口，但出现了：{leaked}"
