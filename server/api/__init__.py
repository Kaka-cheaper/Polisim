"""server/api/ —— HTTP API 层。

子结构：

- `v1/` —— v0.2 当前版本 API（D-017 设计）
- `deps.py` —— FastAPI Depends 依赖注入入口（registry / config）

未来 v0.3 加 v2 时，新建 `v2/` 子目录，与 v1 并存——D-017 第 2.3 节版本化策略。
"""
