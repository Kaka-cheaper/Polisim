# 开发进度

> 本文件是 **session 衔接文件**。每次新开会话的 AI 先读这里，就能在 30 秒内知道上次做到哪、下次从哪开始。
>
> 每次 session 结束前必须更新本文件。格式见文末"更新规则"。

## 一、当前位置

**阶段**：**v0.1 minimum viable engine 已上线 GitHub** 🎉 ——`https://github.com/Kaka-cheaper/Polisim`（session 22 末，2026-04-26）

**进度**：第 1-6 步全通 ✅；**Phase A / B / C 三段闭环**已交付；**D-011 / D-013 / D-014 / D-015 缩限版 / D-016 + LLM 增强分析升级**已落地；**改名 SimEngine → Polisim**；**670 tests passing**（633 起点 + D-016 +29 + LLM 增强升级 +8）

> 路线：**A → B → C 三段式**（session 18 user 选定）→ 已全部完成 → v1 上线 ✅
>
> **下一阶段路线（session 22 末与用户决策）**：v0.1.1 引擎严谨化 → v0.2 实时态势前端（单仓库 + FastAPI WebSocket + React）。详见第 51 条目。
>
> **session 23 已交付**：D-014/D-015/D-016 三份完整 spec（在 `docs/02-design/decisions/`）。
>
> **session 24 已交付**：D-014 全量实施 + D-015 缩限版 同 session 携带落地。详见第 53 条目。
>
> **session 25 已交付**：D-016 全 8 步实施完成——v0.1.1 引擎严谨化收官 ✅。详见第 54 条目。
>
> **session 26 已交付**：LLM 增强分析升级（world_overview 段 + 证据援引 + 章节重排）+ CLI `--output-language` / `--prompt-history-size` 参数。详见第 55 条目。**v0.1.1 全部目标达成 + LLM 增强体验改进，准备进入 v0.2 前端阶段**。

**已完成**：

1. 全部文档设计（00-overview / 01-requirements / 02-design 共 16 份）
2. `schemas/world_definition.schema.json`、`schemas/scenario.schema.json`（含 D-001 / D-003）
3. `models/world_models.py` + `tests/test_world_models.py`（18 项 pytest 通过）
4. `models/scenario_models.py` + `tests/test_scenario_models.py`（10 项 pytest 通过）
5. `core/definition_loader.py` + `tests/test_definition_loader.py`（20 项通过；三层校验）
6. `core/scenario_loader.py` + `tests/test_scenario_loader.py`(28 项通过；三层校验 + 跨文件校验 + 端到端 YAML 加载)
7. `models/config_models.py` + `tests/test_config_models.py`（27 项通过；LLM / Runtime / Storage / Logging 四类系统配置 + 跨字段校验）
8. `models/runtime_models.py` + `tests/test_runtime_models.py`（64 项通过；8 个原始模型 + **Intervention**）
9. `models/config_models.StorageConfig` 重构：单字段 `runs_root` 替代 `event_log_dir` / `snapshot_dir`（D-007）
10. 三份设计文档同步 4 决策：`实现映射设计.md` 目录结构 + 4.4/4.5/4.6 节、`运行时与事件轨迹设计.md` 十三节 Runtime 接口、`LLM决策协议设计.md` 十二节 Provider 抽象
11. `docs/02-design/实现映射设计.md` 第三节加入 `tests/` 目录与 3.1 小节
12. `AGENTS.md`、`docs/03-implementation/pitfalls.md`、本文件——AI 协作基础设施
13. D-001、D-003、D-004、**D-005 / D-006 / D-007 / D-008** 决策落地
14. `core/providers/base.py` + `core/providers/mock.py` + `tests/test_providers.py`（17 项通过；`LLMProvider` ABC + `ProviderError` + `MockProvider` 两种模式）
15. `core/events.py` + `tests/test_events.py`（25 项通过；`EventLog` append-only + `generate_run_id` + `runs/<run_id>/events.jsonl` + `snapshots/tick_N.json`）
16. `models/runtime_models.py` 新增 `AttributeEffect` / `RelationEffect` / `MessageEffect` / `EnvironmentEffect` + `ValidationResult`（D-009 落地；13 项新增测试）
17. `rules/base.py` + `tests/test_rules_base.py`（35 项通过；`BaseRules` ABC + `validate_action` / `apply_constraints` / `resolve_conflicts` 三项通用实现，任意合法 world 都可用）
18. **架构保健**（session 12）：
    - 新增 `pyproject.toml`——依赖版本约束 + `requires-python>=3.10` + `pip install -e .[dev]` 可用
    - `StorageConfig.event_log_format` 收窄 `Literal["jsonl"]`（去除僵尸的 yaml 选项）
    - `AttributeEffect` docstring 强化 v1 限制说明 + `pitfalls.md` P2 条目
    - D-010（Rules 装配机制）进入待决策区
19. `scenarios/minimal_market/world.yaml` + `scenario.yaml`——walkthrough 首份可运行 YAML 对（2 实体类型 + 2 动作 + 1 消息 + 1 环境 + 1 scheduled event）
20. `rules/minimal_market.py` + `tests/test_rules_minimal_market.py`（17 项通过；`MinimalMarketRules` 覆写 `resolve_effects` + `validate_action` 加 `cash>=budget` 前置条件；含 YAML 加载 + 端到端 validate/resolve/apply_constraints 集成测试）
21. **D-010 装配机制落地**：
    - `schemas/scenario.schema.json` + `models/scenario_models.Scenario` 加 `rules_module: "module:Class"` 可选字段（pattern 三方同步：JSON Schema / Pydantic / rules_loader）
    - 新建 `core/rules_loader.py`——`load_rules_class(rules_module)` 动态 import + 类型安全检查
    - `scenarios/minimal_market/scenario.yaml` 引用 `"rules.minimal_market:MinimalMarketRules"`
    - 新增测试：`tests/test_rules_loader.py`（16 项）+ `test_scenario_models.py` 补 11 项 D-010 测试 + `test_rules_minimal_market.py` 加端到端 loader 链路
22. `models/runtime_models.py` 新增 `TickResult`——单 tick 执行结果快照载体（tick / events / snapshot / paused_after / triggered_breakpoints / reached_total_ticks）+ `tests/test_runtime_models.py` +4 项
23. `core/runtime.py`——`Runtime` 类按 D-008 实装：构造接收 `world / scenario / provider / rules` 或自动经 `rules_loader` 解析 `scenario.rules_module`；暴露 `step() / run_until() / pause() / resume() / get_state() / get_snapshot() / intervene() / close()` + `with` 语法；`step()` 主循环完成——投递出站消息 / 触发 scheduled_events / 激活实体 / 收集决策（支持 scripted + llm 双模式）/ 校验降级 / resolve_effects / apply_constraints / 写 Event Log / 落 snapshot / 断点检查 / pause 模式判定
24. `tests/test_runtime.py` 36 项——构造契约 / bootstrap 初态 / run_id / 单 tick 事件与效果 / scripted + llm 决策 / `run_until` 收敛 / scheduled_event 注入 / 消息 outbox→inbox 投递 / 3 种 intervention / pause/resume / breakpoint 触发 / snapshot 三模式（every_tick / final_only / never）/ fallback 降级 / 上下文管理器
25. **架构审阅 session 2 + 保健落地**（Runtime 核心后一次梳理）：
    - 12 项观察：4 P1 语义 bug / 7 P2 清理 / 1 D-011 候选（异常体系）
    - P1 修复：F1 `MessageSummary.delivered_next_tick` 字段值错位（旧值是 mailboxes 累积、应为 outbox当前长）；F2 `step()` docstring 步骤 10-11 顺序倒；F3 `breakpoint_triggered` 事件化全链路（EventKind Literal +1 枚举 / Runtime 写事件 / TickResult 同步 / 测试断言）；F4 scheduled `environment_event` 加变量声明校验 + number-only 型匹配
    - P2 保健：F5 `_deliver_outbox` 死变量 `remaining` 清除；F6 `_resolve_rules` 多余 `hasattr` 减枝；F7 抽 `_is_numeric` 工具函数 → 3 处 isinstance 嵌套消除；F11 `intervene()` tick 语义澄清
    - F8/F9/F10 P1-P2 写入 `pitfalls.md`（force_action 缺独立事件 / fallback_action 启动期无校验 / `RuntimeError` 滥用 3 条）
    - 新增测试 +5：breakpoint_triggered 参数化 / F1 snapshot message_summary 回归 / F4 三条路径（正路径 + 未声明变量 + 类型不匹配）
26. `cli/run.py` + `cli/__main__.py` + `tests/test_cli.py` ——第 2 步子项 6 落地：
    - `run` 子命令：端到端跑完场景 + 每 tick 摘要打印 + 产物落 `<runs_root>/<run_id>/`；支持 `--ticks` / `--seed` / `--runs-root` / `--llm-script` / `--no-persist` / `--world`
    - `step` 子命令：交互式 REPL，支持 `step` / `run [N]` / `state [id]` / `snapshot <tick>` / `pause` / `resume` / `info` / `help` / `quit` 9 条命令；stdin/stdout/stderr 可注入（测试不走 subprocess）
    - `replay` 子命令：从 `events.jsonl` 流式读取 + 格式化打印；`--tick / --kind / --until` 三轴筛选
    - 默认 LLM：`MockProvider(fixed_response='{"action":"do_nothing"}')`，任意声明了 `do_nothing` 的 world 均能跑通
    - `python -m cli.run <cmd>` 或 `python -m cli <cmd>` 两种调起方式；`pyproject.toml` 已将 `cli` 加入 packages
27. `tests/test_cli.py` 29 项——argparse 错路径 2 / run 8 / step 15 / replay 4；含 --llm-script 驱动 `company_a` 真实执行 promote 的端到端验收
28. 全部测试：**376 passed**（+29 新增，0 回归；Pytest 4.55s）
29. `models/analysis_models.py` + `tests/test_analysis_models.py`（31 项通过）——Phase A 模型：`KindStat` / `ActorStat` / `AttributeChange` / `TurningPoint` / `TickValuePoint` / `EnvironmentChange` / `EntityComparison` / `TrajectorySummary` / `AnalysisResult`（9 个结构型）；`AnalysisResult` 预留三个可选 LLM 增强字段（`narrative_summary` / `situation_judgement` / `next_action_suggestions`）给 Phase C
30. `core/analysis.py` + `tests/test_analysis.py`（42 项通过）——Phase A 纯规则核心：
    - `_load_events_from_file` / `_load_snapshots_from_dir`——从磁盘读 UI-ready 文件（**离线消费者**定位；语义与 `core/events.py` docstring 同步更新）
    - `_summarize_events`：按 kind / actor 聚合 + 断点 / 暂停统计；行为统计只计 action_executed / decision_rejected（避免噪声）
    - `_find_turning_points`：扫相邻快照的实体属性差异，按 `|delta|` 降序取前 K（默认 K=5）；非数值属性 delta=None
    - `_trace_environment`：环境变量 tick-by-tick，只收录变化的 tick（避免膨胀）
    - `_compare_entities`：首 snapshot vs 末 snapshot，提供 `initial_attributes` / `final_attributes` / `changes`
    - `analyze_run(run_dir)` + `render_markdown` + `render_json` + `write_analysis`：四个公开 API。markdown 输出结构对齐 MVP 10.3
31. `cli/run.py` cmd_run 结尾接分析层 + `--no-analysis` 开关；Runtime 加 `run_dir` property（封装 `_event_log` 私有引用）；`core/events.py` docstring 同步明确分析层为离线直读磁盘消费者
32. `tests/test_cli.py` +3——默认 run 生成 final.md/json / --no-analysis 跳过 / --no-persist 隐含跳过 / final.md 结构断言 4 个一级标题全在
33. 全部测试：**452 passed**（+76 新增：31 模型 + 42 核心 + 3 CLI；0 回归；Pytest 5.02s）
34. **D-011 异常体系部分落地**——`core/errors.py` 新建：`SimEngineError` 根 + `ProviderError` / `LLMProtocolError` / `RulesError` / `InvalidStateError` / `PausedError` / `TerminatedError` 六个子类；`core/providers/base.py` 做 re-export 保向后兼容；`cli/run.py` `main()` 捕获面追加 `SimEngineError`；渐进策略——现有 `RuntimeError` / `ValueError` 未迁移（留给单独 session）。测试：`tests/test_errors.py` **19 项**（继承树 / re-export 同一对象 / chained cause / 构造 str roundtrip）
35. `core/llm_policy.py` 抽取重构（Phase B.1）：runtime 的 `_build_llm_prompt` / `_parse_llm_response` / `_decide_via_llm` 主逻辑全部移出。`build_prompt` / `parse_response` / `decide` 三个公开 API；parse 失败抛 `LLMProtocolError`（而非返 None）令上层可精确区分传输错/协议错。Runtime.`_decide_via_llm` 缩减至 ~15 行，捕 `ProviderError` / `LLMProtocolError` 后走 fallback。**纯重构 0 行为变化**——没破一项原有测试。测试：`tests/test_llm_policy.py` **22 项**（build_prompt 5 / parse_response 11 / decide 5 + 纯理论 1）
36. `core/providers/openai.py` + `tests/test_providers_openai.py` 落地（Phase B.2）：
    - `OpenAIProvider(LLMProvider)` 包 `openai>=1.50` SDK；构造期从 `api_key_env` 读环境变量，未设立即抛 `ProviderError`
    - 异常映射：`AuthenticationError` / `RateLimitError` / `APITimeoutError` / `APIConnectionError` / `BadRequestError` / 通用 `APIError` → 统一 `ProviderError`，保留 `__cause__`
    - `response_format={"type": "json_object"}` 强制 JSON 模式——降低 `LLMProtocolError` 概率
    - system prompt 内置约 15 行，明确要求 `{"action", "params", "reason"}` 形状与合法动作白名单
    - `base_url` 透传——同一 provider 兼容 Azure / OpenRouter / 本地 vLLM
    - **19 项测试全 mock**（patch `openai.OpenAI`）：构造 6 / 成功路径 5 / 异常映射 8。无真实请求，无需 CI API key
