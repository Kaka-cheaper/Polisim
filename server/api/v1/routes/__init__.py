"""server/api/v1/routes/ —— REST endpoint 实现。

每个文件对应 D-017 第三节的一组 endpoints：

- `runs.py`           —— /api/v1/runs/* （CRUD + step/pause/resume + 状态查询 + 事件查询）
- `interventions.py`  —— /api/v1/runs/:id/intervene
- `analysis.py`       —— /api/v1/runs/:id/analysis (GET / POST)
- `meta.py`           —— /api/v1/scenarios + /api/v1/health

WebSocket 路由（`ws.py`）推迟到 session 32。
"""
