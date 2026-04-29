# 踩坑记录

## 一、本文件用途

记录开发过程中遇到的**所有非 trivial 问题**：

1. 设计/实现冲突
2. 架构边界被破坏的瞬间
3. 某个原本以为"显然"的点，实际踩了坑
4. schema / 文档 / 代码三者不一致的情况
5. 第三方库 / 工具的非直觉行为
6. LLM 决策返回的奇怪结果

## 二、记录原则

- **debug 完成后立刻写一条**——不要攒，攒了就忘
- **一条 ≤ 10 行**——只写"现象+根因+解法"，不写完整 debug 过程
- **按倒序排列**——最新的在最上面
- **每条必带时间戳和严重度**

## 三、严重度分级

- **P0 致命**：直接违反分层边界或验收标准，后续所有相关实现都必须参考
- **P1 重要**：影响某一层的设计选择，未来同类场景可能重现
- **P2 小坑**：局部 workaround，仅影响当前模块

## 四、记录模板

每条坑按下面模板追加到第五节最顶端：

```markdown
### [P?] YYYY-MM-DD 一句话标题

- **现象**：看到了什么
- **根因**：为什么会这样
- **解法**：怎么绕/修
- **相关文件**：`path/to/file.py:L10-L20` 或 `docs/02-design/xxx.md`
- **防再犯**：（可选）是否需要加进 `AGENTS.md` 的 MUST NOT
```

## 五、踩坑清单

### [P2] 2026-04-29 in-memory run（persist=False）跑完不推 run_finished 事件（session 33 审查发现）

- **现象**：`RunService._broadcast_tick` 中 `reached_total_ticks=True` 分支检查 `runtime.run_dir is not None` 才推 `RunFinishedEvent`——**内存模式 run 跑完后前端 WebSocket 收不到 finished 事件**，仅靠 `close_run(None sentinel)` 关闭连接，前端无从知道是"正常完结"还是"server 挂了"。
- **根因**：`RunFinishedEvent.data` 是 `AnalysisResult`，Phase A 分析 `analyze_run(run_dir)` 必须走磁盘——`run_dir is None` 时没法生成 AnalysisResult。设计简化期跳过推送，但语义不完整。
- **影响范围**：
  - v0.2 当前路径**不命中**——`RunService.create_run` 强制 `persist=True`，所有通过 server 创建的 run 都有 run_dir
  - 边缘场景：未来若加 "in-memory mode" 配置（`POST /runs {persist: false}`）会触发
  - 测试场景：单测 fixture 用 `persist=True`，所以也不显形
- **解法**（暂缓）：v0.2 不修。两种潜在思路：
  1. 用空 AnalysisResult（all 字段默认值）—— 但 AnalysisResult 含 `run_id` 等必填字段，构造负担
  2. 改 `RunFinishedEvent.data: AnalysisResult | None`—— 破坏类型契约
  3. 加新事件 `RunFinishedNoAnalysisEvent`—— schema 复杂度↑
- **相关文件**：`server/services/run_service.py:240-251`（`_broadcast_tick` reached_total_ticks 分支）、`server/api/v1/ws_events.py:RunFinishedEvent`
- **防再犯**：v0.3+ 若加 in-memory mode 配置，必须同步修复此分支；当前 docstring 已标注"v0.2 强制 persist=True 自然规避"

### [P2] 2026-04-29 server lifespan shutdown 时 WebSocket 订阅者收不到 run_finished（session 33 审查发现）

- **现象**：`server/app.py` lifespan 关闭顺序是 `registry.shutdown_all()` 后 `stream_service.detach()`。但 `shutdown_all` 仅 close 各 Runtime 的 EventLog——**不**调 `stream_service.close_run()` 通知订阅者；随后 `detach()` 直接清空 `_subscribers` + `_loop=None`。结果：仍连着的 ws 客户端**永远不会**收到 run_finished / 任何关闭信号——它们靠 starlette 在 shutdown 阶段强制 close ASGI 连接才结束。
- **根因**：v0.2 单进程 + Ctrl+C 终止——starlette/uvicorn 的强制关闭兜底了"挂死"问题，但语义上"server 优雅关闭"应该向客户端发 close(1001) 或 RunFinishedEvent。当前实施没做。
- **影响范围**：
  - 用户主动 Ctrl+C 时——客户端收到不明的连接断开（HTTPException 或 1006），不知是 server 关闭还是网络抖动
  - 部署到生产时——若有反向代理（nginx）做 graceful shutdown，可能转发不正确的 close code
