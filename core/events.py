"""事件轨迹 + 快照存储（D-006 / D-007）。

对应 `docs/02-design/实现映射设计.md` 4.5 节与 `docs/02-design/运行时与事件轨迹设计.md`
第九至十一节。

**分层约束**：

- 本模块只管"写"和"查"——**不**决定生成什么事件、**不**决定何时写快照。
  这些由 `core/runtime.py` 的 tick 主循环负责。
- 本模块也**不**做事件 payload 的语义校验——payload 的形状由 `EventKind` 各自
  决定，本层认为由 Runtime 在封装时已经保证
- 分析层（`core/analysis.py`）是**离线消费者**——直接读 `<run_dir>/events.jsonl`
  与 `<run_dir>/snapshots/` 上的 UI-ready 文件（与未来 UI 走同一路径）。EventLog
  自身只服务 Runtime 运行期内的内存查询，不作为分析的必经中介——否则分析无法
  在 Runtime 已关闭后跑任意旧 run

**D-006 约定落地**（UI-ready）：

- 事件走 JSONL（`events.jsonl` 一行一 `EventRecord`），方便 UI 流式消费
- 快照走 JSON（`snapshots/tick_<N>.json` 一文件一快照），方便 UI 定点跳转
- 所有产物都是标准 JSON，字段结构与 `models/runtime_models.py` 对齐
- 第一版只实现 `jsonl`；`StorageConfig.event_log_format="yaml"` 会抛
  `NotImplementedError`——此字段预留给第二阶段

**D-007 约定落地**（按 run 归档）：

- 所有产物归到 `{StorageConfig.runs_root}/<run_id>/` 下
- 子目录结构固定：`events.jsonl` / `snapshots/tick_<N>.json`
- 目录由本模块在 `EventLog.__init__` 自动创建，若已存在则沿用

**append-only 严格保证**：

- 本类对外**不**提供 update / delete / remove / clear 任何形式的写后修改接口
- 同 tick 的快照会被覆盖——这是幂等语义（快照表示"该 tick 结束时世界的状态"，
  不是 append），与事件的 append-only 不冲突
- 若业务需要撤销某个动作，应追加一条补偿事件，而不是删除原事件

两个对外入口：

1. `generate_run_id(world_id, scenario_id, now=None)`——可读 run_id 生成器
2. `EventLog(run_id, storage_config)`——事件队列 + 快照存储，支持 ``with`` 语法
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from models.config_models import StorageConfig
from models.runtime_models import EventKind, EventRecord, Snapshot


# =============================================================================
# run_id 生成器
# =============================================================================


_SLUG_PATTERN = re.compile(r"[^A-Za-z0-9_-]")


def _slugify(value: str) -> str:
    """最小 slug：去首尾空白，非 [A-Za-z0-9_-] 字符一律替换为下划线。

    保留下划线与连字符以支持 id 中的常用分隔符；其余字符（含中文、空格、斜杠等）
    替换为 ``_`` 以保证路径安全。若入参为空字符串，返回 ``_``。
    """
    slugged = _SLUG_PATTERN.sub("_", value.strip())
    return slugged or "_"


def generate_run_id(
    world_id: str,
    scenario_id: str,
    *,
    now: datetime | None = None,
) -> str:
    """生成可读 run_id（D-007）。

    格式：``YYYYMMDD_HHMMSS_<world_slug>_<scenario_slug>``

    Args:
        world_id: World Definition 的 id（`WorldInfo.id`）
        scenario_id: Scenario 的 id（`ScenarioInfo.id`）
        now: 注入时钟，主要供测试使用；为 None 时取 ``datetime.now()``

    Returns:
        示例：``20260424_125600_market_competition_walkthrough_min``

    Note:
        同秒内连续调用会返回相同 id；若调用方需要抗冲突，请自行追加后缀或
        使用 UUID 方案。本函数**不**检查产物目录是否已存在——那是 `EventLog`
        的职责。
    """
    ts = (now if now is not None else datetime.now()).strftime("%Y%m%d_%H%M%S")
    return f"{ts}_{_slugify(world_id)}_{_slugify(scenario_id)}"


# =============================================================================
# EventLog
# =============================================================================


class EventLog:
    """单次仿真的事件队列 + 快照存储（D-006 / D-007）。

    双写模型（同步到内存 + 可选落盘）：

    - 内存：`list[EventRecord]` + `dict[tick, Snapshot]`，供查询
    - 磁盘（`StorageConfig.persist=True`）：流式写 `events.jsonl` + 每 tick 一份
      `snapshots/tick_<N>.json`

    资源管理：

    - 构造时打开 `events.jsonl`（append 模式）；每次 `append()` 后立即 flush
    - 调用方可用 ``with EventLog(...) as log:`` 自动 close
    - 手动创建时需在结束后调用 `close()`，否则文件句柄由 GC 关闭（CPython 安全
      但非跨实现保证）

    禁止操作：

    - 删除、修改已 append 的事件
    - 对事件按 id 查找（防止上层暗示"可以定位+修改"语义）
    """

    def __init__(self, run_id: str, storage_config: StorageConfig) -> None:
        # 注：v1 仅支持 jsonl；StorageConfig.event_log_format 的 Literal 已经收窄到
        # ["jsonl"]，任何非法值在 Pydantic 构造时就被挡下，本构造函数不再做冗余检查
        self.run_id = run_id
        self._config = storage_config
        self._events: list[EventRecord] = []
        self._snapshots: dict[int, Snapshot] = {}

        self._run_dir: Path | None = None
        self._snapshot_dir: Path | None = None
        self._events_file: Path | None = None
        self._events_fh = None  # TextIO | None

        if storage_config.persist:
            self._run_dir = Path(storage_config.runs_root) / run_id
            self._snapshot_dir = self._run_dir / "snapshots"
            self._events_file = self._run_dir / "events.jsonl"
            self._run_dir.mkdir(parents=True, exist_ok=True)
            self._snapshot_dir.mkdir(parents=True, exist_ok=True)
            self._events_fh = self._events_file.open("a", encoding="utf-8")

    # ---------- 写入 ----------

    def append(self, record: EventRecord) -> None:
        """追加一条事件。

        内存立即可查；持久化模式下立即刷盘（保证"UI 实时消费"可行）。
        本方法是**唯一**的事件写入入口——没有 update / delete / bulk_insert。
        """
        self._events.append(record)
        if self._events_fh is not None:
            self._events_fh.write(record.model_dump_json() + "\n")
            self._events_fh.flush()

    def save_snapshot(self, snapshot: Snapshot) -> None:
        """保存某 tick 的快照。

        同 tick 再次调用会**覆盖**前一次——快照是"tick 结束状态"的幂等表示，
        不属于 append-only 语义管辖。
        """
        self._snapshots[snapshot.tick] = snapshot
        if self._snapshot_dir is not None:
            path = self._snapshot_dir / f"tick_{snapshot.tick}.json"
            path.write_text(
                snapshot.model_dump_json(indent=2), encoding="utf-8"
            )

    # ---------- 查询 ----------

    def get_events(
        self,
        *,
        tick: int | None = None,
        kind: EventKind | None = None,
        actor_id: str | None = None,
    ) -> list[EventRecord]:
        """按 tick / kind / actor_id 过滤事件；多个条件 AND 组合；返回副本。

        三个过滤器都可 None（不过滤该维度）；均 None 时返回全部事件的副本。
        返回的列表是新列表——调用方修改返回值不影响内部状态。
        """

        def matches(ev: EventRecord) -> bool:
            if tick is not None and ev.tick != tick:
                return False
            if kind is not None and ev.kind != kind:
                return False
            if actor_id is not None and ev.actor_id != actor_id:
                return False
            return True

        return [ev for ev in self._events if matches(ev)]

    def get_snapshot(self, tick: int) -> Snapshot | None:
        """读取某 tick 的快照；未保存过返回 None。"""
        return self._snapshots.get(tick)

    def all_snapshots(self) -> list[Snapshot]:
        """按 tick 升序返回全部已保存的快照；返回副本列表。"""
        return [self._snapshots[k] for k in sorted(self._snapshots.keys())]

    def event_count(self) -> int:
        """当前已 append 的事件总数。"""
        return len(self._events)

    # ---------- 资源管理 ----------

    def close(self) -> None:
        """关闭底层文件句柄。多次调用是幂等的。"""
        if self._events_fh is not None:
            self._events_fh.close()
            self._events_fh = None

    def __enter__(self) -> "EventLog":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # ---------- 路径访问（供测试与 UI 消费者定位） ----------

    @property
    def run_dir(self) -> Path | None:
        """持久化模式下的 ``runs/<run_id>/`` 目录；in-memory 模式为 None。"""
        return self._run_dir

    @property
    def events_file(self) -> Path | None:
        """持久化模式下的 ``events.jsonl`` 文件；in-memory 模式为 None。"""
        return self._events_file

    @property
    def snapshot_dir(self) -> Path | None:
        """持久化模式下的 ``snapshots/`` 目录；in-memory 模式为 None。"""
        return self._snapshot_dir
