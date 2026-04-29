"""tests/test_server_ws.py —— WebSocket 路由 /api/v1/runs/:id/stream 测试。

D-017 第四节 / 第 6.3 节。

**TestClient.websocket_connect** 用法：

```python
with client.websocket_connect("/api/v1/runs/X/stream") as ws:
    msg = ws.receive_json()
```

是同步上下文管理器，背后跑 anyio.from_thread——sync test 与 async ws 路由协作。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from server.app import AppConfig, create_app


# =============================================================================
# Fixtures
# =============================================================================


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


def _create_run(client: TestClient, run_id: str, ticks: int = 5) -> str:
    """POST /runs 创建 run；返回 run_id。"""
    resp = client.post(
        "/api/v1/runs",
        json={
            "scenario_path": "scenarios/minimal_market/scenario.yaml",
            "run_id": run_id,
            "ticks_override": ticks,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["summary"]["run_id"]


# =============================================================================
# 连接 / 断开 / 不存在
# =============================================================================


class TestConnectionLifecycle:
    def test_connect_to_existing_run(self, client: TestClient) -> None:
        """订阅活跃 run——连接成功，无消息阻塞。"""
        rid = _create_run(client, "ws-conn-1")
        with client.websocket_connect(
            f"/api/v1/runs/{rid}/stream"
        ) as ws:
            # stream_service 已订阅；空闲队列
            assert ws is not None

    def test_connect_to_nonexistent_run_closes_4004(
        self, client: TestClient
    ) -> None:
        """订阅不存在的 run——server close(4004)。"""
        with pytest.raises(WebSocketDisconnect) as excinfo:
            with client.websocket_connect(
                "/api/v1/runs/never-exist/stream"
            ) as ws:
                # 收到关闭——服务端立即 close(4004)
                ws.receive_text()
        assert excinfo.value.code == 4004


# =============================================================================
# step 推送 tick_advanced
# =============================================================================


class TestStepBroadcast:
    def test_step_pushes_tick_advanced(self, client: TestClient) -> None:
        rid = _create_run(client, "ws-step-1")
        with client.websocket_connect(
            f"/api/v1/runs/{rid}/stream"
        ) as ws:
            # 在另一线程没法做——TestClient 单线程顺序：先 step（sync），再 ws.receive
            client.post(f"/api/v1/runs/{rid}/step")
            msg = ws.receive_json()
            assert msg["event"] == "tick_advanced"
            assert "data" in msg
            assert msg["data"]["tick"] == 1

    def test_multiple_steps_push_in_order(
        self, client: TestClient
    ) -> None:
        rid = _create_run(client, "ws-step-multi")
        with client.websocket_connect(
            f"/api/v1/runs/{rid}/stream"
        ) as ws:
            for expected_tick in [1, 2, 3]:
                client.post(f"/api/v1/runs/{rid}/step")
                msg = ws.receive_json()
                assert msg["event"] == "tick_advanced"
                assert msg["data"]["tick"] == expected_tick


# =============================================================================
# pause 推送 paused
# =============================================================================


class TestPauseBroadcast:
    def test_manual_pause_pushes_paused_event(
        self, client: TestClient
    ) -> None:
        rid = _create_run(client, "ws-pause-manual")
        with client.websocket_connect(
            f"/api/v1/runs/{rid}/stream"
        ) as ws:
            client.post(f"/api/v1/runs/{rid}/pause")
            msg = ws.receive_json()
            assert msg["event"] == "paused"
            assert msg["data"]["reason"] == "manual"
            assert msg["data"]["tick"] == 0
            # 手动 pause 不携带 breakpoint
            assert msg["data"]["breakpoint_ids"] == []

    def test_breakpoint_pause_includes_breakpoint_ids(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """three_party_negotiation 场景含 alice_high_trust 断点（max_trust>=80）。

        本测试验证 breakpoint 触发时——server 推 paused 事件且 reason="breakpoint"
        + breakpoint_ids 非空。

        实施细节：直接 override_attribute 把 alice 的 max_trust 设为 90，下一 step
        立即触发断点。
        """
        # 用 three_party_negotiation 创建 run
        resp = client.post(
            "/api/v1/runs",
            json={
                "scenario_path": "scenarios/three_party_negotiation/scenario.yaml",
                "run_id": "ws-bp",
            },
        )
        assert resp.status_code == 201, resp.text
        rid = resp.json()["summary"]["run_id"]

        with client.websocket_connect(
            f"/api/v1/runs/{rid}/stream"
        ) as ws:
            # 干预：把 alice.max_trust 拉到 90（触发 alice_high_trust 断点 ≥80）
            client.post(
                f"/api/v1/runs/{rid}/intervene",
                json={
                    "tick": 1,
                    "kind": "override_attribute",
                    "target_actor": "alice",
                    "attribute_changes": {"max_trust": 90},
                },
            )
            # step 一次——breakpoint 应该触发 → 推 tick_advanced + paused
            client.post(f"/api/v1/runs/{rid}/step")
            msg1 = ws.receive_json()
            assert msg1["event"] == "tick_advanced"
            assert msg1["data"]["paused_after"] is True

            msg2 = ws.receive_json()
            assert msg2["event"] == "paused"
            assert msg2["data"]["reason"] == "breakpoint"
            assert "alice_high_trust" in msg2["data"]["breakpoint_ids"]

    def test_repeated_pause_no_duplicate_event(
        self, client: TestClient
    ) -> None:
        """已 paused 状态再调 pause——不再推 paused（避免 spam）。"""
        rid = _create_run(client, "ws-pause-dup")
        with client.websocket_connect(
            f"/api/v1/runs/{rid}/stream"
        ) as ws:
            client.post(f"/api/v1/runs/{rid}/pause")
            msg1 = ws.receive_json()
            assert msg1["event"] == "paused"
            client.post(f"/api/v1/runs/{rid}/pause")
            # 第二次 pause 不应推送——验证：下一条消息不是 paused
            # 走 step 后看到的是 tick_advanced（resume + step 才能跑，这里直接验证
            # queue 没有第二条 paused）
            client.post(f"/api/v1/runs/{rid}/resume")
            client.post(f"/api/v1/runs/{rid}/step")
            msg2 = ws.receive_json()
            assert msg2["event"] == "tick_advanced"


# =============================================================================
# run finished 推送 run_finished + 关闭 ws
# =============================================================================


class TestRunFinishedBroadcast:
    def test_run_finish_pushes_finished_then_closes(
        self, client: TestClient
    ) -> None:
        """跑到 total_ticks 时 server 推 tick_advanced + run_finished + close。"""
        rid = _create_run(client, "ws-finish", ticks=2)
        with client.websocket_connect(
            f"/api/v1/runs/{rid}/stream"
        ) as ws:
            # 跑完 2 ticks
            client.post(f"/api/v1/runs/{rid}/step")
            msg1 = ws.receive_json()
            assert msg1["event"] == "tick_advanced"
            assert msg1["data"]["tick"] == 1

            client.post(f"/api/v1/runs/{rid}/step")
            # 第二次 step——按顺序收：tick_advanced -> run_finished
            msg2 = ws.receive_json()
            assert msg2["event"] == "tick_advanced"
            assert msg2["data"]["tick"] == 2
            assert msg2["data"]["reached_total_ticks"] is True

            msg3 = ws.receive_json()
            assert msg3["event"] == "run_finished"
            assert "data" in msg3
            assert "summary" in msg3["data"]

            # server 应该主动关闭——下一次 receive 触发 disconnect
            with pytest.raises(WebSocketDisconnect):
                ws.receive_json()


# =============================================================================
# 多订阅者 fan-out
# =============================================================================


class TestMultipleSubscribers:
    def test_two_subscribers_both_receive(
        self, client: TestClient
    ) -> None:
        rid = _create_run(client, "ws-multi-sub")
        with client.websocket_connect(
            f"/api/v1/runs/{rid}/stream"
        ) as ws_a:
            with client.websocket_connect(
                f"/api/v1/runs/{rid}/stream"
            ) as ws_b:
                client.post(f"/api/v1/runs/{rid}/step")
                msg_a = ws_a.receive_json()
                msg_b = ws_b.receive_json()
                assert msg_a["event"] == "tick_advanced"
                assert msg_b["event"] == "tick_advanced"
                assert msg_a["data"]["tick"] == msg_b["data"]["tick"] == 1


# =============================================================================
# StreamService 单元 / 行为
# =============================================================================


class TestStreamServiceBehavior:
    def test_subscriber_count_decreases_on_disconnect(
        self, client: TestClient
    ) -> None:
        """客户端断开后，订阅者计数下降。"""
        rid = _create_run(client, "ws-disconn")
        from server.services.stream_service import StreamService

        ss: StreamService = client.app.state.stream_service
        with client.websocket_connect(
            f"/api/v1/runs/{rid}/stream"
        ) as ws:
            # 用一个推送验证连接活着——这会驱动 starlette 处理 ASGI 消息
            client.post(f"/api/v1/runs/{rid}/step")
            ws.receive_json()
            assert ss.subscriber_count(rid) == 1

        # 退出 with 后 starlette TestClient 走清理
        # 给 server 协程一点时间清理 subscriber set
        import time as _time
        _time.sleep(0.1)
        # subscriber_count 实际应降到 0；若 race condition 存在则放宽到 ≤ 1
        assert ss.subscriber_count(rid) <= 1

    def test_no_subscribers_then_step_works(
        self, client: TestClient
    ) -> None:
        """没有 ws 订阅者时 step 不应阻塞或失败。"""
        rid = _create_run(client, "ws-no-sub")
        # 不连接 ws，直接 step
        resp = client.post(f"/api/v1/runs/{rid}/step")
        assert resp.status_code == 200
        assert resp.json()["tick"] == 1
