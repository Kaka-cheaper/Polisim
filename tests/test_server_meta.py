"""tests/test_server_meta.py —— /scenarios + /health 路由。"""

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
    """构造一个 TestClient——指向真实 scenarios/ + 临时 runs/ 目录。"""
    config = AppConfig(
        runs_root=tmp_path,
        scenarios_root=Path("scenarios").resolve(),
        max_concurrent_runs=3,
    )
    app = create_app(config)
    with TestClient(app) as c:
        yield c


# =============================================================================
# /health
# =============================================================================


class TestHealth:
    def test_health_returns_ok(self, client: TestClient) -> None:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["version"] == "0.2.0"
        assert body["active_runs"] == 0


# =============================================================================
# /scenarios
# =============================================================================


class TestScenariosListing:
    def test_list_includes_minimal_market(self, client: TestClient) -> None:
        resp = client.get("/api/v1/scenarios")
        assert resp.status_code == 200
        items = resp.json()
        assert isinstance(items, list)
        assert len(items) >= 2  # minimal_market + three_party_negotiation

        ids = {s["id"] for s in items}
        assert "walkthrough-min" in ids
        assert "walkthrough-three-party" in ids

    def test_minimal_market_ui_layout_entity_card(
        self, client: TestClient
    ) -> None:
        """D-017 反向校验：minimal_market 应声明 ui_layout=entity_card。"""
        resp = client.get("/api/v1/scenarios")
        items = resp.json()
        target = next(s for s in items if s["id"] == "walkthrough-min")
        assert target["ui_layout"] == "entity_card"
        assert target["world_id"] == "minimal-market"
        assert target["total_ticks"] == 5

    def test_three_party_ui_layout_relation_graph(
        self, client: TestClient
    ) -> None:
        """D-017 反向校验：three_party_negotiation 应声明 ui_layout=relation_graph。"""
        resp = client.get("/api/v1/scenarios")
        items = resp.json()
        target = next(
            s for s in items if s["id"] == "walkthrough-three-party"
        )
        assert target["ui_layout"] == "relation_graph"
        assert target["total_ticks"] == 8

    def test_scenarios_sorted_by_id(self, client: TestClient) -> None:
        resp = client.get("/api/v1/scenarios")
        items = resp.json()
        ids = [s["id"] for s in items]
        assert ids == sorted(ids)

    def test_summary_has_required_fields(self, client: TestClient) -> None:
        """每个 ScenarioSummary 必备字段（D-017 第 3.5 节）。"""
        resp = client.get("/api/v1/scenarios")
        items = resp.json()
        for s in items:
            for field in [
                "path",
                "id",
                "name",
                "description",
                "total_ticks",
                "ui_layout",
                "world_id",
            ]:
                assert field in s, f"{s['id']} 缺字段 {field}"

    def test_empty_scenarios_root_returns_empty_list(
        self, tmp_path: Path
    ) -> None:
        """scenarios_root 不存在或为空时返空列表，不 500。"""
        empty_root = tmp_path / "empty_scenarios"
        config = AppConfig(
            runs_root=tmp_path / "runs",
            scenarios_root=empty_root,
        )
        app = create_app(config)
        with TestClient(app) as c:
            resp = c.get("/api/v1/scenarios")
            assert resp.status_code == 200
            assert resp.json() == []


# =============================================================================
# OpenAPI 文档自动生成
# =============================================================================


class TestOpenAPI:
    def test_openapi_json_endpoint(self, client: TestClient) -> None:
        resp = client.get("/api/v1/openapi.json")
        assert resp.status_code == 200
        spec = resp.json()
        assert spec["info"]["title"] == "Polisim API"
        assert spec["info"]["version"] == "0.2.0"
        # 检查关键 endpoint 都登记了
        paths = spec["paths"]
        assert "/api/v1/runs" in paths
        assert "/api/v1/scenarios" in paths
        assert "/api/v1/health" in paths
        assert "/api/v1/runs/{run_id}/intervene" in paths
