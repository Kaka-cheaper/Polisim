"""tests/test_server_interventions.py —— /api/v1/runs/:id/intervene。

3 类干预（D-017 第 3.2 节）：
- inject_message
- force_action
- override_attribute
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
def run_id(client: TestClient) -> str:
    """提前创建一个 minimal_market run。"""
    resp = client.post(
        "/api/v1/runs",
        json={
            "scenario_path": "scenarios/minimal_market/scenario.yaml",
            "run_id": "intervene-test",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["summary"]["run_id"]


# =============================================================================
# inject_message
# =============================================================================


class TestInjectMessage:
    def test_broadcast_message(
        self, client: TestClient, run_id: str
    ) -> None:
        """tick=1 注入广播消息——target_actor=None 是允许的。"""
        resp = client.post(
            f"/api/v1/runs/{run_id}/intervene",
            json={
                "tick": 1,
                "kind": "inject_message",
                "message": {
                    "type": "policy_signal",
                    "delivery": "broadcast",
                    "payload": {"strength": 50},
                },
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["kind"] == "intervention_applied"

    def test_targeted_message(
        self, client: TestClient, run_id: str
    ) -> None:
        resp = client.post(
            f"/api/v1/runs/{run_id}/intervene",
            json={
                "tick": 1,
                "kind": "inject_message",
                "target_actor": "company_a",
                "message": {
                    "type": "policy_signal",
                    "delivery": "targeted",
                    "to": "company_a",
                    "payload": {},
                },
            },
        )
        assert resp.status_code == 200, resp.text


# =============================================================================
# force_action
# =============================================================================


class TestForceAction:
    def test_force_action_recorded(
        self, client: TestClient, run_id: str
    ) -> None:
        resp = client.post(
            f"/api/v1/runs/{run_id}/intervene",
            json={
                "tick": 1,
                "kind": "force_action",
                "target_actor": "company_a",
                "action": {
                    "tick": 1,
                    "actor_id": "company_a",
                    "action_type": "do_nothing",
                    "params": {},
                },
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["kind"] == "intervention_applied"
        # payload 结构由 Runtime.intervene 决定——只验证含 intervention 类型相关字段
        assert body["tick"] >= 0

    def test_force_action_missing_target_returns_400(
        self, client: TestClient, run_id: str
    ) -> None:
        """target_actor 必填——Pydantic model_validator 抛 ValueError → 422。"""
        resp = client.post(
            f"/api/v1/runs/{run_id}/intervene",
            json={
                "tick": 1,
                "kind": "force_action",
                "action": {
                    "tick": 1,
                    "actor_id": "company_a",
                    "action_type": "do_nothing",
                    "params": {},
                },
            },
        )
        # Pydantic 验证错通常 422
        assert resp.status_code in (400, 422)


# =============================================================================
# override_attribute
# =============================================================================


class TestOverrideAttribute:
    def test_override_attribute_changes_state(
        self, client: TestClient, run_id: str
    ) -> None:
        resp = client.post(
            f"/api/v1/runs/{run_id}/intervene",
            json={
                "tick": 1,
                "kind": "override_attribute",
                "target_actor": "company_a",
                "attribute_changes": {"cash": 999},
            },
        )
        assert resp.status_code == 200, resp.text

        # 验证 state 真的改了
        state = client.get(f"/api/v1/runs/{run_id}/state").json()
        assert state["entities"]["company_a"]["attributes"]["cash"] == 999


# =============================================================================
# 错误路径
# =============================================================================


class TestInterventionErrors:
    def test_intervene_on_nonexistent_run_returns_404(
        self, client: TestClient
    ) -> None:
        resp = client.post(
            "/api/v1/runs/never-exist/intervene",
            json={
                "tick": 1,
                "kind": "inject_message",
                "message": {
                    "type": "x",
                    "delivery": "broadcast",
                    "payload": {},
                },
            },
        )
        assert resp.status_code == 404

    def test_invalid_kind_returns_422(
        self, client: TestClient, run_id: str
    ) -> None:
        resp = client.post(
            f"/api/v1/runs/{run_id}/intervene",
            json={
                "tick": 1,
                "kind": "weird_kind",
                "target_actor": "company_a",
            },
        )
        assert resp.status_code == 422

    def test_override_nonexistent_target_lenient_no_state_change(
        self, client: TestClient, run_id: str
    ) -> None:
        """target_actor 不存在——v1 Runtime.intervene 设计为 lenient：

        写 intervention_applied 事件但不实际改 state。这是 v1 Runtime 既定行为
        （pitfalls.md 提及干预生效是 “下一 step ” 时通过 forced_actions 短路，
        不存在的 actor 当 tick 不会被调度，自然没有效果）。
        """
        before = client.get(f"/api/v1/runs/{run_id}/state").json()
        resp = client.post(
            f"/api/v1/runs/{run_id}/intervene",
            json={
                "tick": 1,
                "kind": "override_attribute",
                "target_actor": "ghost_entity",
                "attribute_changes": {"x": 1},
            },
        )
        # v1 lenient 行为：返 200，写事件
        assert resp.status_code == 200, resp.text
        # state.entities 未变
        after = client.get(f"/api/v1/runs/{run_id}/state").json()
        assert before["entities"].keys() == after["entities"].keys()
        assert "ghost_entity" not in after["entities"]
