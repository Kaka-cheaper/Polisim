"""server/api/v1/middlewares/ —— FastAPI 中间件。

v0.2 占位——`auth.py` 是 no-op 直接 pass。
v0.3+ 加 token 鉴权（环境变量 `POLISIM_API_TOKEN`）。
v0.4+ 加 OAuth + 多用户隔离（每 user 独立 runs/）。
"""
