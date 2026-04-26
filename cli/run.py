"""Polisim 命令行入口（第 2 步子项 6）。

对应 `docs/02-design/实现映射设计.md` 4.9 节与 D-008 对 Runtime 步进式接口的要求。
三个子命令：

- ``run``——端到端跑完一个场景，产物落到 ``<runs_root>/<run_id>/``
- ``step``——进入交互式 REPL，按需推 tick / 打印状态 / 暂停恢复
- ``replay``——读取已存档 run 的 ``events.jsonl``，按 tick 流式打印

**分层约束**：

- CLI 是**编排层**——只调用 `Runtime` / `EventLog` / Provider / Loader 的公开 API
- **不**包含业务规则（走 `rules/`）、**不**直接解析 world/scenario 结构（走 loaders）
- **不**在 CLI 层写额外的业务校验——那是 loaders / rules 的职责
- LLM provider 选择：v1 默认 `MockProvider(fixed_response='{"action":"do_nothing"}')`；
  `--llm-script` 可传 JSONL 脚本文件

**入口风格**：

- 所有 ``cmd_*`` 函数签名统一为 ``(args: argparse.Namespace) -> int``，返回进程退出码
- ``main(argv)`` 接收 ``list[str] | None``，方便测试通过 ``main(["run", "..."])`` 调起
  而无需 subprocess

**不做的事（v1）**：

- 不在 CLI 里集成真实 LLM provider 选择（等 D-005 后续分支）
- 不支持 ``intervene`` 子命令——复杂输入结构暂不做文本协议
- 不做 ``config/logging.yaml`` 装载（logger handler 用 Python 默认即可）
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, TextIO

from core.analysis import analyze_run, enhance_with_llm, write_analysis
from core.definition_loader import load_world_definition
from core.errors import SimEngineError
from core.providers.mock import MockProvider
from core.runtime import Runtime
from core.scenario_loader import load_scenario
from models.config_models import RuntimeConfig, StorageConfig
from models.runtime_models import EventRecord


# =============================================================================
# 默认值与小工具
# =============================================================================

_DEFAULT_LLM_RESPONSE = json.dumps({"action": "do_nothing", "params": {}})
"""默认 Mock LLM 响应——让所有 llm 实体都走 do_nothing。