- **解法**（暂缓）：v0.2 不修。三种潜在思路：
  1. lifespan finally 顺序调整：先 `for run_id in active_runs: stream_service.close_run(run_id)` 再 `registry.shutdown_all` 再 `detach`
  2. 加专门的 `ServerShutdownEvent` ws 事件——但 schema 复杂度↑
  3. detach 内部主动遍历订阅者发 None sentinel——StreamService 单点处理
- **相关文件**：`server/app.py:_lifespan` finally 块、`server/services/stream_service.py:detach`、`server/runtime_registry.py:shutdown_all`
- **防再犯**：v0.3+ 加生产部署时优先修方案 3——StreamService 自治更干净。生产环境 deployment guide 写明"客户端应处理 1006 close code 重连"

### [P3] 2026-04-28 server 测试连发 POST /runs 触发 EventLog.generate_run_id 秒级冲突（session 31）

- **现象**：`tests/test_server_runs.py::test_create_max_concurrent_returns_503` 早期版本——测试 max_concurrent=3 时连续 3 次 POST /runs 不传 run_id；第 2 次起报 400 (`INVALID_REQUEST`) 而非预期 201/503。错误来自 `RuntimeRegistry.register("..." 已注册)`——run_id 重复。
- **根因**：`core/events.generate_run_id()` 用 `<timestamp_秒级>_<scenario_id>` 形态；mock provider + tmp_path 下 Runtime 构造非常快（<100ms），同一秒内多次调用产生**相同** run_id。CLI 单跑场景从不命中（人手隔几秒），但 server 端 TestClient 高速连发就显形。
- **影响范围**：
  - 测试场景：连续 POST /runs 不传 run_id——必命中。已通过测试中显式 run_id 规避
  - 生产场景：人类用户从画廊点 [▶ 开始] 再点下一个，间隔通常 >1s，**不会命中**
  - 边缘场景：未来批量脚本调用 server，必须显式传 run_id 或在 client 加节流
- **解法**（已落地）：v0.2 不动 v1 内核——测试用 explicit run_id 规避；CLI 实际行为不受影响
- **解法**（未来）：若服务端要支持高频创建，让 `generate_run_id` 加微秒或 uuid4 后缀（v1 行为契约不变，只是更精细）。当前不开 D-xxx，等真有用户反馈再做。
- **相关文件**：`core/events.py:generate_run_id`、`server/runtime_registry.py:register`（防御式校验）、`tests/test_server_runs.py::TestCreateRun::test_create_max_concurrent_returns_503`
- **防再犯**：server 路由 / 测试文档明确"高频创建场景必须显式 run_id"——v0.2 不主动改 v1 内核

### [P2] 2026-04-25 `random` decision_mode 对带参动作不友好（v1 限制）

- **现象**：session 21 落地三人谈判场景时发现，charlie（`decision_mode=random`）从 4 个动作（propose / accept / reject / do_nothing）中均匀采样，**75% 概率选到带参动作**——但 `Runtime._decide_via_random` 给出的 `params={}` 是空 dict，必填参数缺失立即被 `BaseRules.validate_action` 判 `decision_rejected` → 走 fallback。结果是 random mode 实际上**只能稳定执行无参动作**。
- **根因**：`_decide_via_random` 的实现假设"动作类型不带参或参数有合理默认"——但 v1 的 `ParamSchema` 只声明 `type` 与 `required`，没有 `default` 字段，random 路径无法填值。
- **影响范围**：
  - 任何 `decision_mode=random` + 多带参动作的实体——random 几乎总会被 rejected → fallback
  - 不影响 `llm` / `rule` mode（前者由 LLM 主动出参；后者目前默认走 `do_nothing` / 列表首项）
- **解法**（短期）：
  - 接受现状——random mode v1 主要演示**架构机制**而非实用决策
  - 场景设计时若希望"随机选有意义的动作"，把该实体类型的 `actions` 限为**无参动作**（如 `do_nothing`）；否则 fallback 是预期行为
  - 测试时这成为可观测的"fallback 路径覆盖证据"——见 `test_rules_three_party_negotiation.py::test_three_decision_modes_all_active`
