"""server/services/run_service.py —— Run 生命周期 + 状态查询的业务层（D-017 第 6.1 节）。

**与 FastAPI 解耦**——所有方法只接受裸数据，不接 Request 对象。
意味着 CLI / 第三方 SDK / 未来 mobile 端都能直接复用 RunService。

**职责边界**：

- 接收平台专有 schema（CreateRunRequest 等）
- 调用 v1 内核：`load_world / load_scenario / Runtime / EventLog`
- 调用 v1 LLM：`MockProvider / OpenAIProvider`
- 把内核异常自然抛出（由 server/api/v1/errors.py 的 handler 映射成 HTTP）
- 返回 v1 模型（TickResult / WorldState / Snapshot / EventRecord）或 server 平台 schema

**v0.2 暂不做**：

- 分布式 / 跨进程 run 共享 → 见 D-017 第 7.2 节演进路径
- 鉴权 / 多用户 → v0.3+
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from core.analysis import analyze_run
from core.definition_loader import load_world_definition
from core.providers.base import LLMProvider
from core.providers.mock import MockProvider
from core.runtime import Runtime
from core.scenario_loader import load_scenario
from models.config_models import RuntimeConfig, StorageConfig
from models.runtime_models import EventRecord, Snapshot, TickResult, WorldState

from server.api.v1.schemas import (
    CreateRunRequest,
    EventListResponse,
    PauseResumeResponse,
    RunDetail,
    RunSummary,
    SnapshotsListResponse,
)
from server.api.v1.ws_events import (
    PausedEvent,
    PausedPayload,
    RunFinishedEvent,
    RunResumedEvent,
    RunResumedPayload,
    TickAdvancedEvent,
)
from server.runtime_registry import RuntimeRegistry
from server.services.stream_service import StreamService

_logger = logging.getLogger(__name__)


# 默认 mock LLM 响应——所有 llm 实体走 do_nothing（与 cli/run.py 一致）
_DEFAULT_LLM_RESPONSE = json.dumps({"action": "do_nothing", "params": {}})


class RunService:
    """Run 生命周期管理 + 状态查询。

    实例化时持有 ``RuntimeRegistry`` 与 ``runs_root``：

    - registry 管"活跃" run（在内存中跑）
    - runs_root 是磁盘 ``runs/`` 根目录——v0.2 不做归档查询，但保留参数方便 v0.3+ 演进
    """

    def __init__(
        self,
        registry: RuntimeRegistry,
        runs_root: Path,
        stream_service: StreamService | None = None,
    ) -> None:
        self._registry = registry
        self._runs_root = runs_root
        self._stream_service = stream_service

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def create_run(self, req: CreateRunRequest) -> RunDetail:
        """创建并注册新 Runtime。

        失败模式（已被 server/api/v1/errors.py 映射为对应状态码）：

        - `FileNotFoundError`——scenario_path / world_path 不存在 → 404
        - `ValueError`——schema 校验失败 → 400
        - `SemanticValidationError`——D-013 跨层校验失败 → 422
        - `ProviderError`——OpenAI provider 鉴权 / 配置错 → 502
        - `RegistryFullError`——超出并发上限 → 由 app 层映射 503

        注：本方法**不**捕获这些异常——交给 server 全局 handler 处理。
        """
        scenario_path = Path(req.scenario_path).resolve()
        world_path = (
            Path(req.world_path).resolve() if req.world_path else None
        )
        resolved_world = self._resolve_world_path(scenario_path, world_path)

        world = load_world_definition(resolved_world)
        scenario = load_scenario(scenario_path, world)

        if req.ticks_override is not None:
            scenario.config.total_ticks = req.ticks_override

        provider = self._build_provider(req)

        runtime_config = req.runtime_config or RuntimeConfig(version="0.1")
        storage_config = StorageConfig(
            version="0.1",
            persist=True,
            runs_root=str(self._runs_root),
        )

        runtime = Runtime(
            world,
            scenario,
            provider,
            runtime_config=runtime_config,
            storage_config=storage_config,
            run_id=req.run_id,
        )
        # 注册到 registry——失败时主动 close runtime，避免泄露 EventLog 文件句柄
        try:
            self._registry.register(runtime.run_id, runtime)
        except Exception:
            runtime.close()
            raise

        return self._build_run_detail(runtime, runtime_config)

    def list_runs(
        self,
        status: str = "all",
        limit: int = 50,
        offset: int = 0,
    ) -> list[RunSummary]:
        """列出 run。

        v0.2 仅返活跃 registry 内容；归档（已 GC 的 run）查询推迟到 v0.3+。

        - status="all"——返全部
        - status in {"active", "paused", "finished"}——按状态过滤
        - status="archived"——v0.2 始终空（没归档机制）
        """
        if limit < 1 or limit > 1000:
            raise ValueError(f"limit 必须在 [1, 1000]，收到 {limit}")
        if offset < 0:
            raise ValueError(f"offset 不能为负，收到 {offset}")
        if status not in {"all", "active", "paused", "finished", "archived"}:
            raise ValueError(
                f"status 必须是 all / active / paused / finished / archived，"
                f"收到 {status!r}"
            )

        all_summaries = self._registry.list_summaries()
        if status == "archived":
            return []
        if status != "all":
            all_summaries = [s for s in all_summaries if s.status == status]
        return all_summaries[offset : offset + limit]

    def get_run(self, run_id: str) -> RunDetail:
        """run 详情；不存在抛 ValueError → 404。"""
        runtime = self._get_or_404(run_id)
        return self._build_run_detail(runtime, runtime.runtime_config)

    def delete_run(self, run_id: str) -> None:
        """关闭并移除 run；不存在则当作幂等成功（测试场景下重试友好）。"""
        self._registry.shutdown(run_id)

    # ------------------------------------------------------------------
    # 控制
    # ------------------------------------------------------------------

    def step(self, run_id: str) -> TickResult:
        """推进一个 tick + 推送 WebSocket 事件。

        **paused 状态下的单步语义**（PR4-fix，session 41 P3 pitfall 修复）：

        若 runtime 处于 paused 状态（手动 pause / every_tick / 断点）调用 step：

        1. 临时 ``resume()`` → ``step()`` → 推进 1 tick
        2. 场景 A（手动暂停单步）：若 step 后 runtime 未自动 pause，
           主动 ``pause()`` + 推 ``PausedEvent(reason="manual")``
        3. 场景 B/C（every_tick / 断点）：runtime 内部 ``paused_after=True``
           自动 pause；``_broadcast_tick`` 已推 PausedEvent

        这样 UI ControlBar「paused 时单步」按钮的语义（推进 1 tick 后保持 paused）
        与 v0.1 runtime「paused 时不允许 step」契约自然桥接。

        推送顺序（D-017 第 4.3 节）：

        1. **tick_advanced** —— 永远推（含本次 step 的 TickResult）
        2. **paused** —— 当 ``result.paused_after=True``（every_tick / breakpoint）
           或场景 A 手动重 pause 时；``reached_total_ticks=True`` 时跳过
        3. **run_finished** —— 仅当 ``result.reached_total_ticks=True`` ——
           **代替** paused，跑 Phase A 分析后推；推完由 stream_service 关闭订阅

        Runtime.step() 自然抛 TerminatedError / RulesError 等——交给 server 全局
        handler 映射为 4xx/5xx；本方法**不**捕获。``PausedError`` 在场景 A/B/C
        包装下不会再抛出（已 resume）。
        """
        runtime = self._get_or_404(run_id)
        was_paused = runtime.is_paused()
        if was_paused:
            runtime.resume()
        result = runtime.step()
        # 场景 A：手动暂停后单步 —— 保持 paused（runtime 未自动 pause 时）
        needs_manual_repause = (
            was_paused
            and not result.paused_after
            and not result.reached_total_ticks
        )
        if needs_manual_repause:
            runtime.pause()
            # **关键修正**：把 paused_after 标 True 写入 broadcast 的 result，避免 client
            # `useRunStream.onTick` 看到 paused_after=False 误把 status 切回 running
            # → 触发 auto-step useEffect race → 直跑到 finished。
            # HTTP response 的 paused_after=True 也准确反映服务端真实状态。
            result = result.model_copy(update={"paused_after": True})
        # 场景 A 时跳过 _broadcast_tick 内部的 paused 推送（reason 会误标 every_tick）；
        # 由下面显式推 reason="manual" 的 PausedEvent 接管
        self._broadcast_tick(
            run_id, result, runtime,
            skip_paused_broadcast=needs_manual_repause,
        )
        if needs_manual_repause and self._stream_service is not None:
            self._stream_service.broadcast(
                run_id,
                PausedEvent(
                    data=PausedPayload(
                        tick=runtime.current_tick(),
                        breakpoint_ids=[],
                        reason="manual",
                    )
                ),
            )
        return result

    def pause(self, run_id: str) -> PauseResumeResponse:
        """暂停 + 推送 paused 事件（reason="manual"）。幂等。"""
        runtime = self._get_or_404(run_id)
        was_paused = runtime.is_paused()
        runtime.pause()
        if not was_paused and self._stream_service is not None:
            # 仅状态变化时推送，避免重复 paused
            self._stream_service.broadcast(
                run_id,
                PausedEvent(
                    data=PausedPayload(
                        tick=runtime.current_tick(),
                        breakpoint_ids=[],
                        reason="manual",
                    )
                ),
            )
        return PauseResumeResponse(status="paused", tick=runtime.current_tick())

    def resume(self, run_id: str) -> PauseResumeResponse:
        """恢复 + 推送 RunResumedEvent（PR4-fix，session 41 P3 修复）。幂等。

        原设计（v0.2 初版）不推 ws 事件——计划由下一次 step 推的 tick_advanced 隐含告知
        客户端。**但 client ``useRunStream`` 状态机仅靠 ws 推送驱动 status 切换**，resume 后不
        推会导致 client status 永远 paused，auto-step useEffect 不启动，step 永远不发，
        ws 永远不推——**死锁**。

        修法：与 PausedEvent 对称，resume 后推 RunResumedEvent（仅当真从 paused 切回时，
        幂等调用不重复推送）。client ``useRunStream.onResumed`` 切 status="running" +
        清 pausedInfo。
        """
        runtime = self._get_or_404(run_id)
        was_paused = runtime.is_paused()
        runtime.resume()
        if was_paused and self._stream_service is not None:
            self._stream_service.broadcast(
                run_id,
                RunResumedEvent(
                    data=RunResumedPayload(tick=runtime.current_tick())
                ),
            )
        return PauseResumeResponse(status="running", tick=runtime.current_tick())

    # ------------------------------------------------------------------
    # WebSocket 推送 helper
    # ------------------------------------------------------------------

    def _broadcast_tick(
        self,
        run_id: str,
        result: TickResult,
        runtime: Runtime,
        *,
        skip_paused_broadcast: bool = False,
    ) -> None:
        """根据 TickResult 推送 1-2 条事件到订阅者。

        ``skip_paused_broadcast=True`` 用于 step 包装的"场景 A 手动暂停单步"路径——
        调用方会自己推 reason="manual" 的 PausedEvent，避免本方法推 every_tick 误标。
        """
        if self._stream_service is None:
            return  # 无 stream_service（CLI / 单测时）跳过
        # 1. 永远推 tick_advanced
        self._stream_service.broadcast(
            run_id, TickAdvancedEvent(data=result)
        )
        # 2. paused 或 run_finished
        if result.reached_total_ticks:
            # 跑 Phase A 分析（不增强）+ 推 run_finished + 关闭订阅
            try:
                if runtime.run_dir is not None:
                    analysis = analyze_run(runtime.run_dir)
                    self._stream_service.broadcast(
                        run_id, RunFinishedEvent(data=analysis)
                    )
            except Exception:  # noqa: BLE001 顶层守护——Phase A 失败不阻断 step
                # F5（session 45）：失败不再静默——log warning 保留诊断信息
                # （analyze_run 解析 events.jsonl 异常 / IO 错等）。
                # 前端仍可手动调 GET /analysis 重新生成。
                _logger.warning(
                    "Phase A analyze_run failed for run_id=%s; "
                    "RunFinishedEvent ws push skipped, client may retry GET /analysis",
                    run_id,
                    exc_info=True,
                )
            # 通知所有订阅者：该 run 已结束
            self._stream_service.close_run(run_id)
        elif result.paused_after and not skip_paused_broadcast:
            # 自动暂停（every_tick 或 breakpoint）
            bp_ids = list(result.triggered_breakpoints or [])
            # reason 字面量在 Literal 范围内——不需 type:ignore（session 33 F5 清理）
            reason: Literal["breakpoint", "every_tick"] = (
                "breakpoint" if bp_ids else "every_tick"
            )
            self._stream_service.broadcast(
                run_id,
                PausedEvent(
                    data=PausedPayload(
                        tick=runtime.current_tick(),
                        breakpoint_ids=bp_ids,
                        reason=reason,
                    )
                ),
            )

    # ------------------------------------------------------------------
    # 状态查询
    # ------------------------------------------------------------------

    def get_state(self, run_id: str) -> WorldState:
        """当前 WorldState。"""
        runtime = self._get_or_404(run_id)
        return runtime.get_state()

    def get_snapshot(self, run_id: str, tick: int) -> Snapshot:
        """指定 tick 的快照；缺失抛 ValueError → 404。"""
        runtime = self._get_or_404(run_id)
        snap = runtime.get_snapshot(tick)
        if snap is None:
            raise FileNotFoundError(
                f"run_id={run_id!r} 在 tick={tick} 没有快照"
            )
        return snap

    def list_snapshots(self, run_id: str) -> SnapshotsListResponse:
        """列出已保存的 tick 编号（升序）。

        实现思路：从磁盘 ``snapshots/`` 目录扫描——v0.1 EventLog 已落 ``tick_N.json``。
        """
        runtime = self._get_or_404(run_id)
        snap_dir = runtime.event_log.snapshot_dir
        if snap_dir is None or not snap_dir.exists():
            return SnapshotsListResponse(ticks=[])
        ticks: list[int] = []
        for path in snap_dir.glob("tick_*.json"):
            stem = path.stem  # "tick_3"
            if stem.startswith("tick_"):
                try:
                    ticks.append(int(stem[len("tick_") :]))
                except ValueError:
                    continue  # 异常文件名容忍跳过
        ticks.sort()
        return SnapshotsListResponse(ticks=ticks)

    # ------------------------------------------------------------------
    # 事件查询（含分页 + 过滤）
    # ------------------------------------------------------------------

    def query_events(
        self,
        run_id: str,
        tick: int | None = None,
        kind: str | None = None,
        actor_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
        until_tick: int | None = None,
    ) -> EventListResponse:
        """事件查询。

        - 优先内存 EventLog（活跃 run）
        - until_tick：返 ``tick <= until_tick`` 的所有事件
        - tick：精确匹配某个 tick（与 until_tick 二选一）
        - kind / actor_id：按字段过滤
        - limit / offset：分页

        返 ``EventListResponse`` 含分页 metadata。
        """
        # session 45 F2：cap 与 route 层 Query(le=5000) 对齐
        if limit < 1 or limit > 5000:
            raise ValueError(f"limit 必须在 [1, 5000]，收到 {limit}")
        if offset < 0:
            raise ValueError(f"offset 不能为负，收到 {offset}")
        if tick is not None and until_tick is not None:
            raise ValueError("tick 与 until_tick 不能同时使用")

        runtime = self._get_or_404(run_id)
        event_log = runtime.event_log

        # 走 EventLog.get_events 的内存查询（含 kind / actor_id 过滤）
        events: list[EventRecord] = event_log.get_events(
            tick=tick,
            kind=kind,  # type: ignore[arg-type]  EventLog 接收 str；EventKind Literal 由元素自身保证
            actor_id=actor_id,
        )

        # until_tick 过滤（EventLog.get_events 不支持，本层补）
        if until_tick is not None:
            events = [e for e in events if e.tick <= until_tick]

        total = len(events)
        page = events[offset : offset + limit]
        has_more = (offset + len(page)) < total
        return EventListResponse(events=page, total=total, has_more=has_more)

    # ------------------------------------------------------------------
    # 内部 helper
    # ------------------------------------------------------------------

    def _get_or_404(self, run_id: str) -> Runtime:
        """统一拿 Runtime 或抛 FileNotFoundError → 404。

        用 FileNotFoundError 而不是 ValueError——server/api/v1/errors.py 的
        映射表里 FileNotFoundError → 404，正好匹配 D-017 设计的"run 不存在 = 404"。
        """
        runtime = self._registry.get(run_id)
        if runtime is None:
            raise FileNotFoundError(f"run_id={run_id!r} 不存在或已归档")
        return runtime

    @staticmethod
    def _resolve_world_path(
        scenario_path: Path, explicit: Path | None
    ) -> Path:
        """复用 cli/run.py 的 world 路径约定：显式 > <scenario_dir>/world.yaml。"""
        if explicit is not None:
            return explicit
        candidate = scenario_path.parent / "world.yaml"
        if not candidate.exists():
            raise FileNotFoundError(
                f"未显式提供 world_path，且 {candidate} 不存在。"
                f"请在请求中指定 world_path。"
            )
        return candidate

    @staticmethod
    def _build_provider(req: CreateRunRequest) -> LLMProvider:
        """按 req.llm_provider 分派 provider 工厂。

        v0.2 暴露的 provider 类型：mock / openai。`mock` 用 do_nothing 默认响应；
        `openai` 走 config/llm.yaml + 环境变量 API key（不在 server 配 key 显式入参）。
        """
        if req.llm_provider == "openai":
            # 延迟 import 避免无 openai 依赖时 mock 路径仍可用
            from core.providers.openai import OpenAIProvider
            from models.config_models import load_llm_config

            config_path = (
                Path(req.config_llm_path)
                if req.config_llm_path
                else Path("config/llm.yaml")
            )
            if not config_path.exists():
                raise FileNotFoundError(
                    f"llm_provider=openai 需要 LLM 配置文件，但 {config_path} 不存在"
                )
            llm_config = load_llm_config(config_path)
            key = req.provider_key or llm_config.default_provider
            if key not in llm_config.providers:
                raise ValueError(
                    f"provider_key {key!r} 未在 {config_path} 的 providers 中声明；"
                    f"可用 keys: {sorted(llm_config.providers.keys())}"
                )
            prov_config = llm_config.providers[key]
            if prov_config.provider != "openai":
                raise ValueError(
                    f"provider_key {key!r} 的 provider 字段是 "
                    f"{prov_config.provider!r}，不是 'openai'"
                )
            return OpenAIProvider(prov_config)
        # 默认 mock
        return MockProvider(fixed_response=_DEFAULT_LLM_RESPONSE)

    def _build_run_detail(
        self, runtime: Runtime, runtime_config: RuntimeConfig
    ) -> RunDetail:
        """从 Runtime 构造 RunDetail。

        所有"动态字段"（current_tick / status）从 Runtime 实时取；
        "静态字段"（world / scenario）走 @property 暴露的引用。
        """
        current = runtime.current_tick()
        total = runtime.scenario.config.total_ticks
        # status 用 Literal 注解，让 RunSummary 字段类型自然推断（去掉 session 33 F5）
        status: Literal["active", "paused", "finished"]
        if current >= total:
            status = "finished"
        elif runtime.is_paused():
            status = "paused"
        else:
            status = "active"
        created_at = self._registry.get_created_at(runtime.run_id) or datetime.now(
            timezone.utc
        )
        summary = RunSummary(
            run_id=runtime.run_id,
            world_id=runtime.scenario.world_id,
            scenario_id=runtime.scenario.scenario.id,
            status=status,
            current_tick=current,
            total_ticks=total,
            created_at=created_at,
        )
        return RunDetail(
            summary=summary,
            world=runtime.world,
            scenario=runtime.scenario,
            runtime_config=runtime_config,
        )