这样任何合法 world（只要声明了 ``do_nothing`` 动作或 ``fallback_action`` 兜底）
都能用默认 CLI 跑通，不需要用户额外配置。若想让 LLM 实体做出实际选择，
用 ``--llm-script <file.jsonl>`` 传递按调用次序排列的响应脚本。
"""


def _resolve_world_path(
    scenario_path: Path, explicit: Path | None
) -> Path:
    """CLI 的 world 路径约定：显式 > `<scenario_dir>/world.yaml`。"""
    if explicit is not None:
        return explicit
    candidate = scenario_path.parent / "world.yaml"
    if not candidate.exists():
        raise FileNotFoundError(
            f"未显式提供 --world，且 {candidate} 不存在。"
            f"请用 --world <path> 指定世界定义文件。"
        )
    return candidate


def _build_mock_provider(llm_script: Path | None) -> MockProvider:
    """根据 --llm-script 选项构造 MockProvider（离线 / CI 默认路径）。"""
    if llm_script is None:
        return MockProvider(fixed_response=_DEFAULT_LLM_RESPONSE)
    responses: list[str] = []
    # utf-8-sig：Windows 上 Notepad / PowerShell Out-File 会加 BOM，这里吞掉
    with llm_script.open("r", encoding="utf-8-sig") as fh:
        for line_no, raw in enumerate(fh, start=1):
            line = raw.strip()
            if not line:
                continue
            # 每行必须是合法 JSON，字段由 LLM决策协议设计第四节规定
            # 本层不再校验内容——Runtime 的 _decide_via_llm 会做降级
            try:
                json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{llm_script}:{line_no} 不是合法 JSON：{exc.msg}"
                ) from exc
            responses.append(line)
    if not responses:
        raise ValueError(f"{llm_script} 未包含任何 LLM 响应行")
    return MockProvider(scripted_responses=responses)


def _build_openai_provider(
    config_llm: Path | None, provider_key: str | None
):
    """根据 config/llm.yaml 构造 OpenAIProvider。

    流程：
    1. 读 `<config_llm>`（默认 ``config/llm.yaml``）得到 `LLMConfig`
    2. ``provider_key`` 指定 providers 字典里某个条目的 key；None 时用 `default_provider`
    3. 校验该条目的 ``provider`` 字段必须为 ``"openai"``
    4. 实例化 `OpenAIProvider`（内部从环境变量读 API key）
    """
    # 延迟 import，避免没装 openai 时 CLI 整体崩掉（mock 模式仍可用）
    from core.providers.openai import OpenAIProvider
    from models.config_models import load_llm_config

    resolved_path = config_llm or Path("config/llm.yaml")
    if not resolved_path.exists():
        raise FileNotFoundError(
            f"--llm-provider=openai 需要 LLM 配置文件，但 {resolved_path} 不存在。"
            f"可复制 config/llm.yaml.example 作为起点。"
        )
    llm_config = load_llm_config(resolved_path)

    key = provider_key or llm_config.default_provider
    if key not in llm_config.providers:
        raise ValueError(
            f"provider key '{key}' 未在 {resolved_path} 的 providers 中声明；"
            f"可用 keys：{sorted(llm_config.providers.keys())}"
        )
    prov_config = llm_config.providers[key]
    if prov_config.provider != "openai":
        raise ValueError(
            f"provider key '{key}' 的 provider 字段是 '{prov_config.provider}'，"
            f"不是 'openai'；--llm-provider=openai 要求选择 openai 类条目"
        )
    return OpenAIProvider(prov_config)


def _build_provider(args: argparse.Namespace):
    """按 args.llm_provider 分派到具体 provider 工厂。"""
    if args.llm_provider == "openai":
        return _build_openai_provider(
            getattr(args, "config_llm", None),
            getattr(args, "provider_key", None),
        )
    # 默认 mock
    return _build_mock_provider(getattr(args, "llm_script", None))


def _load_world_scenario(
    scenario_path: Path, world_path: Path | None
) -> tuple[Any, Any]:
    """统一的 world + scenario 加载入口。"""
    resolved_world = _resolve_world_path(scenario_path, world_path)
    world = load_world_definition(resolved_world)
    scenario = load_scenario(scenario_path, world)
    return world, scenario


def _format_event_line(ev: EventRecord) -> str:
    """单行紧凑的 EventRecord 文本表示（tick/kind/actor + 关键 payload 片段）。"""
    actor = ev.actor_id if ev.actor_id else "-"
    payload_hint = ""
    if ev.kind == "action_executed":
        payload_hint = f" {ev.payload.get('action_type', '')}"
    elif ev.kind == "decision_rejected":
        errs = ev.payload.get("errors", [])
        payload_hint = f" errors={errs[:2]}"
    elif ev.kind == "breakpoint_triggered":
        payload_hint = f" id={ev.payload.get('breakpoint_id', '')}"
    elif ev.kind == "scheduled_event_triggered":
        payload_hint = f" name={ev.payload.get('name', '')}"
    elif ev.kind == "environment_changed":
        payload_hint = (
            f" {ev.payload.get('variable', '')}="
            f"{ev.payload.get('new_value', ev.payload.get('delta'))}"
        )
    elif ev.kind == "message_emitted":
        payload_hint = f" type={ev.payload.get('message_type', '')}"
    return f"[t={ev.tick:>3}] {ev.kind:<28} actor={actor}{payload_hint}"


def _print_tick_summary(rt: Runtime, result: Any, stream: TextIO) -> None:
    """打印单个 TickResult 的摘要（用于 `run` / `step`）。"""
    state = rt.get_state()
    header = (
        f"--- tick {result.tick} "
        f"(events={len(result.events)}, paused={result.paused_after})"
    )
    print(header, file=stream)
    for ev in result.events:
        print(f"  {_format_event_line(ev)}", file=stream)
    # 每个实体属性摘要——keys 太多会刷屏，截取前 4 个
    for ent in state.entities.values():
        attrs = list(ent.attributes.items())[:4]
        brief = ", ".join(f"{k}={v}" for k, v in attrs)
        print(f"  entity[{ent.id}] {brief}", file=stream)
    if result.triggered_breakpoints:
        print(
            f"  >> breakpoints triggered: {result.triggered_breakpoints}",
            file=stream,
        )


def _print_final_summary(rt: Runtime, stream: TextIO) -> None:
    """run 结束时的总览：run_id / 最终 tick / 实体终态 / 事件总数。"""
    state = rt.get_state()
    print("", file=stream)
    print("=" * 60, file=stream)
    print(f"run_id     : {rt.run_id}", file=stream)
    print(f"final tick : {state.tick}", file=stream)
    print(f"paused     : {rt.is_paused()}", file=stream)
    print("entities:", file=stream)
    for ent in state.entities.values():
        attrs = ", ".join(f"{k}={v}" for k, v in ent.attributes.items())
        print(f"  {ent.id:<16} [{ent.type}] {attrs}", file=stream)
    if state.environment:
        env = ", ".join(f"{k}={v}" for k, v in state.environment.items())
        print(f"environment: {env}", file=stream)
    print("=" * 60, file=stream)


# =============================================================================
# `run` 子命令：一次跑完
# =============================================================================


def cmd_run(args: argparse.Namespace) -> int:
    """端到端跑完整个场景（遇暂停或 total_ticks 即止）。"""
    world, scenario = _load_world_scenario(args.scenario, args.world)
    if args.ticks is not None:
        # 允许 CLI 覆盖 total_ticks；max_ticks 由 Pydantic 校验
        scenario.config.total_ticks = args.ticks

    provider = _build_provider(args)
    runtime_config = RuntimeConfig(version="0.1", random_seed=args.seed)
    storage_config = StorageConfig(
        version="0.1",
        persist=not args.no_persist,
        runs_root=str(args.runs_root),
    )

    out = args.stdout
    run_dir: Path | None = None
    with Runtime(
        world,
        scenario,
        provider,
        runtime_config=runtime_config,
        storage_config=storage_config,
    ) as rt:
        print(f"[run_id] {rt.run_id}", file=out)
        print(
            f"[scenario] {scenario.scenario.id} "
            f"(total_ticks={scenario.config.total_ticks})",
            file=out,
        )
        while rt.current_tick() < scenario.config.total_ticks and not rt.is_paused():
            result = rt.step()
            _print_tick_summary(rt, result, out)
            if result.paused_after:
                print(
                    "[paused] 场景触发了暂停条件；可改用 'step' 子命令继续推进",
                    file=out,
                )
                break
            if result.reached_total_ticks:
                break
        _print_final_summary(rt, out)
        run_dir = rt.run_dir

    # 分析层（Phase A 纯规则）——run_dir 为 None（--no-persist）时跳过
    if run_dir is not None and not args.no_analysis:
        try:
            result = analyze_run(run_dir)
            md_path, json_path = write_analysis(run_dir, result)
            print(f"[analysis] {md_path}", file=out)
            print(f"[analysis] {json_path}", file=out)
        except (FileNotFoundError, ValueError) as exc:
            # 分析失败不影响仿真 exit code——仿真本身已成功跑完
            print(f"[analysis] 生成失败：{exc}", file=args.stderr)
        else:
            # Phase C——LLM 增强（显式 --llm-enhance 时启用）
            if args.llm_enhance:
                try:
                    enhanced = enhance_with_llm(
                        result, provider, runtime_config
                    )
                    write_analysis(run_dir, enhanced)
                    print(
                        f"[analysis] LLM 增强已写入 {md_path.name}",
                        file=out,
                    )
                except SimEngineError as exc:
                    # Phase C 失败降级：保留已落盘的 Phase A 产物
                    print(
                        f"[analysis] LLM 增强失败（保留 Phase A 版本）："
                        f"{type(exc).__name__}: {exc}",
                        file=args.stderr,
                    )
    return 0


# =============================================================================
# `step` 子命令：交互式 REPL
# =============================================================================


_STEP_HELP = """可用命令：
  step | s              推进一个 tick
  run [N]               推进到 tick N（省略 N 则推进到 total_ticks）
  state [entity_id]     打印当前 WorldState 全量或指定实体
  snapshot <tick>       打印指定 tick 的快照
  pause | p             暂停（下一次 step 前）
  resume | r            恢复
  info                  显示 run_id / 当前 tick / total_ticks / paused
  help | h | ?          显示本帮助
  quit | exit | q       退出（保留已落盘产物）