- **解法**（未来）：给 `ParamSchema` 加 `default` 或 `random_strategy` 字段（D-xxx 待开）；`_decide_via_random` 升级为“按 schema 填随机参数”
- **相关文件**：`core/runtime.py:580-592`（`_decide_via_random`）、`scenarios/three_party_negotiation/world.yaml`（charlie 演示此限制）
- **防再犯**：场景设计时若用 random mode 且实体有多种动作，**预期 fallback 比例高**——这不是 bug，是 v1 的真实约束
- **已结清**（session 24 落地 D-014）：`ActionParamSchema` 扩充 6 字段（description / default / min / max / values / entity_type_filter）后，`Runtime._decide_via_random` 已升级为“按 schema 填参”——优先用 ``default``，否则按类型采样（number 取 [min,max] 均匀、string 从 values 选、entity_ref 按 entity_type_filter 过滤）。两个场景的 YAML 已迁移补齐字段；negotiation 中 charlie 仅在 self-propose 少数路径仍会 fallback（~33%，来自 target_id 随机选到自己）——从 75% 降到可控水平。本条作为历史样本保留。

### [P0] 2026-04-25 `api_key_env` 字段被误填真实 API key + 项目无 `.gitignore`

- **现象**：session 21 用户配置 `config/llm.yaml` 跑真实 OpenAI smoke 时，把 vveai 真实 key（`sk-...`）直接写进了 `api_key_env` 字段——这个字段的语义是**环境变量名**（如 `VVEAI_API_KEY`），不是 key 本身。同时发现项目根本没有 `.gitignore`——只要 `git add .` 这个含 key 的文件就会进版本历史。
- **根因**：
  - 字段名 `api_key_env` 不够强烈警示（看起来像"放 key 的字段"）；docstring 是放在 `LLMProviderConfig` 模型里的，配置文件用户看不到
  - `config/llm.yaml.example` 顶部第 13 行有"**永远不要**把真实 API key 直接写进 YAML"提示，但用户跳过了注释直接改字段
  - 项目从启动就**没**建 `.gitignore`——session 1-20 全部信赖"用户不会 git add config/"。Phase B（session 19）落地真实 provider 后这个空白才致命化
- **解法**（已落地）：
  1. 立即建 `.gitignore`（仓库子目录级），把 `config/llm.yaml` / `runs/` / `__pycache__/` / `.venv/` 等全 ignore
  2. 教用户：先把 key 复制到 PowerShell `$env:VVEAI_API_KEY = "sk-..."`，然后改 yaml 字段为 `api_key_env: VVEAI_API_KEY`
  3. **强制要求**用户作废已外泄的 key（已写入本地文件 + IDE 历史 + chat 上下文 + checkpoint summary 至少 4 处不可控位置）
- **相关文件**：`.gitignore`（session 21 新建）、`config/llm.yaml.example:13`（已有警示但不够强）、`models/config_models.py:LLMProviderConfig.api_key_env`（字段语义来源）
- **防再犯**：
  - **AGENTS.md MUST**：所有新项目第一次提交前必须建 `.gitignore`，含 `__pycache__/` / `.venv/` / 任何含密钥的本地配置
  - 未来若加 `LLMProviderConfig` 的 Pydantic 校验：检测 `api_key_env` 值是否疑似 API key（如 `sk-` 开头 + 长度 ≥ 30），命中则 `ValueError` 提示"这是 key 不是变量名"
  - `config/llm.yaml.example` 顶部把"key 不能直写"的警示从注释升级为"如果你把 key 写在这里，先 ⚠️ 立即作废再继续"

### [P1] 2026-04-24 Runtime 用 `RuntimeError` 表示业务级错误，未来 CLI 难以精确捕获

- **现象**（原始）：`core/runtime.py` 有 3 处 `raise RuntimeError(...)` + 2 处 `raise ValueError(...)` 混合表达"暂停 / 终止 / 状态不一致"等业务语义；上层 `except RuntimeError` 会意外吃掉真正的 bug。
- **根因**：v1 没开异常体系专项决策（D-011 候选），只有 `ProviderError` 一个自定义类。
- **状态**（session 21 末已结清）：D-011 全链路落地——
  - 基类树齐全（`core/errors.py`：`SimEngineError` + `ProviderError` / `LLMProtocolError` / `RulesError` / `InvalidStateError` / `PausedError` / `TerminatedError`）
  - `RulesLoadError` 入树（session 21 F2）
  - **Runtime 5 处全部迁完**（session 21）：`PausedError` / `TerminatedError` / 3 处 `InvalidStateError`
  - CLI `main()` 顶层 `except SimEngineError` 已就位、测试 `tests/test_errors.py` parametrize 注册全部子类
  - 真实 scope 比原估"30~50 处"小一个量级——业务代码层只有 5 处真正属于 D-011 范畴；其余 `ValueError` / `FileNotFoundError`（mock 构造参数错 / IO 错 / 用户输入错）按 Python 惯例**保留**