37. `cli/run.py` Phase B.4 集成：
    - `--llm-provider {mock,openai}` 选项（默认 mock——保留原有行为）
    - `--config-llm <path>` / `--provider-key <str>` 配套选项：openai 时从 `config/llm.yaml` 的 `LLMConfig.providers` 字典挑条目
    - `_build_provider(args)` dispatch：`mock` 走旧 `_build_mock_provider`；`openai` 走新 `_build_openai_provider`（校验 provider 字段 == "openai" / key 存在 / api_key_env 已设）
    - `main()` 统一 except `SimEngineError` → exit 2；任何 provider 构造错均映射为用户可见错信
    - `config/llm.yaml.example` 新建——三条条目示范（官方 OpenAI / proxy / mock）
    - 测试：`tests/test_cli.py` +5 项（openai dispatch / config 缺失 / provider 字段不匹配 / key 未知 / env 未设）
38. `scripts/smoke_openai.py` ——手动端到端烟雾脚本（Phase B.6）：读 config/llm.yaml + walkthrough world + 构造 tick=0 state + 调 `llm_policy.decide` + 打印返回的 `ActionProposal`。**不进 CI**（需真实 API key + 网络）
39. `pyproject.toml` 新增 `openai>=1.50,<2.0` 主依赖（对齐 session 19 调研结论）。openai-1.109.1 实装可用
40. **多语言输出支持**（session 19 末追加；为 Phase C LLM 分析报告铺前置结构）：
    - `models/config_models.RuntimeConfig` 加 `output_language: str = "zh-CN"` 字段（ISO 639-1 或自然语言名；非空校验）
    - `core/llm_policy.build_prompt` 签名加 `*, language: str = "zh-CN"` 关键字参数；在 payload JSON 尾部追加自然语言指令："When filling natural-language fields (e.g. `reason`), respond in {language}."
    - `core/llm_policy.decide` 从 `config.output_language` 读取，传给 `build_prompt`——闭合"RuntimeConfig → decide → build_prompt → prompt 尾部指令"链路
    - **不影响** provider 层（`generate(prompt: str) -> str` 契约不变）；**不影响** JSON 结构字段（action / params 的 key 保持机器标识符）
    - 适用范围：决策层 `reason` 字段 + 未来 Phase C 分析层叙事/判断/建议段落
    - `docs/02-design/LLM决策协议设计.md` 加十三节"输出语言"，原十三顺延为十四
    - 测试：`test_config_models.py` +3（默认值 / 自定义值 / 空字符串拒绝）、`test_llm_policy.py` 原 4 项适配（_extract_payload helper）+ 新增 3 项 build_prompt 语言测试 + 1 项 decide 透传测试
41. 全部测试：**523 passed**（+71 新增：19 errors + 22 llm_policy + 19 openai provider + 5 CLI + 6 多语言；0 回归；Pytest 10.27s）
42. **Phase C 分析层 LLM 增强落地**（session 20）：
    - `core/analysis.py` 扩展三函数（不新建 `analysis_llm.py`——严守 `实现映射设计.md` 第四节的单模块约定）：
      - `_build_analysis_prompt(result, language)`——把 `AnalysisResult` 的 Phase A 部分序化为 JSON payload + 附 JSON 输出契约段 + 尾部注入语言指令；剔除已填的 3 个增强字段避免“让 LLM 看自己的旧答案”
      - `_parse_analysis_response(raw)`——严校 3 key（`narrative_summary` / `situation_judgement` / `next_action_suggestions`）；额外 key 容忍；全部错转为 `LLMProtocolError`
      - `enhance_with_llm(result, provider, config) -> AnalysisResult` 公开 API：调 provider + 解析 + `model_copy(update=...)` 返新对象（Pydantic v2 不可变性惯例）；失败原样上抛 `ProviderError` / `LLMProtocolError`，**不**做重试
    - **多语言链路复用**：`config.output_language` 同时驱动决策层与分析增强层——session 19 铺的模式长出第二个消费者
    - CLI `run` 子命令加 `--llm-enhance` flag（默认关闭）：启用后在 Phase A 产物落盘后复用已构造 provider、覆盖写 final.md/json；失败降级为 stderr warning＋保留 Phase A 版本，**exit code 不变**（仿真本身没失败）
    - `--no-analysis` 优先于 `--llm-enhance`——两者同时给则整个分析段被跳
    - 文档同步：`分析层设计.md` 新增九节《Phase C LLM 增强落地》（原九 → 十）；`models/analysis_models.py` + `core/llm_policy.py` + `LLM决策协议设计.md` 清掉残留的 `core/analysis_llm.py` 旧表述
    - 测试新增：`test_analysis.py` +30（6 build_prompt / 15 parse / 9 enhance）、`test_cli.py` +4（默认关闭 / 成功路径 / 协议错降级 / 与 --no-analysis 互动）
43. 全部测试：**557 passed**（+34 新增：30 Phase C 分析 + 4 CLI 增强路径；0 回归；Pytest 10.84s）
44. **架构审查 + 保健 session 21**（清债七项 F1-F7，0 回归）：
    - **F1（P1 bug）**：`OpenAIProvider.generate` 接 `system_prompt` kwarg；构造期默认值仍用决策导向 system prompt，但 `enhance_with_llm` 显式传分析导向 `_ANALYSIS_SYSTEM_PROMPT` 覆盖——解决"同一 OpenAI 实例同时服务决策层（要返 `{action,params,reason}`）与分析增强层（要返 `{narrative,judgement,suggestions}`）时的 system prompt 角色冲突"；`LLMProvider` ABC docstring 把 `system_prompt` 列入约定 kwargs（识别的覆盖、不识别的静默忽略）
    - **F2（P1 一致性）**：`RulesLoadError` 改继承 `SimEngineError` 入 D-011 体系——`scenario.rules_module` 写错时 CLI 顶层 `except SimEngineError` 给友好提示而非 traceback；`core/errors.py` 异常树文档同步增条目
    - **F3（P2 死代码）**：`llm_policy.decide` 删 `try: ... except ProviderError: raise` 空重抛——异常自然冒泡更清晰
    - **F4（P2 死代码）**：`MinimalMarketRules.validate_action` 把 `errors = list(base_result.errors)` 改 `[]`——上方短路保证此刻 errors 必空，复制无意义
    - **F5（P3 文档漂移）**：`pitfalls.md` 顶条 P1 引用的 `runtime.py` 行号 `:282/:286/:512` 更正为 `:293/:296/:531`；补"D-011 部分落地状态"
    - **F6（P3 文档漂移）**：`AGENTS.md` 第一节"阶段描述"+ 3.4 节 6 步顺序——从"第 1 步进行中"更新为"全 6 步已通；剩余可选分支"
    - **F7（P3 文档漂移）**：`实现映射设计.md` 第六步追加"4. LLM 增强（Phase C，可选）"项，反映 `enhance_with_llm` 落点
    - 测试新增：`test_providers_openai.py` +2（system_prompt 覆盖 / 默认 fallback）、`test_analysis.py` +1（enhance_with_llm 透传 system_prompt）、`test_rules_loader.py` +2（RulesLoadError 入 SimEngineError 树）
    - **端到端真实 OpenAI smoke**（首次！）：扩展 `scripts/smoke_openai.py` 把 Phase C `enhance_with_llm` 一并跑——session 21 用户跑通过 vveai 代理的 `gpt-4o`，**Phase B 决策 [ok] + Phase C 增强 [ok]**——这是 F1 修复（同一 provider 实例服务双角色 system prompt）在真实 LLM 上的硬证据；附带验证 vveai 代理兼容 `response_format=json_object` + 多语言（zh-CN）链路通
    - **新建 `.gitignore`**——项目首份 .gitignore：屏蔽 `__pycache__` / `runs/` / `config/llm.yaml` 等敏感 / 衍生文件；起源是 session 21 用户在配置 LLM 时把真实 key 误填进 `api_key_env` 字段，发现项目根本没 .gitignore 防御（详见 `pitfalls.md` P1 安全条目）
45. 全部测试：**562 passed**（+5 新增：2 OpenAI system_prompt + 1 enhance system_prompt + 2 rules_loader D-011 入树；0 回归；Pytest 7.54s）+ **e2e smoke 通过**（`python scripts/smoke_openai.py` 真实 OpenAI / vveai 网络调用 Phase B + Phase C 双段全 ok）
46. **D-011 Runtime 迁移完成**（session 21 末追加，从可选支线收尾）：
    - 实地扫描发现真实 scope 比原估"30~50 处"小一个量级——业务代码层只有 5 处真正属于 D-011 范畴
    - `core/runtime.py` 5 处 `raise` 全部迁移：`InvalidStateError`（rules 缺 / run_until 倒退 / unknown decision_mode）/ `PausedError`（step in paused）/ `TerminatedError`（step after total_ticks）
    - `tests/test_runtime.py` 4 处 `pytest.raises` 同步换为对应子类（精度提升）
    - `core/errors.py` 三个子类的"v1 占位"docstring 改为"session 21 已落地于 Runtime"实情说明
    - `pitfalls.md` 顶条 D-011 状态从"待迁移"更新为"已结清"
    - 其余 `ValueError` / `FileNotFoundError`（mock 构造参数错 / IO 错 / 用户输入错）按 Python 惯例**保留**，不属于 D-011 范畴
    - 测试总数仍 **562 passed**（异常类型精化、不增减测试数量；0 回归；Pytest 7.35s）
47. **第二个场景：三人谈判落地**（session 21 末追加，验证架构通用性）：
    - 主动覆盖 minimal_market 没演示的架构特性：`direct` 消息（target_id 路由）/ 关系层 `update_value` / 3 种 `decision_mode` 共存（llm + rule + random）/ rules 同时产生 RelationEffect + AttributeEffect + MessageEffect 三种 effect / breakpoint 真触发
    - 落地：`scenarios/three_party_negotiation/world.yaml`（含 `relation_types.trust`，directed=true）+ `scenario.yaml`（3 实体不同 mode + 6 双向 trust 关系 + breakpoint `alice_high_trust` + scheduled_event）+ `rules/three_party_negotiation.py`（`NegotiationRules` 实现 4 动作的 effect 映射）
    - 设计权衡——**为容纳 3 decision_mode 拆出 3 个实体类型**（`Negotiator` / `RuleNegotiator` / `RandomNegotiator`）：v1 `decision_mode` 在 `EntityTypeSchema` 上是类型级唯一字段，不支持实例级覆盖；只能拆 3 个同结构的类型（属性 / 动作完全相同，仅 decision_mode 不同）。这是已知限制，未来可考虑 D-xxx 让 scenario 实例覆盖 mode
    - 发现并记录新 pitfall：**P2 random mode 对带参动作不友好**——`_decide_via_random` 给 `params={}`，必填参数缺失即被 `validate_action` 判 rejected → fallback。这是 v1 真实约束，不是 bug
    - 测试新增：`test_rules_three_party_negotiation.py` +19（validate / resolve / trust clamp / 5 项端到端 walkthrough）；`test_cli.py` +2（端到端 CLI 跑通 + 默认无脚本回归）
    - 测试总数：**583 passed**（+21 新；0 回归；Pytest 7.39s）
48. **D-013 跨层语义校验落地**（2026-04-26 session 22，第二阶段奠基）：
    - **背景**：用户讨论未来 LLM 辅助建模时提出"自我修复循环"概念——LLM 生成 → 校验 → 反馈错误 → 重试。session 21 末锁定了三件相关待决策（D-012 DSL 形式 / D-013 语义校验）；session 22 推进 D-013 落地
    - **scope 调整**（实地调研收窄）：原计划 4 项跨层校验，调研 `core/scenario_loader._validate_cross_references` 后发现 3 项已覆盖（scheduled_event 消息类型 / breakpoint entity / breakpoint attribute），D-013 真实空白只有"World ↔ Rules 跨层"——loader 看不到 rules 实例的部分
    - **落地产物**：`core/semantic_validator.py` 新模块 + `SemanticValidationError(SimEngineError)` 新异常 + `BaseRules.actions_handled() → set[str] | None` 可选钩子 + 两产线场景 rules 钩子实现 + `Runtime.__init__` 集成调用
    - **设计要点**：(a) 入口纯函数 `validate_semantics(world, scenario, rules)` 不依赖 Runtime / EventLog / LLM；(b) `SemanticIssue` frozen dataclass 三元组结构（field_path / kind / detail），便于不同前端渲染；(c) 错误一次性聚合抛出，便于 LLM 修复循环消费；(d) 钩子返回 None 时跳过两项检查（向后兼容）
    - **不消费 YAML**——和 Polisim 其他校验层一样，本模块只消费已加载完毕的 Pydantic 对象。这意味着无论输入是 YAML / 自创 DSL / LLM 直接生成的 dict，校验都通用——这是回应用户"以后切到别的 DSL 校验模块还有用吗"问题的硬证据
    - **结清 P1 pitfall**：`pitfalls.md` 顶条 P1 `fallback_action` 已被 root cause 上游修复，标注"已结清（D-013 落地）"
    - **测试**：`tests/test_semantic_validator.py` +16（SemanticIssue 数据载体 / 钩子返回 None 跳过 / fallback_action 三种情况 / handled 越界 / 错误聚合 / 异常归属 / 真实场景集成 / Runtime 集成构造成功+失败+不留空目录）
    - 测试总数：**599 passed**（+16 新；0 回归；Pytest 12.53s）
