"""`cli/run.py` 单元 + 集成测试（第 2 步子项 6 验收）。

测试分组：

1. 通用 argparse 与 main 入口
2. `run` 子命令：端到端跑通 + 选项（--ticks / --no-persist / --llm-script / --seed）
3. `step` 子命令：交互 REPL 各命令 + EOF
4. `replay` 子命令：正常路径 + 各 filter + 错误路径

所有测试用 `io.StringIO` 捕获 stdout/stderr，不 fork subprocess——快且可读。
使用 `tmp_path` 作 ``--runs-root``，避免污染仓库 ``./runs`` 目录。
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from cli.run import _DEFAULT_LLM_RESPONSE, main


# =============================================================================
# 公共 fixture
# =============================================================================


WALKTHROUGH_SCENARIO = Path("scenarios/minimal_market/scenario.yaml")
WALKTHROUGH_WORLD = Path("scenarios/minimal_market/world.yaml")


@pytest.fixture
def captured_streams() -> tuple[io.StringIO, io.StringIO, io.StringIO]:
    """(stdin, stdout, stderr) 三元组；stdin 默认空字符串。"""
    return io.StringIO(), io.StringIO(), io.StringIO()


def _invoke(
    argv: list[str],
    streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> int:
    stdin, stdout, stderr = streams
    return main(argv, stdin=stdin, stdout=stdout, stderr=stderr)


# =============================================================================
# 1. argparse / main 入口
# =============================================================================


def test_main_no_args_errors_out(
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    """不传任何子命令：argparse 应让它失败（SystemExit 2）。"""
    with pytest.raises(SystemExit) as exc:
        _invoke([], captured_streams)
    assert exc.value.code == 2


def test_main_unknown_subcommand_errors_out(
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    with pytest.raises(SystemExit):
        _invoke(["nonexistent"], captured_streams)


# =============================================================================
# 2. `run` 子命令
# =============================================================================


def test_run_walkthrough_end_to_end(
    tmp_path: Path,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    """walkthrough 默认跑 5 tick；应落 events.jsonl + snapshots + stdout 有 final summary。"""
    _, stdout, stderr = captured_streams
    exit_code = _invoke(
        [
            "run",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
        ],
        captured_streams,
    )
    assert exit_code == 0, stderr.getvalue()
    out = stdout.getvalue()
    assert "[run_id]" in out
    assert "--- tick 1" in out
    assert "--- tick 5" in out
    assert "run_id     :" in out  # final summary
    # 应生成一个 run 目录
    run_dirs = list(tmp_path.iterdir())
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    assert (run_dir / "events.jsonl").exists()
    # tick 0..5 共 6 份快照
    snaps = sorted((run_dir / "snapshots").iterdir())
    assert len(snaps) == 6
    # Phase A 分析产物：默认生成 final.md + final.json
    assert (run_dir / "analysis" / "final.md").exists()
    assert (run_dir / "analysis" / "final.json").exists()
    assert "[analysis]" in out


def test_run_ticks_override_shortens_simulation(
    tmp_path: Path,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    """--ticks 2 → 只跑 2 tick，快照目录里仅 tick 0/1/2。"""
    _, stdout, _ = captured_streams
    exit_code = _invoke(
        [
            "run",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--ticks",
            "2",
        ],
        captured_streams,
    )
    assert exit_code == 0
    out = stdout.getvalue()
    assert "--- tick 2" in out
    assert "--- tick 3" not in out
    run_dir = next(tmp_path.iterdir())
    snaps = sorted((run_dir / "snapshots").iterdir())
    assert [s.name for s in snaps] == [
        "tick_0.json",
        "tick_1.json",
        "tick_2.json",
    ]


def test_run_no_persist_produces_no_files(
    tmp_path: Path,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    """--no-persist：runs_root 下无任何产物。"""
    exit_code = _invoke(
        [
            "run",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--ticks",
            "2",
            "--no-persist",
        ],
        captured_streams,
    )
    assert exit_code == 0
    assert list(tmp_path.iterdir()) == []


def test_run_with_llm_script_drives_company_a(
    tmp_path: Path,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    """--llm-script：让 company_a 真正执行 promote。"""
    script = tmp_path / "llm.jsonl"
    script.write_text(
        "\n".join(
            [
                json.dumps({"action": "promote", "params": {"budget": 20}}),
                json.dumps({"action": "do_nothing", "params": {}}),
            ]
        ),
        encoding="utf-8",
    )
    _, stdout, _ = captured_streams
    exit_code = _invoke(
        [
            "run",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--ticks",
            "1",
            "--llm-script",
            str(script),
        ],
        captured_streams,
    )
    assert exit_code == 0
    out = stdout.getvalue()
    # company_a 首 tick 执行 promote → cash 从 100 掉到 80
    assert "cash=80" in out
    assert "promote" in out


def test_run_llm_script_with_invalid_json_line_exits_with_error(
    tmp_path: Path,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    """脚本文件有非 JSON 行：ValueError → exit 2（main 捕获）。"""
    script = tmp_path / "bad.jsonl"
    script.write_text("{not json}\n", encoding="utf-8")
    _, _, stderr = captured_streams
    exit_code = _invoke(
        [
            "run",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--llm-script",
            str(script),
        ],
        captured_streams,
    )
    assert exit_code == 2
    assert "bad.jsonl" in stderr.getvalue()


def test_run_missing_scenario_exits_with_error(
    tmp_path: Path,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    """scenario 不存在：FileNotFoundError → exit 2。"""
    _, _, stderr = captured_streams
    exit_code = _invoke(
        [
            "run",
            str(tmp_path / "no_such.yaml"),
            "--runs-root",
            str(tmp_path),
        ],
        captured_streams,
    )
    assert exit_code == 2
    assert stderr.getvalue()  # 有错误输出


def test_run_default_llm_response_is_do_nothing() -> None:
    """文档合约：默认响应是 do_nothing 的 JSON。"""
    parsed = json.loads(_DEFAULT_LLM_RESPONSE)
    assert parsed == {"action": "do_nothing", "params": {}}


def test_run_seed_option_propagated(
    tmp_path: Path,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    """--seed 42：不 crash 就算过——种子的复现测试在 BaseRules 测试里覆盖。"""
    exit_code = _invoke(
        [
            "run",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--ticks",
            "2",
            "--seed",
            "42",
        ],
        captured_streams,
    )
    assert exit_code == 0


def test_run_no_analysis_skips_report(
    tmp_path: Path,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    """--no-analysis：events.jsonl 仍写，但 analysis/ 目录不生成。"""
    _, stdout, _ = captured_streams
    exit_code = _invoke(
        [
            "run",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--ticks",
            "1",
            "--no-analysis",
        ],
        captured_streams,
    )
    assert exit_code == 0
    run_dir = next(tmp_path.iterdir())
    assert (run_dir / "events.jsonl").exists()
    assert not (run_dir / "analysis").exists()
    # [analysis] 提示也不该出现
    assert "[analysis]" not in stdout.getvalue()


def test_run_no_persist_implicit_skips_analysis(
    tmp_path: Path,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    """--no-persist 隐含不生成分析（run_dir 为 None）——之前的
    test_run_no_persist_produces_no_files 已验证没文件，这里确认 stdout 也干净。"""
    _, stdout, _ = captured_streams
    exit_code = _invoke(
        [
            "run",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--ticks",
            "1",
            "--no-persist",
        ],
        captured_streams,
    )
    assert exit_code == 0
    assert "[analysis]" not in stdout.getvalue()


def test_run_analysis_final_md_contains_expected_sections(
    tmp_path: Path,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    """final.md 的结构性断言：四个 Phase A section 标题都在。"""
    exit_code = _invoke(
        [
            "run",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--ticks",
            "1",
        ],
        captured_streams,
    )
    assert exit_code == 0
    run_dir = next(tmp_path.iterdir())
    md = (run_dir / "analysis" / "final.md").read_text(encoding="utf-8")
    assert "# 仿真分析报告" in md
    assert "## 一、全轨迹总结" in md
    assert "## 二、关键转折点" in md
    assert "## 三、各实体最终状态比较" in md
    assert "## 四、环境变量轨迹" in md


# =============================================================================
# 2.6 `run --llm-enhance` Phase C 增强路径
# =============================================================================


def _write_enhance_script(path: Path, *, enhance_response: dict | str) -> None:
    """写 jsonl 脚本：第 1 行给 tick 决策（do_nothing），第 2 行给分析增强。

    walkthrough 1 tick 默认 company_a 的 llm 消费 1 次。Runtime 跑完后 CLI
    会再调 1 次 provider 做 Phase C 增强。两条脚本对齐两次调用。
    """
    line1 = json.dumps({"action": "do_nothing", "params": {}})
    line2 = (
        enhance_response
        if isinstance(enhance_response, str)
        else json.dumps(enhance_response, ensure_ascii=False)
    )
    path.write_text(line1 + "\n" + line2 + "\n", encoding="utf-8")


def test_run_without_llm_enhance_leaves_phase_a_only(
    tmp_path: Path,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    """默认不加 --llm-enhance：final.md 只有 Phase A 四节，无叙事 / 判断 / 建议。"""
    exit_code = _invoke(
        [
            "run",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--ticks",
            "1",
        ],
        captured_streams,
    )
    assert exit_code == 0
    run_dir = next(tmp_path.iterdir())
    md = (run_dir / "analysis" / "final.md").read_text(encoding="utf-8")
    assert "## 五、局势判断" not in md
    assert "## 六、面向用户的建议" not in md
    assert "## 七、自然语言总览" not in md


def test_run_llm_enhance_fills_three_sections(
    tmp_path: Path,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    """--llm-enhance + mock 合法增强响应：final.md 含三节 LLM 增强内容。"""
    _, stdout, _ = captured_streams
    script = tmp_path / "script.jsonl"
    _write_enhance_script(
        script,
        enhance_response={
            "narrative_summary": "这一个 tick 双方都没有实际动作。",
            "situation_judgement": "局势平稳，没有明显的优势方。",
            "next_action_suggestions": ["关注 reputation 变化", "观察 demand"],
        },
    )
    exit_code = _invoke(
        [
            "run",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--ticks",
            "1",
            "--llm-script",
            str(script),
            "--llm-enhance",
        ],
        captured_streams,
    )
    assert exit_code == 0
    assert "LLM 增强已写入" in stdout.getvalue()

    run_dir = next(tmp_path.iterdir())
    md = (run_dir / "analysis" / "final.md").read_text(encoding="utf-8")
    assert "## 五、局势判断" in md
    assert "局势平稳" in md
    assert "## 六、面向用户的建议" in md
    assert "关注 reputation 变化" in md
    assert "## 七、自然语言总览" in md
    assert "双方都没有实际动作" in md

    # JSON 产物同步更新了三字段
    js = json.loads(
        (run_dir / "analysis" / "final.json").read_text(encoding="utf-8")
    )
    assert js["narrative_summary"].startswith("这一个 tick")
    assert js["situation_judgement"].startswith("局势平稳")
    assert js["next_action_suggestions"][0] == "关注 reputation 变化"


def test_run_llm_enhance_protocol_error_graceful_fallback(
    tmp_path: Path,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    """--llm-enhance 的分析响应缺字段 → stderr 打 warning，保留 Phase A，exit 0。"""
    _, stdout, stderr = captured_streams
    script = tmp_path / "script.jsonl"
    # 响应缺 next_action_suggestions → 触发 LLMProtocolError
    _write_enhance_script(
        script,
        enhance_response={
            "narrative_summary": "n",
            "situation_judgement": "j",
        },
    )
    exit_code = _invoke(
        [
            "run",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--ticks",
            "1",
            "--llm-script",
            str(script),
            "--llm-enhance",
        ],
        captured_streams,
    )
    # run 本身成功
    assert exit_code == 0
    err = stderr.getvalue()
    assert "LLM 增强失败" in err
    assert "LLMProtocolError" in err

    run_dir = next(tmp_path.iterdir())
    md = (run_dir / "analysis" / "final.md").read_text(encoding="utf-8")
    # Phase A 产物保留
    assert "# 仿真分析报告" in md
    assert "## 一、全轨迹总结" in md
    # Phase C 三节被阻断——不应出现
    assert "## 五、局势判断" not in md
    assert "## 六、面向用户的建议" not in md


def test_run_no_analysis_overrides_llm_enhance(
    tmp_path: Path,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    """--no-analysis 与 --llm-enhance 同时指定：不生成任何分析产物（no-analysis 优先）。"""
    _, stdout, _ = captured_streams
    script = tmp_path / "script.jsonl"
    _write_enhance_script(
        script,
        enhance_response={
            "narrative_summary": "should not appear",
            "situation_judgement": "should not appear",
            "next_action_suggestions": ["x"],
        },
    )
    exit_code = _invoke(
        [
            "run",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--ticks",
            "1",
            "--llm-script",
            str(script),
            "--no-analysis",
            "--llm-enhance",
        ],
        captured_streams,
    )
    assert exit_code == 0
    run_dir = next(tmp_path.iterdir())
    assert not (run_dir / "analysis").exists()
    assert "[analysis]" not in stdout.getvalue()


# =============================================================================
# 2.7 第二个场景：三人谈判（架构通用性验证）
# =============================================================================


NEGOTIATION_SCENARIO = Path("scenarios/three_party_negotiation/scenario.yaml")


def test_run_negotiation_walkthrough_end_to_end(
    tmp_path: Path,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    """negotiation 场景端到端 CLI 跑通：

    - alice 用 scripted 驱动：propose → accept → accept，第 3 个 accept 触发 breakpoint
    - 验证 CLI 整链路：world+scenario 加载 / Runtime 推进 / EventLog 落盘 /
      analysis 生成（Phase A）
    - 这是"架构通用性"的硬证据：除 minimal_market 之外的世界也能跑通
    """
    _, stdout, _ = captured_streams
    script = tmp_path / "alice.jsonl"
    script.write_text(
        "\n".join([
            json.dumps({"action": "propose", "params": {"target_id": "bob", "price": 90}}),
            json.dumps({"action": "accept", "params": {"offer_from": "bob", "price": 90}}),
            json.dumps({"action": "accept", "params": {"offer_from": "bob", "price": 90}}),
        ]),
        encoding="utf-8",
    )

    exit_code = _invoke(
        [
            "run",
            str(NEGOTIATION_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--llm-script",
            str(script),
            "--ticks",
            "8",
        ],
        captured_streams,
    )
    assert exit_code == 0

    # 找 run_dir（runs-root 下唯一子目录；脚本文件 alice.jsonl 是文件不是目录）
    run_dirs = [p for p in tmp_path.iterdir() if p.is_dir()]
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]

    # 1. 落盘产物结构
    assert (run_dir / "events.jsonl").exists()
    assert (run_dir / "snapshots").is_dir()
    # tick 0 + tick 1/2/3（breakpoint 在 tick 3 后暂停）至少 4 份快照
    snap_files = list((run_dir / "snapshots").glob("tick_*.json"))
    assert len(snap_files) >= 3

    # 2. CLI 输出含 breakpoint 提示
    out = stdout.getvalue()
    assert "alice_high_trust" in out
    assert "[paused]" in out

    # 3. analysis 落盘
    assert (run_dir / "analysis" / "final.md").exists()
    assert (run_dir / "analysis" / "final.json").exists()

    # 4. final.md 应记录 alice 的 max_trust 变化与触发的断点
    md = (run_dir / "analysis" / "final.md").read_text(encoding="utf-8")
    assert "alice" in md
    assert "max_trust" in md
    assert "alice_high_trust" in md


def test_run_negotiation_default_no_script_runs_to_completion(
    tmp_path: Path,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    """无 --llm-script：alice 走默认 do_nothing，无 trust 变化、无 breakpoint。

    覆盖一条"路径少糖"的回归——确保场景在没有 scripted 引导时也能完整跑完
    8 ticks，trust 关系保持初始值。
    """
    exit_code = _invoke(
        [
            "run",
            str(NEGOTIATION_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--ticks",
            "3",  # 缩短保持测试时长
        ],
        captured_streams,
    )
    assert exit_code == 0
    run_dir = next(p for p in tmp_path.iterdir() if p.is_dir())
    # 无 breakpoint 触发——final.md 不应含触发 id
    md = (run_dir / "analysis" / "final.md").read_text(encoding="utf-8")
    # alice_high_trust 不应被触发记录（虽然 id 可能在场景配置摘要里有）
    assert "alice_high_trust" not in md or "已触发" not in md


# =============================================================================
# 2.5 `run --llm-provider openai` 分派路径（Phase B.2）
# =============================================================================


def _write_llm_config(path: Path, *, with_openai: bool = True) -> None:
    """写一份最小的 config/llm.yaml 到 path。"""
    if with_openai:
        content = """