- **相关文件**：`core/runtime.py`（5 处 raise 已迁）、`core/errors.py`（异常树）、`core/rules_loader.py:RulesLoadError`、`tests/test_runtime.py`（4 处 pytest.raises 已同步）
- **防再犯**：CLI / 测试层永远不要用 `except RuntimeError` 兜底业务异常——用 `except SimEngineError` 或更具体的子类；新增 `SimEngineError` 子类时同步登记到 `tests/test_errors.py` 的 parametrize 列表

### [P1] 2026-04-24 `world.defaults.fallback_action` 未在 Runtime 构造时校验合法性

- **现象**：`Runtime._fallback_proposal`（`core/runtime.py:636-651`）读 `world.defaults.fallback_action`，若值是 world 未声明的 action 或 `resolve_effects` 未实现的 action，**要等到第一次 fallback 触发才炸**（`MinimalMarketRules.resolve_effects` 对未知 action 会 `raise ValueError`）。Runtime 没做启动期 sanity check——配错可能要跑到第 N tick 才显形。
- **根因**：v1 的分层纪律是"Runtime 不做业务校验"，于是假设"world_definition 的 fallback_action 字段已在 schema / loader 层保证合法"。但 schema 只保证 fallback_action 是字符串，**不**保证它是"当前 rules 模块能 resolve 的 action"——这是跨 world × rules 的约束，schema 不可能知道。
- **解法**：在 `Runtime.__init__` 末尾加一行 sanity check——构造一个 dummy ActionProposal 试跑 `rules.resolve_effects`，失败即抛错。或者更简单：要求 `fallback_action` 必须是 `do_nothing`（约定）。本次审阅决定**暂不加**，让这条作为 pitfall 候选；若真有用户配错，当场加校验。
- **相关文件**：`core/runtime.py:636-651`、`rules/minimal_market.py`（resolve_effects 对未知 action 的处理）、`schemas/world_definition.schema.json`（fallback_action 声明）
- **防再犯**：新增世界时，`defaults.fallback_action` **必须**是 rules 模块的 `resolve_effects` 已处理的 action（通常是 `do_nothing`）。AGENTS.md 可补 MUST 条款。
- **已结清**（session 22 落地 D-013）：本条 pitfall 现已被 `core/semantic_validator.py` 覆盖——`Runtime.__init__` 在 rules 装配后立刻调 `validate_semantics`，若 `world.defaults.fallback_action` 不在 `rules.actions_handled()` 内即抛 `SemanticValidationError`，**根本不会进入运行期**。两个产线场景（minimal_market / three_party_negotiation）的 rules 子类均已实现 `actions_handled` 钩子。本条作为历史样本保留——给未来 LLM 辅助建模的自我修复循环提供"语义错典型形态"参考。

### [P2] 2026-04-24 `force_action` 生效时缺独立事件，审计链路不完整

- **现象**：`Runtime.intervene(kind="force_action")` 调用瞬间写 `intervention_applied` 事件。但**实际生效是在下一次 `step()` 的 `_make_decision` 里**——此时 LLM/rule 路径被 forced_actions dict 短路，正常的 `decision_proposed` 事件仍然生成（decision_mode 字段标为 `"rule"`，`raw_reasoning_summary="intervention: force_action"`），但**没有专门的事件标明"本次决策是被强制替换的"**。UI 回溯时要看 decision_proposed 的 raw_reasoning_summary 字符串才能判断——脆弱且非结构化。
- **根因**：干预声明与干预生效是**两个 tick**，一次事件化只覆盖了声明瞬间。设计时没考虑到"生效瞬间"也该有事件。
- **解法**（暂缓）：未来可加一条 `decision_forced` EventKind，在 _make_decision 走 forced_actions 路径时写入。短期可用 `decision_proposed.payload` 加 `forced_by_intervention: bool` 字段兼容。
- **相关文件**：`core/runtime.py:487-500`（_make_decision force_actions 分支）、`core/runtime.py:432-477`（intervene）、`models/runtime_models.py:50-63`（EventKind Literal）
- **防再犯**：UI 不要只看 `decision_mode=rule` 就假定"这是常规规则决策"——需要额外看 `raw_reasoning_summary` 是否含 `"intervention"` 前缀。本条记录是 UI 对接时的提醒。