49. **项目改名 SimEngine → Polisim + Git 仓库重建**（session 22 末，v1 收工动作）：
    - **改名理由**：调研 GitHub 高星 multi-agent / simulation 项目命名规律——"SimEngine" 由两个最普通词组合，撞名严重（GitHub 已 ~10 个同名项目），SEO 死。新名 **Polisim** = `polis`（古希腊"城邦"，多实体+规则+演化）+ `sim`（仿真），独占词空间，pypi/npm 都空，CLI 友好（`polisim run scenario.yaml`）
    - **改动范围**：20 个文件全文 `SimEngine → Polisim` / `simengine → polisim`，但**保留** `SimEngineError` 类名（公开 API，已 73 处引用，session 21 D-011 才稳定收口；改名风险大、收益小，等同 `pandas.DataFrame` 不因公司改名而改）。技术实现用"占位法"——先把 `SimEngineError` 临时占位 → 全文替换品牌词 → 还原占位
    - **Git 仓库重建**：原 `d:\桌面\github_project\.git` 是空架子（0 commit，无 remote，从未追踪过任何文件）；删除 outer .git，在 SimEngine/ 内 `git init -b main` + 71 文件首次提交；与 `MiroFish-main`（同 github_project 父目录的兄弟项目）完全隔离，独立仓库
    - **物理目录重命名**：`SimEngine/ → Polisim/`——session 内 PowerShell mv 失败（IDE 文件锁），交给用户手动完成；不影响代码（Python 包路径都是相对的，不依赖目录名）
    - **测试总数仍 599 passed**（改名零回归；Pytest 12.43s）