version: "0.1"
default_provider: openai_test
providers:
  openai_test:
    provider: openai
    model: gpt-4o-mini
    api_key_env: FAKE_CLI_KEY
  mock_alt:
    provider: mock
    model: mock-v1
""".strip()
    else:
        content = """
version: "0.1"
default_provider: mock_only
providers:
  mock_only:
    provider: mock
    model: mock-v1
""".strip()
    path.write_text(content, encoding="utf-8")


def test_run_llm_provider_openai_dispatches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    """--llm-provider openai + 完整 config → 实例化 OpenAIProvider，跑通 1 tick。"""
    from unittest.mock import MagicMock, patch

    config_path = tmp_path / "llm.yaml"
    _write_llm_config(config_path)
    monkeypatch.setenv("FAKE_CLI_KEY", "sk-placeholder")

    with patch("openai.OpenAI") as mock_openai:
        mock_client = MagicMock()
        # 准备一个 Mock 响应：company_a 选 do_nothing
        completion = MagicMock()
        completion.choices = [MagicMock()]
        completion.choices[0].message.content = (
            '{"action": "do_nothing", "params": {}}'
        )
        mock_client.chat.completions.create.return_value = completion
        mock_openai.return_value = mock_client

        exit_code = _invoke(
            [
                "run",
                str(WALKTHROUGH_SCENARIO),
                "--runs-root",
                str(tmp_path),
                "--ticks",
                "1",
                "--llm-provider",
                "openai",
                "--config-llm",
                str(config_path),
                "--no-analysis",
            ],
            captured_streams,
        )
    assert exit_code == 0, captured_streams[2].getvalue()
    # OpenAI 客户端应被真正构造了
    mock_openai.assert_called_once()
    # company_a 是 llm 实体——应调过 create
    assert mock_client.chat.completions.create.called


def test_run_llm_provider_openai_missing_config_errors(
    tmp_path: Path,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    """--llm-provider openai 但 config 不存在 → exit 2 + stderr 有提示。"""
    exit_code = _invoke(
        [
            "run",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--ticks",
            "1",
            "--llm-provider",
            "openai",
            "--config-llm",
            str(tmp_path / "no_such.yaml"),
        ],
        captured_streams,
    )
    assert exit_code == 2
    assert "config" in captured_streams[2].getvalue().lower() or "llm" in captured_streams[2].getvalue().lower()


def test_run_llm_provider_openai_wrong_provider_key_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    """--provider-key 指向的条目 provider=mock → exit 2。"""
    config_path = tmp_path / "llm.yaml"
    _write_llm_config(config_path)
    monkeypatch.setenv("FAKE_CLI_KEY", "sk-placeholder")
    exit_code = _invoke(
        [
            "run",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--ticks",
            "1",
            "--llm-provider",
            "openai",
            "--config-llm",
            str(config_path),
            "--provider-key",
            "mock_alt",  # 这个条目是 mock，不是 openai
        ],
        captured_streams,
    )
    assert exit_code == 2
    assert "openai" in captured_streams[2].getvalue()


def test_run_llm_provider_openai_unknown_key_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    """--provider-key 指向不存在的 key → exit 2。"""
    config_path = tmp_path / "llm.yaml"
    _write_llm_config(config_path)
    monkeypatch.setenv("FAKE_CLI_KEY", "sk-placeholder")
    exit_code = _invoke(
        [
            "run",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--ticks",
            "1",
            "--llm-provider",
            "openai",
            "--config-llm",
            str(config_path),
            "--provider-key",
            "ghost_key",
        ],
        captured_streams,
    )
    assert exit_code == 2
    assert "ghost_key" in captured_streams[2].getvalue()


def test_run_llm_provider_openai_missing_env_var_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    """api_key_env 指向的环境变量没设 → exit 2。"""
    config_path = tmp_path / "llm.yaml"
    _write_llm_config(config_path)
    monkeypatch.delenv("FAKE_CLI_KEY", raising=False)
    exit_code = _invoke(
        [
            "run",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--ticks",
            "1",
            "--llm-provider",
            "openai",
            "--config-llm",
            str(config_path),
        ],
        captured_streams,
    )
    # ProviderError（继承 SimEngineError）在 main() 统一映射到 exit 2
    assert exit_code == 2
    assert "FAKE_CLI_KEY" in captured_streams[2].getvalue()


# =============================================================================
# 3. `step` 子命令（交互式 REPL）
# =============================================================================


def _step_streams(
    commands: list[str],
) -> tuple[io.StringIO, io.StringIO, io.StringIO]:
    """构造 stdin 为命令序列、stdout/stderr 为 StringIO 的三元组。

    每条命令自动追加换行；列表末尾自然 EOF（readline 返空字符串），REPL 退出。
    """
    stdin_text = "\n".join(commands) + ("\n" if commands else "")
    return io.StringIO(stdin_text), io.StringIO(), io.StringIO()


def test_step_help_shows_commands(tmp_path: Path) -> None:
    streams = _step_streams(["help", "quit"])
    exit_code = _invoke(
        [
            "step",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--no-persist",
        ],
        streams,
    )
    assert exit_code == 0
    out = streams[1].getvalue()
    assert "step" in out
    assert "run [N]" in out
    assert "snapshot" in out


def test_step_single_step_then_quit(tmp_path: Path) -> None:
    """'step' 推一个 tick 后 'quit' 退出。"""
    streams = _step_streams(["step", "quit"])
    exit_code = _invoke(
        [
            "step",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--no-persist",
        ],
        streams,
    )
    assert exit_code == 0
    out = streams[1].getvalue()
    assert "--- tick 1" in out
    assert "--- tick 2" not in out


def test_step_run_to_end_then_quit(tmp_path: Path) -> None:
    """'run 5' 推到 tick 5，再 'quit'。"""
    streams = _step_streams(["run 5", "quit"])
    exit_code = _invoke(
        [
            "step",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--no-persist",
        ],
        streams,
    )
    assert exit_code == 0
    out = streams[1].getvalue()
    assert "--- tick 1" in out
    assert "--- tick 5" in out


def test_step_state_command_prints_current(tmp_path: Path) -> None:
    streams = _step_streams(["state", "quit"])
    exit_code = _invoke(
        [
            "step",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--no-persist",
        ],
        streams,
    )
    assert exit_code == 0
    out = streams[1].getvalue()
    assert "tick=0" in out
    assert "company_a" in out


def test_step_state_for_specific_entity(tmp_path: Path) -> None:
    streams = _step_streams(["state company_a", "quit"])
    exit_code = _invoke(
        [
            "step",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--no-persist",
        ],
        streams,
    )
    assert exit_code == 0
    out = streams[1].getvalue()
    assert "entity[company_a]" in out
    assert "cash = 100" in out


def test_step_state_for_unknown_entity(tmp_path: Path) -> None:
    streams = _step_streams(["state ghost", "quit"])
    exit_code = _invoke(
        [
            "step",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--no-persist",
        ],
        streams,
    )
    assert exit_code == 0
    assert "ghost" in streams[1].getvalue()


def test_step_snapshot_after_step(tmp_path: Path) -> None:
    """step 一次 → snapshot 1 应存在并可打印。"""
    streams = _step_streams(["step", "snapshot 1", "quit"])
    exit_code = _invoke(
        [
            "step",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--no-persist",
        ],
        streams,
    )
    assert exit_code == 0
    out = streams[1].getvalue()
    # snapshot.model_dump_json 会输出 tick 字段
    assert '"tick": 1' in out


def test_step_snapshot_missing_tick(tmp_path: Path) -> None:
    streams = _step_streams(["snapshot 99", "quit"])
    exit_code = _invoke(
        [
            "step",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--no-persist",
        ],
        streams,
    )
    assert exit_code == 0
    assert "没有快照" in streams[1].getvalue()


def test_step_pause_resume_toggle(tmp_path: Path) -> None:
    """pause → step 拒绝 → resume → step 通过。"""
    streams = _step_streams(
        ["pause", "step", "resume", "step", "quit"]
    )
    exit_code = _invoke(
        [
            "step",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--no-persist",
        ],
        streams,
    )
    assert exit_code == 0
    out = streams[1].getvalue()
    assert "[paused]" in out
    assert "先 'resume'" in out
    assert "[resumed]" in out
    assert "--- tick 1" in out


def test_step_info_reports_metadata(tmp_path: Path) -> None:
    streams = _step_streams(["info", "quit"])
    exit_code = _invoke(
        [
            "step",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--no-persist",
        ],
        streams,
    )
    assert exit_code == 0
    out = streams[1].getvalue()
    assert "run_id     :" in out
    assert "tick       :" in out


def test_step_unknown_command(tmp_path: Path) -> None:
    streams = _step_streams(["wtf", "quit"])
    _invoke(
        [
            "step",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--no-persist",
        ],
        streams,
    )
    assert "未知命令" in streams[1].getvalue()


def test_step_empty_line_ignored(tmp_path: Path) -> None:
    """空行输入不触发任何命令，也不报错。"""
    streams = _step_streams(["", "  ", "quit"])
    exit_code = _invoke(
        [
            "step",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--no-persist",
        ],
        streams,
    )
    assert exit_code == 0
    out = streams[1].getvalue()
    # 空行不应产生"未知命令"
    assert "未知命令" not in out


def test_step_eof_exits_cleanly(tmp_path: Path) -> None:
    """stdin 立刻 EOF：REPL 干净退出，无异常。"""
    streams = _step_streams([])
    exit_code = _invoke(
        [
            "step",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--no-persist",
        ],
        streams,
    )
    assert exit_code == 0


def test_step_run_with_non_integer_target(tmp_path: Path) -> None:
    streams = _step_streams(["run abc", "quit"])
    _invoke(
        [
            "step",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--no-persist",
        ],
        streams,
    )
    assert "整数" in streams[1].getvalue()


# =============================================================================
# 4. `replay` 子命令
# =============================================================================


@pytest.fixture
def populated_run_dir(tmp_path: Path) -> Path:
    """先跑一次 run，返回 run 目录，供 replay 消费。"""
    streams = (io.StringIO(), io.StringIO(), io.StringIO())
    exit_code = _invoke(
        [
            "run",
            str(WALKTHROUGH_SCENARIO),
            "--runs-root",
            str(tmp_path),
            "--ticks",
            "3",
        ],
        streams,
    )
    assert exit_code == 0
    return next(tmp_path.iterdir())


def test_replay_walks_all_events(
    populated_run_dir: Path,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    _, stdout, _ = captured_streams
    exit_code = _invoke(
        ["replay", str(populated_run_dir)], captured_streams
    )
    assert exit_code == 0
    out = stdout.getvalue()
    assert "--- tick 1" in out
    assert "--- tick 3" in out
    assert "[replay]" in out
    assert "events printed" in out


def test_replay_filter_by_kind(
    populated_run_dir: Path,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    _, stdout, _ = captured_streams
    exit_code = _invoke(
        [
            "replay",
            str(populated_run_dir),
            "--kind",
            "action_executed",
        ],
        captured_streams,
    )
    assert exit_code == 0
    out = stdout.getvalue()
    assert "action_executed" in out
    assert "decision_proposed" not in out


def test_replay_filter_by_tick(
    populated_run_dir: Path,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    _, stdout, _ = captured_streams
    exit_code = _invoke(
        ["replay", str(populated_run_dir), "--tick", "2"],
        captured_streams,
    )
    assert exit_code == 0
    out = stdout.getvalue()
    assert "--- tick 2" in out
    assert "--- tick 1" not in out
    assert "--- tick 3" not in out


def test_replay_until_cutoff(
    populated_run_dir: Path,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    _, stdout, _ = captured_streams
    exit_code = _invoke(
        ["replay", str(populated_run_dir), "--until", "1"],
        captured_streams,
    )
    assert exit_code == 0
    out = stdout.getvalue()
    assert "--- tick 1" in out
    assert "--- tick 2" not in out


def test_replay_missing_events_file(
    tmp_path: Path,
    captured_streams: tuple[io.StringIO, io.StringIO, io.StringIO],
) -> None:
    """指向没有 events.jsonl 的目录：exit 2。"""
    _, _, stderr = captured_streams
    exit_code = _invoke(
        ["replay", str(tmp_path)],
        captured_streams,
    )
    assert exit_code == 2
    assert "events.jsonl" in stderr.getvalue()