### [P3 历史样本] 2026-04-28 D-015 全量版释放实体生命周期 + 动作链能力（session 28）

- **背景**：v0.1.1 收官时 D-015 缩限版仅做了 `AttributeEffect.new_value`（结清下条 P2 第 105 行）；推迟到 v0.2.x 的"全量版"含 3 个新 Effect 类型——session 28 用户决定"先把引擎做扎实"，提前实施
- **释放能力**：
  - **`EntityCreateEffect`**——动态创建实体（公司分裂 / 谈判第三方加入 / 信息节点衍生 / 群体新成员）；含 `initial_attributes` 与 `initial_relations` 一并构造；新实体下一 tick 才激活（spec 第 150 行）
  - **`EntityDestroyEffect`**——按 `cascade=all/preserve_relations/preserve_messages` 三策略删除（公司破产 / 组织解散 / 节点失效）
  - **`ChainedActionEffect`**——规则触发动作链（连锁反应 / 责任传递 / 信息扩散 / DSL-like 复合规则）；同 tick 立即递归 + 跨 tick 延后两路；防递归走 `RuntimeConfig.max_chain_depth`（默认 3，超限抛 `RulesError`）
- **设计要点**（与 spec 一致）：
  - chained 子动作不走 LLM——rules 直接构造 `ActionProposal`（节省 token）
  - chained 子动作仍走 `validate_action`——D-014 强约束兜底，rules bug 会写 `decision_rejected` 而非崩
  - chained 链中事件的 payload 加 `source="chained_action"`——审计与 LLM 决策事件区分
  - 跨 tick 链每 tick 重置 depth=0——不计入同 tick 链上限（spec 第 91 行）
  - `EntityCreate` 重复 id / 未声明 type → `RulesError`（rules 设计错构造期就抓）
  - `EntityDestroy` 不存在 entity → warning 不抛错（与 `_apply_attribute_effect` 防御式风格一致）
- **新启用的异常类**：`core/errors.RulesError`（session 27 标"v1 未使用；保留供未来"——session 28 D-015 全量版正式启用为链深度超限异常）
- **影响面**（10 个修改 + 2 个新建）：
  - 修改：`models/runtime_models.py`（+3 Effect + 3 EventKind + Effect Union 扩充）/ `models/config_models.py`（+max_chain_depth 字段）/ `core/runtime.py`（_apply_effects 加 depth 参数 + 3 helper + _execute_chained_action + _process_delayed_chained_actions + step 主循环加步 2.5）/ `core/errors.py`（RulesError docstring 升级）/ `tests/test_runtime_models.py`（+15 模型校验）
  - 新建：`tests/test_runtime_d015.py`（14 项端到端：4 EntityCreate + 3 EntityDestroy + 2 ChainedAction immediate + 1 ChainedAction delayed + 4 防递归与 max_chain_depth 配置）
- **测试增量**：671 → 700（净 +29；0 回归；Pytest 8.22s）
- **未来工作（推迟）**：spec 第 30 行的 `BatchEffect`（事务语义）—— spec 第 152 行决议**不做**（事务由 EventLog append-only 提供天然原子性）；若未来需要更细的同 tick 内 effect 应用顺序控制，再开 D-xxx
- **相关文件**：`docs/02-design/decisions/D-015-effect系统扩充.md`（spec）、`models/runtime_models.py:367-556` (3 新 Effect)、`core/runtime.py:813-1109`（5 个新 helper）

---

### [P2] 2026-04-24 AttributeEffect 只支持 numeric delta，non-numeric 属性改不动