50. **v0.1 上线 GitHub**（session 22 真正终点）：
    - **仓库地址**：[https://github.com/Kaka-cheaper/Polisim](https://github.com/Kaka-cheaper/Polisim)
    - **README**：中英双语 tagline + 4 个 badges（License/Python/Tests/Architecture）+ mermaid 6 层架构图（GitHub 完美渲染）+ quick start（含 OpenAI Phase B / Phase C 三种用法）+ 两个内置场景说明 + 项目结构 + 文档表格 + Roadmap + Acknowledgments（致敬 AgentVerse / AutoGen / CrewAI）。所有中文路径链接 GitHub 自动 URL-encode 可点
    - **LICENSE**：MIT，与 `pyproject.toml` `license = { text = "MIT" }` 同步
    - **作者身份**：`pyproject.toml` `authors` + LICENSE Copyright 都为 `Kaka-cheaper`；3 个 commit 全部 author 为 `Kaka-cheaper <122336926+Kaka-cheaper@users.noreply.github.com>`（GitHub noreply email 隐私保留 + 贡献图绿格子）
    - **安全检查通过**：git history 无 API key / token / password 泄露；`config/llm.yaml`（含 vveai key）被 `.gitignore` 正确屏蔽（session 21 P1 安全坑修的成果）
    - **README 渲染检查通过**：用户 9 张截图覆盖全部章节，mermaid / 中文路径 / badges / 表格全部正确
51. **v0.2 路线决策 + v0.1.1 严谨化范围锁定**（session 22 末，与用户对话定稿）：
    - **背景**：用户问"项目能否通用 / 先 YAML 适配还是先前端 / 前端形式 / GitHub 部署"——4 个产品方向问题。Cascade 分析后用户先选"先严谨化引擎再做前端"，避免在不规范 schema 上盖前端导致返工
    - **v0.2 目标定位**：**单仓库 + FastAPI WebSocket 后端 + React 实时态势前端**。修订原"独立仓库 polisim-web"方案——用户提出"独立仓库要 clone 两个 + 想要动态实时演进"两个反向意见，Cascade 接受并改方案
    - **v0.2 用户体验**：`pip install polisim` → `polisim serve scenarios/xxx/scenario.yaml` → 浏览器自动打开 `localhost:8000` → 看到实时 tick 推进、关系图演化、属性折线、LLM 决策面板 + 暂停/单步/干预控制
    - **v0.2 项目结构（规划）**：在现有 Polisim/ 仓库内增加 `cli/serve.py` + `server/` (FastAPI WebSocket) + `web/` (Vite + React + TS + Tailwind + shadcn/ui)；通过 monorepo 共存，物理上不依赖（前端只通过 WebSocket 收 JSON，零知识 rules）
    - **GitHub Pages 双部署策略**：主路径是本地 `polisim serve`（实时模式）；辅路径是 `kaka-cheaper.github.io/Polisim/`（静态 demo 模式，内置 sample runs，吸引访客）
    - **v0.1.1 严谨化范围（v0.2 前的预备工作）**：3 个"半通用"坑评估
      - **坑 1：action params 强 schema**——当前 `action_types[].params` 是 free-form dict，需改成强结构化 ParamSpec list（name/type/required/description/constraints）。**v0.2 前端紧迫性 🔴 关键**——前端动作面板没有强 schema 无法解释参数语义。工程量约 3-5 天。需升级为 D-014 决策号
      - **坑 2：effect 系统扩充**——当前只 4 种 effect（属性/关系/消息/环境），缺 EntityCreate/EntityDestroy/ChainedAction。**v0.2 紧迫性 🟡 中等**——撑得住 MVP，可推到 v0.2.x。工程量约 5-7 天。可升级为 D-015
      - **坑 3：prompt 上下文规范化**——当前每个 rules 模块自己组 prompt。**v0.2 前端紧迫性 🔴 关键**——前端做"LLM 决策实时面板"必须能拆 prompt 为可解释段。工程量约 5-7 天。需升级为 D-016
    - **v0.1.1 净工时估算**：坑 1 + 坑 3 = 8-12 天 = 3-4 个 session。坑 2 推迟
    - **session 23 入口任务**：评估这 3 个坑的具体 spec，按紧迫性排序，正式升 D-014/015/016 决策号 + 设计文档 + 测试设计；**先不动代码**——把 spec 写清楚，避免实施时反复返工
52. **D-014/D-015/D-016 完整 spec 起草**（session 23，2026-04-26）：
    - **用户决策（session 23 早段）**：v0.1.1 范围 = 全 3 坑（D-014 + D-015 + D-016），把版本成本压到引擎侧，让 v0.2 前端心无旁骛。Cascade 推荐缩限 D-015 仅做 `AttributeEffect.new_value`，其余推 v0.2.x
    - **代码评估**（在写 spec 前）：读了 `models/world_models.py:142-148`（ActionParamSchema 现状）、`core/llm_policy.py:64-136`（build_prompt 现状）、`rules/minimal_market.py`（一个具体 rules 实现示例）、`pitfalls.md` 全量。3 个坑的现状证据 + 影响面已在代码层面确认
    - **产出 1：`docs/02-design/decisions/`** 子目录（新建，与现有"主题型"设计文档分离，便于决策追溯）
    - **产出 2：`D-014-动作参数强Schema化.md`** 完整版 spec（约 280 行）：8 节内容含背景证据 / 6 个新字段定义 / cross-validation 约束 / 影响面矩阵（11 文件）/ 8 步迁移路径 / 30+ 测试设计 / 9 项验收清单 / 5 项未决问题
    - **产出 3：`D-015-effect系统扩充.md`** 简版 spec（约 175 行）：含 4 个新 Effect 类型设计（EntityCreate/EntityDestroy/ChainedAction/AttributeEffect.new_value）+ 缩限版理由（v0.1.1 仅 0.5 天即可结清 P2 第 105 行）+ 推迟全量到 v0.2.x 的论证
    - **产出 4：`D-016-prompt上下文规范化.md`** 简版 spec（约 200 行）：含 PromptContext 数据类完整设计（6 字段 + render 方法）+ EventLog schema 升级 + Rules.enrich_prompt 钩子 + 8 步迁移路径 + 18+ 测试清单
    - **进度文档同步**：progress.md 的"待决策"段升 D-014/D-015/D-016 三项决策号（每项简短记录核心收益 + 预计 session + 依赖关系，完整内容引用上述独立 spec 文档）
    - **实施顺序锁定**：D-014 → D-015（缩限版可融入 D-014 session）→ D-016。理由：D-016 的 available_actions 必须含 D-014 的 ParamSchema 完整字段；D-015 全量版独立可后做
    - **session 24+ 入口任务**：实施 D-014——按 spec 第四节"迁移路径"的 6 步推进；先 schema/Pydantic 双写 + cross-validation，再 LLM 协议、Rules 校验、Runtime random、场景 YAML 迁移、回归测试
53. **D-014 全量实施 + D-015 缩限版同 session 携带落地**（session 24，2026-04-26）：
    - **D-014 6 步迁移路径全过**：
      1. `schemas/world_definition.schema.json` 扩充 ActionParamSchema 加 6 字段（description / default / min / max / values / entity_type_filter）
      2. `models/world_models.py:ActionParamSchema` Pydantic 双写 + `_check_param_constraints` 实施 6 项跨字段约束（含 bool 是 int 子类陷阱保护——number 校验显式排除 bool）
      3. `core/llm_policy.py:build_prompt` available_actions 依次输出全字段 + None 字段过滤保持 prompt 简洁
      4. `rules/base.py:validate_action` 加约束 7-9：min/max/values/entity_type_filter 校验三项（含实体存在性）
      5. `core/runtime.py:_decide_via_random` + 新 `_random_param_value` helper——按 schema 填参（优先 default，否则按类型采样：number 取 [min,max] 均匀、string 从 values 选、entity_ref 按 entity_type_filter 过滤）。**结清 pitfalls.md P2 顶条**（random mode 75% fallback → 可控水平 ~33%）
      6. `scenarios/minimal_market/world.yaml` + `scenarios/three_party_negotiation/world.yaml` 迁移补齐字段（promote.budget / propose.target_id / propose.price / accept.* / reject.* 等）
    - **D-015 缩限版同 session 携带**：`models/runtime_models.py:AttributeEffect` 加 ``new_value: Any`` 字段 + `_check_delta_xor_new_value` 实施互斥；`core/runtime.py:_apply_attribute_effect` 适配双形式路径（new_value 直接赋值，delta 走原有 numeric 校验 + 增量）；`rules/base.py:_clamp_attribute` 入口对 ``new_value`` 形式透传不裁剪。**结清 pitfalls.md P2 第 105 行**（AttributeEffect 只能改 numeric → 现支持 enum/string/bool）
    - **测试增量：+34 项**（599 → 633 passed，0 回归）：
      - `tests/test_world_models.py` +17（D-014 cross-validation 全分支：合法 5 + 非法 12，覆盖 6 项约束的各角度）
      - `tests/test_llm_policy.py` +3（build_prompt 输出含 D-014 字段 / None 过滤 / action description）
      - `tests/test_rules_base.py` +9（D-014 强约束：min/max/values/entity_type_filter 合法 + 非法 + 多错聚合）
      - `tests/test_runtime_models.py` +6（D-015 cross-validator：string/bool/number absolute / 互斥错 / 都不给错 / delta=0 合法）
      - `tests/test_rules_three_party_negotiation.py` 1 项重写（test_offer_message_routed_directly_to_bob 收紧断言：D-014 后 charlie 不再"哑巴"，按 from_negotiator 精确过滤验证 alice 发出的 offer 路由正确）
    - **产出文档同步**：
      - `pitfalls.md` 两条 P2 标"已结清"（random fallback / AttributeEffect 限制）
      - `docs/02-design/decisions/D-014-动作参数强Schema化.md` 实施过程符合 spec 第四节迁移路径，无偏差
    - **session 25+ 入口任务**：实施 D-016（`docs/02-design/decisions/D-016-prompt上下文规范化.md` 第八节迁移路径推进）——build_prompt 重构为 `PromptContext` 结构化表达 + `BaseRules.enrich_prompt` 钩子 + EventLog schema 升级
54. **D-016 全 8 步完成——v0.1.1 引擎严谨化收官**（session 25，2026-04-26）：
    - **8 步迁移路径全过**：
      1. 新建 `models/llm_models.py:PromptContext` Pydantic BaseModel——6 字段（system_role / actor_view / perception / available_actions / language_hint / custom_segments）+ `render()` 方法。**关键设计**：``system_role=None + custom_segments={}`` 默认值保证 render 输出与 D-014 时代 build_prompt **字节级等价**
      2. `core/llm_policy.py:build_prompt` 重构为 `build_prompt_context + ctx.render()` 薄壳；新增 `_extract_actor_relations` / `_extract_recent_decisions` / `_build_available_actions` 三个 helper
      3. `actor_view.relations` 抽 actor 涉及的 outgoing/incoming 关系子集（spec 第六节决策：只抽 actor 局部不展开全图；outgoing 用 `to` 键、incoming 用 `from` 键）。空时省略字段保字节级等价
      4. `actor_view.recent_decisions` 抽 EventLog 最近 N 条 decision_proposed 事件（按 tick 降序），N 由新字段 `RuntimeConfig.prompt_history_size` 驱动（默认 3，min 0 max 10）
      5. `rules/base.py:BaseRules.enrich_prompt` 钩子（默认 no-op）+ 两产线场景 rules 实施：
         - `rules/minimal_market.py:MinimalMarketRules.enrich_prompt`——给 Company 注入 system_role + objective + constraint
         - `rules/three_party_negotiation.py:NegotiationRules.enrich_prompt`——给 Negotiator 注入 system_role + objective + mechanics（含 trust delta 数值）
      6. EventLog 持久化 prompt_context：新增 `models/llm_models.py:LLMDecisionResult`（封装 proposal + prompt_context）；`core/llm_policy.decide` 返回类型 `ActionProposal` → `LLMDecisionResult`；`core/runtime.py:Runtime` 加 `_last_llm_prompt_context` dict 临时容器；`_decide_via_llm` 解构 result 后存 ctx；主循环写 decision_proposed 事件时弹出 ctx 塞入 `payload['prompt_context']`（仅 LLM 模式塞，rule/random/fallback 跳过）
      7. **测试增量 +29 项**（633 → 662，0 回归）：
         - `tests/test_llm_models.py` 新建 +9（PromptContext 构造 4 + render 5）
         - `tests/test_llm_policy.py` +14（TestBuildPromptContext 6 + TestActorViewRelations 2 + TestActorViewRecentDecisions 4 + TestEnrichPromptHook 3，含 1 项 TestDecide.test_happy_path 重写适配 LLMDecisionResult）
         - `tests/test_config_models.py` +5（prompt_history_size 默认 / 自定义 / 上下界 4 项 + defaults 测试新增断言）
         - `tests/test_runtime.py` +1（test_decision_proposed_event_contains_prompt_context_for_llm_mode 端到端验证）
    - **影响面文件**（与 spec 第三节"影响面矩阵"对齐）：
      - 新建 2：`models/llm_models.py` / `tests/test_llm_models.py`
      - 改 7：`core/llm_policy.py` / `core/runtime.py` / `models/config_models.py` / `rules/base.py` / `rules/minimal_market.py` / `rules/three_party_negotiation.py` / `tests/test_llm_policy.py` / `tests/test_config_models.py` / `tests/test_runtime.py`
    - **向后兼容承诺**：当 `event_log=None` / `history_size=0` / `rules=None` 且 actor 不涉及关系时，`PromptContext.render()` 与 D-014 时代 `build_prompt` 输出**字节级等价**——OpenAI smoke / MockProvider scripted 测试完全无感
    - **API 破坏性变更**：`core.llm_policy.decide` 返回类型由 `ActionProposal` 改为 `LLMDecisionResult`——调用方需改为 `result = decide(...); proposal = result.proposal`。对项目内部影响：runtime._decide_via_llm 已适配；`tests/test_llm_policy.py` `TestDecide.test_happy_path` 已重写
    - **v0.1.1 收官**：D-014 + D-015 缩限版 + D-016 三项全部交付，v0.1.1 引擎严谨化阶段完成。**v0.2 前端可启动**——前端可消费 `decision_proposed` 事件 payload 中的 `prompt_context` 字段，分别渲染 system_role / actor_view / perception / available_actions / custom_segments 五段
    - **session 26+ 入口任务**：用户决定后续——可选项包括 (a) v0.2 前端启动（FastAPI WebSocket + React 实时态势面板）/ (b) D-015 全量版补齐（EntityCreate / EntityDestroy / ChainedAction 三个 Effect 类型）/ (c) B.3 协议级重试 / (d) walkthrough 章节扩
55. **LLM 增强分析升级 + CLI 多语言参数**（session 26，2026-04-28）：
    - **触发**：用户实跑 `python -m cli run scenarios/minimal_market/scenario.yaml --llm-enhance` 后反馈：final.md 中初始/中间/最终状态都是面向开发者的数值表格；LLM 增强叙事段没有解释"初始世界是什么、有哪些实体、关系含义、场景目标"，且局势判断与建议**未援引证据**
    - **同 session 携带的两组改动**：
      1. **CLI 多语言/历史参数**（`@d:\桌面\github_project\Polisim\cli\run.py`）：`run` + `step` 子命令各加 `--output-language`（透传 `RuntimeConfig.output_language`）+ `--prompt-history-size`（透传 D-016 第 4 步的 `prompt_history_size`）；新增 `_build_runtime_config` helper 收口构造逻辑
      2. **LLM 增强分析升级**（commit `f91ec7c`，5 文件 +605/-142）：
         - `models/analysis_models.py:AnalysisResult` 加 `world_overview: str | None` 字段——LLM 据此解释初始世界的实体角色 / 关系含义 / 场景目标
         - `core/analysis.py:_ANALYSIS_SYSTEM_PROMPT` / `_ANALYSIS_PROMPT_HEADER` / `_ANALYSIS_PROMPT_INSTRUCTIONS` 三段常量重写：prompt 由 1 段 JSON（仅 Phase A） → 3 段 JSON（**World Definition + Scenario + Phase A**），LLM 协议从 3 字段升 4 字段，**强制要求 `situation_judgement` 与每条 `next_action_suggestions` 援引具体 tick / 属性变化 / 实体 id 作为证据**
         - `core/analysis.py:enhance_with_llm` 签名变更：新增必填 `world: WorldDefinition` + `scenario: Scenario` 关键字参数；max_tokens 1500 → 2000（容纳 world_overview 段）
         - `core/analysis.py:render_markdown` **章节顺序重排** + 去章节编号：
           - 旧序：元信息 → 一·全轨迹总结 → 二·关键转折点 → 三·实体比较 → 四·环境 → 五·局势判断（C） → 六·建议（C） → 七·叙事（C）
           - 新序：元信息 → **世界概览（C） → 全过程叙事（C） → 局势判断（C） → 面向用户的建议（C）** → 全轨迹总结 → 关键转折点 → 实体比较 → 环境
           - LLM 增强段在前，为读者建立背景；Phase A 数值在后作为支撑。"自然语言总览"重命名为"全过程叙事（自然语言总览）"
         - `cli/run.py:cmd_run` 把 world / scenario 传给 enhance_with_llm
    - **测试增量 +5 项 0 回归**（665 → 670 passed）：
      - `tests/test_analysis.py` +5（`test_contains_world_definition` / `test_contains_scenario_payload` / `test_evidence_requirement_in_instructions` / `test_missing_world_overview_raises` / `test_empty_world_overview_raises`）
      - `tests/test_analysis.py` 适配现有 9 项 TestEnhanceWithLLM（加 world/scenario fixture + kwargs）+ 4 项 TestParseAnalysisResponse（raw json 补 world_overview）+ 2 项 TestRenderMarkdown（断言世界概览 / 全过程叙事）
      - `tests/test_cli.py` 3 项适配新章节标题（`test_run_analysis_final_md_contains_expected_sections` 去章节号 / `test_run_llm_enhance_fills_three_sections` 重命名为 four_sections + 加 world_overview / `test_run_llm_enhance_protocol_error_graceful_fallback` 改新标题断言）
    - **API 破坏性变更**：`core.analysis.enhance_with_llm` 必填 `world` + `scenario` kwargs；调用方（CLI 已改）需要传入完整 World Definition + Scenario 对象
    - **向后兼容**：`AnalysisResult.world_overview` 默认 None；纯 Phase A 模式（不调 enhance_with_llm）输出与升级前**等效**——只是去掉了章节"一二三四"编号
    - **session 27+ 入口任务**：用户重跑 OpenAI smoke 验收新版 final.md 的 4 段 LLM 内容；之后按 session 25 末"v0.2 前端启动 / D-015 全量版 / B.3 重试 / walkthrough 扩章 / 新场景"五选项指派

**进行中**：

- v0.1.1 全部目标达成 + LLM 增强分析升级。**session 27+ 入口任务**：用户重跑 OpenAI smoke 验收新版 final.md，之后按需指派下一阶段

**阻塞中**：

- 无

## 二、下一步该做什么

Phase A / B / C 三个主段已全通。剩下三个选项，按优先级：

1. ~~第 1 步：配置校验与加载~~ ✅
2. ~~第 2 步：Runtime 最小骨架 + walkthrough + CLI~~ ✅
3. ~~第 5 步 Phase A：分析层纯规则核心~~ ✅（452 passed）
4. ~~第 3 步 Phase B.0/B.1/B.2/B.4/B.6：接入真实 LLM 协议~~ ✅（517 → 523 passed）
5. ~~Phase C：分析层 LLM 增强~~ ✅（557 passed）
6. **Phase B.3 协议级重试**（可选）：`llm_policy.decide` + `analysis.enhance_with_llm` 加指数退避 + `LLMProviderConfig.max_retries` 驱动。无强需求不做——OpenAI SDK 自带 `max_retries` 已够处理 429 / 5xx。
7. ~~D-011 Runtime 异常体系迁移~~ ✅（session 21；真实 scope 5 处而非估计的 30~50 处）
8. ~~第二个场景（"三人谈判"）~~ ✅（session 21；3 decision_mode + direct 消息 + relations + 混合 effects + breakpoint 全覆盖）
9. ~~D-013 跨层语义校验~~ ✅（session 22；`core/semantic_validator.py` + `BaseRules.actions_handled` 钩子；root cause 修复 P1 fallback_action；为 LLM 辅助建模"自我修复循环"奠基）
10. 第 4 步：扩展 walkthrough 到多实体 / 断点 / 干预章节——可选（已有 negotiation 场景代码作 backbone）
11. 第二阶段：LLM 辅助建模 PoC——`core/modeling_loop.py` 引导问答 + 生成 + 校验循环。**前置阻塞 D-013 已结清**，可启动；3-5h 大工作量，建议独立 session

最小闭环验收目标（`验收标准.md` 第 14 节）已达成 **7/7**：

- ✅ 跑 walkthrough 最小双实体场景 3~5 tick
- ✅ 产生合法 Event Log + 快照
- ✅ `decision_mode=llm` 的 company_a 用 mock provider 能输出合法动作
- ✅ **最终报告**（Phase A 常开）——`final.md` 包含全轨迹总结 / 关键转折点 / 各实体终态对比 / 环境变量轨迹四章
- ✅ **LLM 增强段落**（Phase C，`--llm-enhance` 启用）——`final.md` 加上局势判断 / 面向用户的建议 / 自然语言总览三节

## 三、待决策（需要人工判断的问题）

> 按优先级排序。每条要么转成实现任务，要么明确放弃。

### D-011 异常体系（已完成 2026-04-25 session 21）

- **决定**：采用方案 A
- **session 19 落地**：`core/errors.py` 新建，`SimEngineError` 基类 + 6 子类；`core/providers/base.py` re-export `ProviderError`；`cli/run.py` `main()` 统一捕 `SimEngineError`
- **session 21 完成**（F2 + 后续迁移）：`RulesLoadError` 入树；Runtime 5 处裸 `RuntimeError` / `ValueError` 全部替换为 `PausedError` / `TerminatedError` / `InvalidStateError`；测试 `test_runtime.py` 4 处 `pytest.raises` 同步换为对应子类
- **真实 scope**：原估"~30 处"，实地扫描后**只有 5 处**符合 D-011 范畴；其余 `ValueError` / `FileNotFoundError`（Pydantic 校验 / IO 错 / 用户输入错）按 Python 惯例保留
- **影响**：CLI 顶层 `except SimEngineError` 已正式落地，所有业务异常分类捕获不再模糊

### D-012 DSL 形式：纯 YAML vs 自创 DSL（待决策）

- **问题**：`docs/00-overview/LLM辅助建模方案.md` 5.3 节陷阱 2 提出——未来引导用户/LLM 编写 World Definition + Rules 时，"DSL"应该是哪种形态？
- **候选方案**：
  - **A. 沿用 YAML + JSON Schema + Pydantic**——当前形式；LLM 直接生成 YAML，用 OpenAI `response_format` + 现有 schema 严格约束输出；校验链路完整
  - **B. 自创更高层抽象**（如 `"Alice 信任 Bob 50 分"` 半结构化文本）——需新 parser 把 DSL 翻译为 YAML；可读性更强但实现/调试成本陡增
- **倾向**：**A**（保留 YAML）——LLM 生成 YAML 比生成自创 DSL 风险低、生态成熟；可视化层独立做美化即可
- **何时决定**：第二阶段启动 LLM 辅助建模时；当前**不阻塞**任何 v1 工作

### D-013 语义级跨层校验（已完成 2026-04-26 session 22）

- **决策**：采用方案 **B**——独立模块 `core/semantic_validator.py`
- **session 22 落地**：
  - 新增 `core/errors.SemanticValidationError(SimEngineError)`——携带结构化 `issues: list[SemanticIssue]` 字段，便于 LLM 修复循环消费一份完整反馈
  - 新增 `core/semantic_validator.py`——`SemanticIssue` frozen dataclass（field_path / kind / detail）+ `validate_semantics(world, scenario, rules)` 入口；当前两项校验：(1) `fallback_action ∈ rules.actions_handled()` (2) `rules.actions_handled() ⊆ world.action_types`
  - 新增 `BaseRules.actions_handled() → set[str] | None` 可选钩子；默认返回 None 跳过两项检查（向后兼容）
  - 两个产线 rules 子类（`MinimalMarketRules` / `NegotiationRules`）补钩子实现，分别声明 `{"promote", "do_nothing"}` 与 `{"propose", "accept", "reject", "do_nothing"}`
  - 集成到 `Runtime.__init__`——在 `_resolve_rules` 之后、`EventLog` 构造之前调用，失败时不留空 run 目录
- **scope 调整**（session 22 实地调研发现）：原计划 4 项校验，但 `core/scenario_loader._validate_cross_references` 已覆盖其中 3 项（scheduled_event 消息类型 / breakpoint entity / breakpoint attribute）；D-013 真实空白只有"World ↔ Rules 跨层"，不与 loader 重叠
- **影响**：
  - `pitfalls.md` P1 `fallback_action` 已结清——root cause 上游修复
  - 为未来 LLM 辅助建模铺好关键基础设施——`SemanticIssue` 结构化错误已对接 LLM 反馈循环消费契约
  - 两个产线场景（minimal_market / three_party_negotiation）以及未来新场景的 rules 子类有了显式的"能力声明"机制，scope 错配在构造期就暴露
- **测试**：`tests/test_semantic_validator.py` 16 项（SemanticIssue 数据载体 / 钩子返回 None 跳过 / fallback_action 合法+不合法+未配置 / handled 越界 / 错误聚合 / 异常归属 / 真实场景集成 / Runtime 集成构造成功+失败+不留空目录）
- **关联**：`pitfalls.md` P1 fallback_action（已结清）/ `LLM辅助建模方案.md` 5.3 陷阱 1（已落地，5.4 第 1 项可勾除）

### D-014 动作参数强 Schema 化（✅ 已实施 2026-04-26 session 24）

- **决策**：扩充 `ActionParamSchema` 加 6 个新字段（description / default / min / max / values / entity_type_filter）+ cross-validation
- **完整 spec**：`docs/02-design/decisions/D-014-动作参数强Schema化.md`（含 8 节验收清单 / 影响面表 / 测试设计 / 未决问题）
- **核心收益**：
  - 结清 `pitfalls.md` 顶条 P2（random mode 75% 失败 → 100% 成功）
  - 让 LLM 看到参数语义（description）与约束（min/max/values），减少 LLM 出错
  - **v0.2 前端**的"动作详情面板"前提条件
- **预计 session**：session 24-25（4-5 天）
- **依赖**：无；是 D-016 的前置依赖（available_actions 必须含完整字段）
- **测试增量**：约 30+ 项

### D-015 effect 系统扩充（✅ 缩限版已实施 2026-04-26 session 24；全量版推 v0.2.x）

- **决策（缩限版）**：v0.1.1 只做 `AttributeEffect.new_value` 字段（与 delta 互斥）——结清 `pitfalls.md` 第 105 行 P2（AttributeEffect 不支持 enum/string/bool）
- **完整 spec**：`docs/02-design/decisions/D-015-effect系统扩充.md`（含全量提案 + 缩限版理由 + 推迟到 v0.2.x 的 EntityCreate / EntityDestroy / ChainedAction）
- **核心收益**（缩限版）：
  - 结清 `pitfalls.md` 第 105 行 P2
  - 让动作能改 enum/string/bool 属性（如把 `strategy_bias` 从 `"balanced"` 改到 `"aggressive"`），不再依赖 Intervention 后门
- **预计 session**：缩限版 0.5 天（融入 D-014 一并做）；全量版 5-7 天（推迟 v0.2.x）
- **依赖**：无
- **测试增量**：缩限版 5+ 项；全量版 20+ 项

### D-016 prompt 上下文规范化（spec 已起草 2026-04-26 session 23，待实施）

- **决策**：把 `build_prompt` 重构为结构化 `PromptContext`（system_role / actor_view / perception / available_actions / language_hint / custom_segments）+ `BaseRules.enrich_prompt` 钩子 + EventLog 持久化结构化版本
- **完整 spec**：`docs/02-design/decisions/D-016-prompt上下文规范化.md`（含完整 PromptContext 设计 / 8 步迁移路径 / 18+ 测试清单）
- **核心收益**：
  - actor 看到关系视图 + 决策历史 + 角色提示——**LLM 行为更连贯**
  - rules 模块可注入场景特化提示（"你是谈判者，目标是…"）
  - **v0.2 前端**的"LLM 决策实时面板"前提条件——能拆段可视化
- **预计 session**：session 26-27（5-6 天）
- **依赖**：D-014（available_actions 必须含完整 ParamSchema）
- **测试增量**：约 18+ 项 + smoke OpenAI 验证

### D-002 schema 与 Pydantic 模型的同步策略

- **问题**：两份约束目前手工双写，未来容易漂移。
- **候选方案**：
  - A. 手工双写 + loader 测试里双重校验（当前做法）
  - B. 从 Pydantic 自动生成 JSON Schema（`.model_json_schema()`），删除手写 schema 文件
  - C. 反向从 JSON Schema 生成 Pydantic（工具：`datamodel-code-generator`）
- **倾向**：A 继续，直到某次漂移真的踩坑再升级到 B
- **何时决定**：非紧急，pitfalls 出现 1 次后再讨论

## 四、已决策记录

### D-010（已决） Rules 模块的装配机制

- **决策日期**：2026-04-24
- **结论**：采用**方案 A**——`Scenario` 顶层加可选 `rules_module: str` 字段，格式为 `"module.path:ClassName"`（例：`"rules.minimal_market:MinimalMarketRules"`）。`core/rules_loader.py` 负责：
  1. 校验字符串格式（恰好一个 `:` 分隔）
  2. `importlib.import_module(module_path)` 动态导入
  3. `getattr(module, class_name)` 取到类
  4. 校验 `issubclass(cls, BaseRules)` 且不是 `BaseRules` 本身
  5. 返回**类**（不是实例）——由 Runtime 根据 `RuntimeConfig.random_seed` 等决定构造参数
- **格式说明**：选用 `module:Class` 冒号分隔（而非 `module.Class` 点号），是为了消除"class 名也是点号分隔的" 歧义；同时对齐 setuptools entry_points / FastAPI ASGI 等业界惯例
- **为什么不选 B（CLI 传 rules）**：Scenario 是"本次仿真的完整描述"，规则选择游离在场景外会违反"一次仿真自包含"原则；且复现时（从 `runs/<id>/config.yaml` 读取）无法知道跑的是哪套规则
- **为什么不选 C（约定自动发现）**：world.id 到模块名的映射隐式，改 id 会静默失效；多世界共享同一规则时需要重复文件
- **落地位置**：
  - `schemas/scenario.schema.json`——顶层加 `rules_module` 可选字段
  - `models/scenario_models.Scenario`——加 `rules_module: str | None = None`
  - `core/scenario_loader.py`——加字符串格式校验（结构层）
  - `core/rules_loader.py`（新建）——`load_rules_class(rules_module: str) -> type[BaseRules]`
  - `scenarios/minimal_market/scenario.yaml`——加示范性引用
  - `tests/test_rules_loader.py`——覆盖 6 条失败路径
- **未来影响**：
  - 第 5 步 `core/runtime.py` 构造函数可从 `scenario.rules_module` 解出 rules 类并实例化，零破坏分层
  - CLI `cli/run.py` 可让用户显式覆盖 `--rules` 参数（方案 A 的扩展），但默认走 scenario 自带的 rules_module
  - 未来 UI 展示"本次仿真跑的规则模块"时直接读 scenario.rules_module

### D-009（已决） 规则层公式表示形式

- **决策日期**：2026-04-24
- **结论**：采用"路线 1（接口通用 + 公式插件化）+ 未来过渡到路线 2（schema 数据化）"
  - v1：`rules/base.py` 封装 80% 通用逻辑——`validate_action` / `apply_constraints` / `resolve_conflicts` / 消息路由，完全基于 `WorldDefinition` 数据推导，任意合法 world 都能运行
  - v1：`resolve_effects`（动作公式）保留为**抽象方法**，每个世界自己写 `rules/<world>.py` 模块实现
  - 第二阶段/v0.2：考虑扩展 `ActionEffectSchema` 携带 `delta` / `target` / `param_binding` 字段，使简单公式也能从 world 数据推出——彻底去掉 `rules/<world>.py`
- **为什么不一步到位走路线 2**：设计文档 `世界定义文件格式设计.md` 七节明确"第一版不做复杂表达式 DSL"；提前扩展 schema 会触发连带重构（Pydantic + JSON Schema + loader + 运行时引擎），且路线 2 的简单公式仍覆盖不到条件分支，复杂情况下还是逃回代码——不如 v1 接受这点成本
- **落地位置**：
  - `rules/base.py`（通用接口 + 3 项通用实现）
  - `rules/minimal_market.py`（walkthrough 的 `resolve_effects` 公式，下一 session 产出）
  - `models/runtime_models.py`（新增 `AttributeEffect` / `RelationEffect` / `MessageEffect` / `EnvironmentEffect` 4 个 Effect 模型 + `ValidationResult`）
  - `core/runtime.py` 构造函数接收 `rules: BaseRules` 参数（与 D-008 对齐）
- **未来影响**：每加一个世界都要写一个 Python 规则模块——这是 v1 明确接受的成本，换来零 DSL 复杂度。未来扩展 schema 时，本决策的接口可保留，只是 `resolve_effects` 的默认实现从"raise NotImplementedError"升级为"从 schema 公式字段推导"

### D-008（已决） Runtime 步进式接口

- **决策日期**：2026-04-24
- **结论**：`Runtime` 落成**类**（非纯函数），暴露 `step() / run_until(tick) / pause() / resume() / get_state() / get_snapshot(tick) / intervene(intervention)`。每次 `step()` 返回 `TickResult`（本 tick 的 events + snapshot + paused 标志）。同时新增 `Intervention` 数据模型，对齐 `需求分析.md` 8.3 三级（inject_message / force_action / override_attribute）
- **落地位置**：`docs/02-design/运行时与事件轨迹设计.md` 十三节、`docs/02-design/实现映射设计.md` 4.4 节、`models/runtime_models.Intervention` + 12 项 pytest 测试
- **未来影响**：CLI / 测试 / 未来 UI 共享同一套接口；暂停/断点/干预语义自然表达；不会因为"加一个 UI"就要重构内核

### D-007（已决） Run 上下文与产物目录约定

- **决策日期**：2026-04-24
- **结论**：每次仿真生成可读 `run_id`（默认 `YYYYMMDD_HHMMSS_<world>_<scenario>`），产物统一落到 `{runs_root}/<run_id>/`，包含 `config.yaml` / `events.jsonl` / `snapshots/tick_<N>.json` / `analysis/interim_tick_<N>.{md,json}` + `final.{md,json}`。`StorageConfig` 顶层只保留 `runs_root`，删除原 `event_log_dir` / `snapshot_dir`（后者已加强制失败的回归测试）
- **落地位置**：`models/config_models.StorageConfig` + 3 项更新/新增测试（含 legacy 字段拒绝测试）、`docs/02-design/实现映射设计.md` 目录结构 + 4.5 节
- **未来影响**：所有文件写入按 run 归档，便于第二阶段 UI 展示"历史仿真列表"；`core/events.py` 写入路径由 runtime 层按约定拼接，配置层不越俎代庖定义内部结构

### D-006（已决） UI 策略：第一阶段 UI-ready 但不实装

- **决策日期**：2026-04-24
- **结论**：采用方案 C——第一阶段**不做前端 UI**，但**所有输出强制 UI-ready**（Event Log 走 JSONL、Snapshot 走 JSON、Analysis 走 MD+JSON 双格式；Runtime 暴露步进式 API，见 D-008）。未来 UI 作为独立项目，消费 `runs/<run_id>/` 目录即可，无需改动内核。这解决了 `验收标准.md` 4.3 节"用户可感知"与 `需求分析.md` 11 节"不做复杂 UI"的表面矛盾
- **落地位置**：`docs/02-design/实现映射设计.md` 4.5 节、`models/config_models.StorageConfig` 文档字符串
- **未来影响**：`core/events.py` 必须以流式 JSONL / per-tick JSON 落盘；分析层输出必须 MD+JSON 双格式；不允许任何 "只能从内存读" 的输出路径

### D-005（已决） LLM Provider 抽象层

- **决策日期**：2026-04-24
- **结论**：新建 `core/providers/base.py` 定义 `LLMProvider` ABC（`generate(prompt, **kwargs) -> str`），`core/providers/{mock,openai,anthropic}.py` 分别实现。`core/llm_policy.py` 与 `core/runtime.py` **只依赖 ABC**，严禁 `import openai` / `import anthropic` 外溢到这些文件。第 2~4 步用 `MockProvider` 跑通 tick，第 5 步再实装真实 provider。与 `LLMConfig.provider: Literal["openai", "anthropic", "mock"]` 的配置侧枚举一一对应
- **落地位置**：`docs/02-design/LLM决策协议设计.md` 十二节、`docs/02-design/实现映射设计.md` 4.6 节 + 目录结构新增 `core/providers/`
- **未来影响**：换 provider 不影响协议，协议升级不影响 provider；所有 API key 只在对应 provider 文件内读取；真实 SDK 的异常由 provider 包装成统一 `ProviderError`

### D-004（已决） 系统级 `config/*.yaml` 的字段清单由实现层自定

- **决策日期**：2026-04-24
- **结论**：`docs/02-design/实现映射设计.md` 4.8 节只给出了 `llm / runtime / storage / logging` 四份配置的职责边界，未定具体字段。第一版字段清单由 `models/config_models.py` 固化，所有字段带合理默认值，使首次运行**不需要**任何 `config/*.yaml`。此外不引入独立 `core/config_loader.py`——配置无跨文件引用、无语义复杂度，Pydantic `model_validator` 足够。
- **落地位置**：`models/config_models.py`（LLMConfig / RuntimeConfig / StorageConfig / LoggingConfig 四个 Pydantic 模型 + 各自 `load_*_config(path)` 函数）、`tests/test_config_models.py`（27 项）
- **未来影响**：LLM 协议或 Runtime 演进时，新增字段**必须**回到本文件扩充，而非在各 module 里散写默认值；若 `providers` 将来扩展到多 provider 真实场景，`default_provider` 的跨字段校验已预留

### D-003（已决） `entities` 是否应声明 `min_length=1`

- **决策日期**：2026-04-24
- **结论**：采用方案 A——schema 层加 `minItems: 1`，Pydantic 层用 `Field(..., min_length=1)`。空实体场景在 schema 层就挡下，不给 loader / Runtime 留语义模糊空间
- **落地位置**：`schemas/scenario.schema.json:31`（entities 的 `minItems: 1`）、`docs/02-design/场景文件格式设计.md` 4.2 节约束 4、第六节校验规则 4
- **未来影响**：`models/scenario_models.py` 的 `entities` 字段必须写 `Field(..., min_length=1)`

### D-001（已决） `scenario.schema.json` 中 `required` 字段范围

- **决策日期**：2026-04-24
- **结论**：采用"精细版 B 方案"——schema `required` 只保留 `version / world_id / scenario / entities / config`；`relations / environment / scheduled_events / breakpoints` 改为可选；Pydantic 模型用 `default_factory=list/dict` 保证消费端收到空容器
- **落地位置**：`schemas/scenario.schema.json:6`、`docs/02-design/场景文件格式设计.md` 6.1 节、`docs/03-implementation/pitfalls.md` P1 记录
- **详细理由**：见 `pitfalls.md` 2026-04-24 P1 条目

## 五、会话历史（最近 5 次）

### 2026-04-25 session 21

- 用户发令"先进行一次架构审查和保健，清除技术债"。我通读 `core/` + `models/` + `cli/` + `rules/` + 测试套 + 文档，整理观察清单（P1 bug 2 项 / P2 死代码与一致性 5 项 / P3 已知待办 3 项），向用户呈现并请求决策范围
- 用户选 **P1 + P2 全修**——执行 F1-F7 七项清债：
  - **F1（P1 bug）**：`OpenAIProvider.generate` 加 `system_prompt` kwarg；`enhance_with_llm` 显式传分析导向 `_ANALYSIS_SYSTEM_PROMPT` 覆盖默认；ABC docstring 同步约定。审查时这个 bug 暴露的关键路径——session 19 加了决策导向 system prompt（"decision-making agent"，要返 `{action,params,reason}`）；session 20 把同一 provider 实例又用于 `enhance_with_llm`，user 消息要返三段叙事 JSON——**system + user 角色冲突，但全部测试用 MockProvider 蒙混过关，没暴露**。本次架构审查抓住
  - **F2（P1 一致性）**：`RulesLoadError(Exception)` 改 `RulesLoadError(SimEngineError)` 入 D-011 体系——CLI 顶层 `except SimEngineError` 由此一并捕获 `rules_module` 解析错误
  - **F3-F4（P2 死代码）**：`llm_policy.decide` 删空重抛 `except ProviderError: raise`；`MinimalMarketRules.validate_action` 修死代码 `errors = list(base_result.errors)` → `[]`
  - **F5（P3 文档漂移）**：`pitfalls.md` 顶条 P1 引用的 `runtime.py:282/286/512` 行号更正为 `:293/296/531`，补 D-011 进展状态
  - **F6-F7（P3 文档漂移）**：`AGENTS.md` 阶段描述从"第 1 步进行中"更新为"全 6 步已通"；`实现映射设计.md` 第六步追加 Phase C LLM 增强项
- 测试总数：**562 passed**（+5：2 OpenAI system_prompt + 1 enhance 透传 + 2 rules_loader 入 D-011 树；0 回归；Pytest 7.54s）

**验收证据 1**（对应 `验收标准.md` 第 18 节自检：内审与债清）：

```text
验收对象：架构审查 + 保健（P1+P2 清债 F1-F7）
对应验收项：内部健康度——D-011 异常体系一致性 / OpenAI 多消费者解耦 / 文档与代码漂移消解
输入：
  - 4 代码修复：core/providers/{base,openai}.py、core/{analysis,llm_policy,rules_loader,errors}.py、rules/minimal_market.py
  - 3 文档订正：AGENTS.md、docs/03-implementation/pitfalls.md、docs/02-design/实现映射设计.md
  - 5 测试新增：test_providers_openai.py +2 / test_analysis.py +1 / test_rules_loader.py +2
执行方式：
  python -m pytest tests/ --tb=short -q
实际输出：
  562 passed in 7.54s（+5 新；0 回归）
是否通过：通过
备注：D-011 全量迁移、rules/base 抽 _is_numeric helper、cmd_run 主循环冗余 break 三项 P3 留待独立 session
```

**验收证据 2**（F1 修复在真实 LLM 上有效——首次端到端 OpenAI smoke）：

```text
验收对象：F1 系统提示角色解耦 + Phase B/C 真实 LLM 链路
对应验收项：MVP 8.4 节"接入真实 LLM"+ 10.3 节"LLM 自然语言总览"——首次离开 mock
输入：
  - scripts/smoke_openai.py 扩展：Phase B 决策 smoke + Phase C enhance_with_llm smoke 双段
  - config/llm.yaml：通过 vveai 代理调 gpt-4o，api_key_env 间接引用 VVEAI_API_KEY
执行方式：
  python scripts/smoke_openai.py（需 $env:VVEAI_API_KEY 已设）
实际输出（关键摘要）：
  ========== Phase B：决策层 smoke ==========
  [ok] action_type : do_nothing
       reason      : 当前没有紧迫需要行动的情况，选择暂不采取行动以保持资源。
  ========== Phase C：分析增强 smoke ==========
  [ok] narrative_summary : 本次模拟运行时间较短，仅持续了3个时间刻，共发生了8个事件。...
       situation_judgement: 当前情况缺乏足够的数据来判断优势或风险。...
       next_action_suggestions: 5 条中文建议（命中 prompt 上限 2-5）
  ========== 总结 ==========
  Phase B 决策 smoke    : [ok]
  Phase C 增强 smoke    : [ok]
是否通过：通过
顺带验证：
  - 同一 OpenAIProvider 实例先后服务两种角色 → 无 system prompt 冲突（F1 真实有效）
  - vveai 代理兼容 OpenAI response_format=json_object（潜在风险点排除）
  - 多语言 zh-CN 默认链路通（reason / 三段叙事全中文且对齐 input payload）
备注：smoke 用空骨架 AnalysisResult，narrative 抱怨"数据不足"是预期行为；想要更精彩的 demo 须真跑 minimal_market 多 tick 后再 enhance
```

### 2026-04-24 session 20

- 用户发令 Phase C（分析层 LLM 增强）。我按 AGENTS.md 3.3 严守落点——`实现映射设计.md` 第四节只列 `core/analysis.py` 单模块，所以**不**新建 `core/analysis_llm.py`，Phase C 代码进 `core/analysis.py`（原 Phase A 函数身边）
- **Phase C 落地**（`core/analysis.py` 扩展）：
  - `_build_analysis_prompt(result, language)`——吃 `AnalysisResult` 的 Phase A 部分，剔除 3 个增强字段避免自循环；尾部注入语言指令（与 session 19 `llm_policy.build_prompt` 同款机制）
  - `_parse_analysis_response(raw)`——严校 3 key、额外 key 容忍、全部错转为 `LLMProtocolError`
  - `enhance_with_llm(result, provider, config)` 公开 API——调 provider + 解析 + `model_copy(update=...)` 返新对象；失败原样上抛，**不**做重试（与 `llm_policy.decide` 对齐）
- **多语言链路复用**：`config.output_language` 同时驱动决策层和分析增强层——session 19 铺的模式长出第二个消费者；测试里新增一条 `test_passes_output_language_to_prompt` 断言 `fr-FR` 注入、`zh-CN` 不出现
- **CLI 集成**：`run` 子命令加 `--llm-enhance` flag（默认关闭，因为 LLM 调用要钱/要网），Phase A 产物落盘后复用已构造 provider、覆盖写 final.md/json；失败降级为 stderr warning+保留 Phase A 版本、**exit code 不变**；`--no-analysis` 优先于 `--llm-enhance`
- **docstring / 设计文档清理**：同步订正 `models/analysis_models.py` + `core/llm_policy.py` + `docs/02-design/LLM决策协议设计.md` 13.3/13.5 里 4 处残留的 `core/analysis_llm.py` 旧表述；`分析层设计.md` 新增九节《Phase C LLM 增强落地》（原九→十，补一条"不做即时分析 LLM 增强"）
- 测试总数：**557 passed**（+34：30 Phase C 分析 + 4 CLI 增强路径；0 回归；Pytest 10.84s）

**验收证据**（对应 `验收标准.md` 第 5 步：分析层 LLM 增强）：

```text
验收对象：Phase C——分析层 LLM 增强端到端
对应验收项：MVP 10.3 #4/#5 最终输出的"趋势判断"与"面向用户建议"段
输入：
  - 1 扩展：`core/analysis.py` +三函数 / docstring 更正 / imports 补 LLMProvider+RuntimeConfig
  - 1 扩展：`cli/run.py` +`--llm-enhance` flag + cmd_run 调用链路 + warning 降级
  - 2 订正：`models/analysis_models.py` + `core/llm_policy.py` docstring 清掉 `core/analysis_llm.py` 旧说法
  - 2 文档：`分析层设计.md` +九节《Phase C 落地》、`LLM决策协议设计.md` 13.3/13.5 同步
  - 2 测试补：`test_analysis.py` +30 项 / `test_cli.py` +4 项
执行方式：
  1. 测试：python -m pytest tests/ --tb=short -q
  2. CLI 人工验证：python -m cli.run run scenarios/minimal_market/scenario.yaml \
       --runs-root ./runs --ticks 1 --llm-script <script> --llm-enhance
实际输出：
  - pytest：557 passed in 10.84s（+34：30 分析 Phase C + 4 CLI；0 回归）
  - CLI：final.md 追加五/六/七节（局势判断 / 面向用户的建议 / 自然语言总览）
是否通过：通过
备注：最小闭环 7/7 达成（含 Phase C LLM 增强段）；剩余可选分支：Phase B.3 重试 / D-011 迁移 / walkthrough 扩章
```

### 2026-04-24 session 19

- 用户确认 Phase B 接 OpenAI，指示先调研再动手。我跑了 6 个 parallel web search + 3 个文档读取。结论：
  - **LangChain / AutoGen / CrewAI 都过重**——与 Polisim 工程纪律 (AGENTS.md MUST NOT) 冲突
  - **裸用 `openai` SDK (v1.x) 最符需求**——它自带 max_retries + response_format(json_object) + base_url 多端点兼容
  - Instructor 的模式 + Stanford generative-agents 的 prompt 模板结构值得借鉴，但不引入依赖
  - 用户选定 A 方案（裸用 openai SDK）
- **Phase B.0 落地**：`core/errors.py` 新建 + `SimEngineError` 基类树（D-011 部分解决）
  - 19 测试：继承树 / re-export 同一对象 / chained `__cause__` / 构造 str roundtrip
- **Phase B.1 落地**：`core/llm_policy.py` 抽取——`build_prompt` + `parse_response` + `decide` 三公开 API
  - Runtime 的 `_decide_via_llm` 缩至 ~15 行，捕 `ProviderError` / `LLMProtocolError` 后走 fallback
  - `parse_response` 抛 `LLMProtocolError` 而非返 None——令上层区分传输/协议错
  - 22 测试全通；**纯重构 0 行为变化**——原有测试全绿
- **Phase B.2 落地**：`core/providers/openai.py`——裸包 `openai>=1.50` SDK
  - 构造期校 `api_key_env` + `os.environ` 立即抛错，避免延迟到首次调用
  - 6 类 SDK 异常映射到 `ProviderError`（auth / rate / timeout / conn / bad请求 / 通用 API）
  - `response_format={"type":"json_object"}` + system prompt 双保险 LLM 返 JSON
  - 19 测试 patch `openai.OpenAI` 全 mock——未发任何真实请求；CI 不需 API key
- **Phase B.4 落地**：CLI `run` / `step` 加 `--llm-provider {mock,openai}` + `--config-llm` + `--provider-key`
  - `_build_provider(args)` dispatch 版；mock 默认保留原有行为
  - `main()` 统一 except `SimEngineError` → exit 2
  - `config/llm.yaml.example` 新建——三条条目示范（官方 OpenAI / proxy / mock）
  - 5 测试：openai dispatch / config 缺失 / wrong provider / unknown key / env 未设
- **Phase B.6 落地**：`scripts/smoke_openai.py`——手动端到端脚本，用真实 API key 验证单次往返；**不进 CI**
- **Phase B.3 重试**——暂延：OpenAI SDK 自带 `max_retries` 已处理传输层 429/5xx；协议层重试（重提 + 附错误信息）对 v1 收益低，留给 Phase C 前的专站会议
- **多语言输出支持**（末段追加，为 Phase C 铺前置）：
  - `RuntimeConfig.output_language: str = "zh-CN"` 新字段（ISO 639-1 / 自然语言名均可，非空校验）
  - `llm_policy.build_prompt(..., language="zh-CN")` 链路打通，在 payload JSON 尾部注入自然语言指令
  - `llm_policy.decide` 从 `config.output_language` 取值传入——闭合 "Runtime 初始化 → decide → build_prompt → prompt 尾部" 链路
  - 不改 provider 层契约；不改 JSON 输出 schema——只改受影响的自然语言字段（`reason` 、Phase C 叙事段落）
  - `docs/02-design/LLM决策协议设计.md` 新增十三节《输出语言》（原十三 → 十四）
  - 6 新测：3 `RuntimeConfig` 字段 + 3 `build_prompt` 语言参数 + 1 `decide` 透传 （共 7）
- **依赖新增**：`pyproject.toml` 加 `openai>=1.50,<2.0`；实装版 `openai-1.109.1`
- 测试总数：**523 passed**（+71：19 errors + 22 llm_policy + 19 openai provider + 5 CLI + 6 多语言；0 回归；Pytest 10.27s）

**验收证据**（对应 `验收标准.md` 第 3 步：接入 LLM 决策协议）：

```text
验收对象：Phase B 核心——端到端走通 OpenAI provider
对应验收项：LLM 决策协议设计.md 十二节 Provider 抽象层 + D-005 + D-011
输入：
  - 4 新建：`core/errors.py` / `core/llm_policy.py` / `core/providers/openai.py` / `scripts/smoke_openai.py`
  - 3 新建测试：`test_errors.py` (19) / `test_llm_policy.py` (22) / `test_providers_openai.py` (19)
  - 3 修改：`core/providers/base.py` re-export / `core/runtime.py` _decide_via_llm 简化 / `cli/run.py` +4 选项 + main SimEngineError
  - 2 配置：`pyproject.toml` +openai / `config/llm.yaml.example` 新建
  - 1 CLI 测试补：`test_cli.py` +5 openai 路径
执行方式：
  1. 依赖安装：pip install "openai>=1.50,<2.0"
  2. 测试：python -m pytest tests/ --tb=short -q
实际输出：
  - 安装：openai-1.109.1 + jiter-0.14.0 + distro-1.9.0
  - pytest：523 passed in 10.27s（+71：19 errors + 22 llm_policy + 19 openai provider + 5 CLI + 6 多语言）
是否通过：通过
备注：Phase B 核心通 + 多语言链路铺好；Phase C / B.3 / D-011 迁移 三个可选分支等用户发令
```

### 2026-04-24 session 18

- 用户问项目最终呈现形式——我拆成 v1 CLI+文件产物 vs v2 独立 UI 消费 runs/ 目录（D-006）
- 用户问下一步选择文档原顺序（LLM 优先）还是先做分析层——我推荐分析层优先（离线可测 / 触及最小闭环第 7 项）
- 用户追问能否纯规则和真实 LLM 都要——确认二者不冲突，细化成 **A → B → C 三段式**路线，用户选 A
- **Phase A 落地**：
  - `models/analysis_models.py`（9 结构型，~250 行）：`KindStat` / `ActorStat` / `AttributeChange` / `TurningPoint` / `TickValuePoint` / `EnvironmentChange` / `EntityComparison` / `TrajectorySummary` / `AnalysisResult`
  - `core/analysis.py`（~430 行）：`_load_events_from_file` + `_load_snapshots_from_dir` + 4 个聚合函数 + `analyze_run` + `render_markdown` + `render_json` + `write_analysis`
  - `core/runtime.py`：加 `run_dir` property（封装 `_event_log.run_dir`）
  - `cli/run.py`：`cmd_run` 结尾调 `analyze_run + write_analysis`；增 `--no-analysis` flag；`--llm-script` 读写改用 `utf-8-sig` 容 BOM
  - `core/events.py` docstring：修正分层约束描述——原文说分析层不直读磁盘，实际设计是离线直读（与未来 UI 同路）
- **关键设计决定**：
  - `AnalysisResult` 预留 3 个可选 LLM 字段：`narrative_summary` / `situation_judgement` / `next_action_suggestions`——Phase A 默认 None，renderer 发现 None 自动省略对应 section；Phase C 只需写 enricher 不动 renderer
  - `turning_points` 算法：相邻快照属性差按 `|delta|` 降序取 top-5；非数值 delta=None 排在末
  - `_summarize_events` 行为统计只计 `action_executed` / `decision_rejected`——避免 `decision_proposed` 的每 tick 噪声
  - 环境变量轨迹只记变化的 tick 加初始值——避免膨胀
- **烟雾手跑验证**：`python -m cli.run run scenarios/minimal_market/scenario.yaml --runs-root <tmp> --ticks 3 --llm-script <script>` → exit=0；run_dir 中产出 `analysis/final.md` (1064B) + `analysis/final.json` (1725B)；company_a 的 cash/reputation 变化在 turning_points 中正确呈现
- **测试新增 76 项**：
  - `tests/test_analysis_models.py` 31（每结构型回践 + extra=forbid + 约束下界）
  - `tests/test_analysis.py` 42（I/O 9 / 聚合子步骤 16 / 公开 API 14 / CLI 集成 3）
  - `tests/test_cli.py` +3（--no-analysis / --no-persist 隐含跳过 / final.md 结构断言）
- **最小闭环 7/7**：`验收标准.md` 第 14 节第 7 项 “结束后拿到最终报告” 达成
- 测试总数 **452 passed**（+76；0 回归；Pytest 5.02s）

**验收证据**（对应 `验收标准.md` 第 14 节 + 11.2 最终报告）：

```text
验收对象：核心 Phase A——纯规则分析层
对应验收项：验收标准.md 第 14 节最小闭环第 7 项 + 11.2 最终报告输出
输入：
  - 1 新建 `models/analysis_models.py`（~250 行）
  - 1 新建 `core/analysis.py`（~430 行）
  - 1 新建 `tests/test_analysis_models.py`（31 项）
  - 1 新建 `tests/test_analysis.py`（42 项）
  - 4 修改：`core/runtime.py` +run_dir / `cli/run.py` +analysis 调用 + --no-analysis + utf-8-sig / `core/events.py` docstring / `tests/test_cli.py` +3 项
执行方式：
  1. 烟雾：python -m cli.run run scenarios/minimal_market/scenario.yaml --runs-root <tmp> --ticks 3 --llm-script <script>
  2. pytest tests/ --tb=short -q
实际输出：
  - 烟雾：exit=0；<tmp>/<run_id>/analysis/ 下产出 final.md (1064B含 4 个一级标题) + final.json (1725B结构化产物)
  - pytest：452 passed in 5.02s（+76：31 models / 42 分析核心 / 3 CLI）
是否通过：通过
备注：Phase A 完结；Phase B（接 OpenAI provider + llm_policy）可立刻起步。Phase A 产出的
      同一份 `AnalysisResult` 在 Phase C 只需填三个可选字段，markdown renderer 自动补上对应章节，
      无需改 render 代码。
```

### 2026-04-24 session 17

- 完成第 2 步子项 6（`cli/run.py`）——末端 CLI 落地，第 2 步挂牌 **100%**
- 代码落地：
  - **`cli/run.py` ~470 行**，argparse 驱动三子命令：
    - `run <scenario.yaml> [--world P] [--ticks N] [--seed S] [--runs-root R] [--llm-script F] [--no-persist]`——端到端跑完，每 tick 打 events + 实体属性摘要 + 最终 summary
    - `step <scenario.yaml> [同上]`——交互式 REPL，`step / run [N] / state [id] / snapshot <t> / pause / resume / info / help / quit` 9 条命令
    - `replay <run_dir> [--tick T] [--kind K] [--until N]`——从 `events.jsonl` 流式回放
  - **`cli/__main__.py`**：允许 `python -m cli <cmd>` 的更短形式
  - `pyproject.toml` packages 加 `cli`——wheel 能押包进去
- 关键设计点：
  - `main(argv, *, stdin, stdout, stderr)` 显式流注入——测试用 `io.StringIO` 截获，无需 subprocess，29 项 CLI 测试跑在 ~0.4s
  - 默认 LLM provider = `MockProvider(fixed_response='{"action":"do_nothing"}')`，任何声明 `do_nothing` 的 world 均可用 CLI 跑通——不需用户配套
  - `--llm-script <file.jsonl>` 每行一个 JSON，走 MockProvider.scripted——验收测试用它驱动 company_a 的 promote→cash 100→80
  - 异常分级：`FileNotFoundError` / `ValueError` → exit 2，argparse 错→exit 2，正常结束→exit 0
  - 子命令底层状态通过 `args.stdin/stdout/stderr` 传递，不共享全局 `sys.*`——测试并发安全
- **烟雾测试手跑验证**：`python -m cli.run run scenarios/minimal_market/scenario.yaml --runs-root $env:TEMP/...` 成功产出 `events.jsonl`（3846 bytes）+ `snapshots/tick_{0..5}.json`（6 份×351 bytes），exit=0
- **测试新增 29 项**（`tests/test_cli.py`）：
  - argparse 错路径 2（无参 / 未知子命令）
  - run 8（端到端 / --ticks / --no-persist / --llm-script 驱 promote / --llm-script 非法 JSON / scenario 不存在 / 默认响应合约 / --seed）
  - step 14（help / step / run N / state / state id / state unknown / snapshot / snapshot missing / pause-resume / info / unknown / empty / EOF / run 非整数）
  - replay 5（全量 / --kind / --tick / --until / events.jsonl 缺失）
- **最小闭环验收**（验收标准.md 第 14 节的 6/7）：
  - ✅ 合法 World + Scenario（scenarios/minimal_market/）
  - ✅ 规则层处理最小动作（MinimalMarketRules）
  - ✅ Runtime 推进 5 tick
  - ✅ Event Log + Snapshot 正常生成
  - ✅ llm + rule 两类实体均能输出合法动作
  - ⏸ 中间/最终分析（第 5 步对象，不属于本阶段）
- 测试总数 **376 passed**（+29 新增，0 回归；Pytest 4.55s）

**验收证据**（对应 `验收标准.md` 第 14 节 + 10.1 每轮输出）：

```text
验收对象：cli/run.py 端到端运行——第 2 步最后一块拼图
对应验收项：验收标准.md 第 14 节最小闭环（1…6）+ 10.1 每轮输出
输入：
  - 1 新建 `cli/run.py`（~470 行）
  - 1 新建 `cli/__main__.py`
  - 1 新建 `tests/test_cli.py`（29 项）
  - `pyproject.toml` packages 列表 +1
执行方式：
  1. 烟雾：python -m cli.run run scenarios/minimal_market/scenario.yaml --runs-root <tmp>
  2. pytest tests/ --tb=short -q
实际输出：
  - 烟雾：exit=0；tmp/<run_id>/ 中产出 events.jsonl (3846B) + snapshots/tick_{0..5}.json (6 × 351B)
  - pytest：376 passed in 4.55s（+29：平布到 argparse 2 / run 8 / step 14 / replay 5）
是否通过：通过
备注：第 2 步正式完结；下一步进第 3 步（接真实 LLM），将涉及 `core/llm_policy.py` + 
      openai/anthropic provider + D-011 异常体系可能开决策。
```

### 2026-04-24 session 16

- 用户要求"再进行一次架构审阅和保健"——Runtime 核心落地后的第二轮审阅，覆盖 Runtime / Rules / Providers / EventLog 四层交界
- **审阅产出：12 项观察**分级：
  - 4 项 **P1 语义 bug**（F1-F4）——需当场修
  - 7 项 **P2 保健**（F5-F7, F11）——清理死代码 / 可读性 / docstring
  - 1 项 **D-011 候选**（异常体系）——等 CLI 实装时再决
  - 3 项 写入 pitfalls（F8-F10）：`RuntimeError` 滥用 / `fallback_action` 启动期无校验 / `force_action` 生效瞬间无事件
- **P1 修复（核心 bug）**：
  - **F1 `MessageSummary.delivered_next_tick` 字段值错位**：旧值是 `sum(len(v) for v in mailboxes.values())`——累积投递数；字段语义是"下一 tick 将投递的"，应为 `len(outbox)`。改之后 emitted == delivered_next_tick（v1 outbox 每 tick 清空的推论）
  - **F2 `step()` docstring 步骤 10/11 倒序**：实际是"9 断点 → 10 暂停 → 11 snapshot"，docstring 写成了"10 snapshot → 11 断点"，已同步
  - **F3 `breakpoint_triggered` 事件化**：EventKind Literal +1 枚举（`models/runtime_models.py:50-62`）；`_check_breakpoints` 改签名 `-> tuple[list[str], list[EventRecord]]`，每命中写一条 `breakpoint_triggered`（payload：`breakpoint_id` + `tick`）——修复 D-006 UI-ready 一致性漏洞
  - **F4 scheduled `environment_event` 校验**：提出 `_apply_scheduled_environment_event` 方法；未声明变量 → warn + 跳过；`number` 变量收到非 numeric 值 → warn + 跳过（避免类型漂移）
- **P2 保健**：
  - F5 `_deliver_outbox` 删除死变量 `remaining`，开头 docstring 写明不存在跨 tick 滯留语义
  - F6 `_resolve_rules` 删除多余 `hasattr(self, "_runtime_config")`
  - F7 抽出模块级 `_is_numeric(value) -> bool` 工具函数 → 消除 3 处重复的 `isinstance(v, (int, float)) and not isinstance(v, bool)` 嵌套
  - F11 `intervene()` docstring 明确区分 `EventRecord.tick`（Runtime 当前 tick）与 `payload["tick"]`（intervention 声明 tick）
- **测试新增 5 项**：
  - `test_runtime_models.py` ALL_EVENT_KINDS +1 参数化（breakpoint_triggered）
  - `test_runtime.py` +1：`test_snapshot_message_summary_reflects_outbox_not_mailbox`（F1 回归防护）
  - `test_runtime.py` +3：F4 三条路径（正路径 delta=40 / 未声明变量 → 不写不改 / 类型不匹配 → 维持原值）
  - `test_runtime.py` breakpoint 测试 +断言：`events 中查 breakpoint_triggered 且 payload.breakpoint_id 对应`
- **分层健康复查**（grep 验证）：`rules/*` 零 core 依赖；`core/providers/*` 零业务依赖；`core/events.py` 零 runtime/rules 依赖——依赖方向整洁
- 测试总数 **347 passed**（+5 新增，0 回归失败；Pytest 3.40s）

**验收证据**（对应 `验收标准.md` 17.1 架构维护 + 9.1 Event Log 一致性）：

```text
验收对象：架构审阅 session 2 + F1-F7/F11 保健落地 + F3 breakpoint_triggered 全链路
对应验收项：验收标准.md 4.2 / 17.1（架构维护）+ 9.1（Event Log 完备性）+ D-006 UI-ready 约束
输入：
  - 19 源文件 + 11 测试文件 + 16 设计文档 + 10 条 D-00x 决策的综合审视
  - 3 处修改：`models/runtime_models.py`（Literal +1）/ `core/runtime.py`（~80 行修动）/ `tests/test_runtime_models.py`（同步 Literal）
  - 2 处新增：`tests/test_runtime.py`（+4 项）/ `docs/03-implementation/pitfalls.md`（+3 条）
执行方式：
  1. grep 扫描各层 import 验证依赖方向干净
  2. 穷举脚注 F1-F11 对应的行号与影响范围
  3. python -m pytest tests/ --tb=short -q
实际输出：
  - 12 条观察分级输出到用户回复（8 项即时落地 + 3 项 pitfalls + 1 项 D-011）
  - 全量 347 passed in 3.40s（+5 项，0 回归）
是否通过：通过
备注：全部修改尺寸 <100 行，未引入新模块 / 新依赖；分层齐齐整整。
      下一 session 可直接起子项 6 `cli/run.py`，没有架构调整待办。
```

### 2026-04-24 session 15

- 完成第 2 步子项 5（`core/runtime.py` + `tests/test_runtime.py`）——Runtime 核心按 D-008 + D-010 全量实装
- 代码落地：
  - `models/runtime_models.TickResult`——单 tick 结果载体（tick / events / snapshot / paused_after / triggered_breakpoints / reached_total_ticks 六字段；`extra="forbid"`）
  - `core/runtime.Runtime`——构造签名 `Runtime(world, scenario, provider, rules=None, *, config=None, event_log=None)`：若 `rules=None` 则经 `rules_loader.load_rules_class(scenario.rules_module)` 动态装配；接受外部注入的 `EventLog`（便于测试隔离）
  - `Runtime.step()` 主循环九阶段严格分层：
    1. 投递上 tick 的 outbox → 本 tick 的 inbox
    2. 触发 scheduled_events（按 `tick == current_tick` 筛选）
    3. 按 `decision_mode` 分支收集决策（scripted 走实体 `script`，llm 走 provider.generate + 解析）
    4. `rules.validate_action`——失败走 world `defaults.fallback_action` 降级
    5. `rules.resolve_effects` → `rules.apply_constraints` → `rules.resolve_conflicts`
    6. 应用 effects 到 `WorldState`（4 类 Effect 按类型 dispatch）
    7. 写 Event Log（`decision` / `effect` / `message_sent` / `intervention_applied` / `breakpoint_triggered` / `tick_end` 六类）
    8. 按 `snapshot_mode` 决定是否存快照（every_tick / final_only / never）
    9. 断点检测 + pause 模式判定（manual / at_tick / at_breakpoint 三模式）
  - `Runtime.intervene()`——三级干预（inject_message / force_action / override_attribute）分别对应 inbox 注入 / 本 tick force map 覆盖 / WorldState 直接写；均产生 `intervention_applied` 事件
  - `Runtime.run_until(target_tick)`——循环 step 直至 `current_tick >= target_tick` 或遇 pause/breakpoint 主动中断
- 测试落地 40 项：
  - `tests/test_runtime_models.py` +4（TickResult 最小构造 / 完整字段 / 字段校验 / extra 拒绝）
  - `tests/test_runtime.py` 36 项，覆盖：构造契约（含自动从 `rules_module` 装配） / bootstrap 初态 / `run_id` 生成 / 单 tick 事件与效果 / scripted + llm 双决策模式 / `run_until` / scheduled_event 触发 / 消息 outbox→inbox 流水 / 3 级 intervention / `pause()`/`resume()` / breakpoint 触发 / snapshot 三模式 / fallback 降级链路 / `with` 上下文关闭
- 工程要点：
  - Runtime 构造函数的 `rules=None` 分支——装配责任在 Runtime 内部，外部测试不需要显式 `load_rules_class`（但可传已实例化的 rules 做隔离）
  - scheduled_events 的 `tick == current_tick` 而非 `<=`——避免积压事件一次性喷发（pitfalls 未记，当前没踩；若改语义需开 D-011）
  - `force_action` 的作用域是"下一次 step 的该 actor"——用 `_forced_actions` dict 承载，step 开头消费+清空
  - `snapshot_mode="never"` 时 `get_snapshot(tick)` 返回 `None`，保持 API 一致性
  - walkthrough scenario 缺 pause/breakpoint 配置——对应测试 deepcopy 场景后显式注入（不污染真实 YAML）
- 测试总数 **342 passed**（+40 新增，0 回归失败）
- 第 2 步 **95%**（仅剩 CLI 子项 6）

**验收证据**（对应 `验收标准.md` 第 14 节最小闭环 + 7.1 / 7.2 / 8.3 / 9.1 / 9.2 多项打通）：

```text
验收对象：Runtime 核心（core/runtime.py）+ TickResult 模型
对应验收项：验收标准.md 第 14 节（最小闭环）+ 7.1（动作合法性）+ 7.2（效果映射）+ 8.3（干预）+ 9.1（Event Log）+ 9.2（Snapshot）
输入：
  - 1 源文件新建（core/runtime.py ~531 行）
  - 1 模型扩展（models/runtime_models.TickResult + 4 项测试）
  - 1 测试新建（tests/test_runtime.py 36 项）
  - 依赖前序全链路：world/scenario 加载 + rules_loader + BaseRules + MinimalMarketRules + MockProvider + EventLog
执行方式：python -m pytest tests/ --tb=short -q
实际输出：342 passed in 3.39s
  [tests/test_runtime.py] 36 项全通过
  [tests/test_runtime_models.py] 4 项 TickResult 新增 + 64 项回归 = 68 项全通过
  [回归] 其余 238 项测试全通过
是否通过：通过
备注：第 2 步子项 5 达成；下一步（子项 6：CLI）纯包装层，无新核心语义。验收目标
      "跑 walkthrough 的最小双实体场景 3~5 tick + 产生合法 Event Log/Snapshot + 
      llm 决策能用 mock provider 输出合法动作"——已由 test_runtime.py 若干集成测试验证
```

### 2026-04-24 session 14

- 用户敲定 D-010 方案 A——`Scenario.rules_module: "module.path:ClassName"` 字段 + `core/rules_loader.py` 动态导入
- 代码落地（schema / Pydantic / loader / 测试 / YAML / 设计文档 一致性全链路）：
  - `schemas/scenario.schema.json`——顶层加 `rules_module` 可选字段，含 regex pattern
  - `models/scenario_models.Scenario`——加 `rules_module: str | None` 字段，Pydantic `pattern` 与 schema 三方同步（第一次在模型层用 `pattern` 参数）
  - `core/rules_loader.py`（新建）——`load_rules_class` + `RulesLoadError`；6 条失败路径显式检查：非字符串 / 空串 / 冒号数量错 / 冒号两侧为空 / 模块导入失败 / 类不存在 / 不是类 / 不是 BaseRules 子类 / 是 BaseRules 本身（抽象）
  - `scenarios/minimal_market/scenario.yaml`——加上 `rules_module: "rules.minimal_market:MinimalMarketRules"` 示范引用
- 测试新增 28 项：
  - `tests/test_rules_loader.py` 16 项（合法路径 / 4 类失败分组）
  - `tests/test_scenario_models.py` 11 项（None 默认 / 合法路径 / 9 组 parametrize 的格式错误）
  - `tests/test_rules_minimal_market.py` +1（端到端：scenario.yaml → rules_loader → MinimalMarketRules）
- 设计文档同步：
  - `场景文件格式设计.md` 顶层结构 + 新增 4.0 `rules_module` 小节
  - `实现映射设计.md` 目录结构加 `core/rules_loader.py`，4.3 节加 D-010 约束
- 工程要点：
  - 三方 pattern 同步（JSON Schema regex / Pydantic pattern / rules_loader split 校验）——属于 D-002 待决策范围内的手工双写成本，当前接受
  - `load_rules_class` 返回**类**而非实例——把构造参数（如 `random_seed`）的责任留给 Runtime
  - 测试夹具放在 `test_rules_loader.py` 模块尾部，复用 pytest 自动 sys.path 机制，避免新增 fixture 文件
- 测试总数 **302 passed**（+28 新增，0 回归失败）

**验收证据**（对应 `验收标准.md` 第 14 节最小闭环第 2 步"Runtime 骨架前置条件"之装配机制）：

```text
验收对象：D-010 方案 A 全量落地（schema + Pydantic + rules_loader + 集成）
对应验收项：验收标准.md 第 14 节；与 D-008 的 Runtime 构造签名打通
输入：
  - 2 源文件改动（scenario.schema.json / scenario_models.py）
  - 1 新建源文件（core/rules_loader.py）
  - 1 新建测试（tests/test_rules_loader.py 16 项）
  - 2 测试更新（test_scenario_models.py + 11 项、test_rules_minimal_market.py + 1 项）
  - 1 YAML 更新（scenarios/minimal_market/scenario.yaml）
  - 2 设计文档（场景文件格式设计 + 实现映射设计）
执行方式：python -m pytest tests/ --tb=short -q
实际输出：302 passed in 2.28s
  [tests/test_rules_loader.py] 16 项全通过
  [tests/test_scenario_models.py] 11 项 D-010 新增全通过（含 9 参数化）
  [tests/test_rules_minimal_market.py] 18 项全通过（+1 端到端）
  [回归] 其余 257 项测试全通过
是否通过：通过
备注：Runtime 实装路径完全解锁；rules 装配的失败模式由 RulesLoadError 统一承载
```

- 完成第 2 步子项 4 后半（D-009 路线 1 的具体兑现）：
  - `scenarios/minimal_market/world.yaml`——walkthrough 首份可运行 world（2 实体类型 + 2 动作 + policy_signal 消息 + policy_pressure 环境变量）
  - `scenarios/minimal_market/scenario.yaml`——对齐 `docs/01-requirements/最小示例Walkthrough.md` 的 5-tick 场景（含 tick=2 的 scheduled policy_signal 注入）
  - `rules/minimal_market.py`——`MinimalMarketRules(BaseRules)`：覆写 `resolve_effects`（promote → cash -budget + reputation +5；do_nothing → []）+ `validate_action`（追加 cash>=budget 前置条件，其他校验走基类）
  - `tests/test_rules_minimal_market.py` 17 项：YAML 加载形状校验 / 公式映射正确 / 前置条件拒绝 / 基类透传未知动作与缺失参数 / **端到端**集成（validate → resolve → apply_constraints 含 reputation clamp 边界）
- 工程要点：
  - 真实 YAML 通过现有 loaders 加载 → 回测了 loader 链路的端到端正确性（scheduled event 的 message.type 跨文件校验等）
  - `MinimalMarketRules.validate_action` 在 base 已 invalid 时不叠加业务错误——避免"基础错 + 业务错"让用户困惑
  - 端到端测试固化"前置条件失败时 apply_constraints 的 min=0 clamp 作为兜底"——Runtime 的防御路径有明确契约
- 测试总数 **274 passed**（+17 项 minimal_market 测试）
- 第 2 步 **70%**（子项 4/6 完成；5 和 6 为 Runtime 与 CLI，5 阻塞于 D-010）

**验收证据**（对应 `验收标准.md` 6.1 World + 6.2 Scenario + 7.1 动作合法性 + 7.2 效果映射 + 14 节最小闭环前半）：

```text
验收对象：scenarios/minimal_market/world.yaml + scenario.yaml + rules/minimal_market.py
对应验收项：验收标准.md 6.1 / 6.2 / 7.1 / 7.2 + 第 14 节（前半：配置+规则可运行）
输入：
  - 真实 YAML 文件 2 份（world + scenario）
  - tests/test_rules_minimal_market.py 17 项 fixture
  - 依赖前序 base.py / definition_loader / scenario_loader 全链路
执行方式：python -m pytest tests/ --tb=short -q
实际输出：274 passed in 1.94s
  [tests/test_rules_minimal_market.py] 17 项全通过
    - YAML 加载 + 形状校验 2 项 ✅
    - 实例化契约 2 项 ✅
    - resolve_effects 4 条公式路径 ✅
    - validate_action 6 条校验路径（含业务前置 + 3 条基类透传）✅
    - 端到端集成 3 项（正常 / reputation 上限 clamp / cash 下限 clamp 兜底）✅
  [回归] 其余 257 项测试全通过
是否通过：通过
备注：第 2 步子项 5（Runtime）等 D-010 决策；rules + scenarios 的分层纪律经此一役得到实证——
      rules/minimal_market.py 只有 ~40 行业务代码，80% 逻辑来自 BaseRules
```

## 六、更新规则

每次 session 结束前（或在用户准备关闭窗口前），按下面流程更新本文件：

1. 改"当前位置"的已完成/进行中/阻塞
2. 改"下一步"——确保第一条是真正能马上执行的粒度（2~5 分钟任务）
3. 如有新的设计犹豫，加到"待决策"
4. 在"会话历史"最顶端追加一条（格式：`### YYYY-MM-DD session N`），保持最多 5 条，老的删掉
5. 如踩坑了，去 `docs/03-implementation/pitfalls.md` 追加

## 七、本文件不做什么

- ❌ 不记录完整实现细节（那是代码和 docstring 的事）
- ❌ 不复述设计文档内容（那些在 `docs/02-design/`）
- ❌ 不存放决策的完整论证（待决策区只写"问题+候选+倾向"）
- ❌ 不当 TODO 垃圾桶（多于 10 条待办说明粒度太细，该合并）
