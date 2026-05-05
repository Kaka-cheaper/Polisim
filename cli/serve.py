"""cli/serve.py —— `polisim serve` 子命令实现。

启动 v0.2 server（FastAPI + uvicorn）——D-017 落地。

**用法**：

```
polisim serve [--host 127.0.0.1] [--port 8000] [--scenarios-root scenarios] [--runs-root runs] [--reload]
```

**默认行为**：

- 绑 127.0.0.1（本地）+ 8000 端口
- 不开 --reload（生产路径），但 --reload 适合 demo + 前端开发热更
- scenarios_root / runs_root 都默认 cwd 下同名子目录

**进程退出**：

- Ctrl+C → uvicorn 优雅停机 → AppLifespan 触发 registry.shutdown_all()
- 退出码 0
"""

from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn

from server.app import AppConfig, create_app


def cmd_serve(args: argparse.Namespace) -> int:
    """启动 v0.2 server。

    在主进程内构造 AppConfig + create_app + uvicorn.run 阻塞。
    """
    config = AppConfig(
        runs_root=Path(args.runs_root).resolve(),
        scenarios_root=Path(args.scenarios_root).resolve(),
        max_concurrent_runs=args.max_concurrent_runs,
    )

    if args.reload:
        # --reload 走 uvicorn 的字符串入口：必须是 "module:attr" 形式
        # 顶层 server.app:app 已经构造好——但 reload 模式 uvicorn 会重新 import 它，
        # 此时配置走默认值。--reload 主要用于前端开发；生产用 --no-reload + 自定义 config。
        uvicorn.run(
            "server.app:app",
            host=args.host,
            port=args.port,
            reload=True,
            reload_dirs=[
                str(Path("server").resolve()),
                str(Path("core").resolve()),
                str(Path("models").resolve()),
                str(Path("rules").resolve()),
            ],
        )
    else:
        # 非 reload：直接传 app 实例，使用我们传入的 config
        app = create_app(config)
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def add_serve_subparser(subparsers: argparse._SubParsersAction) -> None:
    """把 `serve` 子命令注册到 cli/run.py 的 subparsers。

    分离这个函数让 cli/run.py 引用一行就能挂上——不重复 argparse 配置。
    """
    serve_p = subparsers.add_parser(
        "serve",
        help="启动 v0.2 server (FastAPI + uvicorn)",
        description=(
            "v0.2 实时态势 server。挂载 D-017 设计的 REST endpoints，"
            "前端可对接做 web 实时态势演示。"
        ),
    )
    serve_p.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="绑定 host（默认 127.0.0.1，仅本机）",
    )
    serve_p.add_argument(
        "--port",
        type=int,
        default=8000,
        help="绑定端口（默认 8000）",
    )
    serve_p.add_argument(
        "--scenarios-root",
        type=Path,
        default=Path("./scenarios"),
        help="scenarios/ 根目录（GET /scenarios 扫描的目录；默认 ./scenarios）",
    )
    serve_p.add_argument(
        "--runs-root",
        type=Path,
        default=Path("./runs"),
        help="runs/ 根目录（runs 落盘 events.jsonl + snapshots；默认 ./runs）",
    )
    serve_p.add_argument(
        "--max-concurrent-runs",
        type=int,
        default=20,
        help="活跃 run 并发上限（默认 20；超出返 503）",
    )
    serve_p.add_argument(
        "--reload",
        action="store_true",
        help="开启 uvicorn --reload（开发模式，监控代码变更自动重启）",
    )
    serve_p.set_defaults(func=cmd_serve)