- **现象**：Session 11 实现 `rules/base.py` 的通用 `apply_constraints` 时发现——`AttributeEffect.delta: float` 的设计让规则公式**无法**在动作效果里改 enum / string / boolean 属性（如把 `strategy_bias` 从 `"balanced"` 改到 `"aggressive"`）。遇到这类需求，当前唯一出口是 `Intervention.override_attribute`，但那是"人工干预"路径，会写 `intervention_applied` 事件，语义上不是"动作产生的效果"。
- **根因**：D-009 路线 1 把公式表达留在代码层（每个世界写 `rules/<world>.py`），但 Effect 模型本身是跨世界共享的 schema。v1 为简化定义，把 delta 固化为 float，隐含假设"属性都是数值型"。真实世界定义里 enum/string/bool 属性合法存在（见 `models/world_models.AttributeSchema.type`），于是产生缺口。
- **解法**（当前）：
  - 在 `models/runtime_models.AttributeEffect` 的 docstring 明确标注此限制
  - walkthrough 的 minimal_market 公式**绕开**改 enum/string/bool 属性的需求；若 walkthrough 设计里确实有这类需求，走 `Intervention.override_attribute` 或暂缓
  - 未来需要解除：开 D-xxx，加 ``new_value: Any | None`` 字段 + `model_validator`（delta 与 new_value 互斥）。**不是小改**——鉴于 D-009 决定“公式在代码层”，或可等第二阶段路线 2（schema 数据化）一并处理
- **已结清**（session 24 落地 D-015 缩限版）：`AttributeEffect` 已增加 ``new_value: Any`` 字段 + `model_validator` 实施 ``delta`` XOR ``new_value`` 互斥。现在规则可用 `AttributeEffect(actor_id=..., attribute=..., new_value="aggressive")` 表达改 enum/string/bool 属性，同时 `Runtime._apply_attribute_effect` 已适配双形式路径。`BaseRules._clamp_attribute` 对 ``new_value`` 形式透传不裁剪（后续若需给数值形 new_value 加 clamp 仅需在该 helper 内追加分支）。所有现有 rules 仍用 ``delta`` 形式，完全向后兼容。
- **相关文件**：
  - `models/runtime_models.py` 的 `AttributeEffect` 类（限制说明已更新）
  - `docs/02-design/规则层设计.md` 3.2 节效果映射规则
  - `docs/00-overview/progress.md` D-009 决策条目
- **防再犯**：若遇到"改 enum 属性"类需求时，**立即查本条**；若第 4 步 walkthrough 真实需要，**当场**开 D-xxx 处理，而不是默默走 Intervention 后门。

### [P1] 2026-04-24 Scenario schema 把可选字段误列为 required，与 walkthrough 矛盾

- **现象**：`scenario.schema.json` 把 `relations / environment / scheduled_events / breakpoints` 全列为 `required`，但 `docs/01-requirements/最小示例Walkthrough.md` 描述的最小场景只有 2 实体 + 1 事件，没有关系也没有断点。严格按 schema 走，walkthrough 的最小例子无法通过校验。
- **根因**：最初写 schema 时把"文档里列过的字段"全当成"必须出现"，没有区分"语义必须" vs "文档示例里出现过"。`relations: []` 与"不写 `relations`" 在语义上等价，强制 required 只增加用户负担和 LLM 辅助建模重试成本。
- **解法**：采用"精细版 B 方案"：
  - schema `required` 只保留 `version / world_id / scenario / entities / config`
  - `relations / environment / scheduled_events / breakpoints` 改为可选
  - Pydantic 模型用 `default_factory=list/dict` 填空容器
  - 消费端对象结构与严格模式完全一致，无 `None` 风险
- **相关文件**：
  - `schemas/scenario.schema.json:6`
  - `docs/02-design/场景文件格式设计.md` 第 6.1 节
  - 未来的 `models/scenario_models.py`（实现时按此约定）
- **防再犯**：所有 schema 的 `required` 字段今后必须回答——"不写这个字段是否会导致语义不明？"如果答案是"不写就等于空/默认且语义明确"，就**不应列为 required**。已在 `docs/02-design/场景文件格式设计.md` 6.1 节固化此约定。

<!-- 示例（请勿删除本示例，它既是格式参考也是 placeholder）：

### [P1] 2026-04-24 示例：schema 和 Pydantic 模型约束漂移

- **现象**：`world_definition.schema.json` 里 `decision_interval` 的 `minimum: 1`，但 `models/world_models.py` 里写成 `ge=0`
- **根因**：手工双写两份约束，改一份忘改另一份
- **解法**：统一为 `ge=1`，并在 loader 测试中加入两份都校验
- **相关文件**：`schemas/world_definition.schema.json:141`、`models/world_models.py:74`
- **防再犯**：加入 `AGENTS.md` 4.5 条——"schema 和 Pydantic 模型的约束必须等价"
-->
