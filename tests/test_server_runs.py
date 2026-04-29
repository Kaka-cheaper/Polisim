"""tests/test_server_runs.py —— /api/v1/runs/* 路由完整 lifecycle 测试。

覆盖 D-017 第 3.1-3.4 节：CRUD + 控制 + 状态查询 + 事件查询。

**测试策略**：

- 每个测试用 ``client`` fixture 独立初始化 app（保证 registry 隔离）
- `_create_min_run` helper：POST /runs 创建 minimal_market run，返回 run_id
- 测试覆盖：成功路径 + 关键 4xx/5xx 错误形态
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.app import AppConfig, create_app


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """每个测试一个独立 app + 临时 runs 目录。"""
    config = AppConfig(
        runs_root=tmp_path,
        scenarios_root=Path("scenarios").resolve(),
        max_concurrent_runs=3,
    )
    app = create_app(config)
    with TestClient(app) as c:
        yield c


def _create_min_run(client: TestClient, **overrides) -> str:
    """POST /runs 创建一个 minimal_market run，返回 run_id。"""
    body = {
        "scenario_path": "scenarios/minimal_market/scenario.yaml",
        "llm_provider": "mock",
    }
    body.update(overrides)
    resp = client.post("/api/v1/runs", json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()["summary"]["run_id"]


# =============================================================================
# POST /runs 创建
# =============================================================================


class TestCreateRun:
    def test_create_minimal_market_returns_run_detail(
        self, client: TestClient
    ) -> None:
        resp = client.post(
            "/api/v1/runs",
            json={
                "scenario_path": "scenarios/minimal_market/scenario.yaml",
                "llm_provider": "mock",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        # RunDetail 形状
        assert "summary" in body
        assert "world" in body
        assert "scenario" in body
        assert "runtime_config" in body

        summary = body["summary"]
        assert summary["scenario_id"] == "walkthrough-min"
        assert summary["world_id"] == "minimal-market"
        assert summary["status"] == "active"
        assert summary["current_tick"] == 0
        assert summary["total_ticks"] == 5

    def test_create_with_explicit_run_id(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/runs",
            json={
                "scenario_path": "scenarios/minimal_market/scenario.yaml",
                "run_id": "custom-id-001",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["summary"]["run_id"] == "custom-id-001"

    def test_create_with_ticks_override(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/runs",
            json={
                "scenario_path": "scenarios/minimal_market/scenario.yaml",
                "ticks_override": 3,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["summary"]["total_ticks"] == 3

    def test_create_nonexistent_scenario_returns_404(
        self, client: TestClient
    ) -> None:
        resp = client.post(
            "/api/v1/runs",
            json={"scenario_path": "scenarios/nonexistent/scenario.yaml"},
        )
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"

    def test_create_invalid_request_returns_422(
        self, client: TestClient
    ) -> None:
        """缺 scenario_path → FastAPI 自身 422（pydantic 验证）。"""
        resp = client.post("/api/v1/runs", json={})
        assert resp.status_code == 422

    def test_create_max_concurrent_returns_503(
        self, client: TestClient
    ) -> None:
        # max_concurrent_runs=3，开 3 个之后第 4 个应该 503
        # 显式给 run_id——避免 generate_run_id 同一秒冲突
        for i in range(3):
            r = client.post(
                "/api/v1/runs",
                json={
                    "scenario_path": "scenarios/minimal_market/scenario.yaml",
                    "run_id": f"max-test-{i}",
                },
            )
            assert r.status_code == 201, r.text
        resp = client.post(
            "/api/v1/runs",
            json={
                "scenario_path": "scenarios/minimal_market/scenario.yaml",
                "run_id": "overflow",
            },
        )
        assert resp.status_code == 503
        assert resp.json()["error"]["code"] == "REGISTRY_FULL"


# =============================================================================
# GET /runs 列表
# =============================================================================


class TestListRuns:
    def test_empty_registry_returns_empty_list(
        self, client: TestClient
    ) -> None:
        resp = client.get("/api/v1/runs")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_after_creation(self, client: TestClient) -> None:
        rid = _create_min_run(client)
        resp = client.get("/api/v1/runs")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["run_id"] == rid

    def test_filter_by_status_active(self, client: TestClient) -> None:
        _create_min_run(client)
        resp = client.get("/api/v1/runs", params={"status": "active"})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_filter_by_status_paused(self, client: TestClient) -> None:
        rid = _create_min_run(client)
        client.post(f"/api/v1/runs/{rid}/pause")
        resp = client.get("/api/v1/runs", params={"status": "paused"})
        items = resp.json()
        assert len(items) == 1
        assert items[0]["status"] == "paused"

    def test_invalid_status_returns_400(self, client: TestClient) -> None:
        resp = client.get("/api/v1/runs", params={"status": "weird"})
        assert resp.status_code == 400


# =============================================================================
# GET /runs/{run_id}
# =============================================================================


class TestGetRun:
    def test_get_existing_run(self, client: TestClient) -> None:
        rid = _create_min_run(client)
        resp = client.get(f"/api/v1/runs/{rid}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["summary"]["run_id"] == rid
        # scenario.ui_layout 必须透传到响应（D-017 反向校验）
        assert body["scenario"]["ui_layout"] == "entity_card"

    def test_get_nonexistent_returns_404(self, client: TestClient) -> None:
        resp = client.get("/api/v1/runs/never-exist")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


# =============================================================================
# DELETE /runs/{run_id}
# =============================================================================


class TestDeleteRun:
    def test_delete_returns_204(self, client: TestClient) -> None:
        rid = _create_min_run(client)
        resp = client.delete(f"/api/v1/runs/{rid}")
        assert resp.status_code == 204
        assert client.get(f"/api/v1/runs/{rid}").status_code == 404

    def test_delete_nonexistent_is_idempotent(
        self, client: TestClient
    ) -> None:
        """v0.2 简化：DELETE 不存在的 run 也返 204（幂等）。"""
        resp = client.delete("/api/v1/runs/never-exist")
        assert resp.status_code == 204


# =============================================================================
# 控制：step / pause / resume
# =============================================================================


class TestControlOperations:
    def test_step_advances_tick(self, client: TestClient) -> None:
        rid = _create_min_run(client)
        resp = client.post(f"/api/v1/runs/{rid}/step")
        assert resp.status_code == 200
        body = resp.json()
        assert body["tick"] == 1
        assert isinstance(body["events"], list)

    def test_step_then_get_state(self, client: TestClient) -> None:
        rid = _create_min_run(client)
        client.post(f"/api/v1/runs/{rid}/step")
        resp = client.get(f"/api/v1/runs/{rid}/state")
        assert resp.status_code == 200
        state = resp.json()
        assert state["tick"] == 1

    def test_pause_blocks_step(self, client: TestClient) -> None:
        rid = _create_min_run(client)
        # pause
        r1 = client.post(f"/api/v1/runs/{rid}/pause")
        assert r1.status_code == 200
        assert r1.json()["status"] == "paused"
        # step 在 paused 状态 → 409
        r2 = client.post(f"/api/v1/runs/{rid}/step")
        assert r2.status_code == 409
        assert r2.json()["error"]["code"] == "RUNTIME_PAUSED"

    def test_resume_allows_step(self, client: TestClient) -> None:
        rid = _create_min_run(client)
        client.post(f"/api/v1/runs/{rid}/pause")
        client.post(f"/api/v1/runs/{rid}/resume")
        r = client.post(f"/api/v1/runs/{rid}/step")
        assert r.status_code == 200

    def test_step_after_total_ticks_returns_410(
        self, client: TestClient
    ) -> None:
        rid = _create_min_run(client, ticks_override=2)
        # 跑两次到 total_ticks
        client.post(f"/api/v1/runs/{rid}/step")
        client.post(f"/api/v1/runs/{rid}/step")
        # 第 3 步 → 410
        r = client.post(f"/api/v1/runs/{rid}/step")
        assert r.status_code == 410
        assert r.json()["error"]["code"] == "RUNTIME_TERMINATED"

    def test_step_on_nonexistent_returns_404(self, client: TestClient) -> None:
        r = client.post("/api/v1/runs/never-exist/step")
        assert r.status_code == 404


# =============================================================================
# 状态查询
# =============================================================================


class TestStateQuery:
    def test_get_state_initial(self, client: TestClient) -> None:
        rid = _create_min_run(client)
        resp = client.get(f"/api/v1/runs/{rid}/state")
        assert resp.status_code == 200
        state = resp.json()
        assert state["tick"] == 0
        assert "company_a" in state["entities"]

    def test_list_snapshots_initial_has_tick0(
        self, client: TestClient
    ) -> None:
        rid = _create_min_run(client)
        resp = client.get(f"/api/v1/runs/{rid}/snapshots")
        assert resp.status_code == 200
        body = resp.json()
        # Runtime 构造时已经写 tick=0 快照
        assert 0 in body["ticks"]

    def test_list_snapshots_after_steps(self, client: TestClient) -> None:
        rid = _create_min_run(client)
        for _ in range(3):
            client.post(f"/api/v1/runs/{rid}/step")
        resp = client.get(f"/api/v1/runs/{rid}/snapshots")
        ticks = resp.json()["ticks"]
        # 至少有 tick 0/1/2/3
        assert all(t in ticks for t in [0, 1, 2, 3])

    def test_get_snapshot_at_specific_tick(self, client: TestClient) -> None:
        rid = _create_min_run(client)
        client.post(f"/api/v1/runs/{rid}/step")
        client.post(f"/api/v1/runs/{rid}/step")
        resp = client.get(f"/api/v1/runs/{rid}/snapshots/2")
        assert resp.status_code == 200
        assert resp.json()["tick"] == 2

    def test_get_snapshot_missing_tick_returns_404(
        self, client: TestClient
    ) -> None:
        rid = _create_min_run(client)
        resp = client.get(f"/api/v1/runs/{rid}/snapshots/999")
        assert resp.status_code == 404


# =============================================================================
# 事件查询
# =============================================================================


class TestEventsQuery:
    def test_query_events_empty_initially(self, client: TestClient) -> None:
        rid = _create_min_run(client)
        resp = client.get(f"/api/v1/runs/{rid}/events")
        assert resp.status_code == 200
        body = resp.json()
        # 初始可能有 0 事件——total >= 0
        assert "events" in body
        assert "total" in body
        assert "has_more" in body

    def test_query_events_after_step(self, client: TestClient) -> None:
        rid = _create_min_run(client)
        client.post(f"/api/v1/runs/{rid}/step")
        resp = client.get(f"/api/v1/runs/{rid}/events")
        body = resp.json()
        assert body["total"] > 0
        # 必含 decision_proposed / action_executed 这种 EventKind
        kinds = {e["kind"] for e in body["events"]}
        assert "decision_proposed" in kinds or "action_executed" in kinds

    def test_query_events_filter_by_tick(self, client: TestClient) -> None:
        rid = _create_min_run(client)
        client.post(f"/api/v1/runs/{rid}/step")
        client.post(f"/api/v1/runs/{rid}/step")
        resp = client.get(
            f"/api/v1/runs/{rid}/events", params={"tick": 1}
        )
        body = resp.json()
        for ev in body["events"]:
            assert ev["tick"] == 1

    def test_query_events_filter_by_kind(self, client: TestClient) -> None:
        rid = _create_min_run(client)
        client.post(f"/api/v1/runs/{rid}/step")
        resp = client.get(
            f"/api/v1/runs/{rid}/events",
            params={"kind": "decision_proposed"},
        )
        body = resp.json()
        for ev in body["events"]:
            assert ev["kind"] == "decision_proposed"

    def test_query_events_pagination(self, client: TestClient) -> None:
        rid = _create_min_run(client)
        for _ in range(3):
            client.post(f"/api/v1/runs/{rid}/step")

        all_resp = client.get(f"/api/v1/runs/{rid}/events", params={"limit": 1000})
        all_total = all_resp.json()["total"]
        assert all_total > 1

        # 分页：limit=1 → 多次取应该收集到全部
        page1 = client.get(
            f"/api/v1/runs/{rid}/events", params={"limit": 1, "offset": 0}
        ).json()
        assert len(page1["events"]) == 1
        if all_total > 1:
            assert page1["has_more"] is True

    def test_query_events_until_tick(self, client: TestClient) -> None:
        rid = _create_min_run(client)
        for _ in range(3):
            client.post(f"/api/v1/runs/{rid}/step")
        resp = client.get(
            f"/api/v1/runs/{rid}/events", params={"until_tick": 2}
        )
        for ev in resp.json()["events"]:
            assert ev["tick"] <= 2

    def test_invalid_limit_returns_400(self, client: TestClient) -> None:
        rid = _create_min_run(client)
        # FastAPI 路由层 Query(le=1000) 拦截 → 422 (validation error)；
        # 服务端 ValueError 也是 400——任何 4xx 都接受
        resp = client.get(
            f"/api/v1/runs/{rid}/events", params={"limit": 5000}
        )
        assert 400 <= resp.status_code < 500
