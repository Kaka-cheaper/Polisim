"""允许 `python -m cli <subcommand>` 直接调起 CLI。

等价于 `python -m cli.run <subcommand>`，但命令行更短。
"""

from cli.run import main


if __name__ == "__main__":
    raise SystemExit(main())
