"""tests/test_server_registry.py —— RuntimeRegistry 单元测试。

覆盖 D-017 第七节：注册 / 取 / 关闭 / 并发上限。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from core.providers.mock import MockProvider
from core.runtime import Runtime
from models.config_models import StorageConfig

from server.runtime_registry import RegistryFullError, RuntimeRegistry


# =============================================================================
# 测试 fixture：用最小 world + scenario 构造可管理的 Runtime
# =============================================================================


def _make_runtime(tmp_path: Path, run_id: str | None = None) -> Runtime:
    """从仓库内置的 minimal_market 场景构造一个 Runtime。

    StorageConfig.runs_root 指向 tmp_path——测试隔离。
    """
    from core.definition_loader import load_world_definition
    from core.scenario_loader import load_scenario

    scenario_path = Path("scenarios/minimal_market/scenario.yaml").resolve()
    world_path = scenario_path.parent / "world.yaml"
    world = load_world_definition(world_path)
    scenario = load_scenario(scenario_path, world)
    provider = MockProvider(fixed_response='{"action": "do_nothing", "params": {}}')
    storage = StorageConfig(version="0.1", persist=True, runs_root=str(tmp_path))
    return Runtime(world, scenario, provider, storage_config=storage, run_id=run_id)


@pytest.fixture
def registry() -> RuntimeRegistry:
    return RuntimeRegistry(max_concurrent=3)


# =============================================================================
# 基本 CRUD
# =============================================================================


class TestRegistryBasic:
    def test_init_invalid_max_concurrent(self) -> None:
        with pytest.raises(ValueError):
            RuntimeRegistry(max_concurrent=0)

    def test_register_and_get(self, registry: RuntimeRegistry, tmp_path: Path) -> None:
        rt = _make_runtime(tmp_path, run_id="r1")
        try:
            registry.register("r1", rt)
            assert registry.get("r1") is rt
            assert registry.active_count() == 1
        finally:
            registry.shutdown_all()

    def test_get_nonexistent_returns_none(
        self, registry: RuntimeRegistry
    ) -> None:
        assert registry.get("never-exist") is None

    def test_register_duplicate_raises(
        self, registry: RuntimeRegistry, tmp_path: Path
    ) -> None:
        rt1 = _make_runtime(tmp_path, run_id="dup")
        rt2 = _make_runtime(tmp_path, run_id="dup-2")
        try:
            registry.register("dup", rt1)
            with pytest.raises(ValueError, match="已注册"):
                registry.register("dup", rt2)
        finally:
            registry.shutdown_all()
            rt2.close()

    def test_max_concurrent_enforced(
        self, registry: RuntimeRegistry, tmp_path: Path
    ) -> None:
        rts = [_make_runtime(tmp_path, run_id=f"max-{i}") for i in range(3)]
        extra = _make_runtime(tmp_path, run_id="overflow")
        try:
            for i, rt in enumerate(rts):
                registry.register(f"max-{i}", rt)
            assert registry.active_count() == 3
            with pytest.raises(RegistryFullError):
                registry.register("overflow", extra)
        finally:
            registry.shutdown_all()
            extra.close()

    def test_shutdown_removes_run(
        self, registry: RuntimeRegistry, tmp_path: Path
    ) -> None:
        rt = _make_runtime(tmp_path, run_id="rm")
        registry.register("rm", rt)
        assert registry.shutdown("rm") is True
        assert registry.get("rm") is None
        assert registry.active_count() == 0

    def test_shutdown_nonexistent_returns_false(
        self, registry: RuntimeRegistry
    ) -> None:
        assert registry.shutdown("never-exist") is False

    def test_shutdown_all_closes_all(
        self, registry: RuntimeRegistry, tmp_path: Path
    ) -> None:
        for i in range(3):
            registry.register(f"all-{i}", _make_runtime(tmp_path, run_id=f"all-{i}"))
        closed = registry.shutdown_all()
        assert closed == 3
        assert registry.active_count() == 0

    def test_get_created_at_returns_datetime(
        self, registry: RuntimeRegistry, tmp_path: Path
    ) -> None:
        rt = _make_runtime(tmp_path, run_id="time")
        try:
            registry.register("time", rt)
            ts = registry.get_created_at("time")
            assert ts is not None
            assert ts.tzinfo is not None  # UTC
        finally:
            registry.shutdown_all()

    def test_get_created_at_nonexistent_returns_none(
        self, registry: RuntimeRegistry
    ) -> None:
        assert registry.get_created_at("never-exist") is None


# =============================================================================
# list_summaries
# =============================================================================


class TestListSummaries:
    def test_empty_registry_returns_empty(
        self, registry: RuntimeRegistry
    ) -> None:
        assert registry.list_summaries() == []

    def test_active_run_status(
        self, registry: RuntimeRegistry, tmp_path: Path
    ) -> None:
        rt = _make_runtime(tmp_path, run_id="active")
        try:
            registry.register("active", rt)
            summaries = registry.list_summaries()
            assert len(summaries) == 1
            s = summaries[0]
            assert s.run_id == "active"
            assert s.status == "active"
            assert s.current_tick == 0
            assert s.world_id == "minimal-market"
            assert s.scenario_id == "walkthrough-min"
            assert s.total_ticks == 5
        finally:
            registry.shutdown_all()

    def test_paused_run_status(
        self, registry: RuntimeRegistry, tmp_path: Path
    ) -> None:
        rt = _make_runtime(tmp_path, run_id="paused")
        rt.pause()
        try:
            registry.register("paused", rt)
            summaries = registry.list_summaries()
            assert summaries[0].status == "paused"
        finally:
            registry.shutdown_all()

    def test_finished_run_status(
        self, registry: RuntimeRegistry, tmp_path: Path
    ) -> None:
        """跑到 total_ticks 之后，registry 视它为 finished。"""
        rt = _make_runtime(tmp_path, run_id="done")
        try:
            for _ in range(rt.scenario.config.total_ticks):
                rt.step()
            registry.register("done", rt)
            summaries = registry.list_summaries()
            assert summaries[0].status == "finished"
            assert summaries[0].current_tick == 5
        finally:
            registry.shutdown_all()

    def test_multiple_runs_ordered(
        self, registry: RuntimeRegistry, tmp_path: Path
    ) -> None:
        for i in range(3):
            registry.register(f"m-{i}", _make_runtime(tmp_path, run_id=f"m-{i}"))
        try:
            summaries = registry.list_summaries()
            assert len(summaries) == 3
            run_ids = {s.run_id for s in summaries}
            assert run_ids == {"m-0", "m-1", "m-2"}
        finally:
            registry.shutdown_all()


# =============================================================================
# 容错：Runtime.close() 失败不影响 registry 清理
# =============================================================================


class TestErrorTolerance:
    def test_shutdown_tolerates_close_failure(
        self, registry: RuntimeRegistry, tmp_path: Path
    ) -> None:
        rt = _make_runtime(tmp_path, run_id="badclose")
        registry.register("badclose", rt)

        # 让 close() 抛错——验证 shutdown 仍清理 dict
        rt.close = lambda: (_ for _ in ()).throw(RuntimeError("boom"))  # type: ignore[method-assign]

        assert registry.shutdown("badclose") is True
        assert registry.get("badclose") is None
        assert registry.active_count() == 0
