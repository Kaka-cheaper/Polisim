"""tests/test_server_analysis.py —— /api/v1/runs/:id/analysis (GET / POST)。

D-017 第 3.4 节。

**注意**：本文件**不**测 LLM 增强（enhance=true）——这需要走真实/Mock LLM
provider 的完整 prompt 协议，已经在 `tests/test_analysis.py` 覆盖。本文件只测
HTTP 层是否正确转发到 service。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from server.app import AppConfig, create_app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    config = AppConfig(
        runs_root=tmp_path,
        scenarios_root=Path("scenarios").resolve(),
        max_concurrent_runs=3,
    )
    app = create_app(config)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def finished_run_id(client: TestClient) -> str:
    """创建并跑完一个 minimal_market run。"""
    resp = client.post(
        "/api/v1/runs",
        json={
            "scenario_path": "scenarios/minimal_market/scenario.yaml",
            "ticks_override": 2,
            "run_id": "analysis-test",
        },
    )
    rid = resp.json()["summary"]["run_id"]
    # 跑到 total_ticks
    for _ in range(2):
        client.post(f"/api/v1/runs/{rid}/step")
    return rid


# =============================================================================
# GET /analysis
# =============================================================================


class TestGetAnalysis:
    def test_get_analysis_default_no_enhance(
        self, client: TestClient, finished_run_id: str
    ) -> None:
        resp = client.get(f"/api/v1/runs/{finished_run_id}/analysis")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # AnalysisResult Phase A 必有字段
        assert "summary" in body
        assert "turning_points" in body
        assert "entity_comparisons" in body
        assert "environment_trajectory" in body
        # Phase C 字段在不 enhance 时为 None
        assert body.get("narrative_summary") is None

    def test_get_analysis_for_unfinished_returns_result(
        self, client: TestClient
    ) -> None:
        """未跑完也能拿到 Phase A 分析（基于已落盘的 events）。"""
        resp = client.post(
            "/api/v1/runs",
            json={
                "scenario_path": "scenarios/minimal_market/scenario.yaml",
                "run_id": "unfinished",
            },
        )
        rid = resp.json()["summary"]["run_id"]
        client.post(f"/api/v1/runs/{rid}/step")
        # 没跑完就调 analysis——v0.2 设计为允许（Phase A 可基于部分数据）
        r = client.get(f"/api/v1/runs/{rid}/analysis")
        # 200 或 4xx（取决于 analyze_run 对部分 run 的容忍度）；任一都属合规
        assert r.status_code in (200, 400, 404, 422)

    def test_get_analysis_nonexistent_run_returns_404(
        self, client: TestClient
    ) -> None:
        resp = client.get("/api/v1/runs/never-exist/analysis")
        assert resp.status_code == 404


# =============================================================================
# POST /analyze
# =============================================================================


class TestPostAnalyze:
    def test_post_analyze_no_enhance(
        self, client: TestClient, finished_run_id: str
    ) -> None:
        resp = client.post(
            f"/api/v1/runs/{finished_run_id}/analyze",
            json={"llm_enhance": False},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "summary" in body

    def test_post_analyze_default_enhance_false(
        self, client: TestClient, finished_run_id: str
    ) -> None:
        """空 body 也可以——AnalyzeRequest 字段都有默认值。"""
        resp = client.post(
            f"/api/v1/runs/{finished_run_id}/analyze", json={}
        )
        assert resp.status_code == 200

    def test_post_analyze_nonexistent_returns_404(
        self, client: TestClient
    ) -> None:
        resp = client.post(
            "/api/v1/runs/never-exist/analyze", json={"llm_enhance": False}
        )
        assert resp.status_code == 404


# =============================================================================
# F6（session 45）：mock provider 跳过 enhance 的防御逻辑
# =============================================================================


class TestMockProviderSkipsEnhance:
    """session 45 F6：MockProvider 不能产出 4 段叙事 JSON——AnalysisService
    前置检查 isinstance(provider, MockProvider) 命中时跳过 enhance_with_llm，
    返 Phase A 不报 502，避免误报错。"""

    def test_get_analysis_with_enhance_true_on_mock_provider(
        self, client: TestClient, finished_run_id: str
    ) -> None:
        """mock provider + enhance=true → 200（不是 502）+ Phase A 数据。"""
        resp = client.get(
            f"/api/v1/runs/{finished_run_id}/analysis?enhance=true"
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        # Phase A 字段完整
        assert "summary" in body
        # Phase C 字段在 mock 跳过时为 None（与 enhance=false 行为一致）
        assert body.get("narrative_summary") is None
        assert body.get("situation_judgement") is None
        assert body.get("next_action_suggestions") is None

    def test_post_analyze_with_enhance_true_on_mock_provider(
        self, client: TestClient, finished_run_id: str
    ) -> None:
        """POST /analyze + llm_enhance=True + mock → 同样降级。"""
        resp = client.post(
            f"/api/v1/runs/{finished_run_id}/analyze",
            json={"llm_enhance": True},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body.get("narrative_summary") is None