"""


def cmd_step(args: argparse.Namespace) -> int:
    """交互式逐 tick 推进。

    命令从 ``args.stdin`` 读取、输出写到 ``args.stdout``——方便测试注入。
    """
    world, scenario = _load_world_scenario(args.scenario, args.world)
    provider = _build_provider(args)
    runtime_config = RuntimeConfig(version="0.1", random_seed=args.seed)
    storage_config = StorageConfig(
        version="0.1",
        persist=not args.no_persist,
        runs_root=str(args.runs_root),
    )
    out: TextIO = args.stdout
    stdin: TextIO = args.stdin

    handlers: dict[str, Callable[[list[str], Runtime], bool]] = {}

    def _handle_step(tokens: list[str], rt: Runtime) -> bool:
        if rt.is_paused():
            print("[paused] 先 'resume' 再 'step'", file=out)
            return True
        if rt.current_tick() >= scenario.config.total_ticks:
            print(
                f"[done] 已达 total_ticks={scenario.config.total_ticks}",
                file=out,
            )
            return True
        result = rt.step()
        _print_tick_summary(rt, result, out)
        return True

    def _handle_run(tokens: list[str], rt: Runtime) -> bool:
        if rt.is_paused():
            print("[paused] 先 'resume' 再 'run'", file=out)
            return True
        target = scenario.config.total_ticks
        if len(tokens) >= 2:
            try:
                target = int(tokens[1])
            except ValueError:
                print(f"[error] run 需要整数目标 tick，收到 '{tokens[1]}'", file=out)
                return True
        if target <= rt.current_tick():
            print(
                f"[noop] 目标 tick={target} 不大于当前 tick={rt.current_tick()}",
                file=out,
            )
            return True
        for result in rt.run_until(target):
            _print_tick_summary(rt, result, out)
        return True

    def _handle_state(tokens: list[str], rt: Runtime) -> bool:
        state = rt.get_state()
        if len(tokens) >= 2:
            eid = tokens[1]
            ent = state.entities.get(eid)
            if ent is None:
                print(f"[error] 未知实体 id='{eid}'", file=out)
                return True
            print(f"entity[{ent.id}] type={ent.type}", file=out)
            for k, v in ent.attributes.items():
                print(f"  {k} = {v}", file=out)
            return True
        print(f"tick={state.tick}", file=out)
        for ent in state.entities.values():
            attrs = ", ".join(f"{k}={v}" for k, v in ent.attributes.items())
            print(f"  entity[{ent.id}] {attrs}", file=out)
        if state.environment:
            env = ", ".join(f"{k}={v}" for k, v in state.environment.items())
            print(f"  env: {env}", file=out)
        return True

    def _handle_snapshot(tokens: list[str], rt: Runtime) -> bool:
        if len(tokens) < 2:
            print("[error] 用法：snapshot <tick>", file=out)
            return True
        try:
            t = int(tokens[1])
        except ValueError:
            print(f"[error] tick 必须是整数，收到 '{tokens[1]}'", file=out)
            return True
        snap = rt.get_snapshot(t)
        if snap is None:
            print(f"[error] tick={t} 没有快照", file=out)
            return True
        print(snap.model_dump_json(indent=2), file=out)
        return True

    def _handle_pause(tokens: list[str], rt: Runtime) -> bool:
        rt.pause()
        print("[paused]", file=out)
        return True

    def _handle_resume(tokens: list[str], rt: Runtime) -> bool:
        rt.resume()
        print("[resumed]", file=out)
        return True

    def _handle_info(tokens: list[str], rt: Runtime) -> bool:
        print(f"run_id     : {rt.run_id}", file=out)
        print(f"tick       : {rt.current_tick()} / {scenario.config.total_ticks}", file=out)
        print(f"paused     : {rt.is_paused()}", file=out)
        return True

    def _handle_help(tokens: list[str], rt: Runtime) -> bool:
        print(_STEP_HELP, file=out)
        return True

    def _handle_quit(tokens: list[str], rt: Runtime) -> bool:
        return False

    handlers.update(
        {
            "step": _handle_step,
            "s": _handle_step,
            "run": _handle_run,
            "state": _handle_state,
            "snapshot": _handle_snapshot,
            "pause": _handle_pause,
            "p": _handle_pause,
            "resume": _handle_resume,
            "r": _handle_resume,
            "info": _handle_info,
            "help": _handle_help,
            "h": _handle_help,
            "?": _handle_help,
            "quit": _handle_quit,
            "exit": _handle_quit,
            "q": _handle_quit,
        }
    )

    with Runtime(
        world,
        scenario,
        provider,
        runtime_config=runtime_config,
        storage_config=storage_config,
    ) as rt:
        print(f"[run_id] {rt.run_id}", file=out)
        print(
            f"[scenario] {scenario.scenario.id} "
            f"(total_ticks={scenario.config.total_ticks})",
            file=out,
        )
        print("type 'help' for commands", file=out)

        while True:
            # prompt 到 stderr（或 out）——当 stdin 是 pipe 时不 flush 会丢失
            out.write("polisim> ")
            out.flush()
            line = stdin.readline()
            if line == "":
                # EOF（Ctrl+D 或测试注入的 pipe 耗尽）
                print("", file=out)
                break
            tokens = line.strip().split()
            if not tokens:
                continue
            cmd = tokens[0]
            handler = handlers.get(cmd)
            if handler is None:
                print(
                    f"[error] 未知命令 '{cmd}'，输入 'help' 查看可用命令",
                    file=out,
                )
                continue
            if not handler(tokens, rt):
                break
    return 0


# =============================================================================
# `replay` 子命令：回放已存档 run 的事件流
# =============================================================================


def cmd_replay(args: argparse.Namespace) -> int:
    """从 ``<run_dir>/events.jsonl`` 按顺序读事件并格式化打印。"""
    run_dir: Path = args.run_dir
    events_file = run_dir / "events.jsonl"
    if not events_file.exists():
        print(
            f"[error] 找不到 {events_file}；请检查 run_dir 是否正确",
            file=args.stderr,
        )
        return 2

    out: TextIO = args.stdout
    print(f"[replay] {events_file}", file=out)
    current_tick = -1
    total = 0
    with events_file.open("r", encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                print(f"[error] 解析失败：{exc.msg}；行内容被跳过", file=args.stderr)
                continue
            try:
                ev = EventRecord.model_validate(data)
            except Exception as exc:  # noqa: BLE001 Pydantic ValidationError 属于合理宽捕获
                print(f"[error] EventRecord 校验失败：{exc}", file=args.stderr)
                continue

            if args.until is not None and ev.tick > args.until:
                break
            if args.tick is not None and ev.tick != args.tick:
                continue
            if args.kind is not None and ev.kind != args.kind:
                continue
            if ev.tick != current_tick:
                current_tick = ev.tick
                print(f"--- tick {ev.tick}", file=out)
            print(f"  {_format_event_line(ev)}", file=out)
            total += 1
    print(f"[replay] {total} events printed", file=out)
    return 0


# =============================================================================
# argparse 入口
# =============================================================================


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="polisim",
        description=(
            "Polisim CLI — 分层仿真引擎的命令行入口。"
            "三个子命令：run / step / replay。"
        ),
    )
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # ---- run
    run_p = subparsers.add_parser("run", help="端到端跑完一个场景")
    run_p.add_argument("scenario", type=Path, help="scenario.yaml 路径")
    run_p.add_argument(
        "--world",
        type=Path,
        default=None,
        help="world.yaml 路径；默认 <scenario_dir>/world.yaml",
    )
    run_p.add_argument(
        "--ticks", type=int, default=None, help="覆盖 total_ticks"
    )
    run_p.add_argument(
        "--runs-root",
        type=Path,
        default=Path("./runs"),
        help="runs/ 根目录（默认 ./runs）",
    )
    run_p.add_argument("--seed", type=int, default=None, help="随机种子")
    run_p.add_argument(
        "--llm-script",
        type=Path,
        default=None,
        help="LLM 响应脚本 JSONL；仅 --llm-provider=mock 时有效",
    )
    run_p.add_argument(
        "--llm-provider",
        choices=["mock", "openai"],
        default="mock",
        help="LLM provider 类型；默认 mock（离线）。openai 需配合 --config-llm",
    )
    run_p.add_argument(
        "--config-llm",
        type=Path,
        default=None,
        help="LLM 配置文件路径；默认 config/llm.yaml；仅 --llm-provider=openai 时读取",
    )
    run_p.add_argument(
        "--provider-key",
        type=str,
        default=None,
        help="config/llm.yaml 中 providers 字典的 key；省略时用 default_provider",
    )
    run_p.add_argument(
        "--no-persist",
        action="store_true",
        help="仅内存运行，不落盘事件与快照",
    )
    run_p.add_argument(
        "--no-analysis",
        action="store_true",
        help="跳过 runs/<run_id>/analysis/ 产物生成（默认自动生成）",
    )
    run_p.add_argument(
        "--llm-enhance",
        action="store_true",
        help=(
            "Phase C：仿真结束后用 LLM 为分析报告补齐叙事总览 / 局势判断 / "
            "行动建议三段内容（复用 --llm-provider 指定的 provider）。"
            "LLM 调用失败时保留 Phase A 版本并打 warning，不影响 exit code。"
        ),
    )
    run_p.set_defaults(func=cmd_run)

    # ---- step
    step_p = subparsers.add_parser("step", help="交互式 REPL 逐 tick 推进")
    step_p.add_argument("scenario", type=Path)
    step_p.add_argument("--world", type=Path, default=None)
    step_p.add_argument("--runs-root", type=Path, default=Path("./runs"))
    step_p.add_argument("--seed", type=int, default=None)
    step_p.add_argument("--llm-script", type=Path, default=None)
    step_p.add_argument(
        "--llm-provider", choices=["mock", "openai"], default="mock"
    )
    step_p.add_argument("--config-llm", type=Path, default=None)
    step_p.add_argument("--provider-key", type=str, default=None)
    step_p.add_argument("--no-persist", action="store_true")
    step_p.set_defaults(func=cmd_step)

    # ---- replay
    replay_p = subparsers.add_parser(
        "replay", help="回放已存档 run 的 events.jsonl"
    )
    replay_p.add_argument(
        "run_dir",
        type=Path,
        help="某次 run 的目录（包含 events.jsonl）",
    )
    replay_p.add_argument(
        "--until", type=int, default=None, help="只回放到 tick N（含）"
    )
    replay_p.add_argument(
        "--tick", type=int, default=None, help="只回放某个 tick"
    )
    replay_p.add_argument(
        "--kind",
        type=str,
        default=None,
        help="只回放某种 EventKind（如 action_executed）",
    )
    replay_p.set_defaults(func=cmd_replay)

    return parser


def main(
    argv: list[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """CLI 总入口。

    显式参数流允许测试无 subprocess 调用并捕获输出；默认走 ``sys.*``。
    返回值即进程退出码。
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    # 把流注入 args，方便各 cmd_* 统一消费
    args.stdin = stdin if stdin is not None else sys.stdin
    args.stdout = stdout if stdout is not None else sys.stdout
    args.stderr = stderr if stderr is not None else sys.stderr
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"[error] {exc}", file=args.stderr)
        return 2
    except SimEngineError as exc:
        # Phase B.0：D-011 引入的 SimEngineError 体系——`ProviderError` 等
        # 业务错误统一走本分支；继承自 SimEngineError 的所有子类通吃
        print(f"[error] {exc}", file=args.stderr)
        return 2
    except ValueError as exc:
        print(f"[error] {exc}", file=args.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
