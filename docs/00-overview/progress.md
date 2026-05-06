# 开发进度

> 本文件是 **session 衔接文件**。每次新开会话的 AI 先读这里，就能在 30 秒内知道上次做到哪、下次从哪开始。
>
> 每次 session 结束前必须更新本文件。格式见文末"更新规则"。

## 一、当前位置

**阶段**：**v0.2 架构清债（F1-F10 / docstring 重写 / 3 dead alias / 4 dead i18n keys / cytoscape + recharts 共用抽离 / playwright race fix）交付**（session 43 末，2026-05-06）——`https://github.com/Kaka-cheaper/Polisim`

**进度**：第 1-6 步全通 ✅；**Phase A / B / C 三段闭环**已交付；**D-011 / D-013 / D-014 / D-015 全量版 / D-016 + LLM 增强分析升级**已落地；**改名 SimEngine → Polisim**；**810 tests passing**（本 session 仅前端，0 后端测试变动）；**v0.2 阶段：D-017 spec（session 29）+ UI mockup v1（session 30）+ Server REST（session 31）+ WebSocket（session 32）+ 架构审查 F1-F10（session 33）+ mockup 第二阶段配套（session 34）+ PR1 web/ 项目骨架（session 35）+ PR2 API 层 + 7 hooks + ErrorBoundary（session 36）+ **PR3：routes/Gallery + routes/PreRun + components/{ScenarioCard, ScenarioIntroPanel, AdvancedOptionsPanel} + i18n 4 组 keys + schema.ts 加 6 嵌套类型别名**（session 37）**

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
> **session 26 已交付**：LLM 增强分析升级（world_overview 段 + 证据援引 + 章节重排）+ CLI `--output-language` / `--prompt-history-size` 参数。详见第 55 条目。
>
> **session 27 已交付**：架构审查 + 保健清债——F1-F11 全量修复（2 P1 / 3 P2 / 5 P3 / 1 latent gap），含 smoke_openai.py 修复 D-016 + session 26 双破坏性 API 变更下游遗漏（F1+F2+F10）+ pyproject 0.1.1 + README v0.1.1 收官内容。详见第 56 条目。**671 passed / 0 回归 / 净 +1 测试**。
>
> **session 28 已交付**：D-015 全量版实施——EntityCreate / EntityDestroy / ChainedAction 三类新 Effect + max_chain_depth 防递归 + RulesError 启用为链深度超限异常。详见第 57 条目。**700 passed / +29 净新 / 0 回归**。
>
> **session 29 已交付**：v0.2 启动——D-017 v0.2 API 契约与 Server 架构 spec 完整起草（约 730 行 11 节）+ AGENTS.md / 实现映射设计.md / 需求分析.md 三份既有设计文档同步反映 v0.2 阶段。详见第 58 条目。**Spec 阶段 0 代码改动 0 测试改动**。
>
> **session 30 已交付**：v0.2 前端 UI mockup 起草——`docs/02-design/v0.2-前端-UI-mockup.md`（约 1120 行 9 节）+ 8 项核心决策（用户对话产物）+ 5 用户故事 + 11 区块详细设计（场景画廊 / 跑前 / 跑中三种 layout / 跑中共用控件 / 跑完）+ 三段式 Layout / 中英切换 / 5 步典型用户流程 / 8 段技术约定 / 10 项未决问题。**反向校验产物**：补 D-017 第 3.5 节 `Scenario.ui_layout` 字段（Literal 三选一）+ 联动改动清单。详见第 59 条目。**Spec 阶段 0 代码改动 0 测试改动**。
>
> **session 31 已交付**：v0.2 server 骨架实施——`server/` 完整骨架（8 个路径 18 个文件：app.py / runtime_registry.py / api/deps.py / api/v1/{errors,schemas,middlewares/auth} / api/v1/routes/{runs,interventions,analysis,meta} / services/{run,intervention,analysis}_service）+ 16 业务 endpoint + 3 服务层 + ERROR_MAP（10 异常 → HTTP 状态码）+ Runtime registry（并发上限、生命周期、状态查询）+ `cli/serve.py` 与 cli/run.py 集成。**D-017 反向校验产物同 session 携带落地**：schemas/scenario.schema.json + models/scenario_models.py + 2 scenario.yaml 加 `ui_layout` 字段。**6 测试文件 99 项新增**：test_server_errors / registry / meta / runs / interventions / analysis。详见第 60 条目。**799 passed / +99 净新 / 0 回归**。
>
> **session 32 已交付**：WebSocket 实时推送实施——新建 4 文件：`server/api/v1/ws_events.py`（6 个 typed 事件）+ `server/services/stream_service.py`（StreamService 订阅广播、线程安全、反压丢弃）+ `server/api/v1/routes/ws.py`（WS 路由、关闭码 1000/4004/4500）+ `tests/test_server_ws.py`（10 项）。**RunService.step / pause 增加推送逻辑**：step 后推 tick_advanced；auto-pause/breakpoint 推 paused；reached_total_ticks 跑 Phase A 分析 + 推 run_finished + close。`server/app.py` lifespan 集成 StreamService.attach_loop。**v1 内核完全不动**——纯 server 层组合。详见第 61 条目。**809 passed / +10 净新 / 0 回归**。
>
> **session 33 已交付**：server 全面架构审查 + 保健清债——发现 10 项问题 F1-F10（8 修复 + 2 pitfalls 记录）。全路径详见第 62 条目。交付亮点：取消 3 处 `runtime._private` 访问——为 Runtime 加 `runtime_config` / `provider` 两个只读 @property；StreamService.broadcast 加顶层 try/except 防序列化失败阻断 step；清理 dead import 与 不必要 type:ignore；D-017 spec ScenarioSummary 补 world_id 字段；ws_events 三个事件 docstring 标注 v0.2 未触发；补 breakpoint 触发 paused 事件测试 + 2 项 P2 pitfalls（in-memory run finished + lifespan 不优雅 ws shutdown）。**810 passed / +1 净新 / 0 回归**。
>
> **session 34 已交付**：v0.2 前端 mockup 第二阶段配套——三件套：(A) `design-system/tokens.css` 基于 linear.app 抽取的 design tokens（316 行三层结构：24 primitives + 30+ semantic + 9 个 polisim-* 业务专属 + 8 类基础 token）；(B1) mockup §10 「第二轮 API 反向校验」——对照 session 31-33 实施的 server，识别 2 🔴 + 5 🟡 + 5 🟢 + 23 ✅ 共 35 项偏差；(B3) mockup §11 「React 组件清单 + props API」——4 routes + 3 layouts + 12 共用 + 12 基础 + 11 hooks + 1 store + 数据流图 + 5 PR 实施顺序；(B2) §8.4 颜色主题节重写为 token 引用 + §4.3.2 关系图 token 化。**810 passed / 0 代码变动 / 0 测试变动**（纯文档 + design-system 产出）。详见第 63 条目。
>
> **session 35 已交付**：v0.2 React 前端 PR1 实施——按 mockup §11.11 PR1 清单 1:1 落地：`web/` 项目骨架（Vite 8 + React 19 + TS + 16 工程文件）+ Tailwind v3（PostCSS + tailwind.config.ts 桥接 tokens.css 全部 semantic 层 + Polisim 业务专属 token）+ design-system/tokens.css 拷贝至 web/src/styles/tokens.css 并经 index.css `@import` 引入 + react-router-dom v6 4 个空 route（Gallery / PreRun / Running / Finished，路径符合 D-017）+ react-i18next 初始化（zh.json / en.json 骨架）+ zustand uiStore（speed / sidePanelCollapsed / locale 持久化 + prevSnapshotByRunId 非持久化）+ TopBar 中英切换按钮 + package.json `gen:types` 脚本（openapi-typescript）。**Vite dev server 5173 验收通过**：所有路由 200 / SPA fallback 工作 / Tailwind transform 后 33899 bytes 含全部 semantic token utility（`.bg-canvas{--bg-canvas}` / `.text-fg-primary{--text-primary}` / `.max-w-layout{--layout-max-width}` 等）/ tokens.css 应用至 body computed style（深色画布 #08090a）。**0 v1 内核改动 / 0 server 改动 / 810 后端测试不变**——纯前端骨架。详见第 64 条目。
>
> **session 36 已交付**：v0.2 React 前端 PR2 实施——按 mockup §11.11 PR2 清单 1:1 落地：装包 axios + @tanstack/react-query + sonner（6包 + 23 deps）+ 启 server（8000）跑 `npm run gen:types` 生成 `src/api/types.gen.ts`（2493 行 / 77 KB / 100+ schema）+ 写 `src/api/{schema.ts, client.ts, ws.ts}` + 7 hooks（`useScenarios` / `useRun` / `useCreateRun` / `useStep` / `usePause` / `useResume` / `useRunStream` 核心 WS 状态机）+ `components/ErrorBoundary.tsx`（mockup §9.8 决策 C）+ `main.tsx` 集成 QueryClientProvider + Toaster + ErrorBoundary + i18n key 补充 error.boundary / error.toast。**发现以及修正两项**：(a) mockup §8.3 默认 `gen:types` URL 为 `/openapi.json`，但 server `app.py:openapi_url` 实际是 `/api/v1/openapi.json` → 修脚本 URL（P3 pitfall）；(b) `useRunStream.onTick` 原接受 `tick.snapshot.tick` 但 schema 表明 `snapshot` 是 nullable（snapshot_mode=final_only/never 时 server 推 null）→ 改用 `tick.tick` + 空安全累加。**验收**：`tsc --noEmit` 0 错 / Vite re-optimize 含 axios 等新 deps / dev server 5173 ready 1172ms / SPA fallback / 0 控制台错。**0 v1 / 0 server / 0 后端测试变动**。详见第 65 条目。
>
> **session 37 已交付**：v0.2 React 前端 PR3 实施——按 mockup §11.11 PR3 清单 1:1 落地：重写 `routes/Gallery.tsx`（useScenarios + ScenarioCard 列表 + 2 upcoming + 1 custom 占位 + loading skeleton + error banner）+ 重写 `routes/PreRun.tsx`（useRun + ScenarioIntroPanel + AdvancedOptionsPanel + [▶ 开始仿真] + [← 返回画廊]）+ 新建 3 业务组件：`ScenarioCard`（三种 kind discriminated union: production/upcoming/custom + ui_layout 图标提示 🎴/🕸️/📜）/ `ScenarioIntroPanel`（场景描述 + 实体列表含 decision_mode 标签 + scheduled_events 摘要）/ `AdvancedOptionsPanel`（折叠式 + ticks_override + llm_provider，PR3 disabled 占位）+ schema.ts 加 6 个嵌套类型别名（WorldDefinition / EntityTypeSchema / Scenario / ScenarioInfo / EntityInstance / ScheduledEvent）+ i18n 加 4 组 keys（gallery / scenario_card / pre_run / advanced_options）。**修正 1 项**：openapi-typescript v7 把 Pydantic v2 default 字段（`CreateRunRequest.llm_provider`）仍列为 TS required → Gallery 调用方显式传 `llm_provider: "mock"`（P3 pitfall）。**验收**：`tsc --noEmit` 0 错 / Vite ready 389ms / GET / + GET /runs/test_run/intro 返 200 / GET /api/v1/scenarios 返 697 bytes 2 个生产场景。**0 v1 / 0 server / 0 后端测试变动**——mockup §6 用户流程第 1-2 步走通。详见第 66 条目。
>
> **session 38 已交付**：v0.2 React 前端 PR4.1 实施（跑中页最小可演示路径，按用户选定的 PR4 拆分粒度）——按 mockup §11.11 PR4 清单 1:1 落地 5 主文件：重写 `routes/Running.tsx`（useRun cache hit + useRunStream ws 订阅 + auto-step loop 按 speed 控 1000/speed ms 调 useStep.mutateAsync + finished 自动 navigate /finished + PausedEvent reason toast + Layout dispatch by ui_layout：entity_card 走 EntityCardLayout，relation_graph / event_stream 占位 PR4.5 提示 + [🚪 退出] fire-and-forget DELETE /runs/:id + navigate /）+ 新建 `components/ControlBar.tsx`（mockup §4.4.1：tick 计数 + 8 状态 badge + 暂停/恢复切换 + 单步（仅 paused 启用）+ 4 档速度选择对接 zustand uiStore.speed + 副区按钮 PR5 占位 + 退出按钮）+ 新建 `layouts/EntityCardLayout.tsx`（mockup §4.3.1：grid 1col/tablet 2col/desktop 3col + entries 数组 + environment 底部行）+ 新建 `components/EntityCard.tsx`（emoji 头部按 type 关键词匹配 + decision_mode 标签 + 属性列表 + diff 箭头按数值 prev vs current 计算 + LLMThoughtBubble（LLM 模式专属）+ rule/random 单行简化提示 + 刚执行动作显示 action(params) + [📌 干预] 占位按钮 PR4.2）+ 新建 `components/LLMThoughtBubble.tsx`（reason + [📋 看完整 prompt] disabled 占位）+ i18n 加 5 组 keys（running / control_bar 含 8 状态 + 4 paused_reason / entity_card / llm_thought / rule_thought）。**关键设计**：(a) auto-step loop 用 while + cancelled flag + setTimeout，stepMutAsync deps 稳定避免 effect 抖动，cleanup 清 cancelled；(b) PausedPayload reason toast 用 i18next 插值 ids；(c) attribute emoji + entity emoji 按关键词匹配（cash/reputation/trust/strict/regul/compan/negotiat），v0.3+ 可改 EntityTypeSchema.icon 字段驱动；(d) decision_mode 三档（llm/rule/random）UI 风格区分：llm 渲染气泡，rule/random 单行提示。**验收**：`tsc --noEmit` 0 错 / Vite ready 630ms（5173 假性占用 → 自动跑 5174）/ GET /api/v1/health + /api/v1/scenarios + 5174 / + 5174 /runs/test/run 全 200。**0 v1 / 0 server / 0 后端测试变动**——纯前端增量，mockup §6 第 3 步走通（点画廊→跑前→开始仿真→实体卡片自动 tick 推进 + LLM 气泡 + diff 箭头）。详见第 67 条目。
>
> **session 41 已交付**：v0.2 Playwright E2E 自动化测试 + 修复 PR4.3 latent bug——按 user 选定 "Playwright E2E（推荐）" 粒度落地 mockup §6 全 8 步用户故事 1:1 测试：装 `@playwright/test` + `chromium` + `@types/node` + `react-is`（4 包；前 3 个 dev，最后一个 prod，全用 `--legacy-peer-deps`）+ 新建 `playwright.config.ts`（baseURL 5173 / 单 worker / 失败截图+录像+trace / chromium 1440x900 viewport）+ 新建 `tests/e2e/mockup-flow.spec.ts`（170 行，8 个 test.step：画廊→跑前→跑中→0.5x 速度→干预 force_action→prompt modal→副区折叠→退出）+ 改 `web/.gitignore` 加 test-results / playwright-report / tests/screenshots 三段。**关键修复 1 P3 bug**：PR4.3 装 recharts 用 `--legacy-peer-deps` 漏装 react-is 传递依赖 → vite 抛 `[plugin:vite:import-analysis] Failed to resolve import "react-is"` → 跑中页 React app 完全不渲染（**PR4.3 提交时 tsc + 路由 200 验收没暴露此 bug**，因为 vite 仅在浏览器实际 import 时才解析 recharts 内部依赖）。补装 react-is + 重启 vite 触发 deps re-optimize 修复。**测试结果**：**1 passed (11.1s) / 9 截图全生成 / mockup §6 全流程走通**（含 LLM prompt modal——证实 minimal_market 场景含 LLM 决策实体）。**踩坑 P3 已记 pitfalls.md**：(a) 写 spec 凭印象假设 5 处全错（H1 文案 Polisim → 场景画廊 / scenario id minimal_market → walkthrough-min / entity 文案 id → name / 实体集 + company_b → regulator_main / 路由 /scenarios/:id/pre-run → /runs/:runId/intro）；(b) recharts 漏装 react-is。**0 后端测试变动 / 810 passed 不变**——纯前端 + E2E 测试增量。详见第 70 条目。
>
> **session 40 已交付**：v0.2 React 前端 PR4.3 实施（MiniDashboard 副区）——按 mockup §11.11 PR4.3 子集 + §4.4.2 数据副区 1:1 落地：装 recharts（38 包，`--legacy-peer-deps` 跳 openapi-typescript@7 peer dep 冲突，已知 P3 pitfall）+ 新建 `components/MiniDashboard.tsx`（属性折线 LineChart × N numeric attrs + 事件分布 BarChart by EventKind + responsive container + 5 色 palette + 3 兜底文案：snapshots<2 / 无 numeric attrs / 0 events）+ 改 `components/ControlBar.tsx`（[📊] 按钮从 disabled 占位 → enable + sidePanelCollapsed prop + onSidePanelToggle prop + active 视觉 toggle + dynamic title show/hide）+ 改 `routes/Running.tsx`（zustand 加 sidePanelCollapsed/toggleSidePanel selector + ControlBar 传两新 prop + main 双区 grid 布局：xl breakpoint 启动 1fr/22rem，下 size 自动单列 + MiniDashboard 仅 entity_card layout + 未折叠时渲染）+ i18n 加 1 组 mini_dashboard.* keys + 改 control_bar.side_panel_pr5 → side_panel_show / side_panel_hide。**关键修复 1 项**：MiniDashboard 初版用 `snap.entities[]` 数组遍历是错的，Snapshot 实际 schema 是 `entity_state_summary: { [entityId]: { [attr]: unknown } }` 字典 → 改 `Object.entries(snap.entity_state_summary ?? {})` 两处（collectNumericAttributes / buildAttributeSeries）。**验收**：tsc --noEmit 0 错 / vite 5173 重启（recharts 装包后 deps re-optimize）/ GET 8000/api/v1/{health,scenarios} 200 / GET 5173/src/components/{MiniDashboard,ControlBar,Running} 全 200（vite transform OK）。**0 v1 / 0 server / 0 后端测试变动**——纯前端增量 + 1 dev dep。详见第 69 条目。
>
> **session 39 已交付**：v0.2 React 前端 PR4.2 实施（干预面板 + Prompt 上下文 modal）——按 mockup §11.11 PR4 子集 + §10.6 M4 流程 + D-016 §2.1 PromptContext 6 段 1:1 落地：新建 `hooks/useIntervene.ts`（POST /runs/:id/intervene react-query mutation + onError toast）+ 新建 `components/InterventionDrawer.tsx`（侧抽屉，3 tab discriminated union 对齐 Intervention.kind：force_action / inject_message / override_attribute；通用 tick / reason 字段；Esc 取消；params/payload/attribute_changes 用 JSON textarea + parse + 校验；4 项校验消息）+ 新建 `components/PromptContextModal.tsx`（modal 6 段 collapsible：system_role / actor_view / perception / available_actions / language_hint / custom_segments；JSON pretty-print；Esc / 点击外部关闭）+ 改 `components/EntityCard.tsx`（接通 onIntervene 按钮 + 解析 latestDecision.payload.prompt_context + LLMThoughtBubble 条件性传 onClickViewPrompt + 持有 PromptContextModal local state）+ 改 `routes/Running.tsx`（新增 useIntervene hook + 3 字段 drawer state（open/entityId/wasPaused）+ handleEntityClick 自动暂停-打开 + handleDrawerSubmit 提交-条件 resume-关闭 + handleDrawerCancel 条件 resume-关闭 + 渲染 InterventionDrawer page-level singleton + 传 onEntityClick 给 EntityCardLayout）+ i18n 加 2 组 keys（intervention 含 3 tab + 全字段 + 校验消息 + success / prompt_modal 含 6 段标题 + 关闭提示）。**关键设计**：(a) wasPaused 记录用户原始状态——已暂停状态下提交不自动 resume（保持用户意图）；(b) drawer 是 page-level singleton 由 Running 持有（避免多实例 state 冲突）；PromptContextModal 由 EntityCard local 持有（per-entity 入口）；(c) 提交失败保持 drawer 打开让用户修改后重试（useIntervene.onError 已 toast）；(d) JSON parse helper 用 discriminated union { ok: true; value } | { ok: false; error } 而非 throw。**修复 1 项**：PromptContextModal 用 `JSX.Element` 类型在 React 19 + TS 5 下不再可用 → 改用 `ReactElement`（非阻塞 lint，tsc 0 错）。**验收**：`tsc --noEmit` 0 错 / Vite HMR 自动重载 Running.tsx + index.css / GET /api/v1/health 200 / GET 5174/ + /runs/test/run 全 200 / 3 个新文件 vite transform 全 200。**0 v1 / 0 server / 0 后端测试变动**——纯前端增量，mockup §6 第 4-5 步走通（点 [📌 干预] → 自动暂停 + drawer 打开 → 选 force_action 填动作 → 提交 → 自动恢复 + 下 tick 看效果；点 LLMThoughtBubble [📋 看完整 prompt] → modal 6 段 PromptContext）。详见第 68 条目。

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
56. **架构审查 + 保健清债 F1-F11 全量修复**（session 27，2026-04-28）：
    - **触发**：用户在 v0.1.1 收官 + LLM 增强升级（session 26）后发起一次"全面架构审查 + 保健"，与 session 21 同等级别；通读全部 8000+ 行代码 + 测试索引 + 文档后整理观察清单
    - **观察清单总览**：**2 P1 / 3 P2 / 5 P3 / 1 latent gap** 共 11 项，关键发现是 `scripts/smoke_openai.py` **同时积累两次破坏性 API 变更下游遗漏**——`progress.md` 第 253 行 "session 27+ 入口任务：用户重跑 OpenAI smoke 验收"承诺 smoke 可跑、但实际**两段 smoke 一跑就碎**
    - **用户决策**：选 **全量 F1-F11**——session 27 入口任务的"硬基础"补好 + 同等于 session 21 的彻底清账
    - **F1（P1，session 25 D-016 第 6 步未同步）**：`scripts/smoke_openai.py` _phase_b_smoke 调用 `llm_policy.decide()` 后访问 `.action_type / .params / .raw_reasoning_summary`——但 D-016 把返回类型升为 `LLMDecisionResult`（封装 `proposal + prompt_context`）→ AttributeError 立崩。修：`result = decide(...); proposal = result.proposal`
    - **F2（P1，session 26 升级未同步）**：`scripts/smoke_openai.py` _phase_c_smoke 调 `enhance_with_llm()` 缺必填 kwargs `world / scenario`（session 26 加 world_overview 段时把签名升为 5 参数）→ TypeError 立崩。修：补 `world=world, scenario=scenario` kwargs
    - **F10（P3 升级，与 F2 同 session 携带）**：原版用空骨架 `AnalysisResult` 让 LLM "没数据可说"——升级为**真跑 minimal_market 3 ticks → analyze_run → enhance_with_llm**，让 LLM 看到真实 turning_points / entity_comparisons / environment_trajectory 后再 enhance；4 段叙事终于有具体证据可援引
    - **F3（P2 文档漂移）**：`models/analysis_models.py` 顶层与 `AnalysisResult.__doc__` 把 Phase C 字段数描述为"三个"（实际四个，session 26 加 world_overview 后未同步）；前 Phase A 字段写"前五个"（实际六个）。两处文档同步修正
    - **F4（P2 死代码）**：`core/errors.py:RulesError` 自定义但**全仓库未被任何 raise / except 实际使用**——只 `tests/test_errors.py` parametrize 注册保它存活；docstring 仍写"v1 占位；尚未替换现有 RuntimeError"但 rules 层根本不抛 RuntimeError。改 docstring 为"v1 未使用；保留供未来扩展点"——保留类不删（避免破坏 tests 注册）
    - **F5（P2 文档漂移）**：`core/errors.py` 顶层 docstring 说"渐进迁移... 不做全量"——session 21 已完成 Runtime 5 处全量迁移，docstring 同步更新；连带异常树注释里 InvalidStateError / PausedError / TerminatedError 三个的"v1 占位"标记同步更新为"session 21 落地"
    - **F6（P3 一致性）**：`core/runtime.py:_is_numeric` 与 `core/analysis.py:_is_numeric` 双份实现——`runtime` docstring 说"集中处理此陷阱供 Runtime 多处统一复用"但 `analysis` 又重复一份。两份 docstring 互相 cross-reference 加 note 段说明：双存来自分层纪律（`analysis` 不能 `from core.runtime import`），AGENTS.md 4.3 也不允许 `utils/` 共享层；修改任一份请同步另一份
    - **F7（P3 cosmetic）**：`runtime.step()` docstring 列 12 步骤但代码内 comment 用 11 编号——校准 docstring 改为"步 0-11"与 comment 一一对应
    - **F8（P3 类型安全）**：`core/llm_policy.py` 三处 `rules: Any | None` 注释"避免循环导入"但实际无真实循环——改用 `TYPE_CHECKING + 守护 import + 字符串前向引用` 提升 IDE / mypy 类型安全；`core/runtime.py:_random_param_value(schema: Any)` 改为 `schema: ActionParamSchema`（runtime.py 已从 world_models 导入）
    - **F9（P3 版本同步）**：`pyproject.toml` version 0.1.0-dev → **0.1.1**（v0.1.1 收官后 bump）+ description 加"引擎严谨化 + LLM 增强分析"；`README.md` Roadmap 段重写——v0.1.1 收官状态 + v0.2 前端为下一阶段优先；CLI 段加 `--prompt-history-size` 演示 + Phase C 段补 4 段说明（含 world_overview）
    - **F11（latent gap）**：`core/semantic_validator.py:_check_fallback_action` 在 `world.defaults.fallback_action=None` 时**静默跳过**校验——但 `Runtime._fallback_proposal` 实际用字面 `"do_nothing"` 兜底；rules 不处理 do_nothing 时构造期放行、运行期 fallback 一触发崩。改：计算 `effective_fallback`（与 Runtime 同语义——None 时取 `"do_nothing"`），然后检查 `effective_fallback ∈ handled`。两个产线 rules 均处理 do_nothing，无现存影响；保护**未来用户上传新场景**
    - **测试影响**：F11 改造 `tests/test_semantic_validator.py` —— 重写 `test_fallback_unset_skips_check` 为 `test_fallback_unset_falls_back_to_do_nothing_check`（新行为：要求 do_nothing 在 handled）+ 加 `test_fallback_unset_with_do_nothing_handled_passes` 验证正路径。**净 +1 测试**
    - **影响面文件**（10 个修改 + 0 新建）：
      - 修改：`scripts/smoke_openai.py` / `models/analysis_models.py` / `core/errors.py` / `core/runtime.py` / `core/analysis.py` / `core/llm_policy.py` / `core/semantic_validator.py` / `pyproject.toml` / `README.md` / `tests/test_semantic_validator.py`
    - 全部测试：**671 passed**（670 → 671；+1 净新测试 from F11；0 回归；Pytest 9.12s）

**验收证据**（对应 `验收标准.md` 第 18 节自检：内审与债清）：

```text
验收对象：架构审查 + 保健（F1-F11 全量清债）
对应验收项：内部健康度——session 25/26 双破坏性 API 变更下游遗漏修复 / 文档与代码漂移消解 / D-013 fallback gap 封堵 / 类型安全提升
输入：
  - 10 文件修改：smoke_openai.py / analysis_models.py / errors.py / runtime.py /
    analysis.py / llm_policy.py / semantic_validator.py / pyproject.toml /
    README.md / tests/test_semantic_validator.py
  - 0 新建文件（严守 AGENTS.md "不创建自娱自乐 .md"）
  - 1 测试改造（rename + 加正路径）+ 1 测试新增 = +1 净测试
执行方式：
  python -m pytest tests/ --tb=short -q
实际输出：
  671 passed in 9.12s（670 → 671；+1 净新；0 回归）
是否通过：通过
备注：
  - F1+F2+F10 是核心修复——session 27+ 入口任务"OpenAI smoke 用户验收"现在能真正跑起来
  - F11 是 latent gap 封堵——为 v0.2 前端用户上传新场景做防御
  - F4 RulesError 死代码处理为"保留类 + 改 docstring"，避免破坏 tests/test_errors.py 注册
  - README lint warnings (MD060/MD032) 是原有结构问题，不属本次范畴
  - smoke_openai.py 不进 CI——本次改后需用户重跑验收（与 session 27+ 入口任务一致）
```

57. **D-015 全量版实施——实体生命周期 + 动作链能力释放**（session 28，2026-04-28）：
    - **触发**：session 27 入口任务 OpenAI smoke 验收成功（用户跑通 4 段 LLM 叙事）→ 用户决策"先把引擎做扎实，开始 D-015"。Cascade 解释 D-015 全量版释放的能力（EntityCreate / EntityDestroy / ChainedAction）+ 工量评估（5-7 天 / 2-3 session）后用户拍板
    - **spec 全实施**（按 `docs/02-design/decisions/D-015-effect系统扩充.md` 第二节）：
      1. **`models/runtime_models.py`** 加 3 个新 Effect 类（`EntityCreateEffect` / `EntityDestroyEffect` / `ChainedActionEffect`）+ 3 个新 EventKind（`entity_created` / `entity_destroyed` / `chained_action_triggered`）+ Effect Union 别名扩充至 7 类
      2. **`models/config_models.RuntimeConfig`** 加 `max_chain_depth: int = 3`（ge=1, le=20）—— 防 chained 链无限递归
      3. **`core/runtime.py`**：
         - `_apply_effects(effects, tick, depth=0)` 改造——加 depth 参数，dispatch 三类新 effect
         - 新建 5 个 helper：`_apply_entity_create_effect` / `_apply_entity_destroy_effect` / `_apply_chained_action_effect` / `_execute_chained_action` / `_process_delayed_chained_actions`
         - `step()` 主循环加步 2.5（fire 跨 tick 延后链）
         - `__init__` 加 `_delayed_chained_actions: list[tuple[int, ChainedActionEffect]]` 队列容器
      4. **`core/errors.RulesError`** 启用为链深度超限异常（session 27 标"v1 未使用；保留供未来"——session 28 D-015 全量版正式启用，docstring 大幅扩展）
    - **关键设计决策**（与 spec 第六节未决问题逐条对齐）：
      - **chained 子动作不走 LLM**——`_execute_chained_action` 直接构造 `ActionProposal(decision_mode="rule", raw_reasoning_summary=f"chained_action depth={N+1}")`，绕过 `_decide_via_llm`
      - **chained 仍走 validate_action**——D-014 强约束兜底；rules bug 时写 `decision_rejected` 事件不崩
      - **chained 不走 conflict_resolution**——chained 是规则主动设计的连锁，rules 应自己保证不冲突
      - **EntityCreate 新实体下一 tick 才激活**——避免同 tick 内的顺序敏感 bug；本 tick `active_ids` 已在 `_apply_effects` 之前定（spec 第 150 行）
      - **EntityDestroy cascade 三策略**：`all`（含 outbox + forced_actions + ctx 全清）/ `preserve_relations` / `preserve_messages`
      - **跨 tick 链每 tick 重置 depth=0**——不计入同 tick 链上限（spec 第 91 行）
      - **EntityCreate 重复 id / 未声明 type → RulesError**（构造期就抓，不等运行期崩）
      - **EntityDestroy 不存在 entity → warning 不抛错**（与 `_apply_attribute_effect` 防御式风格一致）
    - **测试增量：+29 项**（671 → 700 passed，0 回归；Pytest 8.22s）：
      - `tests/test_runtime_models.py` +15（D-015 模型校验：EntityCreate 5 + EntityDestroy 5 + ChainedAction 5，覆盖最小构造 / 完整字段 / extra='forbid' / Literal 边界 / min_length / ge）
      - `tests/test_runtime_d015.py` +14 端到端（**新建文件**）：
        - **EntityCreate 4 项**：创建 + 关系建立 / 下一 tick 激活 / 重复 id 抛 RulesError / 未声明 type 抛 RulesError
        - **EntityDestroy 3 项**：cascade=all 清理 / preserve_relations 保留 / 不存在 entity warning 不崩
        - **ChainedAction immediate 2 项**：report → manager.acknowledge 同 tick 链 / chained_action_triggered 事件 depth=1
        - **ChainedAction delayed 1 项**：delay_ticks=2 在 tick=3 fire（manager.approvals tick 1/2 不变 / tick 3 +1）
        - **防递归 4 项**：recursive_chain 默认 max=3 抛 RulesError / max=1 配合 recursive 在 depth=1 抛 / 单层链不抛 / **跨 tick 链不计入深度上限**（max=1 + delay 也通过）
    - **影响面文件**（10 个修改 + 2 个新建）：
      - 修改：`models/runtime_models.py` / `models/config_models.py` / `core/runtime.py` / `core/errors.py` / `tests/test_runtime_models.py`（细节见 pitfalls.md 顶条）
      - 新建：`tests/test_runtime_d015.py`（460 行，14 项）+ `tests/test_runtime_d015.py` 的内嵌 `_D015TestRules` 测试 rules 子类（按 action_type 产出 D-015 各类 effect）+ 程序化构造的 D-015 测试 world（Worker / Manager 实体类型 + 9 演示动作 + reports_to 关系 + 默认 fallback do_nothing）
    - **未来可选**（本次未做，spec 第 30 / 152 行）：
      - `BatchEffect`（事务语义）——spec 决议**不做**：事务由 EventLog append-only 提供天然原子性
      - 数值形 `new_value` 的 clamp——`BaseRules._clamp_attribute` 当前透传不裁剪；需要时在该 helper 内追加分支即可
    - **session 29+ 入口任务**：v0.1.1 全部 + 架构审查 + D-015 全量版 = 引擎严谨化彻底完成。下一阶段五选项（v0.2 前端 / B.3 重试 / walkthrough 扩章 / 新场景 / 第二阶段 LLM 辅助建模 PoC）由用户指派

**验收证据**（对应 `验收标准.md` 第 18 节自检：D-015 全量版实施）：

```text
验收对象：D-015 全量版（EntityCreate / EntityDestroy / ChainedAction 三类新 Effect + max_chain_depth 防递归）
对应验收项：spec 第二节定义 + 第五节测试设计（最小测试列表全覆盖）
输入：
  - 5 文件修改：models/runtime_models.py / models/config_models.py /
    core/runtime.py / core/errors.py / tests/test_runtime_models.py
  - 1 文件新建：tests/test_runtime_d015.py（14 端到端测试）
执行方式：
  python -m pytest tests/ --tb=short -q
实际输出：
  700 passed in 8.22s（671 → 700；+29 净新；0 回归）
是否通过：通过
备注：
  - spec 第五节"最小测试列表"6 项全覆盖：
    1. AttributeEffect.new_value 与 delta 互斥 + 类型兼容（D-015 缩限版已覆盖；保留）
    2. EntityCreateEffect 创建后属性按 schema 走默认值 + clamp（默认值 ✅；clamp 透传未做但 spec 标注"留 v0.2.x"）
    3. EntityDestroyEffect 级联删除关系 / 邮箱 / inbox（cascade=all 测试覆盖）
    4. ChainedActionEffect 单 tick 内链深度 ≤ max_chain_depth（recursive_chain 测试覆盖）
    5. ChainedActionEffect 跨 tick（delay_ticks > 0）正确进入 scheduled_events 队列（delayed 测试覆盖；用专门的 _delayed_chained_actions 队列而非 scheduled_events——更精准的语义）
    6. 防无限递归：A → B → A 触发时立即抛 RulesError（recursive_chain 测试覆盖）
  - 用户对话明确"先把引擎做扎实"——D-015 全量版完成后引擎严谨化彻底收尾
```

58. **D-017 v0.2 API 契约与 Server 架构 spec 起草**（session 29，2026-04-28）：
    - **触发**：session 28 D-015 全量版完成后，用户问"前端开发顺序"（先 UI 还是先 API）。Cascade 初次回答倾向"复用 models/ 不抽 api 模块"——用户**反驳**"v0.1 → v0.2 是关键迭代节点，必须考虑后续扩展和维护"。Cascade 承认偏激 + 修正立场——抽 server/api/ 工程化模块（routes / services / registry / errors / ws_events）但**不**抽 schema 翻译层；用户拍板 + 要求"判断 v0.1 → v0.2 过渡是否需要写进相关设计文档"
    - **核心决策**（D-017 spec 第二节）：
      - **三层抽象**：routes（HTTP 协议）/ services（业务逻辑，可被 CLI / mobile / 第三方复用）/ registry（多并发 Runtime 内存生命周期）
      - **数据 schema 复用**：response_model 直接用 `models/*` Pydantic 模型——不新建 `server/api/schemas.py` 翻译层（避免 session 27 F3 漂移教训重演）
      - **API 版本化**：所有 endpoint `/api/v1/` 前缀；v0.3 加 v2 不冲突
      - **错误标准化**：`SimEngineError` 子类→HTTP 状态码完整映射表 + 统一 `ErrorResponse` 格式
      - **平台专有 schema 落点**：CreateRunRequest / RunSummary / ErrorResponse / WSEvent 等新模型在 `server/api/v1/`，**不侵入** `models/`
      - **WebSocket typed**：每种事件类型独立 Pydantic 模型（TickAdvancedEvent / PausedEvent / RunFinishedEvent / ErrorEvent / Ping/Pong）；server → client 单向，控制走 REST
      - **鉴权策略**：v0.2 不鉴权（本地）/ v0.3 token / v0.4 OAuth；路由结构预留 `middlewares/auth.py` 占位
    - **D-017 spec 产物**：`docs/02-design/decisions/D-017-v0.2-API契约与Server架构.md`（约 730 行 11 节）：
      1. 决策背景（v0.1 → v0.2 迭代节点 + v1 沉淀的契约证据）
      2. 架构决策（三层抽象 + 复用纪律 + 版本化 + 错误标准 + 鉴权）
      3. REST endpoints 完整清单（约 14 个 endpoint，每个标注 response_model + service 方法 + 错误映射）
      4. WebSocket 协议（路径 / typed events / 服务端推送时机 / 关闭码）
      5. 错误处理标准（ErrorResponse schema + ERROR_MAP + 全局异常处理器）
      6. Service 层设计（RunService / InterventionService / StreamService / AnalysisService）
      7. Runtime Registry 设计（v0.2 内存版 + v0.3+ 演进路径）
      8. 影响面文件清单（13 新建 + 9 修改既有文档）
      9. 测试设计（约 45-50 项；金字塔结构）
      10. 未决问题（10 项，含倾向方案 + 决策时机）
      11. 与 v0.1 → v0.2 过渡的整体定位（5 层 → 7 层架构 + 反规模复杂度检查）
    - **设计文档同步**（session 29 携带，吸取 session 27 F3-F5 漂移教训）：
      - **`AGENTS.md`** 第一节状态描述（v0.1.1 全交付 + 架构审查 + D-015 全量版完成 + v0.2 启动）；3.3 节落点（v0.1 内核保留 + v0.2 server/web 新加 + 数据 schema 复用纪律）；3.4 节实施顺序（6 步主路径全通 + v0.2 阶段 5 步推进 7-11）；4.2 节解禁 UI；4.3 节加 D-017 反模式
      - **`docs/02-design/实现映射设计.md`** 第三节代码结构加 server/ + web/ 树形展开（约 30 行新增）；新加 4.10 节（API 服务层 D-017 落点 + 数据 schema 复用纪律 + 与 v1 内核的关系）+ 4.11 节（前端层 + 与 server 的关系 + GitHub Pages 静态 demo 分叉）
      - **`docs/01-requirements/需求分析.md`** 第 11 节"非功能要求"按 v0.1/v0.2 拆分：11.1 v0.1 已完成、11.2 v0.1 不追求（含 UI 不做但 UI-ready）、11.3 v0.2 引入两层（API + 前端）+ 4 项设计纪律、11.4 v0.2 仍不追求（分布式 / 鉴权 / 多用户 / 自动建模）
    - **未同步文档**（推迟到 v0.2 实施 session 携带）：开发流程.md / 验收标准.md / 如何使用这套文档与配置体系.md
    - **session 30+ 入口任务**：起草 v0.2 前端 UI mockup（文字 wireframe）—— 反向校验 D-017 spec 完整性（发现缺字段时回头补 spec）。之后按 D-017 第三节 5 步推进顺序实施

59. **v0.2 前端 UI mockup 起草 + D-017 反向校验**（session 30，2026-04-28）：
    - **背景**：D-017 spec 已完整起草（session 29）；进入 v0.2 5 步推进路径的第 2 步——UI mockup 起草反向校验 D-017 完整性
    - **方法论**：先用 6 个连续问答与用户对话锁定 UI 走向（不直接画 mockup），避免后期推倒重来
    - **8 项核心决策**（session 30 用户对话产物，按问答顺序）：
      1. **目标用户**：演示/教学（非技术观众）—— 非 debug 用、非研究用
      2. **核心看点**：剧情 / LLM 决策 / 系统演化 / 最终报告 4 类全要
      3. **整体 Layout**：展览馆三段式（跑前 → 跑中 → 跑完）跟随仿真生命周期
      4. **节奏**：默认自动跑 + 可暂停 + 实时干预 + 干预后恢复
      5. **干预交互**：**点击实体卡片直接操作**式（非表单式选实体）—— UX 关键修正
      6. **场景范围**：画廊页 + 2 现有 + 2-3 即将到来 + LLM 自动生成入口（v0.3+ 占位）
      7. **跑中 Layout 风格**：混合——`scenario.ui_layout` 字段三选一（entity_card / relation_graph / event_stream）
      8. **覆盖范围**：桌面 1280+ + 平板 1024+ + 中英切换；手机推迟 v0.3
    - **mockup 文档产物**：`docs/02-design/v0.2-前端-UI-mockup.md`（约 1120 行 9 节）：
      1. 决策来源（8 项决策表）
      2. 5 个核心用户故事（按演示/教学定位）
      3. UI 区块全清单（11 区块 × 出现阶段 × 数据源）
      4. 各区块详细设计——4.1 场景画廊 / 4.2 跑前 / 4.3 跑中三种 layout（实体卡片 + 关系图 + 事件流，每种含完整 ASCII + 数据 + 交互 + 状态）/ 4.4 共用控件（控制条 + mini dashboard + 干预面板含两层选项 + LLM 决策 modal）/ 4.5 跑完阶段（4 段 LLM 报告 + tabs）
      5. 总体 Layout（桌面 / 平板 / 中英切换）
      6. 典型用户流程（5 步走通 minimal_market）
      7. **D-017 反向校验**（10 项发现 → 1 必加 + 1 可选 + 5 客户端处理 + 3 已覆盖）
      8. 技术约定（13 项 React 技术栈 + 目录结构 + OpenAPI 自动 type 生成 + 颜色主题 + 与 v0.1 内核边界）
      9. 未决问题（10 项含倾向方案 + 决策时机）
    - **D-017 反向校验产物**（session 30 同 session 携带改动）：
      - **D-017 第 3.5 节**：`ScenarioSummary` 加 `ui_layout: Literal["entity_card", "relation_graph", "event_stream"] = "entity_card"` 字段 + v1 模型联动改动清单（schemas / scenario_models / scenario_loader / 两个 minimal/three_party scenario.yaml）
      - **触发原因**：决策 7（混合 layout）让前端依据此字段切换跑中主区风格——D-017 起草时未发现此需求
    - **未同步文档**（推迟到 v0.2 实施 session 31 携带）：
      - `schemas/scenario.schema.json` / `models/scenario_models.py` / 两个 scenario.yaml 的 ui_layout 字段——属于 v1 模型扩展，应该在 server 实施 session 一并落地（避免 spec 阶段触动代码）
    - **session 31 入口任务**：v0.2 5 步推进路径第 3 步——Server 骨架 + REST routes + service 抽象 + error map（不含 WebSocket）；同时落地 D-017 反向校验产物（ui_layout 字段 + 两个 scenario.yaml 改动）
    - **设计纪律**：
      - **不动代码**——session 30 仍是 spec 阶段，0 代码改动 0 测试改动
      - **反向校验先于实施**——发现 D-017 缺字段必须回头补 D-017，而不是在 server 实施时偷偷加（避免 mockup 与 spec 不一致）
      - **mockup 不是决策号**——独立文档（不进 `decisions/`），决策号专属决策性文档
    - **过程笔记**：
      - 用户最初问"先设计 UI 还是先抽 API"——澄清 "server 是抽 API 接口" 后用户希望"考虑后续扩展和维护"——D-017 spec 应运而生（session 29）
      - mockup 起草前的 6 个连续 ask_user_question 是关键——避免做"通用 UI"而是定位"演示/教学"，避免做"完整产品"而是"v0.2 演示场景"
      - 用户在第 5 问期间提出关键修正："干预面板应该是用户可以手动点击实体的图像"——这是 UX 突破式修正，把表单式干预改为直接操作式，提升演示沉浸感
      - 用户提出"自定义场景可以改为 LLM 自动生成的引导流程"——巧妙将"LLM 辅助建模 PoC"（v0.3+）的入口在 v0.2 mockup 里预留，未来不破坏 UI 框架

60. **v0.2 server 骨架实施**（session 31，2026-04-28）：
    - **背景**：D-017 spec（session 29）+ UI mockup（session 30）双交付完成；进入 v0.2 5 步推进路径第 3 步——Server 骨架实施（不含 WebSocket，WebSocket 在 session 32）
    - **交付范围**：
      - **D-017 反向校验产物落地**（4 个文件）：
        - `schemas/scenario.schema.json`：加 `ui_layout` 枚举字段（默认 entity_card）
        - `models/scenario_models.py Scenario`：加 `ui_layout: Literal[...] = "entity_card"`字段
        - `scenarios/minimal_market/scenario.yaml`：显式声明 `ui_layout: "entity_card"`
        - `scenarios/three_party_negotiation/scenario.yaml`：显式声明 `ui_layout: "relation_graph"`
      - **依赖**加 fastapi>=0.110 + uvicorn[standard]>=0.27 + httpx>=0.27；pyproject packages 加 5 个 server 子包
      - **server/ 完整骨架**（18 个新建文件）：
        - `server/__init__.py` + `server/api/__init__.py` + `server/api/v1/__init__.py` + `server/api/v1/routes/__init__.py` + `server/api/v1/middlewares/__init__.py` + `server/services/__init__.py`（6 个命名空间包 + 职责边界 docstring）
        - `server/api/v1/errors.py`：`ErrorBody` / `ErrorResponse` / `ErrorIssue` Pydantic + ERROR_MAP（10 异常 → (status, code) 二元组）+ 3 个全局异常 handler
        - `server/api/v1/schemas.py`：平台专有 7 个 Pydantic（CreateRunRequest / RunSummary / RunDetail / EventListResponse / SnapshotsListResponse / ScenarioSummary / HealthResponse / PauseResumeResponse / AnalyzeRequest）
        - `server/runtime_registry.py`：`RuntimeRegistry` 多并发管理 + threading.Lock + max_concurrent + RegistryFullError→503
        - `server/services/run_service.py`：`RunService` 11 个方法完整 lifecycle（CRUD + step/pause/resume + state/snapshot/events 查询）+ provider 工厂
        - `server/services/intervention_service.py` + `analysis_service.py`：包装 Runtime.intervene + analyze_run/enhance_with_llm
        - `server/api/deps.py`：FastAPI Depends 注入入口（registry / 3 services）
        - `server/api/v1/middlewares/auth.py`：v0.2 no-op 占位，为 v0.3+ 鉴权预留位置
        - `server/api/v1/routes/runs.py`：11 个 /runs 路由（CRUD + 控制 + 状态查询 + 事件查询）
        - `server/api/v1/routes/interventions.py`：1 个 /intervene 路由
        - `server/api/v1/routes/analysis.py`：GET /analysis + POST /analyze
        - `server/api/v1/routes/meta.py`：GET /scenarios + /health
        - `server/app.py`：FastAPI 应用工厂 + AppConfig dataclass + lifespan + CORS + handler 注册 + 4 router 挂载（`/api/v1` 前缀）
      - **CLI 集成**：`cli/serve.py`（独立模块）+ `cli/run.py` 添加 `serve` 子命令（延迟 import 避免未装 fastapi 时三个子命令仕仍可用）
      - **最小 v1 内核调整**：`core/runtime.py` 加 3 个只读 @property（`world` / `scenario` / `event_log`）供 server 上层读元信息；**不动语义**，纯读只暴露。原 “world_id” 走 `scenario.world_id`（字符串引用，避免访问嵌套 `world.world.id`）。
    - **6 测试文件 99 项新增**：
      - `tests/test_server_errors.py`（8 表项 + 10 参数化 + 10 handler 集成 = 28）——覆盖 ERROR_MAP 全表 + handler 返回状态码 + issues 字段透传 + traceback 不泄露
      - `tests/test_server_registry.py`（16）——register/get/shutdown/active_count/list_summaries + max_concurrent→503 + close 失败容忍
      - `tests/test_server_meta.py`（8）——/scenarios 掃描 + ui_layout 透传 + /health + openapi.json
      - `tests/test_server_runs.py`（33）——完整 lifecycle：POST/GET/DELETE /runs + step/pause/resume + state/snapshot 查询 + events 过滤分页 + max_concurrent 上限 + paused/terminated 状态 主要 4xx 路径
      - `tests/test_server_interventions.py`（8）——三类 kind交互 + Runtime lenient 行为记录
      - `tests/test_server_analysis.py`（6）——GET / POST + Phase A 字段透传
    - **总测试**：700 → 799 (+99净新 / 0 回归 / pytest 13.20s)
    - **技术决策亮点**：
      - **复用 models/* 不抽翻译层**（D-017 第 2.2 节）——response_model 直接用 `Snapshot` / `TickResult` / `WorldState` / `EventRecord` / `AnalysisResult` / `Intervention`；v0.2 server 专有 schema 只在 `server/api/v1/schemas.py` 新建
      - **routes / services / registry 三层分离**（D-017 第 2.1 节）——services 不接 Request 对象，为未来 mobile / SDK 复用预留
      - **并发 registry 线程安全**——`threading.Lock` 保护 dict；跨同步 / 异步 都能用
      - **错误响应统一 envelope**（D-017 第 2.4 节）——`{error: {code, message, issues?}}` 响应体不励traceback泄露
      - **API 版本化**——所有 endpoint 加 `/api/v1` 前缀；v0.3+ 可加 `/api/v2` 不冲突
      - **CORS 默认开启**（v0.2 本机使用）——前端开发友好
    - **发现的潜在限制记录**（补充到 pitfalls.md）：EventLog.generate_run_id 同一秒可能冲突——测试中采用显式 run_id 避免；生产不会同一秒 3 次创建不成问题
    - **session 32 入口任务**：v0.2 5 步推进路径第 4 步——WebSocket 推送：`server/api/v1/ws_events.py` typed 事件 + `server/api/v1/routes/ws.py` WS 路由 + `server/services/stream_service.py` 订阅广播 + `tests/test_server_ws.py`。Runtime.step() 后调 stream_service.broadcast 推 tick_advanced 事件。
    - **设计纪律**：
      - **D-017 spec 驱动实施**——所有路由、服务、 schema 都对齐 D-017 第三到六节
      - **实现不漂移 spec**——发现 ”`runtime.world` 使用不事“ 则加 @property 只读暴露，不走访问私有属性 / 不保全词法
      - **澕机交付 0 回归**——每阶段跑一次完整 pytest 验证；不动 v1 内核 700 项机制

61. **v0.2 WebSocket 实时推送实施**（session 32，2026-04-29）：
    - **背景**：session 31 交付 server REST 骨架；本 session 补齐 D-017 第四节 + 第 6.3 节设计——让前端能实时收到 tick_advanced / paused / run_finished事件。
    - **交付范围**（4 文件新建 + 2 文件修改）：
      - **新建**：
        - `server/api/v1/ws_events.py`：6 个 typed 事件（`WSEventBase` 基类 + `TickAdvancedEvent` / `PausedEvent` + `PausedPayload` + `RunFinishedEvent` / `ErrorEvent` / `PingEvent` / `PongEvent`）；discriminator 指 `event` 字段 Literal；data 复用 `TickResult` / `AnalysisResult` / `ErrorBody`。提供 `WSServerEvent` 与 `WSClientEvent` 联合类型。
        - `server/services/stream_service.py`：`StreamService` 类——`subscribe`/`unsubscribe`（async）+ `broadcast`/`close_run`（sync）+ `attach_loop`/`detach`（lifespan）。每连接独立 `asyncio.Queue(maxsize=100)`；跨线程用 `loop.call_soon_threadsafe`；满队列静默丢弃（反压）。锁保护订阅者集合。
        - `server/api/v1/routes/ws.py`：WebSocket 路由 GET /api/v1/runs/{run_id}/stream。连接后检查 run 存在→404则 close(4004)。起 `_send_loop`（queue 消费） + `_receive_loop`（检测断开 + v0.2 接受任意客户端消息不验证）；`asyncio.wait` FIRST_COMPLETED 并发调度；`finally` 必取消订阅 + close。关闭码：1000（正常） / 4004（run 不存在） / 4500（内部错）。
        - `tests/test_server_ws.py`（8 测试类 10 项）——连接lifecycle / step 推 tick_advanced / multi-step 顺序 / manual pause 推 paused / 重复 pause 不 duplicate / run finished 推 finished + close / 多订阅者 fan-out / subscriber_count 随断开下降 / 无订阅者时 step 不阻塞
      - **修改**：
        - `server/services/run_service.py`：`RunService.__init__` 可选参数 `stream_service`；`step` 后调 `_broadcast_tick`：永远推 tick_advanced；`reached_total_ticks=True` 跑 `analyze_run` + 推 `RunFinishedEvent` + `close_run`；`paused_after=True` 推 `PausedEvent`（breakpoint/every_tick）。`pause` 不重复推送。
        - `server/app.py`：lifespan 加 `StreamService` 构造 + `attach_loop(asyncio.get_running_loop())` + RunService 注入；关闭调 `detach()`；`include_router(ws_routes.router, prefix="/api/v1")`。
    - **总路由**：HTTP 16 + WS 1 + FastAPI 自带 docs/redoc/openapi = **20 个**。
    - **总测试**：799 → 809 (+10净新 / 0 回归 / pytest 13.25s)
    - **技术决策亮点**：
      - **v1 内核完全不动**——不加 callback / observer；RunService.step 闭环后面调 stream_service.broadcast，v1 Runtime.step 原封不动
      - **线程安全 sync/async 跨界**——`broadcast` 是 sync（FastAPI sync 路由可调）；内部 `loop.call_soon_threadsafe(_safe_put, queue, message)` 安全跨线程投递
      - **反压丢弃**——每 queue 100 上限，满静默丢弃；保证慢客户端不拖垄 server
      - **typed 事件 + discriminated union**——前端可以强类型化处理；事件 schema 与 REST response 完全复用同一套 Pydantic——不需记两套格式
      - **质量关闭码**——1000/4004/4500 清晰表达语义；前端根据码分支决定是否重连 / 跳起 toast 提示
      - **TestClient.websocket_connect 与 sync test 協作**——全部 10 项一次性跑过，论证 starlette 后台 anyio.from_thread 处理干净足够退点
    - **session 33+ 入口任务**：v0.2 5 步推进路径第 5 步——React 前端实现（预计 3-5 session）。按 mockup 中 11 区块详细设计逐步起场：web/ 项目初始化（Vite + TS + shadcn）→ routes/ 4 页骨架 → layouts/ 3 种实现 → components/ 共用 → hooks/ （useRun / useRunStream / useScenarios）→ i18n + 主题 → e2e。OpenAPI 自动 type 生成（`openapi-typescript`）保证与 server Pydantic 同步。
    - **设计纪律**：
      - **不动 v1 内核**——session 31 加了 3 个 `@property` 只读暴露；session 32 v1 零改动。“WebSocket 推送” 定位为“server 层组合 v1 产出”，不是“v1 报告事件给 server”
      - **D-017 spec 为唯一权威**——ws_events / stream_service / routes/ws 三个文件的设计都对齐 spec 第 4.1-4.5 与 6.3
      - **完整测试驱动 0 回归**——实施后一次跑通全部 ws 测试；v1 700 项 + REST 99 项 + WS 10 项三部分都保持绿色

62. **server 全面架构审查 + 保健清债**（session 33，2026-04-29）：
    - **背景**：session 31 + 32 实施了 22 个 server 文件 + 众多测试。用户要求"全面架构、代码审查和保健"——参考 session 27 架构审查 F1-F11 成功模式。
    - **审查维度**（A-G 7 个）：A 架构边界 · B WebSocket 关键路径 · C RunService 关键路径 · D 测试覆盖盲点 · E 配置与 lifespan · F spec 与实施漂移 · G 代码质量
    - **发现 10 项**（友好分级）：
      - 🟡 **F1 P2**：RunService / AnalysisService 3 处 `runtime._private` 访问（`_runtime_config` ×2 + `_provider` ×1）——违反封装
      - 🟡 **F2 P2**：`StreamService.broadcast` 序列化无顶层守护——万一 Pydantic dump 报错会阻断 step 主路径
      - 🟢 **F3 P3**：breakpoint 触发的 paused 事件没测试覆盖——重要路径盲点
      - 🟢 **F4 P3**：`run_service.py` import `EventLog` 但未使用——dead import
      - 🟢 **F5 P3**：3 处不必要 `# type:ignore[arg-type]` + 1 处 `Any` 占位类型应为 `Literal`
      - 🟢 **F6 P3**：D-017 第 3.5 节 `ScenarioSummary` spec 漏列 `world_id` 字段——session 31 实施时补上但未同步 spec
      - 🟢 **F7 P3**：ws_events 的 `ErrorEvent` / `PingEvent` / `PongEvent` v0.2 未触发但 docstring 未标注——可能误导读者以为已实施
      - 🟡 **F8 P2**：in-memory run 跑完不推 run_finished——v0.2 强制 persist=True 自然规避，但语义缺失
      - 🟡 **F9 P2**：server lifespan shutdown 不通知 ws 订阅者——依赖 starlette 强制 close 兼底
      - 🟢 **F10 P3**：ping/pong 未实施但 schema 预留——需 docstring 标明
    - **修复范围**（8 项代码修改 + 2 项 pitfalls 记录 + 1 项测试补齐）：
      - **F1**：`core/runtime.py` 加 `runtime_config` / `provider` 两个只读 @property（同 session 31 `world` / `scenario` / `event_log` pattern，**不动语义**纯只读暴露）+ RunService.get_run / AnalysisService.analyze 去掉 noqa SLF001
      - **F2**：`server/services/stream_service.py:broadcast` 包 try/except——任何序列化报错只 log warning + return，不拖垄 step 调用者
      - **F3**：`tests/test_server_ws.py` 加 `test_breakpoint_pause_includes_breakpoint_ids`——用 three_party_negotiation + override_attribute alice.max_trust=90 触发 alice_high_trust 断点；验证 ws 推 paused (reason="breakpoint", breakpoint_ids=["alice_high_trust"])；同时补 manual pause 的 breakpoint_ids=[] 验证
      - **F4**：`server/services/run_service.py` 删 `from core.events import EventLog` (line 29) + 删 `from typing import Any` (line 25, F5 后不再需要)
      - **F5**：`server/runtime_registry.py` `status` 用 `Literal["active", "paused", "finished"]` 局部变量注解 + `server/services/run_service.py` `_build_run_detail` 同 pattern + `_broadcast_tick` 里 `reason` 同 pattern——去掉 3 处 `# type:ignore[arg-type]`（仅保留 EventLog.get_events 的 kind 参数 ignore——该参数跨 EventKind Literal 与 str 边界，该 ignore 是有说服力的）
      - **F6**：`docs/02-design/decisions/D-017-v0.2-API契约与Server架构.md` 第 3.5 节 ScenarioSummary 加 `world_id: str` 字段与实施同步
      - **F7 + F10**：`server/api/v1/ws_events.py` 为 `ErrorEvent` / `PingEvent` / `PongEvent` 加 "v0.2 未触发" docstring 标注，同时说明 v0.3+ 启用场景
      - **F8 + F9**：`docs/03-implementation/pitfalls.md` 补 2 条 P2：(1) in-memory run 跑完不推 run_finished + (2) lifespan shutdown 不通知 ws 订阅者——含现象/根因/3 种修复思路/v0.3+ 防再犯
    - **总代码改动范围**：5 个 server 文件 + 1 个 v1 内核文件（core/runtime.py +12 行）+ 1 个文档 + 1 个测试
    - **总测试**：809 → 810 (+1净新，来自 F3 补测 / 0 回归 / pytest 13.64s)
    - **架构审查原则**：
      - **v1 内核只可增加 @property 只读暴露**——不动语义，不添加 callback / observer，不增加额外状态
      - **守护主路径**——推送、存储、附加服务都不能拖垄 step 主调用，all 顶层 try/except + log warning
      - **设计反向驱动 spec 修补**——实施发现的字段补充 (F6) 走 D-017 须同步原则，不能只改代码不同步设计文档
      - **未触发 schema 明示标记**——v0.2 未触发的事件要 docstring 标清阅读期望，避免误导以为已实施
      - **pitfalls 记警**——发现的边界问题 (F8/F9) v0.2 不修但记录为 P2 供 v0.3+ 只需取出修补
    - **补充**：D-017 spec 补 ScenarioSummary.world_id 是本 session 唯一设计文档同步产物；其他全是实施代码 + 测试代码 + pitfalls 修改。
    - **设计纪律补充**：
      - **架构审查选点列表**（代码仓库 grep + spec 对照 + 测试覆盖检查）——可复用模式：session 27 (F1-F11) · session 33 (F1-F10) 都遵守
      - **友好分级**——P0/P1/P2/P3 明于决策几项必修、几项记录、几项可推迟。P2 表示“不是阅读預期，有发现价值但不重造”
      - **全量 pytest 验证**——每个修复后跑一次；最后跑一次确认 +1净新/0 回归
    - **session 34+ 入口任务**：React 前端实现 (v0.2 5 步推进路径第 5 步)——预计 3-5 session。起点：创建 `web/` 目录 (Vite + TS + Tailwind + shadcn/ui) + OpenAPI type 生成 + 项目骨架。

63. **v0.2 前端 mockup 第二阶段配套**（session 34，2026-04-29）：
    - **背景**：session 30 已起草 mockup v1（1120 行 ASCII wireframe）；session 31-33 已交付 server REST + WebSocket + 架构审查。本 session 补齐 mockup 三项缺口：(1) 视觉 token 系统（为 React 实施准备）；(2) 以 server 实际实施为底对 mockup 的二轮校准；(3) React 组件粒度拆解。**目标**：让 session 35+ 启动 Vite 项目时按本 session 产出 1:1 落地，避免边写边发明。
    - **交付范围**（3 工作流 + 4 产出文件）：
      - **工作流 A：风格定锚 + tokens.css**——
        - 用 `extract-design-system` skill：`npx playwright install chromium`（179 MiB）+ `npx -y extract-design-system https://linear.app` 抓取 linear.app
        - dembrandt normalize 阶段过滤太严（仅推 2 色）；从 raw.json 直接读 `cssVariables` / `borderRadius` / `typography` 字段——值均为 linear 显式声明
        - 重写 `design-system/tokens.css` 316 行三层结构：
          - **Reference / Primitives 层（24 个）**：linear 原生命名——5 档背景（`--color-bg-primary: #08090a` / `bg-secondary` / `bg-panel` 等）+ 4 档边框 + 4 档文字 + 5 个 accent（`--color-accent: #7170ff` linear 紫）+ 6 个 status colors（green/red/yellow/orange/blue/teal）+ linear 专用色（plan/build/security）
          - **Semantic 层（30+ 个）**：Polisim 业务命名——`--bg-canvas` / `--bg-surface` / `--text-primary` / `--accent` / `--status-success` 等，每条都映射到 linear primitive
          - **9 个 polisim-* 业务专属**：`polisim-tick-active` / `polisim-llm-bubble` / `polisim-rule-bubble` / `polisim-paused` / `polisim-breakpoint` / `polisim-relation-positive` / `polisim-relation-negative` / `polisim-environment` / `polisim-intervention`
          - **8 类基础 token**：Typography（Inter Variable + Berkeley Mono 后置，15 档字号 + 4 档字重 + 5 档行高 + 3 档字间距）/ Spacing（4px 网格 16 档）/ Radius（7 档含 pill / circle）/ Shadow（6 档含 focus ring）/ Motion（5 档 duration + 5 档 easing）/ Z-index（7 层）/ Layout（顶栏 / 侧栏 / 控制条高度）/ Breakpoints（tablet 1024 / desktop 1280 / wide 1536）
          - 预留 `[data-theme="light"]` hook，v0.3+ 加 light mode
        - **透明度声明**：所有色值 / 字号 / radius 来自 linear.app 显式 CSS variables；Semantic 命名是 Polisim 自有；Shadow elevation 体系（lg/xl/2xl）+ Motion duration 是基于 linear 视觉惯例自定（明确标注）
        - 更新 `.gitignore`：追加 `.extract-design-system/`（dembrandt 临时产物 57KB）+ `node_modules/` + `web/dist/` + `playwright-report/` 等
      - **工作流 B1：第二轮 API 反向校验**（mockup §10 新章节）——
        - 扫 8 个 server 文件（`server/api/v1/routes/{runs,meta,analysis,interventions,ws}.py` + `schemas.py` + `ws_events.py` + `services/run_service.py`）对照 mockup 11 区块「数据来源」段
        - **🔴 必改 2 项**：(M1) 跑完页 4 段 LLM 报告流程错位——`RunFinishedEvent.data` 是 Phase A 不含 LLM 增强，必须异步调 `GET /analysis?enhance=true`；(M2) `[📥 下载 events.jsonl]` 是客户端纯 JS 实现（多次分页 + Blob），不依赖 server
        - **🟡 应补 5 项**：(M3) PausedEvent ws 监听；(M4) 干预"自动暂停"是前端 UX 而非 server 约束；(M5) `[🚪 退出]` 激活 DELETE；(M6) 画廊卡片显示 ui_layout 图标；(M7) 数据来源 `WorldState.relations` 校准为 `Snapshot.relation_state_summary`
        - **🟢 自然规避 5 项**：ErrorEvent / Ping/Pong / run_finished 后主动 close ws / diff 客户端计算 / OpenAPI type 生成
        - **✅ 已对齐 23 项**——核心架构假设全部成立；本轮偏差**全部是细节层**
        - **结论**：第一轮校验（session 30）完整覆盖 spec 缺口；React 实施时按 §10.5 / §10.6 修订项落地即可
      - **工作流 B3：React 组件清单 + props API**（mockup §11 新章节）——
        - **4 页 routes**：Gallery / PreRun / Running / Finished + 路由 path 定义
        - **3 layouts**（按 `scenario.ui_layout` 三选一）：EntityCardLayout / RelationGraphLayout / EventStreamLayout + dispatch 逻辑
        - **12 共用组件**（跑中 5 + 跑完 7）：TopBar / ControlBar / MiniDashboard / InterventionDrawer / PromptContextModal / NarrativeReport / FinishedSidePanel / AttributeChart / FinalRelationGraph / EventDistributionChart / RawDataView / ReplayPlayer
        - **12 基础组件**：ScenarioCard / ScenarioIntroPanel / AdvancedOptionsPanel / EntityCard / EntityMiniCard / LLMThoughtBubble / EventStreamLog / ParamSchemaFormField / AttributeFormField / LanguageSwitch / ErrorBoundary / LoadingSkeleton
        - **11 hooks**：useScenarios / useRun / useCreateRun / **useRunStream**（核心：管 ws 生命周期 + 累积 events / snapshots + 处理 PausedEvent / RunFinishedEvent + diff 计算）/ useIntervention / useStep+pause+resume+delete / useFinishedRun（含 §10.5 M1 异步 enhance 流程）/ useEvents / useSnapshot / useDownloadEventsJsonl（§10.5 M2 客户端纯 JS）/ useI18n
        - **1 zustand uiStore**：speed / sidePanelCollapsed / locale（持久化）+ prevSnapshotByRunId（diff 用）
        - **数据流图**：跑中 ws tick_advanced → useRunStream → 组件 re-render；干预流程（点击 EntityCard → POST /pause → InterventionDrawer → POST /intervene → POST /resume）
        - **7 项 v0.2 不实施**：ErrorEvent handler / Ping-Pong / ReplayPlayer 完整 / 多 run 对比 / 工具模式 / GitHub Pages / 移动端响应式
        - **5 PR 实施顺序**：PR1 骨架 → PR2 hooks → PR3 画廊+跑前 → PR4 跑中 → PR5 跑完
      - **工作流 B2：mockup 视觉描述 token 化**——
        - mockup §8.4「颜色主题」整节重写：保留原 Indigo 主题作"历史"+ 新增「实际采用：linear-inspired tokens」含 4 张表（背景 / 文字 / accent+status / Polisim 业务专属）每条标注出现区块 + light-mode hook
        - mockup §4.3.2 关系图 layout 数据来源段：节点颜色（llm 蓝 → `var(--status-info)` / rule 灰 → `var(--text-tertiary)` / random 紫 → `var(--accent)`）+ 边颜色（≥7 → `var(--polisim-relation-positive)` / 40-69 → `var(--status-warning)` / ≤4 → `var(--polisim-relation-negative)`）+ 字段名校准 `WorldState.relations` → `Snapshot.relation_state_summary`（同步 §10.6 M7）
        - 修正 mockup §11.5 表格列数（5→6 加"依赖 / 备注"列）+ §11.8 store 表格去 inline `<br>` 改纵向布局
    - **总产出**：4 文件——`design-system/tokens.css`（新建 316 行）+ `docs/02-design/v0.2-前端-UI-mockup.md`（+460 行：§10 新增 + §11 新增 + §8.4 重写 + §4.3.2 token 化）+ `.gitignore`（追加前端 ignore 块）+ 文档历史 session 34 条目
    - **总测试**：810 passed / 0 代码变动 / 0 测试变动（纯文档 + design-system 产出）
    - **技术决策亮点**：
      - **风格锚定 linear.app**——选定理由：与 Polisim「实时仿真态势盘 + 高信息密度 + 演示/教学」气质强匹配；linear.app 的「冷静 + 深色基底 + 紫色 accent + 微过渡」风格优于原 Indigo 浅色主题
      - **dembrandt normalize 绕过**——工具默认输出过滤太严，直接读 raw.json `cssVariables` 字段拿到完整 36 个 design token；不无中生有，所有值都来自 linear 显式声明
      - **三层 token 结构**——Reference / Primitives / Semantic 严格分层；组件代码只能用 semantic 层，不能直接用 primitives，让未来主题切换 / 维护漂移成本低
      - **mockup 两轮校验**——session 30 spec 阶段 + session 34 实施后两轮校验；每轮发现的偏差类型不同（前者发现 spec 缺口、后者发现细节漂移），印证 D-017 spec 阶段做反向校验的价值
      - **组件清单 1:1 落地导向**——每组件含 props API + 数据来源 + 引用区块；React 实施 session 不需要"边写边发明"，只需查表实现
      - **5 PR 切片清晰**——PR1-2 端到端连不上 server 但 type 跑通；PR3-5 累积可演示完整 5 步用户流程（mockup §6）
    - **§9 关键问题已拍板**（session 34 末追加，与用户对话产物，落地到 mockup §9.2/§9.4/§9.6/§9.8）：
      - **§9.2 关系图库**：✅ **B `cytoscape.js`** + `react-cytoscapejs` + `cytoscape-cose-bilkent`——**重评决策**（原倾向 react-force-graph-2d）。理由：mockup §1 画廊已预告 v0.3+ 信息级联（D-015 EntityCreate）+ 组织决策（D-015 ChainedAction）需要 hierarchical / dagre layout——react-force-graph-2d 不能胜任，未来必须重写 RelationGraphLayout。cytoscape 多 layout 引擎一次到位，未来 0 迁移成本；包大小 +100KB lazy load 不影响首屏。**v0.3+ 扩展**装 `cytoscape-dagre` + `cytoscape-popper` + 算法 extensions。
      - **§9.4 字体**：✅ **B + C 组合**——`--font-sans = "Inter Variable" + 系统 fallback`（中文走 PingFang/Microsoft YaHei 系统 fallback，不预加载思源黑体）；`--font-mono = "JetBrains Mono"`（免费开源）+ `"Berkeley Mono"`（linear 实际值，商业字体 fallback）+ ui-monospace 系统 fallback。**已修改** `design-system/tokens.css` 的 `--font-mono` 值。**v0.2 不预加载 Web Font**——依赖用户本地已装；v0.3+ 可加 `<link rel="preload">`。
      - **§9.6 4 段 LLM 报告渲染**：✅ **B Markdown** ——装 `react-markdown`；tick 引用写为 `[tick 3](#tick-3)` 点击副区高亮。为何不选 C（自动跳转）：B 零额外代价、C 需 NarrativeReport 与 FinishedSidePanel 互通 state，推 v0.3+ 再试。
      - **§9.8 错误处理 UI**：✅ **C 分级处理**——4xx → toast（sonner / shadcn Toaster）；5xx → modal（shadcn Dialog）需用户点 “重试” 或 “关闭”；ws 断开 → 顶部 banner + 自动重连计数。`ErrorBoundary` 负责 React 未捕获异常。实施点：PR2 hooks + ErrorBoundary 同 session。
      - **其他 6 项 §9 保持"倾向"未决**（9.1 默认速度 / 9.3 GitHub Pages / 9.5 实体图标 / 9.7 重播模式 / 9.9 演示vs工具 / 9.10 多 run 对比）——可"边做边定"或推迟。
    - **session 35+ 入口任务**：v0.2 React 前端实现起点——按 mockup §11 PR1 实施：创建 `web/` 目录 + Vite + TS + Tailwind + 引入 `design-system/tokens.css` + react-router 4 个空 route + react-i18next + zustand uiStore + openapi-typescript 生成 types.gen.ts。**关键依赖**：server `/openapi.json` 已暴露（FastAPI 自动），可直接 `npm run gen:types`。**4 项 §9 决策已拍板**——PR1-PR5 实施时无需再决策这 4 项。
    - **设计纪律**：
      - **mockup 是 React 实施的唯一权威**——按 §11 PR 顺序、按各组件 props 定义、按各 token 引用、按 §9 已决策项 1:1 落地
      - **不动 v1 内核**——本 session 0 代码变动；后续 React 实施同样不应推动 v1 内核改动（如需新字段，先走 D-017 spec 再实施）
      - **transparent token 来源**——design-system/tokens.css 顶部 docstring 明确标注「来自 linear.app raw.json + 哪些是自定义」；尊重 extract-design-system skill 的 Safety Boundaries
      - **未来场景视角驱动决策**——§9.2 重评 react-force-graph → cytoscape 是「考虑 v0.3+ 复杂场景」的决策范式：v0.2 不需要 dagre，但 v0.3+ 必需，**用户明确指出"通用场景怎么办"才看清这点**
64. **v0.2 React 前端 PR1 实施**（session 35，2026-04-29）：
    - **背景**：session 34 已交付 design tokens（`design-system/tokens.css`）+ §10 API 反向校验 + §11 React 组件清单。session 35 是 v0.2 React 前端 5-PR 实施路径的第 1 步——按 mockup §11.11 PR1 清单 1:1 落地项目骨架，不写组件 / 不写 hooks（PR2 范围）。
    - **任务范围**（用户 prompt 明确锁定）：(1) `npm create vite@latest web -- --template react-ts` 创建项目；(2) 装 runtime deps 4 个 + dev deps 4 个；(3) 引入 tokens.css；(4) Tailwind v3 + tailwind.config.ts 桥接 semantic 层；(5) react-router 4 个空 route + i18n + zustand uiStore；(6) `gen:types` 脚本；(7) 验收 dev server。
    - **交付清单**（16 文件，全在 `web/` 子树）：
      - **配置层**（4 文件）：`package.json`（自动生成 + 加 `gen:types` script）/ `vite.config.ts`（vite 模板默认）/ `postcss.config.js`（PostCSS + Tailwind + autoprefixer）/ `tailwind.config.ts`（**完整 token 桥接**：colors 30+ 项 / fontFamily / fontSize 14 档 / spacing / borderRadius 9 档 / boxShadow 9 档 / transitionDuration / transitionTimingFunction / zIndex / maxWidth / screens 三断点）
      - **样式层**（2 文件）：`src/styles/tokens.css`（拷贝自 `design-system/tokens.css` 全 321 行，单源真理在 design-system/）/ `src/index.css`（`@import "./styles/tokens.css"` + Tailwind 三 directives + `@layer base` 全局深色基底）
      - **入口与路由层**（2 文件）：`src/main.tsx`（StrictMode + BrowserRouter + i18n init）/ `src/App.tsx`（4 路由 + i18n.changeLanguage 同步钩子）
      - **i18n 层**（3 文件）：`src/i18n/index.ts`（fallbackLng=zh，escapeValue=false）/ `src/i18n/zh.json` / `src/i18n/en.json`（含 4 路由标签 + 顶栏切换 + PR1 占位提示）
      - **store 层**（1 文件）：`src/store/ui_store.ts`（zustand persist 中间件，**partialize 排除 prevSnapshotByRunId**——Map 不可 JSON.stringify 且按 run 自然失效）
      - **组件层**（1 文件）：`src/components/TopBar.tsx`（顶栏：项目名 Link + 中英切换按钮 + ARIA label）
      - **路由占位层**（4 文件）：`src/routes/{Gallery, PreRun, Running, Finished}.tsx`——每个仅渲染 `<h1 i18n>` + 占位提示 + （非 Gallery 路由）`runId` URL 参数显示
    - **关键设计决策**（PR1 范围内）：
      - **i18n 单一真理在 store**——i18n init 用静态 'zh'，App.tsx useEffect 把 store.locale 同步到 `i18n.changeLanguage`。zustand persist 是 sync hydrate，首屏 locale 已是上次保存值。避免 i18n 内置 detector / store 双源同步竞争
      - **Tailwind v3 not v4**——v4 改 CSS-first 配置（`@theme`），废弃 tailwind.config.ts。用户 prompt 明确要 ts 配置 + 团队对 v3 更熟，不冒进
      - **token 桥接策略**——`theme.extend.colors` 用 `'var(--bg-canvas)'` 字符串而非函数式（不支持 opacity-modifier，PR1 不需要）。命名空间避免冲突：文字用 `fg-*` 不用 Tailwind 默认 `text-*`（与 `text-5xl` 字号语义冲突），背景直接用 `canvas` / `surface` / `panel` 等 short name
      - **tokens.css 拷贝而非 alias**——单源真理在 `design-system/tokens.css`，web/ 拷贝一份。Vite resolve.alias 引外部目录会增加构建复杂度；拷贝两份的同步成本极低（PR2-5 不会改 tokens.css）
      - **Tailwind v3 vs `verbatimModuleSyntax`**——Vite 8 模板的 `tsconfig.app.json` 开了 `verbatimModuleSyntax: true`；i18n 资源 import 用 `import zh from "./zh.json"`（非 type-only）正常工作（json 是 value）。OK
      - **App.css / assets/ 不删**——Vite 模板 hero 资源在 src/，但 App.tsx 不引用就不打包（tree-shake）。删除增加风险，保留无成本
    - **验收证据**（mockup §11.11 PR1 验收清单 + 用户 prompt 明确要求）：
      ```text
      验收对象：v0.2 React 前端 PR1（项目骨架 + tokens + i18n + Router + uiStore）
      对应验收项：mockup §11.11 PR1 清单（5 项 + 用户 prompt 验收 4 项）
      输入：cd web && npm run dev → 浏览器开 localhost:5173
      执行方式：vite dev server（5173）+ PowerShell Invoke-WebRequest 自动验证
      实际输出：
        - Vite v8.0.10 ready in 1250ms（无 ESM/Tailwind/类型错误）
        - GET / 返 200 / 610 bytes index.html
        - GET /runs/abc/run 返 200 / 610 bytes（SPA fallback 工作 → React Router 客户端路由 OK）
        - GET /src/main.tsx 返 200，含 React 转译后代码 + 我们的 docstring 注释
        - GET /src/index.css 返 33899 bytes（远大于源 41 行 ~1.3KB，证 PostCSS+Tailwind transform 完整工作）
          - 含 .bg-canvas { background-color: var(--bg-canvas); }
          - 含 .text-fg-primary { color: var(--text-primary); }
          - 含 .max-w-layout { max-width: var(--layout-max-width); }
          - 含 .duration-fast { transition-duration: var(--motion-duration-fast); }
          - 含 .rounded-md / .text-5xl / .bg-header（顶栏 token） / .focus-visible:ring-border-focus
          - 全部 Polisim 业务专属 token utility 全 transform 出来
          - @layer base 把 html/body/#root 应用 var(--bg-canvas) #08090a 深色背景
      是否通过：✅
      备注：F12 浏览器手动验证（用户做）：
        - body computed style 应 `background-color: rgb(8, 9, 10)` (= #08090a)
        - 顶栏 [EN] 按钮点一下切英文，再点切回中文（zustand persist 保存 + i18n 同步）
        - 4 路由 URL 切换显示对应 t('routes.xxx') 文本
        - 控制台 0 ESM / Tailwind / 类型错误
      ```
    - **测试影响**：**0 后端测试变动 / 810 passed 不变**——本 session 0 v1 内核改动 / 0 server 改动 / 0 后端测试改动；纯 `web/` 子树新增（v0.2 8 层架构第 8 层落地起点）。
    - **session 36+ 入口任务**：PR2 实施——`src/api/types.gen.ts`（启 server 跑 `npm run gen:types` 自动生成）+ `src/api/client.ts`（axios / fetch wrapper）+ `src/api/ws.ts`（WebSocket client）+ hooks 全套（mockup §11.7 11 个）+ ErrorBoundary（§9.8 决策 C：4xx toast / 5xx modal / ws 断开 banner，需装 sonner）+ TanStack Query v5 集成。**PR2 后端到端连不上但 type 跑通**；PR3 起累积可演示完整 5 步用户流程。
    - **设计纪律遵守**：
      - **MUST NOT 全员遵守**——0 v1 内核改动 / 0 server 改动 / 0 hooks（PR2 范围）/ 0 mockup §8.1 之外的依赖（cytoscape / react-markdown 等留给 PR4-5）/ 0 §11.10 7 项 v0.2 不做列表
      - **mockup 是唯一权威**——§11.11 PR1 清单 1:1 落地，0 边写边发明（store 字段对 §11.8、路由路径对 §11.2、i18n init 对 §8.1 react-i18next）
      - **token 单源 + 业务层只用 semantic**——所有组件代码引用 `bg-canvas` / `text-fg-primary` 等 semantic 类，0 引用 primitives `--color-bg-primary` 等
      - **AGENTS.md 落点纪律**——所有新增代码全在 `web/` 子树，无新顶层目录、无 `utils/` 垃圾桶
    - **新踩坑（已记 P3）**：TS 6.0 与 openapi-typescript@7 peer dep 冲突——`npm install -D openapi-typescript` 因 TS 6 vs `peer typescript@^5.x` ERESOLVE 失败；解法 `--legacy-peer-deps`。openapi-typescript 是 type-generation 工具，TS 6 在类型层面 5.x 超集，不会触发实际语法不兼容。详见 `pitfalls.md`。
65. **v0.2 React 前端 PR2 实施**（session 36，2026-04-29）：
    - **背景**：session 35 交付 PR1 项目骨架。session 36 是 v0.2 React 5-PR 路径的第 2 步——按 mockup §11.11 PR2 清单 1:1 落地 API 层 + 7 核心 hooks + ErrorBoundary，为 PR3-5 组件提供数据套件。本 session 范围不含组件或 routes 实体 UI。
    - **任务范围**（用户 prompt 明确锁定 + mockup §11.11）：(1) 装 axios / @tanstack/react-query / sonner；(2) 启 server 跑 gen:types；(3) 写 client.ts + ws.ts + schema.ts；(4) 7 hooks；(5) ErrorBoundary；(6) main.tsx 集成 QueryClientProvider + Toaster + ErrorBoundary。
    - **交付清单**（13 文件、全在 `web/src/`）：
      - **API 层**（3 文件）：`api/types.gen.ts`（自动生成 2493 行 / 77 KB / 100+ schema）/ `api/schema.ts`（type aliases 马软业务层 import，暴露 14 个常用类型如 RunDetail / TickResult / Snapshot 等）/ `api/client.ts`（axios 实例 + 统一 baseURL `/api/v1` + ApiError 包装器 + 60s timeout + 4xx/5xx isClientError/isServerError helper）
      - **WebSocket 层**（1 文件）：`api/ws.ts` `connectRunStream(runId, callbacks)` —— 手写 WS event schema（TickAdvancedEvent / PausedEvent / RunFinishedEvent / WsErrorEvent，openapi-typescript 不产包括 WS）+ 指数退避重连（500ms → 10s 五档）+ NO_RECONNECT_CODES = {1000, 4004} + 客户端主动 close 不重连
      - **Hooks 层**（7 文件）：`useScenarios`（staleTime=30s）/ `useRun`（staleTime=30s，runId undefined 时 disabled）/ `useCreateRun`（onSuccess 插缓存，onError 4xx 与 5xx 按§9.8 分级 toast）/ `useStep` / `usePause` / `useResume`（mutation pattern，4xx/5xx prefix 错信）/ `useRunStream`（核心状态机 8 个 status：idle/connecting/running/paused/finished/reconnecting/closed/error + events/snapshots/latestTick/pausedInfo/finishedAnalysis/errorInfo/reconnectAttempt 7 个状态字段）
      - **错误边界**（1 文件）：`components/ErrorBoundary.tsx`——class component + getDerivedStateFromError + RenderErrorFallback 用 useTranslation 的函数子组件访问 i18n + 错误信息 / [重置视图] / [刷新页面] 三区
      - **入口集成**（1 文件改动）：`main.tsx`——从里到外：BrowserRouter（原有） → QueryClientProvider（PR2 新） → ErrorBoundary（PR2 新）；同级 Toaster（PR2 新，position=top-right + theme=dark + richColors）。QueryClient 默认 retry=1 / refetchOnWindowFocus=false / staleTime=5s
      - **i18n 补充**（2 文件改动）：`zh.json` + `en.json` 加 `error.boundary.{title,description,retry,reload}` + `error.toast.{4xx_prefix,5xx_prefix}`
      - **脚本修正**（1 文件改动）：`package.json` `gen:types` URL `…/openapi.json` → `…/api/v1/openapi.json`（mockup vs server 漂移修正 → P3 pitfall）
    - **关键设计决策**（PR2 范围内）：
      - **types.gen.ts 不含 WS schema** —— FastAPI 不把 WS schema 写进 openapi.json，openapi-typescript 存在本体缺口。解法：ws.ts 手写一份 PausedPayload / TickAdvancedEvent / PausedEvent / RunFinishedEvent / WsErrorEvent，与 `server/api/v1/ws_events.py` 1:1 对齐（未来 server 改动 ws_events.py 时同步本文件）
      - **types.gen.ts 也不含 ErrorBody / ErrorResponse** —— server 全局 exception handler 返回的 `ErrorResponse` 未作任何 endpoint response_model 声明。解法：client.ts 手写 ApiErrorBody 接口 + interceptor 送容两种 shape（{ error: ErrorBody } 与 裸 ErrorBody）+ 网络层错 fallback 为 status=0 + code='NETWORK_ERROR'
      - **错误处理分层**（mockup §9.8 决策 C）：(a) client.ts 是纯数据层，不 toast；(b) hooks 的 onError 调 toast 且区分 4xx/5xx prefix；(c) ErrorBoundary 仅 catch React 渲染错（不扫楬 API 错，各取其职）
      - **useRunStream 状态机 + StrictMode 双 mount** —— effect deps `[runId]` 使得 dev 带双连接一次，可接受（生产不发生）。`status` 8 个完备状态 —— idle / connecting / running / paused / finished / reconnecting / closed / error，finished 优先级高于 closed
      - **react-query QueryClient 配置** —— retry=1 / refetchOnWindowFocus=false / staleTime=5s；mutations.retry=0（mutation 不重试，避免双重副作用如双推送）
      - **API_BASE / API_PREFIX 环变量** —— 默认 `http://localhost:8000` + `/api/v1`；可覆盖 `VITE_API_BASE` / `VITE_API_PREFIX`（PR3+ 需部署到其他 host 时使用）
    - **TS 修复 1 条**：`useRunStream.onTick` 原状拿 `tick.snapshot.tick` 作 latestTick + 未考虑 snapshot 可为 null（snapshot_mode=final_only/never 时）→ 改为：snapshots 仅在 tick.snapshot 非空时累加 / latestTick 用 tick.tick（始终非空 number）。修后 `tsc --noEmit` 0 错
    - **验收证据**（mockup §11.11 PR2 标准）：
      ```text
      验收对象：v0.2 React 前端 PR2（API 层 + 7 hooks + ErrorBoundary + react-query/sonner）
      对应验收项：mockup §11.11 PR2：openapi-typescript types.gen.ts + axios client + 7 hooks + WS + ErrorBoundary
      输入：(1) `python -m cli serve --port 8000` 启 server；(2) `cd web && npm run gen:types`；(3) `npx tsc --noEmit -p tsconfig.app.json`；(4) `npm run dev`
      执行方式：openapi-typescript v7.13.0 + tsc 6.0 + Vite v8.0.10
      实际输出：
        - gen:types：444.3ms 生成 src/api/types.gen.ts（2493 行 / 77 KB / paths + components.schemas 完备）
        - tsc --noEmit：exit 0 / 0 type 错
        - vite dev：ready in 1172ms，那中 Re-optimizing dependencies 含新装 axios
        - GET / 返 200 / 610 bytes（Gallery 占位页）
        - GET /runs/abc/run 返 200 / 610 bytes（SPA fallback OK）
        - GET /src/main.tsx 返 200 / 6519 bytes（QueryClientProvider + Toaster + ErrorBoundary 被转译出现）
        - GET /src/hooks/useRunStream.ts 返 200 / 13716 bytes（核心 hook 转译后仍添加了完整 docstring）
        - vite client 推 "new dependencies optimized: axios" 后重载页面 — PR1 PR2 位置状态差交接顺利
      是否通过：✅
      备注：F12 手动验证（用户做）：— 控制台 0 ESM/Tailwind/类型错误；— PR1 4 路由、中英切换、顶栏全部照旧工作；— 未来 PR3+ 里调用 useScenarios 时 toast 应出（本阶段没调起到实体，遇到应是默默不处理）
      ```
    - **测试影响**：**0 后端测试变动 / 810 passed 不变**——本 session 0 v1 内核改动 / 0 server 改动 / 0 后端测试文件变动；纯前端增量。
    - **session 37+ 入口任务**：PR3 实施——画廊页（`Gallery.tsx` 完整实体）+ 跑前页（`PreRun.tsx` 完整实体）+ 两个新组件：`ScenarioCard.tsx`（画廊卡片，含 ui_layout 图标与 [▶ 开始] 按钮）+ `ScenarioIntroPanel.tsx`（mockup §4.2 场景叙事）+ `AdvancedOptionsPanel.tsx`（上体可选覆盖 ticks/llm_provider）。都使用本 session 交付的 useScenarios + useCreateRun + useRun，PR2 点起 PR3 点进入 mockup §6 场景五步用户流程的前 2 步。
    - **设计纪律遵守**：
      - **MUST NOT 全员遵守**——0 v1 内核改动 / 0 server 改动 / 0 组件或 routes 实体（PR3+ 范围）/ 0 mockup §8.1 之外的依赖（cytoscape / react-markdown / framer-motion 留给 PR3-5）/ 0 §11.10 7 项不做项（ErrorEvent / Ping-Pong / ReplayPlayer 等）
      - **mockup 是实施唯一权威**——§11.11 PR2 清单 1:1 落地（0 边写边发明）；hooks 类型依赖 mockup §10 反向校验产出（ScenarioSummary 7 字段含 ui_layout / world_id，TickResult 含 paused_after）
      - **token 单源 + 业务层只用 semantic** —— ErrorBoundary 的 fallback UI 全部用 `bg-surface` / `text-fg-primary` / `border-status-danger` / `rounded-lg` 等 PR1 桥接过的 semantic class，0 直接引 primitives
      - **AGENTS.md 落点纪律**——所有新增代码全在 `web/src/{api,hooks,components,i18n}/`，无新顶层目录、无 utils/ 垃圾桶
    - **新踩坑（已记 P3）**：mockup §8.3 默认 `gen:types` URL 为 `http://localhost:8000/openapi.json`，但 server `app.py` 设 `openapi_url="/api/v1/openapi.json"`（§10 反向校验未捕获此漂移）。首次跑 gen:types 报 404 后修 `package.json` 脚本为 `…/api/v1/openapi.json`。详见 `pitfalls.md`。
66. **v0.2 React 前端 PR3 实施**（session 37，2026-04-29）：
    - **背景**：session 36 交付 PR2 API 层 + 7 hooks。session 37 是 v0.2 React 5-PR 路径的第 3 步——按 mockup §11.11 PR3 清单 1:1 落地「画廊 + 跑前」两个路由的实体 UI，走通 mockup §6 场景五步用户流程的第 1-2 步。本 session 不含跑中布局（PR4 范围）与跑完页（PR5 范围）。
    - **交付清单**（8 文件变动，全在 `web/src/`）：
      - **路由**（2 文件重写）：`routes/Gallery.tsx`（header 中央标题 + 三段 grid：production（useScenarios）/ upcoming（2 占位硬编码）/ custom（1 占位））/ `routes/PreRun.tsx`（useParams 拿 runId + useRun cache-only 命中 + ScenarioIntroPanel + AdvancedOptionsPanel + [▶ 开始仿真] / [← 选其他场景]，后者 fire-and-forget DELETE 当前 run）
      - **业务组件**（3 文件新建）：`components/ScenarioCard.tsx`（三种 kind discriminated union：production 走 ScenarioSummary + ui_layout 图标（🎴 entity_card / 🕸️ relation_graph / 📜 event_stream, mockup §10.6 M6） + [▶ 开始] 主按钮；upcoming/custom 走 emoji + name + description + [v0.3+] 占位按钮） / `components/ScenarioIntroPanel.tsx`（三段：描述（whitespace-pre-line） + 实体列表（entity emoji 按 type 关键词匹配 + `world.entity_types[type].decision_mode` 查 i18n 标签） + scheduled_events 摘要） / `components/AdvancedOptionsPanel.tsx`（`<details>` 受控折叠 + ticks_override（number input） + llm_provider（select），PR3 disabled 以示意 UI占位，提示 v0.2 不接通业务）
      - **类型补全**（1 文件改动）：`api/schema.ts` 加 6 个嵌套子类型别名（`WorldDefinition` / `EntityTypeSchema` / `Scenario` / `ScenarioInfo` / `EntityInstance` / `ScheduledEvent`）供业务层直接 import。
      - **i18n 补充**（2 文件改动）：`zh.json` + `en.json` 加 4 组 keys：`gallery.{title, subtitle, tagline, error_*, retry, section.*, upcoming.*, custom.*, coming_soon_toast}` / `scenario_card.{start, v0_3_label, ticks_label, world_id_label, ui_layout_hint.*}` / `pre_run.{back, story_title, section.*, scheduled_event, no_scheduled_events, no_description, decision_mode.*, start, back_to_gallery, error_title}` / `advanced_options.{title, tip, ticks_override, ticks_override_placeholder, llm_provider, llm_provider_options.*}`。插值用 i18next `{{count}}` / `{{tick}}` / `{{type}}` / `{{id}}`。
    - **关键设计决策**（PR3 范围内）：
      - **ScenarioCard 三 kind discriminated union**——主场景走 ScenarioSummary，占位走手写 emoji+name+description。这让画廊页不为每种 kind 写三份 JSX，同时 props 类型严格区分（TS narrowing）
      - **AdvancedOptionsPanel disabled 默认** —— mockup §4.2 未明确高级选项生效路径（POST /runs 已在画廊点 [▶ 开始] 时发出，PreRun 的 [▶ 开始仿真] 仅跳转不重 POST）。PR3 disabled 反映「v0.2 占位 UI / 下 PR 接通」；v0.3+ 可加 [应用并重新创建 run] 按钮（DELETE + POST 路径）
      - **fire-and-forget DELETE on back-to-gallery** —— PreRun [← 返回画廊] 按钮在 navigate 前调 `apiDelete(`/runs/${runId}`)`，但 try/catch 并静默失败（用户已在切走的路上，不需要 toast）。未来可出 `useDeleteRun` hook 包装
      - **decision_mode emoji 映射 helper** —— ScenarioIntroPanel 用 entity type 名的关键词匹配（compan/regul/negotiat/agent）决定图标。v0.3+ 可改为 `EntityTypeSchema.icon` 字段驱动（mockup §9.5 未决）
      - **token 单源深色化**——所有组件 0 直接引 primitives（0 `--color-bg-*`），全走 PR1 桥接过的 semantic class：bg-canvas / bg-surface / bg-surface-hover / bg-surface-active / text-fg-primary / text-fg-secondary / text-fg-tertiary / text-fg-muted / border-border-default / border-border-subtle / border-border-divider / status-danger / accent / accent-hover。避免用 Tailwind opacity-modifier 在 var-based token上（`hover:border-accent/40` 不生效——改用净色 `hover:border-accent`）
    - **TS 修复 1 条**：`useCreateRun.mutateAsync` 拿 CreateRunRequest 入参，`llm_provider` 被 openapi-typescript v7 生成为 required（Pydantic v2 default 字段进了 OpenAPI required 数组）。Gallery `handleStartProduction` 显式传 `llm_provider: "mock"`——作为最小修。未来可考虑在 `useCreateRun` hook 里默认填（或 server 端改 `llm_provider` 字段为 `Optional[Literal[...]]` 并明变 server 代码套）。详见 P3 pitfall。修后 `tsc --noEmit` 0 错
    - **验收证据**（mockup §11.11 PR3 标准 + §6 用户流程前 2 步）：
      ```text
      验收对象：v0.2 React 前端 PR3（画廊 + 跑前页 + 3 业务组件）
      对应验收项：mockup §4.1 §4.2 §6 步 1-2 §11.11 PR3
      输入：(1) `python -m cli serve --port 8000`（PR2 代付仍在跑 PID 28756）；(2) `cd web && npm run dev`；(3) `npx tsc --noEmit -p tsconfig.app.json`
      执行方式：FastAPI 8000 + Vite 5173 + axios + react-query + sonner
      实际输出：
        - tsc --noEmit：exit 0 / 0 type 错
        - vite dev：ready 389ms（deps cache 命中）
        - GET / 返 200 / 610 bytes（Gallery 页面）
        - GET /runs/test_run/intro 返 200 / 610 bytes（PreRun SPA fallback）
        - GET /src/routes/Gallery.tsx + /src/components/ScenarioCard.tsx + /src/components/ScenarioIntroPanel.tsx 全 200（vite transform OK）
        - GET /api/v1/scenarios 返 697 bytes 2 个生产场景：{path: minimal_market…, id: walkthrough-min, total_ticks: 5, ui_layout: "entity_card", world_id: "minimal-market"} + {path: three_party_negotiation…, id: walkthrough-three-party, total_ticks: 8, ui_layout: "relation_graph", world_id: "three-party-negotiation"}
      是否通过：✅
      备注：F12 手动验证（用户做）：— 画廊页看到两个生产场景卡片（🎴 + 🕸️ 图标） + 2 upcoming + 1 custom；— hover 卡片 错elevate 动画；— 点 [▶ 开始] 跳转跑前页，看场景叙事/实体列表/预设事件 + 顶部 run_id；— [▶ 开始仿真] 跳 /run 路由（PR4 未实施，仅占位页）；— [← 返回画廊] 后反查 server 日志应看到 DELETE /runs/…
      ```
    - **测试影响**：**0 后端测试变动 / 810 passed 不变**——本 session 0 v1 / 0 server / 0 后端测试文件变动；纯前端增量。
    - **session 38+ 入口任务**：PR4 实施——**跑中布局最小可演示路径**：`routes/Running.tsx`（使用 useRun + useRunStream 核心 + Layout dispatch by `scenario.ui_layout`）+ `components/ControlBar.tsx`（mockup §4.4.1：[⏸ 暂停] / [⏭ 单步] / 速度 / [📊 副区] / [🚪 退出]）+ `layouts/EntityCardLayout.tsx`（mockup §4.3.1）+ `components/EntityCard.tsx`（实体卡片 + LLMThoughtBubble + diff 箭头）。可选加 `MiniDashboard.tsx`（§4.4.2）与 `InterventionDrawer.tsx`（§4.4.3）。累积可演示 mockup §6 第 3-4 步（开始跑 + 点实体卡片干预）。剩余 PR4-PR5 预计 2-3 session。
    - **设计纪律遵守**：
      - **MUST NOT 全员遵守**——0 v1 内核改动 / 0 server 改动 / 0 跑中布局或跑完页（PR4-5 范围）/ 0 mockup §8.1 之外依赖（cytoscape / react-markdown / framer-motion / recharts 留给 PR4-5） / 0 §11.10 不做项
      - **mockup 是实施唯一权威**——§11.11 PR3 清单 1:1 落地（0 边写边发明）；三 kind ScenarioCard 其设计可反复查 §4.1 ASCII wireframe 验证
      - **token 单源 + 业务层只用 semantic** ——§8.4 可迫期检查（0 `--color-*` primitives 引用）
      - **AGENTS.md 落点纪律**——所有新增在 `web/src/{routes, components, api, i18n}/`，无新顽层目录 / utils 垃圾桶
    - **新踩坑（已记 P3）**：openapi-typescript v7 把 Pydantic v2 有 default 的字段仍列为 TS required——例 `CreateRunRequest.llm_provider` 从 Pydantic 看是“可选但默认 mock”，但 OpenAPI 将其放入 required 数组，openapi-typescript 生成为非 optional 字段。调用方必须显式传 default 值。详见 `pitfalls.md`。
67. **v0.2 React 前端 PR4.1 实施**（session 38，2026-04-29）：
    - **背景 + 范围**：用户在 PR4 拆分粒度选择中选定 PR4.1（最小可演示）—— mockup §11.11 PR4 清单的核心 5 文件，先打通 mockup §6 第 3 步（点 [▶ 开始仿真] → ws 自动跑 → 实体卡片浮 LLM 想法气泡 + 属性 diff 箭头）。本 session 不含干预面板（PR4.2）/ PromptContextModal（PR4.2）/ MiniDashboard（PR4.2）/ relation_graph + event_stream layouts（PR4.5）。
    - **交付清单**（5 主文件 + i18n + 1 删除 PR1 占位）：
      - `routes/Running.tsx`（重写）—— useRun cache hit + useRunStream ws 订阅 + auto-step loop + finished 跳转 + PausedEvent reason toast + Layout dispatch by ui_layout + [🚪 退出] DELETE + navigate
      - `components/ControlBar.tsx`（新建）—— tick 计数 + 8 状态 badge（mockup §4.4.1）+ 暂停/恢复/单步 按钮 + 4 档速度对接 zustand uiStore.speed + 副区按钮 PR5 占位 + 退出按钮
      - `layouts/EntityCardLayout.tsx`（新建）—— grid 1col/tablet 2col/desktop 3col + entries 数组 + environment 底部行（mockup §4.3.1）
      - `components/EntityCard.tsx`（新建）—— emoji 头部按 type 关键词匹配 + decision_mode 标签 + 属性列表 + diff 箭头（数值型 prev vs current）+ LLMThoughtBubble（LLM 模式专属）+ rule/random 单行简化提示 + 刚执行动作 action(params) + 干预占位按钮
      - `components/LLMThoughtBubble.tsx`（新建）—— reason 文本 + [📋 看完整 prompt] disabled 占位（mockup §4.3.1 内嵌气泡）
      - `i18n/{zh,en}.json`（+ 5 组 keys：running / control_bar 含 8 状态 + 4 paused_reason / entity_card / llm_thought / rule_thought）
    - **关键设计决策**（PR4.1 范围内）：
      - **Auto-step loop 模式**：客户端 while + cancelled flag + setTimeout，间隔 = max(50, 1000/speed) ms；await stepMutAsync 串行（避免请求积压）；status!="running" 时 effect cleanup 清 cancelled 自然停。dev StrictMode 双 mount 触发 1 次额外 step（dev only，prod 不发生）
      - **EntityCardEntry 在 Running 内组装**：把 runDetail.scenario.entities + runDetail.world.entity_types + stream.snapshots[-1/-2] + stream.events 拼成 entries[]，传 Layout 与 EntityCard。Layout 不耦合 hooks（保持 mockup §11.3 L1 props 与 React 基本设计模式）
      - **PausedEvent reason toast**：mockup §10.6 M3 简化版（toast.info 而非顶部 banner）；breakpoint reason 用 i18next 插值 ids
      - **decision_mode 三档 UI 风格区分**：llm 渲染 LLMThoughtBubble 气泡（var(--polisim-llm-bubble) bg）；rule 渲染 "🤐 规则决策" 单行；random 渲染 "🎲 随机决策" 单行
      - **emoji 关键词匹配 helper**：entity type 名 / attribute name 用 includes 关键词（cash/reputation/trust/strict/regul/compan/negotiat）匹配 emoji；v0.3+ 可改 EntityTypeSchema.icon 字段驱动（mockup §9.5 未决问题）
      - **退出流程**：先 stream.close()（防 ws 重连尝试）→ apiDelete fire-and-forget（清 server registry）→ navigate('/')；3 步顺序保证不留半挂状态
    - **验收证据**（mockup §11.11 PR4.1 + §6 步 3）：
      ```text
      验收对象：v0.2 React 前端 PR4.1（跑中页最小可演示路径）
      对应验收项：mockup §4.3.1 §4.4.1 §6 步 3 §11.11 PR4 核心子集
      输入：(1) python -m cli serve --port 8000；(2) cd web && npm run dev；(3) npx tsc --noEmit -p tsconfig.app.json
      执行方式：FastAPI 8000 + Vite 5174（5173 假性占用 → 自动跑下一个）+ axios + react-query + sonner
      实际输出：
        - tsc --noEmit：exit 0 / 0 type 错
        - vite dev：ready 630ms
        - GET /api/v1/health 返 200 / 49 bytes
        - GET /api/v1/scenarios 返 200 / 697 bytes（2 个生产场景）
        - GET 5174/ + 5174/runs/test/run 全 200 / 610 bytes（SPA fallback）
      是否通过：✅
      备注：F12 手动验证（用户做）：— 画廊 → 选 minimal_market → 跑前 → [▶ 开始仿真] → 跑中页自动每秒 1 tick；— company_a 卡片每 tick 浮 LLM reason 气泡 + cash/reputation 属性右侧 ↑/↓ 箭头；— [⏸ 暂停] 切到 paused 状态 + auto-step 停止；— [⏭ 单步] 单步推进；— 速度切到 4x → 间隔 ~250ms；— 跑到 tick 5 → ws 推 run_finished → 自动跳 /finished（PR5 未实施仅占位）；— [🚪 退出] DELETE + 回画廊
      ```
    - **测试影响**：**0 后端测试变动 / 810 passed 不变**——本 session 0 v1 / 0 server / 0 后端测试文件变动；纯前端增量。
    - **session 39+ 入口任务**：PR4.2 实施——补干预面板：`components/InterventionDrawer.tsx`（mockup §4.4.3 三表单：force_action / inject_message / override_attribute）+ EntityCard 接通 onIntervene → POST /pause 乐观更新 + 打开 Drawer + 提交 POST /intervene + POST /resume + close drawer（mockup §10.6 M4 流程）+ `components/PromptContextModal.tsx`（D-016 6 段 prompt 展开）+ LLMThoughtBubble [📋 看完整 prompt] 接通 + 可选 `components/MiniDashboard.tsx`（mockup §4.4.2 副区折线 + 事件分布）。PR4.5 加 `RelationGraphLayout` + `EventStreamLayout`。剩余 PR4.2-PR5 预计 2-3 session。
    - **设计纪律遵守**：MUST NOT 全员遵守——0 v1 / 0 server / 0 干预面板（PR4.2）/ 0 PromptContextModal（PR4.2）/ 0 MiniDashboard（PR4.2）/ 0 关系图与事件流 layout（PR4.5）/ 0 mockup §8.1 之外依赖；mockup §11.11 PR4 拆分子集 1:1 落地。
68. **v0.2 React 前端 PR4.2 实施**（session 39，2026-04-29）：
    - **背景 + 范围**：session 38 PR4.1 已交付跑中页最小可演示路径（自动 step + 实体卡片 + LLM 想法气泡）。session 39 在 PR4.2 拆分子集中聚焦「干预面板 + Prompt 上下文 modal」两个 mockup §6 用户流程的核心交互（步 4「点击实体 → 干预 LLM 决策」+ 步 5「展开 prompt 看 AI 在想啥」）。MiniDashboard（mockup §4.4.2 副区折线 + 事件分布）需装 recharts，推 PR4.3 单独成 PR；relation_graph + event_stream layouts 推 PR4.5。
    - **交付清单**（3 文件新建 + 2 文件改 + i18n）：
      - **新建**：`hooks/useIntervene.ts` —— POST /runs/:id/intervene react-query mutation + onError toast；`components/InterventionDrawer.tsx` —— 侧抽屉 + 3 tab（force_action / inject_message / override_attribute discriminated union 对齐 server `Intervention` schema）+ 通用 tick / reason 字段 + Esc 取消 + JSON textarea + parse + 4 项校验消息；`components/PromptContextModal.tsx` —— modal + 6 段 collapsible（system_role / actor_view / perception / available_actions / language_hint / custom_segments；D-016 §2.1 PromptContext 全字段）+ JSON pretty-print + Esc / 点击外部关闭
      - **改动**：`components/EntityCard.tsx`（接通 onIntervene 按钮 + 解析 latestDecision.payload.prompt_context + LLMThoughtBubble 条件性传 onClickViewPrompt + 持有 PromptContextModal local state）；`routes/Running.tsx`（新增 useIntervene hook 调用 + drawer state（open/entityId/wasPaused）+ handleEntityClick 流程：仅 status=running 时 pauseMut.mutate + 打开 drawer + handleDrawerSubmit 流程：interveneMut.mutateAsync + toast.success + 条件 resume + 关闭 + handleDrawerCancel 流程：条件 resume + 关闭 + 渲染 InterventionDrawer page-level singleton + 传 onEntityClick 给 EntityCardLayout）
      - **i18n**：`zh.json` + `en.json` 加 2 组 keys：`intervention.{title, subtitle, tab.*, field.*, submit, cancel, submitting, json_parse_error, validation.*, success, auto_resume_skipped}`（含 3 tab 名 + 全 field 标签 + 4 项校验消息 + success 插值 kind/target/tick） / `prompt_modal.{title, subtitle, no_data, section.*, empty_field, close, close_hint}`（6 段标题 + Esc 提示）
    - **关键设计决策**（PR4.2 范围内）：
      - **wasPaused 记录**：`handleEntityClick` 时记录 `stream.status === "paused"` —— 用户原本已手动暂停（点 ControlBar [⏸ 暂停]）→ 提交后**不**自动 resume（保持用户意图）；用户原本 running → 提交后自动 resume 继续跑。同样在 cancel 路径生效
      - **drawer 持有位置**：page-level singleton 由 Running 持有（避免多 EntityCard 同时开多 drawer）；PromptContextModal 由 EntityCard local 持有（per-entity 入口，可同时开多个 modal 但 UX 上单击单展开）
      - **失败保留 drawer**：useIntervene.onError 已 toast；handleDrawerSubmit catch 不关闭 drawer，让用户修正 form 后重试。这是 mockup §10.6 M4 未明确的细节
      - **JSON parse helper**：`parseJsonObject` 用 discriminated union `{ ok: true; value } | { ok: false; error }` 而非 throw —— 支持表单端集中收 4 项校验消息一次性给用户
      - **JSON textarea 权宜方案**：force_action.params / inject_message.payload / override_attribute.attribute_changes 都用 JSON textarea + 校验，而非按 D-014 ParamSchema 自动生成 form fields。v0.3+ 可补「按 schema 自动生成 input」让普通用户填表更友好。当前对开发用户（懂 JSON）够用
      - **LLMThoughtBubble onClickViewPrompt 条件性传**：仅 promptContext 非 null 时传 callback —— rule / random 决策事件 payload 不含 prompt_context，按钮自然 disabled（PR4.1 LLMThoughtBubble 已 disabled fallback）
      - **token 单源**：所有新组件 0 直接引 primitives，全用 PR1 桥接的 semantic class（bg-surface / bg-canvas / bg-panel / bg-overlay / text-fg-primary / text-fg-secondary / text-fg-tertiary / text-fg-muted / border-border-default / border-border-subtle / border-border-divider / accent / accent-hover / status-danger / z-modal）
    - **TS 修复 1 条 + IDE lint stale 1 条**：(a) PromptContextModal 用 `JSX.Element` 在 React 19 + TS 5 下不再有效 → 改用 `ReactElement`（from "react"）。(b) IDE Volar lint 报 "ReactElement 已声明但从未读取" stale —— 实际 line 55 用了，tsc --noEmit 0 错。
    - **验收证据**（mockup §11.11 PR4 子集 + §6 步 4-5 + §10.6 M4）：
      ```text
      验收对象：v0.2 React 前端 PR4.2（干预面板 + Prompt 上下文 modal + 三流程接通）
      对应验收项：mockup §4.4.3 §6 步 4-5 §10.6 M4 D-016 §2.1
      输入：(1) python -m cli serve --port 8000（PID 28756，PR2 时启的仍在跑）；(2) cd web && npm run dev（5174）；(3) npx tsc --noEmit -p tsconfig.app.json
      执行方式：FastAPI 8000 + Vite 5174 + axios + react-query + sonner（PR4.1 dev server 自动 HMR 重载）
      实际输出：
        - tsc --noEmit：exit 0 / 0 type 错
        - vite HMR：Running.tsx + index.css 自动重载
        - GET /api/v1/health 返 200 / 49 bytes
        - GET 5174/ + 5174/runs/test/run 全 200 / 626 bytes（SPA fallback）
        - GET /src/components/InterventionDrawer.tsx 返 200 / 61329 bytes（vite transform OK）
        - GET /src/components/PromptContextModal.tsx 返 200 / 20891 bytes
        - GET /src/hooks/useIntervene.ts 返 200 / 4955 bytes
      是否通过：✅
      备注：F12 手动验证（用户做）：— 跑中页 → 点 company_a 卡片 [📌 干预] → drawer 从右滑出 + 自动暂停 + ControlBar 状态切「已暂停」；— 默认 tab=force_action + tick 自动填 latestTick+1；— 切 inject_message tab → message_type select 列出 world.message_types keys；— 切 override_attribute tab → attribute_changes 提示当前实体属性名 / / 列表；— params/payload/attribute_changes JSON 错填 → 提交时 inline 校验消息；— 提交成功 → toast "干预已应用：force_action → company_a (tick X)" + drawer 关 + 自动恢复 + 下 tick 看 server 实际应用动作；— 点 LLMThoughtBubble [📋 看完整 prompt] → modal 6 段全部展开 + JSON pretty 看 actor_view/perception/available_actions；— Esc 关 modal + drawer
      ```
    - **测试影响**：**0 后端测试变动 / 810 passed 不变**——本 session 0 v1 / 0 server / 0 后端测试文件变动；纯前端增量。
    - **session 40+ 入口任务**：剩余 PR4 子项 + PR5 跑完页。3 条可选支线：(a) **PR4.3 MiniDashboard**：装 recharts → `components/MiniDashboard.tsx`（属性折线 + 事件分布 + 副区折叠对接 zustand sidePanelCollapsed）+ ControlBar [📊 副区] 启用；(b) **PR4.5 第二/第三 layout**：`layouts/RelationGraphLayout.tsx`（装 cytoscape，用于 three_party_negotiation 场景的实体-关系图谱）+ `layouts/EventStreamLayout.tsx`（事件流时间线，适用于无 spatial 结构的纯叙事场景）+ Running 已有 layout dispatch 直接接通；(c) **PR5 跑完页**：`routes/Finished.tsx`（D-009 分析报告渲染 + Markdown narrative + 6 类指标卡片 + 重跑 + 回画廊）+ useAnalysis hook（GET /runs/:id/analysis）。**推荐顺序**：PR4.3（演示价值高，相对独立）→ PR5（跑完页对收尾故事重要）→ PR4.5（多 layout 加广度但需要 cytoscape 学习曲线）。
    - **设计纪律遵守**：
      - **MUST NOT 全员遵守**——0 v1 内核改动 / 0 server 改动 / 0 MiniDashboard / 0 跑完页 / 0 第二第三 layout / 0 mockup §8.1 之外依赖（recharts / cytoscape / react-markdown 留给 PR4.3 / PR4.5 / PR5）/ 0 §11.10 不做项
      - **mockup 是实施唯一权威**——§11.11 PR4 干预子集 1:1 落地（0 边写边发明）；3 tab discriminated union 对齐 Pydantic Intervention.kind union；6 段 collapsible 对齐 D-016 §2.1 PromptContext 字段
      - **token 单源 + 业务层只用 semantic** ——§8.4 可迫期检查（0 `--color-*` primitives 引用）
      - **AGENTS.md 落点纪律**——所有新增在 `web/src/{routes, components, hooks, api, i18n}/`，无新顶层目录 / utils 垃圾桶
    - **未引入新 pitfall**：JSX.Element → ReactElement 迁移是 React 19 + TS 5 已知向前兼容点，0 P3 升级；其他改动按设计预期工作。
69. **v0.2 React 前端 PR4.3 实施**（session 40，2026-04-29）：
    - **背景 + 范围**：session 38 PR4.1 + session 39 PR4.2 已让跑中页支持「自动 step + 实体卡片 + 干预 + Prompt 查看」。session 40 按 progress.md 第 68 条目末尾「推荐顺序」走第 1 条：PR4.3 MiniDashboard 副区。剩余 PR5 跑完页 + PR4.5 第二/第三 layout 留下 session。
    - **交付清单**（1 dev dep + 1 文件新建 + 2 文件改 + i18n）：
      - **装 recharts**：38 包，用 `--legacy-peer-deps` 跳 openapi-typescript@7 peer dep 冲突（已知 P3 pitfall：session 35 PR1 时已记录；TS 6 + 7 冲突链条不解，dep 加 `--legacy-peer-deps` 是单点最小修）
      - **新建**：`components/MiniDashboard.tsx`（mockup §4.4.2 副区两段：(a) 📈 属性趋势——LineChart × N numeric attrs，X=tick / Y=value / 每实体一条 Line，5 色 palette `var(--polisim-line-1..5)` 循环 / Tooltip + Legend / isAnimationActive=false 防 ws 推送时 GPU 抖动；(b) 📊 事件分布——BarChart layout="vertical" by EventKind，X=count / Y=kind 名 / 高度按 kind 数自适应 `Math.max(140, n*22+40)`；3 项兜底文案：snapshots<2 / 无 numeric attrs / 0 events）
      - **改动**：
        - `components/ControlBar.tsx`：副区按钮从 PR4.1 的 disabled 占位 → 加 2 prop `sidePanelCollapsed: boolean` + `onSidePanelToggle: () => void`；active 视觉切换（!collapsed → accent bg / collapsed → default surface + hover）；aria-pressed 支持 SR；dynamic title show/hide
        - `routes/Running.tsx`：useUiStore 加 `sidePanelCollapsed` + `toggleSidePanel` selector；ControlBar 传两 prop；main 改双区布局——xl breakpoint 启动 `grid xl:grid-cols-[1fr_22rem]`，下 size 自动单列；副区仅 `entity_card` layout 且未折叠时渲染（其他 layout 现仍占位 PR4.5）
      - **i18n**：`zh.json` + `en.json` 加 `mini_dashboard.{title, section.attributes, section.events, no_snapshots, no_numeric_attrs, no_events, tooltip_tick}` + 改 `control_bar.side_panel_pr5` → `side_panel_show` / `side_panel_hide`
    - **关键设计决策**（PR4.3 范围内）：
      - **数据来源单一**：MiniDashboard 0 直接发请求，全部数据从父 Running 传入的 `entries / stream.snapshots / stream.events`——保持单源真相 + 单 ws 订阅
      - **属性趋势按"每属性一图"而非"每实体一图"**：因为用户阅读心智是「我想看 reputation 怎么变化」（属性维度），而非「我想看 company_a 的所有指标」（实体维度）。每图展示该属性所有实体并列，5 色 palette 区分
      - **numeric attribute 推断**：从最新 snapshot 取 `entity_state_summary` 字典里 `typeof === 'number' && Number.isFinite()` 的 key 集合（去重 + 排序）。不依赖 World Definition.entity_types[type].attributes 静态 schema —— 允许场景对属性 schema 演化
      - **事件分布用 vertical BarChart 而非 PieChart**：(a) kind 数量可达 15+（含 `chained_action_triggered` / `entity_destroyed` 等长名）→ 饼图 label 重叠不可读；(b) BarChart 高度自适应支持任意 kind 数量；(c) layout="vertical" 让长 kind 名水平显示在 Y 轴避免 overlap
      - **isAnimationActive=false**：ws 推 tick 频率高（speed=4x = 250ms 一次 rerender），动画会重叠 + 抖动；recharts 默认动画 1500ms 不适合实时更新
      - **副区折叠时 conditional unmount**：`{!sidePanelCollapsed && <MiniDashboard/>}` 而非 `display: none` —— 节省非演示状态下的 recharts 计算 + DOM 节点（recharts ResponsiveContainer 在 hidden 状态会反复 ResizeObserver fire 占 CPU）
      - **token 单源**：5 色 palette 用 `var(--polisim-line-N, fallback-hex)` —— design-system tokens.css 定义业务专属 5 色（mockup §8.4 §11.4 已规划），fallback 防 token 未定义时灰屏。Tooltip / 边框 / 网格全用 semantic tokens（var(--bg-surface) / --border-default 等）
      - **副区接通仅 entity_card layout**：mockup §4.4.2 副区设计专为 entity_card layout 服务（属性趋势 + 事件分布对实体场景最有意义）；relation_graph / event_stream layouts 推 PR4.5 自带数据可视化，无需通用副区
    - **关键修复 1 项**：MiniDashboard 初版用 `snap.entities[]` 数组遍历是错的——Snapshot schema 实际字段是 `entity_state_summary: { [entityId]: { [attr]: unknown } }`（字典，非数组）+ `relation_state_summary[]` + `environment_state` + `message_summary` —— openapi-typescript 生成的 types 已暴露此 schema，但我写时按经验假设了 `entities[]`。改两处遍历（collectNumericAttributes + buildAttributeSeries）→ `Object.entries(snap.entity_state_summary ?? {})` + entityIds Set 过滤。
    - **验收证据**（mockup §11.11 PR4.3 + §4.4.2）：
      ```text
      验收对象：v0.2 React 前端 PR4.3（MiniDashboard 副区 + ControlBar [📊] 按钮接通 + 双区 grid 布局）
      对应验收项：mockup §4.4.2 §11.4 §11.11 PR4.3
      输入：(1) recharts 装包 `npm install recharts --save --legacy-peer-deps`；(2) python -m cli serve --port 8000；(3) cd web && npm run dev（5173，因 npm install 触发 vite optimize 重启）；(4) npx tsc --noEmit -p tsconfig.app.json
      执行方式：FastAPI 8000 + Vite 5173 + recharts 2.x + axios + react-query
      实际输出：
        - npm install recharts：added 38 packages / audited 313 / 0 vulnerabilities
        - tsc --noEmit：exit 0 / 0 type 错（修 schema 后）
        - vite 5173：ready 2759ms（含 deps re-optimize）
        - GET /api/v1/health 返 200 / 49 bytes
        - GET /api/v1/scenarios 返 200 / 697 bytes
        - GET 5173/ + /runs/test/run 返 200 / 610 bytes（SPA fallback）
        - GET /src/components/MiniDashboard.tsx 返 200 / 30210 bytes（含 recharts imports）
        - GET /src/components/ControlBar.tsx 返 200 / 18542 bytes
        - GET /src/routes/Running.tsx 返 200 / 38744 bytes
      是否通过：✅
      备注：F12 手动验证（用户做）：— 跑中页 → ControlBar 右侧 [📊] 按钮高亮（accent bg）默认开启状态；— xl breakpoint（≥1280px 屏宽）双列布局：左主区 EntityCardLayout / 右副区 22rem 宽；— 副区上半部分：cash 折线 / reputation 折线（minimal_market 场景）每实体一条 Line + 颜色区分 + Tooltip 鼠标悬停看具体 tick 值；— 副区下半部分：BarChart 显示 decision_proposed / action_executed / message_emitted 等 kind 横条 + count；— 点 [📊] 切到 collapsed → 副区消失 + 主区全宽；— 切回展开 → 副区出现；— 切到 paused → MiniDashboard 数据冻结；— 跑到 tick 5 → 折线延伸到 5 个点
      ```
    - **测试影响**：**0 后端测试变动 / 810 passed 不变**——本 session 0 v1 / 0 server / 0 后端测试文件变动；纯前端增量。
    - **session 41+ 入口任务**：剩余 PR4-PR5 子项 2 条（按 progress.md 第 68 条目推荐顺序余下 2 条）：(a) **PR5 跑完页**：`routes/Finished.tsx`（D-009 分析报告渲染：6 类指标卡片——entity_count / event_count / decision_count / fallback_count / message_count / tick_count；Markdown narrative 用 react-markdown 渲染；2 按钮——重跑 + 回画廊；可选 ConsistencyMarker 显示 v0.1.1 增强分析的「可信度」标签）+ `useAnalysis` hook（GET /runs/:id/analysis）+ i18n 加 finished.* 一组 keys；(b) **PR4.5 第二/第三 layout**（装 cytoscape + react-cytoscapejs：`layouts/RelationGraphLayout.tsx`（实体节点 + 关系边 + force-directed 布局，用于 three_party_negotiation 场景）+ `layouts/EventStreamLayout.tsx`（事件流时间线，适用纯叙事场景）；Running 已有 layout dispatch 直接接通）。**推荐顺序**：PR5 → PR4.5（PR5 收尾故事重要，PR4.5 加广度但 cytoscape 学习曲线）。
    - **设计纪律遵守**：
      - **MUST NOT 全员遵守**——0 v1 内核改动 / 0 server 改动 / 0 跑完页（PR5 留空）/ 0 第二第三 layout（PR4.5 留空）/ 0 mockup §8.1 之外依赖（cytoscape / react-markdown 留 PR5 / PR4.5）
      - **mockup 是实施唯一权威**——§4.4.2 副区双段 1:1 落地（属性趋势 + 事件分布）；§11.4 C2 / C3 ControlBar + MiniDashboard props 1:1 落地；§8.4 token 单源（0 primitives 引用）
      - **AGENTS.md 落点纪律**——所有新增在 `web/src/{components, routes, i18n}/`，无新顶层目录 / utils 垃圾桶
    - **未引入新 pitfall**：MiniDashboard schema 错误（`entities[]` vs `entity_state_summary{}`）是「不读 types.gen.ts 凭印象写」教训，已在 PR1 的 P3 pitfall 类似归档（"openapi-typescript 生成 types 是单一真相，写代码前先读"）。本 session 已修，无需新条目。
70. **v0.2 Playwright E2E 自动化测试 + 修复 PR4.3 latent bug**（session 41，2026-04-29）：
    - **背景 + 范围**：user 主动请求"自动化测试一下网页"。给 4 选项（Playwright E2E 推荐 / Server API 流脚本 / Vitest 前端单测 / 三者混合）；user 选 Playwright E2E（覆盖最高 + 一次性投入）。本 session 落地 mockup §6 全 8 步用户故事的 1:1 自动化测试，并在测试过程中**意外发现 + 修复了 PR4.3 提交时的 latent bug**——recharts 装包用 `--legacy-peer-deps` 时漏装 react-is 传递依赖，跑中页 vite 抛 plugin error 全页 React app 不渲染。**这是 E2E 测试的核心价值证明**——tsc 0 错 + 路由 200 没暴露的 bug 被自动化捕获。
    - **交付清单**（4 dev/prod dep + 2 文件新建 + 1 文件改 + 1 docs 加 2 条 P3）：
      - **装包**：`@playwright/test` (3 包) + `chromium` browser binary (~150MB) + `@types/node`（spec 文件 string path 用不到但 tsconfig 声明） + `react-is`（修 PR4.3 latent bug，prod dep）；4 次装包全用 `--legacy-peer-deps`
      - **新建**：`web/playwright.config.ts`（baseURL=5173 / 单 worker / 失败时截图+录像+trace / chromium Desktop Chrome 1440x900 viewport / list+html dual reporter / outputDir=test-results/）
      - **新建**：`web/tests/e2e/mockup-flow.spec.ts`（170 行 / 1 spec / 8 个 test.step：步 1 画廊 → 步 2 跑前 → 步 3 跑中 → 步 4 切 0.5x 速度 + 等 auto-step → 步 5 干预 force_action（promote action_type / `{"amount": 30}` params）→ 步 6 暂停 + best-effort 看 prompt modal → 步 7 副区折叠/展开 → 步 8 退出 + 回画廊；每步 + 9 个截图）
      - **改动**：`web/.gitignore` 加 3 段 `# Playwright E2E` + `test-results/` + `playwright-report/` + `tests/screenshots/`
      - **docs**：`docs/03-implementation/pitfalls.md` 加 2 条 P3（详见下"踩坑记录"）
    - **关键修复 1 P3 bug（PR4.3 latent）**：装 recharts 用 `--legacy-peer-deps` 漏装 react-is → 跑测试时 page snapshot 抛 `[plugin:vite:import-analysis] Failed to resolve import "react-is" from "node_modules/.vite/deps/recharts.js"` → 全页 vite error overlay 遮挡 React app。手动 `npm install react-is --save --legacy-peer-deps` 补装 + kill vite 5173 + 重启触发 deps re-optimize 修复。
    - **关键修复 5 处 selector 错误（写 spec 凭印象）**：测试一次 spec 一稿写完 → 跑了 4 轮，每轮 fail 1 个不同 step：
      1. **步 1 H1 文案**：以为 "Polisim"（topbar 那个），实际 Gallery `<h1>` = `gallery.title` = "场景画廊"
      2. **步 1/8 scenario id**：以为 "minimal_market"（**目录名**），实际 `/api/v1/scenarios` 返回 `id` = "walkthrough-min"（来自 scenario.yaml `scenario.id: walkthrough-min`）
      3. **步 2 entity 文案**：以为跑前页用 entity.id（`company_a`），实际 `ScenarioIntroPanel:77` 用 `entity.name ?? entity.id` → 跑前显示 "A 公司" / "监管方"（中文 name），跑中页 EntityCard 才用 entity.id
      4. **步 2 实体集**：以为有 `company_a` + `company_b`，实际是 `company_a` + `regulator_main`（A 公司 + 监管方）
      5. **步 2 路由 pattern**：以为 Gallery → 跑前是 `/scenarios/:scenarioId/pre-run`，实际是 `/runs/:runId/intro`（Gallery [▶ 开始] 触发 useCreateRun + navigate `/runs/${runId}/intro`）
    - **测试结果**：**1 passed (11.1s) / 9 截图全生成**：
      - `01-gallery.png` 84KB / `02-prerun.png` 44KB / `03-running-tick0.png` 47KB
      - `04-running-advanced.png` 66KB / `05-drawer-filled.png` 73KB / `06-after-intervene.png` 73KB
      - `07-prompt-modal.png` **114KB**（**最大 → modal 真打开了 6 段 PromptContext** → minimal_market 场景**含 LLM 决策实体**——意外验证了 PR4.1/4.2/4.3 的 LLM 联动通路）
      - `08-side-collapsed.png` 40KB（**最小 → MiniDashboard 真卸载了**）
      - `09-back-to-gallery.png` 84KB（与 01 同 size → 回到画廊）
    - **关键设计决策**（PR4.3 范围内）：
      - **best-effort 步 6/7**：步 6 看 prompt modal 用 `if (await viewPromptBtn.isVisible().catch(false))` —— 若场景 entities 全是 rule/random 决策则 LLMThoughtBubble 不渲染，跳过 modal 验证。同样步 7 副区折叠用 `if visible` 防 layout=relation_graph 时无副区。这是 **mockup §6 用户故事覆盖度** vs **测试稳定性** 的权衡——production 场景 minimal_market 实际有 LLM 实体，步 6 走通；future 场景可能 0 LLM，让 spec 自动跳过而非 fail
      - **0.5x 速度切换**：minimal_market 默认 ticks=5 + 1x speed = 5s 跑完，留给 step 5+ 干预 + prompt 查看 + 副区切换的窗口太短。切 0.5x → 每 tick 2000ms → 总 10s，给后续步充足时间
      - **单 worker 串行**：playwright.config.ts `fullyParallel: false / workers: 1` —— 多 worker 并发会在 server runtime registry 上互相污染（同一个 minimal_market 创建多个 run + 同时 intervene），且 chromium 多实例占用 RAM
      - **失败时 trace + video + screenshot**：`trace: "retain-on-failure" + video: "retain-on-failure" + screenshot: "only-on-failure"` —— 跑通时不存（节省磁盘），失败时全留（debug 三件套）
      - **不用 webServer 自动起**：playwright config 没设 `webServer` —— vite + python server 都是外部跑（已在跑），避免覆盖；CI 环境再加 webServer 配置
    - **验收证据**（user 主动请求 + Playwright E2E 全流程通过）：
      ```text
      验收对象：v0.2 Playwright E2E 自动化测试 + PR4.3 react-is bug 修复
      对应验收项：mockup §6 用户故事 8 步 + PR4.1/4.2/4.3 全部 UI 集成
      输入：(1) npm install --save-dev @playwright/test --legacy-peer-deps；(2) npx playwright install chromium；(3) npm install react-is --save --legacy-peer-deps；(4) kill vite 5173 + npm run dev；(5) npx playwright test
      执行方式：FastAPI 8000 + Vite 5173 + chromium headless + Playwright runner 单 worker
      实际输出：
        - playwright install chromium：exit 0（~150MB browser binary）
        - 4 轮 fail 4 个不同 step（spec selector 凭印象错），最后 1 轮：
          ✓ 1 [chromium] › mockup §6 minimal_market full user flow (11.1s)
          1 passed (15.2s)
        - 9 截图全生成在 tests/screenshots/，size 范围 40-114KB
        - 步 6 prompt modal 实际开了（07 截图最大 114KB）
        - 步 7 副区折叠实际生效（08 截图最小 40KB）
      是否通过：✅
      备注：bug 不仅修了 react-is 装包，也证明了 mockup §6 全流程在 PR4.1/4.2/4.3 后 mock 决策模式跑通；E2E 测试可作为 PR5/PR4.5 后续实施前的 baseline regression check（每次新功能后回跑确认未 break）
      ```
    - **测试影响**：**0 后端测试变动 / 810 passed 不变 + 新增 1 个 Playwright spec / 1 个测试通过**——纯前端 + E2E 增量。
    - **session 42+ 入口任务**：剩余 v0.2 R 前端支线（按 progress.md 第 69 条推荐顺序余下 2 条）：(a) **PR5 跑完页**：装 react-markdown + 新建 `routes/Finished.tsx`（D-009 分析报告 + 6 类指标卡片 + Markdown narrative + 重跑/回画廊 + ConsistencyMarker）+ `useAnalysis` hook（GET /runs/:id/analysis）+ i18n 加 finished.* 一组 keys；**实施完后扩 spec 加 step 9-10**（跑完页指标卡片 + 重跑按钮验证）；(b) **PR4.5 第二/第三 layout**：装 cytoscape + react-cytoscapejs + 新建 `layouts/RelationGraphLayout.tsx` + `layouts/EventStreamLayout.tsx`；Running 已有 layout dispatch 直接接通；**实施完后扩 spec 加 second test for three_party_negotiation 场景**（用 relation_graph layout）。**推荐顺序**：PR5 → PR4.5。剩余预计 1-2 session 收尾 v0.2 R 前端。
    - **设计纪律遵守**：
      - **MUST NOT 全员遵守**——0 v1 内核改动 / 0 server 改动 / 0 PR5 / 0 PR4.5 / 0 mockup §8.1 之外依赖（cytoscape / react-markdown 留 PR5 / PR4.5）；@playwright/test 是 user 选定的工具栈扩展，符合"测试是开发活动"分类
      - **AGENTS.md 落点纪律**——所有新增在 `web/` 子目录（playwright.config.ts 工程配置 / tests/e2e/ E2E 目录 / .gitignore），无新顶层目录
      - **pitfalls.md 纪律**——session 中踩的 P3 立刻记 2 条（recharts 漏装 react-is + 写 spec 凭印象假设），按既有 P3 模板（现象+根因+解法+相关文件+防再犯）
    - **新踩坑（pitfalls.md 已加 2 条 P3）**：(a) `recharts` 装包用 `--legacy-peer-deps` 漏装 react-is，跑中页 vite plugin 报错；(b) 写 Playwright E2E 凭印象假设页面文案/路由/数据，5 处 selector 全错。
    - **session 41 第 2 阶段（user 主动质疑覆盖度后扩展）**：user 质疑「你确定你覆盖了所有的测试了吗」→ 给出 gap 清单（已测 8 step ≈ smoke test；未测约 20+ 关键交互）+ 4 选项；user 选「扩现 spec 加关键交互（~10 step）」。落地：spec 8 step → **13 step / 1 spec 1 passed (13.5s) / 10 截图**：
      - **PART 1 画廊与 i18n**：步 1 zh→en→zh 切换 + H1 文案变化双向断言；步 2 upcoming/custom 占位卡片点击触发 v0.3+ toast
      - **PART 2 跑前页**：步 3 进入 + AdvancedOptionsPanel 展开（best-effort 见 ticks_override label）；步 4 [← 返回画廊] 按钮 + 重新进入跑前
      - **PART 3 跑中页基础**：步 5 4 档速度（1x/2x/4x/0.5x 末档）循环点击 + 每档 `aria-pressed=true` 强断言；步 6 弱断言 tick ≥ 1 + EntityCard `↑/↓` diff 箭头 best-effort；步 7 MiniDashboard `.recharts-line` + `.recharts-bar` SVG 可见 best-effort
      - **PART 4 干预 3 tabs + cancel**：步 8 force_action(promote, **budget=30** 修正 amount→budget) + toast；步 9 inject_message tab 切换 + selectOption("policy_signal") + cancel 路径（drawer 2 个 ✕ 取消 button 用 `.last()` 取 footer）；步 10 override_attribute tab + `{"strictness": 99}` JSON + 提交
      - **PART 5 prompt modal 6 段**：步 11 暂停 + 打开 prompt modal + **6 段标题全验**（system_role / actor_view / perception / available_actions / language_hint / custom_segments）+ Esc 关
      - **PART 6 副区与退出**：步 12 副区折叠/展开 best-effort；步 13 [🚪 退出] + 回画廊
    - **第 2 阶段调试历程：4 轮 fail 4 个不同根因**：
      - **Round 1（step 1 i18n EN 切换）**：playwright `getByRole({name})` 优先 aria-label 而非 button text → topbar lang button 有 aria-label="切换至英文"，需用 aria-label 匹配
      - **Round 2（step 6 切 0.5x 找不到）**：4x×5tick=1.25s 跑完 5 tick → 自动 navigate `/finished` → 后续 step 找不到 ControlBar 控件。修：4 档切档顺序末档改 0.5x + 末尾立即 pause
      - **Round 3（step 6 resume 后 tick 不推进）**：resume click 成功但 status 不切 running。**根因深挖发现 v0.2 简化协议设计漏洞**：`server/services/run_service.py:213-221` resume 端点**不推 ws 事件**（v0.2 简化），但 client `useRunStream` 状态机仅靠 ws 推送切 status → resume 后 status 永远 paused → auto-step `useEffect` 不启动。临时改用单步按钮 → 又遇 Round 4
      - **Round 4（step 9 cancel button strict mode）**：drawer 2 个 ✕ 取消 button（header 关闭 aria-label + footer 长文本），strict mode 拒绝。修：`getByRole('dialog').last()` 取 footer
    - **session 41 第 2 阶段意外发现 1 个 P3 latent bug（已记 pitfalls.md）**：**v0.2 UI 单步功能与 v0.1 runtime.step() 语义错位**：UI `ControlBar.tsx:116` `disabled={!isPaused}` 的设计意图是「paused 时单步推进」，但 v0.1 `runtime.py:380-381` 在 paused 时**raise PausedError**——直接禁止 step。server step 路由不前置 resume，所以 UI 单步按钮在 paused 时 click 全部失败，server 返回 4xx，前端 toast 一闪而过没截到。**本质**：PR4.1 设计 ControlBar 时漏了 v0.1 接口契约校验；v0.1 内核「paused = 完全阻塞」与 v0.2 UI「paused = 可单步审查」语义直接冲突。**修复选项**（按上游修最小排序）：(a) server `RunService.step` 包装：`if paused: resume + step + pause`（推荐，5-10 行 server 改动）；(b) runtime `step(force_single)` 参数（v0.1 内核改动）；(c) UI 三调用 round-trip。**临时绕开**：spec step 6 改为弱断言（验证 step 5 期间 auto-step 已推进的 tick ≥ 1 + diff 箭头 best-effort）。**留 PR4-fix 单独处理**——本 session 不动代码。
    - **覆盖度对比（旧 8 step vs 新 13 step）**：新增覆盖：i18n 切换 / upcoming toast / AdvancedOptionsPanel / 返回画廊 / 4 档速度 aria-pressed / EntityCard diff 箭头 / MiniDashboard 折线+柱状图 / inject_message tab + cancel / override_attribute tab / prompt modal **6 段全验**（旧仅 1 段）/ Esc 关。**仍未覆盖**（PR5/PR4.5 实施后再扩）：跑完页 /finished + 6 类指标卡片 + 重跑路径；relation_graph + event_stream layout（cytoscape 未装）；错误流程（404/500/ws 断开重连）。
    - **测试结果（第 2 阶段）**：**1 passed (13.5s) / 10 截图全生成**：`01a-gallery-zh.png` 84KB / `01b-gallery-en.png` 73KB / `02a-prerun-advanced.png` 63KB / `03-running-4x.png` 51KB / `04-running-tick-advanced.png` 62KB / `05-mini-dashboard.png` 63KB / `06-drawer-force-action.png` 68KB / **`07-prompt-modal-6sections.png` 104KB（最大 → 6 段全验）** / `08-side-collapsed.png` 40KB / `09-back-to-gallery.png` 84KB。

    - **session 41 第 3 阶段（PR4-fix，user 选定路线 1 同 session 落地）**：上一阶段发现的 P3 latent bug（v0.1+v0.2 单步语义错位）user 选定 server side 包装路线（推荐路线 1）+ 顺手修 cli/serve.py help 文本不一致。**5 处改动 + 1 race 子修正 + 双层验收**：
      - **A. cli/serve.py:108**：help 「默认 10」→「默认 20」（user 改了 default 值未同步 help，顺手修）
      - **B. server/services/run_service.py:176-243**：`RunService.step` 加 paused 单步包装：`if was_paused: resume → step → manual_repause + paused_after=True 注入 broadcast result + 补推 PausedEvent(reason="manual")`
      - **C. tests/test_server_runs.py:250-282**：原 `test_pause_blocks_step`（断 409 RUNTIME_PAUSED）改名重写为 `test_step_in_paused_is_single_step`（断 200 + tick++ + 仍 paused）+ 新增 `test_step_in_paused_advances_multiple_times`（多次单步连推）
      - **D. web/tests/e2e/mockup-flow.spec.ts:130-152**：spec step 6 从弱断言「auto-step 推进的 tick≥1 best-effort + diff 箭头」升级为强断言「paused 状态点单步 → tick++ + resume button 仍 visible（仍 paused 证据）」
      - **E. 关键 race 子修正**：第一版 server fix 仅 `is_paused()` + `pause()`，跑 spec 时 step 7 后 page 跳到 `/finished` 页 → step 8 找不到 [📌 干预] 按钮。**根因深挖**：client `useRunStream.onTick` 见 `paused_after=False` 切 status="running" 短暂触发 auto-step useEffect race → run 跑到 5 tick finished。修：server 把 broadcast 的 TickResult.paused_after 改 True（`result.model_copy(update={"paused_after": True})`），让 client onTick 看到 paused_after=True → 切 status="paused"，避开 race。这是 **v0.2 ws 协议设计的隐性约束**：`tick_advanced.paused_after` 不仅是 v0.1 raw value，还得反映「服务端 step 后客户端应认为的实际暂停状态」——必要时由 service 层修改语义。
      - **测试影响**：`pytest 810 → 811 passed`（+1：`test_step_in_paused_advances_multiple_times`；`test_pause_blocks_step` rename 为 `test_step_in_paused_is_single_step` 内容重写但不计 +）；`playwright 13 step 1 passed 15.4s`（step 6 强断言版）；pitfalls.md 第 1 条 P3「✅ 已修」标记追加。
      - **设计纪律遵守**：MUST NOT 全员遵守——0 v0.1 内核改动（runtime.step() PausedError 行为保留，仅 service 层包装）/ 0 PR5 / 0 PR4.5 / 0 mockup §8.1 之外依赖；AGENTS.md 第 3.2 节「Runtime 不直接修改业务逻辑」继续遵守——server service 层是 v0.1 内核的**包装层**，承担 v0.2 用户操作语义到 v0.1 raw 接口的桥接职责
      - **未引入新 pitfall**——race 修正记录在原 P3 的"已修"段内（"关键避坑"小节），不另起新条目
    - **session 41 第 4 阶段（user 报 resume bug → 同 session 修复 RunResumedEvent 对称设计）**：上一阶段 PR4-fix 后 user 立刻报新 bug：「手动点击暂停后再点击恢复，界面无任何反应」。这是 session 41 第 2 阶段 Round 3 调试时已发现但未修的 v0.2 协议设计漏洞——**resume 不推 ws 事件 + client 状态机仅 ws 驱动 → 死锁**。**5 处对称改动 + 1 副发现 race 子修正 + 4 测试**：
      - **A. server/api/v1/ws_events.py:113-137**：加 `RunResumedEvent` + `RunResumedPayload`（与 `PausedEvent` 完全对称）；加入 `WSServerEvent` 联合类型
      - **B. server/services/run_service.py:260-282**：`resume()` 推 `RunResumedEvent`（仅 `was_paused=True` 时推，幂等防重复）
      - **C. web/src/api/ws.ts:44-60,75-80,91-92,184-186**：加 `RunResumedEvent` + `RunResumedPayload` typed schema + `onResumed` callback + handleMessage `case "run_resumed"`
      - **D. web/src/hooks/useRunStream.ts:138-146**：`onResumed` handler 切 `status="running"` + 清 `pausedInfo`（触发 Running.tsx auto-step useEffect 启动）
      - **E. 副发现 + 子修正**：调试中发现 `_broadcast_tick` 在 `paused_after=True` 时推 `every_tick` PausedEvent，service step 末尾又显式推 `manual` PausedEvent → **双推 + reason 错乱**。修：`_broadcast_tick` 加 `skip_paused_broadcast` 参数（`server/services/run_service.py:290-302`），让 service step 包装路径自己接管 paused 推送
      - **测试**：tests/test_server_ws.py 新建 `TestResumeBroadcast` 类 3 个单测（`test_resume_after_pause_pushes_run_resumed` / `test_resume_when_not_paused_pushes_nothing` / `test_resume_after_step_in_paused_no_extra_event`）+ 修原 `test_repeated_pause_no_duplicate_event`（resume 现在推 ws 事件，receive_json 多取一条）
      - **验收**：`pytest 811 → 814 passed`（+3 ResumeBroadcast 单测）；`playwright 13 step regression check 1 passed 14.9s`（RunResumedEvent 改动不破坏现有 spec）；user 在浏览器手动验证（基于 server CommandId 712 起的新进程 + ws 重连）
      - **本质**：v0.2 简化协议设计的**对称性漏洞**——pause 推 PausedEvent 但 resume 不推对应事件，client 状态机依赖 ws 推送但没数据可拉。设计假设"下一次 step 推 tick_advanced 足以告知"忽略了 client side **auto-step 仅 status=running 才发**这个前置条件
      - **新 P3 pitfall（pitfalls.md 顶端）**：「v0.2 简化协议漏洞：resume 不推 ws 事件 → client 死锁」，含完整根因链 + 5 处修复 + 防再犯纪律「v0.2+ 协议设计纪律：所有'状态变迁'（pause/resume/cancel/retry）都必须有对称的 ws 事件——client 状态机靠 ws 驱动，缺事件即死锁」
      - **设计纪律遵守**：0 v0.1 内核改动 / 0 PR5 / 0 PR4.5 / 0 mockup §8.1 之外依赖；AGENTS.md 第 3.2 节继续遵守；新增的 ws 事件落点 `server/api/v1/ws_events.py` 是合规的设计层
    - **session 41 第 5 阶段（user 选定路线 1 收尾后立即推 PR5）**：上一阶段 docs 收尾后 user 选「先收尾 session 41（docs + e2e regression）再推 PR5」并立即继续推进。落地 **PR5 精简版**（4 段叙事 + 6 类指标 + 重跑/回画廊；副区 tabs / 下载 / 关系图 / 折线 / 事件分布留 PR5.5+PR4.5）。**装包 1 + 新建 3 文件 + 重写 1 + i18n 加 1 组 + spec 扩 2 step**：
      - **装包**：`react-markdown` --legacy-peer-deps（79 包）
      - **新建 hooks/useAnalysis.ts**：基于 `useQuery` 的简单 GET 包装；query key 含 `enhance` 参数；staleTime 5min（runtime 跑完后数据稳定）；retry 1 次
      - **新建 components/NarrativeReport.tsx**：4 段 LLM 叙事（📖 world_overview / 📜 narrative_summary / ⚖️ situation_judgement / 💡 next_action_suggestions）+ react-markdown 渲染 + 每段 fallback「LLM 未生成此段（Phase A 模式）」+ loading skeleton（4 个灰色块脉动）
      - **新建 components/FinishedMetricsCard.tsx**：6 类指标卡片（⏱️ total_ticks / 📋 total_events / 🏷️ event_kinds / 👥 entities / 📈 turning_points / 🔔 breakpoints）+ responsive grid（2 → 3 → 6 col）+ loading skeleton
      - **重写 routes/Finished.tsx**（PR1 占位 24 行 → PR5 145 行）：mockup §10.5 M1 **双查询模式**——`useAnalysis(enhance=false)` 拿 phaseA 渲染指标（必然成功）+ `useAnalysis(enhance=true)` 拿 enhanced 渲染 4 段（失败时显示 ⚠️ banner + phaseA fallback）；header 含 [← 返回画廊] + [🔄 重跑]（反查 scenario_path：`useScenarios()` 列表 + `runDetail.summary.scenario_id` 匹配）
      - **i18n zh/en finished.* keys**：header / back_to_gallery / rerun / error.title+hint / metrics.* (6 标签 + aria) / narrative.* (title / loading / empty_section / 4 段标题)
      - **E2E spec 步 13 改写 + 加步 14-15**：原 step 13（退出回画廊）改为「resume + 4x 跑完 → 自动 navigate /finished」；新 step 14「verify finished page → 6 metrics + 4 narrative sections + buttons」（强断言 6 个 i18n 标签 + 4 段 + 2 按钮）；新 step 15「back to gallery from finished page」
      - **关键 race 子修正**：spec 第一版用 emoji 在 button name regex（`/🔄\s*重跑/`），chromium accessible name 处理 emoji 不一致 fail。修：移除 emoji 用 `/重跑|Rerun/i` 简化匹配
      - **关键设计修正（mockup §10.5 M1 落地）**：第一版 useAnalysis 单查询 `enhance=true`，mock provider 跑 narrative 失败 → server 502 Bad Gateway → 整页 error。改双查询：`useAnalysis(enhance=false)` 必然成功（Phase A 数据）+ 异步 `useAnalysis(enhance=true)` 失败时降级为 phaseA fallback。这正是 mockup §10.5 M1「先 Phase A 渲染 + 异步 enhance + 失败 fallback」的标准流程
      - **验收**：`pytest 814 passed`（PR5 纯前端，0 后端测试变动）；`playwright 15 step 1 passed 16.8s`（13 → 15 step / 9 → 11 截图：加 `10-finished-page.png` 67KB + `11-back-to-gallery.png` 84KB）
      - **后续 PR5.5 留**：副区 tabs（`FinishedSidePanel` + 5 tabs）/ events.jsonl 下载（`useDownloadEventsJsonl`）/ tick 引用点击跳副区高亮（`onTickRefClick`）/ FinalRelationGraph（依赖 cytoscape PR4.5）/ AttributeChart（recharts 折线）/ EventDistributionChart（recharts bar）/ RawDataView
      - **设计纪律遵守**：0 v0.1 内核改动 / 0 server 改动 / 0 mockup §8.1 之外新依赖（react-markdown 在 §8.1 清单内）/ AGENTS.md 第 3.2 节落点合规（`hooks/` + `components/` + `routes/`）/ pitfalls.md 未引入新条目（emoji selector + mock provider 502 都是 spec 调试期发现的小问题，已自修无后续风险）
    - **session 41 第 6 阶段（user 选定 (a) PR4.5 后立即推进）**：上一阶段 PR5 后 user 选 (a) 即 PR4.5 第二/第三 layout。落地 **PR4.5 完整版**（RelationGraphLayout + EventStreamLayout + Running 三 layout dispatch + i18n + 第二个 spec test）。**装包 3 + 新建 3 文件 + 修 2 文件 + i18n 加 2 组 + spec 加 second test 4 step**：
      - **装包**：`cytoscape` + `react-cytoscapejs` + `cytoscape-cose-bilkent`（8 包；mockup §8.1 + §9.2 决议）
      - **新建 layouts/RelationGraphLayout.tsx**：基于 react-cytoscapejs；cose-bilkent 力导向 layout；节点颜色按 decision_mode（llm 蓝 / rule 灰 / random 紫）；边粗细 1-4px 线性映射 trust value；边颜色阈值（绿 ≥70 / 黄 40-69 / 红 ≤40）；directed 关系自动加箭头；底部 LLM decision 气泡（reason + action.type）；图例 section（3 mode + edge hint）；点击节点委派 onEntityClick
      - **新建 layouts/EventStreamLayout.tsx**：左侧栏（实体小卡片：id / mode label / 前 2 数值属性 / [📌 干预] 按钮）+ 主区瀑布（按 tick 分组 + tick 内顺序 + 自动滚到底部）；mockup §4.3.3 简化版
      - **新建 components/event_templates.ts**：i18n 自然语言模板 + groupEventsByTick helper；8 种 EventKind 模板（decision_proposed / action_executed / relation_changed / breakpoint_triggered / intervention_applied / scheduled_event_triggered / environment_changed / decision_rejected）+ fallback ℹ️ 默认；payload 字段 typed extract（reason / action.type / variable / source / target / value 等）；非数值用 num() 兜底
      - **修 routes/Running.tsx**：(1) imports 加 RelationGraphLayout + EventStreamLayout + RelationEntry type（合规：从 layouts/ 导入，避免循环依赖）；(2) 新增 `relations` useMemo（snapshot.relation_state_summary 优先 + scenario.relations fallback；弱类型 `{[key]: unknown}[]` filter to typed）；(3) 新增 `latestDecision` useMemo（events 倒序 find decision_proposed）；(4) layout dispatch 改为 `entity_card / relation_graph / event_stream` 三分支（弃用占位提示）；(5) MiniDashboard 副区放开三 layout 都可显示（原仅 entity_card）
      - **修 web/src/api/schema.ts**：加 `export type RelationTypeSchema = Schemas["RelationTypeSchema"]`（RelationGraphLayout 需要 directed 字段；schema.ts 此前缺）
      - **i18n zh/en 加 relation_graph + event_stream 2 组**：`relation_graph.legend.{llm,rule,random,edge_hint}` / `relation_graph.decision_aria` / `event_stream.{entities_title,stream_aria,no_events}` / `event_stream.template.{8 种 EventKind}`（含 i18next 占位符 `{{actor}}` / `{{action}}` 等）
      - **E2E spec 加 second test for three_party_negotiation**：4 step（A: gallery → 找三人谈判卡片 → 进跑前；B: 跑前验 alice/bob/charlie；C: 开始仿真 → 验图例 3 mode 文本 + edge hint；D: 暂停 + 退出 → 回画廊）；不验证 cytoscape canvas 节点（无 DOM id 可断言）；2 截图（12-three-party-pre-run + 13-three-party-running）
      - **关键 selector 子修正**：spec 第一版用 `page.locator("article")` 找 ScenarioCard，实际 ScenarioCard 顶层是 `<div className="group ...">`。改 `page.locator("div.group", { hasText: ... })` 通过
      - **关键 EventKind enum 子修正**：event_templates.ts 第一版按 mockup 文字写 `attribute_changed` / `relation_value_changed` / `environment_event`，schema 真实 enum 是 `relation_changed` / `environment_changed`（无 attribute_changed）。修 3 个 case 名 + 删 attribute_changed
      - **关键 cytoscape 类型子修正**：第一版用 `cytoscape.Stylesheet[]`，cytoscape 包导出名为 `StylesheetCSS`。修
      - **验收**：`pytest`（PR4.5 纯前端，0 后端测试变动）；`playwright 2 passed 23.7s`（test 1 minimal_market 15 step / test 2 three_party_negotiation 4 step / 4 新截图）
      - **设计纪律遵守**：0 v0.1 内核改动 / 0 server 改动 / 装包均在 mockup §8.1 + §9.2 已决议清单内 / AGENTS.md 第 3.2 节落点合规（`layouts/` + `components/` 已预设）/ pitfalls.md 未引入新条目（3 个子修正都是 spec/code 调试期发现的小类型问题，已自修无后续风险）
71. **v0.2 PR5.5 跑完页副区**（session 42，2026-04-30）：按 `docs/02-design/PR5.5-spec.md`（session 41 末起草）的 5 子步 1:1 落地——**副区容器 + 5 tabs + 3 新 hooks + 客户端 Blob 下载 + E2E step 15-18**：
    - **子步 1**：schema.ts 加 7 个 alias（`KindStat` / `ActorStat` / `TurningPoint` / `EntityComparison` / `EventListResponse` / `SnapshotsListResponse`）；新建 3 hooks：
      - `hooks/useEvents.ts`（GET `/runs/:id/events` 分页 + 过滤 + cast `unknown[]` → `EventRecord[]`；react-query 5min staleTime）
      - `hooks/useSnapshot.ts`（含三 hooks：`useSnapshot` 单 tick + `useSnapshotsList` tick 列表 + **`useAllSnapshots` 批量 Promise.all 拉指定 tick 列表**——绕开"React hooks 不能动态调用"约束）
      - `hooks/useDownloadEventsJsonl.ts`（客户端分页循环 + Blob + URL.createObjectURL + `<a download>` 触发浏览器下载；总进度条按 `total` 字段估算）
    - **子步 2**：i18n `finished_side_panel.*` 两组共 36 keys（tabs / attribute_chart / final_relation_graph / event_distribution / replay / raw_data + narrative.enhance_failed 补漏）
    - **子步 3**：5 tab 组件（全在 `web/src/components/`）：
      - **`AttributeChart`**（~240 行）：useSnapshotsList + useAllSnapshots → recharts LineChart；实体/属性双 checkbox 过滤（默认全选）；支持 `highlightTick` ReferenceLine；loading / no_data 占位
      - **`EventDistributionChart`**（~120 行）：消费 `AnalysisResult.summary.events_by_kind / events_by_actor`（**schema 是 `KindStat[]` / `ActorStat[]` array，不是 mockup 猜想的 `Record<>`**——schema-first 胜利）；维度切换 2 按钮；recharts vertical BarChart
      - **`ReplayPanel`**（~140 行）：tick slider + ◀▶⏮⏭ 4 按钮 + 当前 tick 事件列表（复用 `formatEvent` 自然语言模板）；**不做**真正的自动播放（留 v0.3+）
      - **`RawDataView`**（~100 行）：前 200 行 JSONL 预览（`<pre>` 可滚动）+ 统计摘要（events / ticks / 预估 KB）+ `useDownloadEventsJsonl` 触发 + 进度条 + 错误 banner
      - **`FinalRelationGraph`**（~240 行）：cytoscape.js + cose-bilkent 力导向图；time-axis slider 切 tick；节点按 decision_mode 着色、边按 trust value 色/粗细映射；**不复用 RelationGraphLayout**（props 不同 + 避免破 PR4.5 e2e 回归；v0.3+ 可共享 refactor）
    - **子步 4**：`components/FinishedSidePanel.tsx`（~160 行）：5 tab 容器 + role="tab" + aria-selected 切换 + 懒加载（tab 切换才挂载对应组件）；顶部 useEvents(limit=5000) 共享给 ReplayPanel + RawDataView 避免重复拉取；GraphLoader wrapper 专供 FinalRelationGraph（react-query queryKey 与 AttributeChart 共享缓存）
    - **子步 5**：`routes/Finished.tsx` 底部挂 `<FinishedSidePanel runId={runId} runDetail={runDetail} result={phaseA} />`（`phaseA` 必然成功——复用 session 41 PR5 的双查询模式）
    - **E2E spec 扩展**（`web/tests/e2e/mockup-flow.spec.ts`）：原 15 step → 18 step。改 PART 7 注释为"PR5（步 14）+ PR5.5 副区（步 15-17）+ 回画廊（步 18）"；old step 15 （back to gallery）编号改 18；新 step 15（5 tab aria-selected 切换循环 + 截图）+ step 16（属性折线 tab 验 `.recharts-surface` svg + "实体：" filter 标签）+ step 17（原始数据 tab 点下载 → `page.waitForEvent("download")` → 验 `events_<runId>.jsonl` 文件名）
    - **关键 bugfix（同 session 踩坑 + 已记 P2 pitfall）**：第一版 RawDataView `disabled={downloading || events.length === 0}` 导致 playwright step 17 等 10s 超时——上层 `events = eventsResp?.events ?? []` 使得 "loading" 和 "empty run" 状态无法区分。改 `disabled={downloading}` —— 空 run 触发下载生成 0 行 jsonl 合法。pitfalls.md 新加 P2 条目（disabled + loading 语义混淆）
    - **关键设计纪律 schema-first 胜利**：写 EventDistributionChart 前发现 `AnalysisResult.summary.events_by_kind` 在 schema 是 `KindStat[]` array（`{kind: str, count: int}`），mockup §11.7 隐性假设是 `Record<EventKind, number>` —— session 41 末立的 P5 纪律（AGENTS.md 3.1 §：字段名/enum 冲突以 schema 为准）立即触发避免重写
    - **设计决策**：
      - FinalRelationGraph 不重构 RelationGraphLayout 抽 RelationGraphBase —— 避免破 PR4.5 e2e 回归（`three_party_negotiation` test 2）；接受 ~80 行 cytoscape stylesheet 重复（v0.3+ refactor）
      - AttributeChart 用 `useAllSnapshots` 一次性批量拉（Promise.all）—— N≤100 场景（walkthrough=6 tick）可接受；**未来**：server 加 `GET /snapshots?from_tick&to_tick` 批量 endpoint
      - events 共享（ReplayPanel + RawDataView）走 `useEvents(limit=5000)` 一次性拉 —— 大场景（>5000 events）下 RawDataView 的下载走 `useDownloadEventsJsonl` 独立分页路径；预览仍只显示前 5000 的前 200 行；v0.3+ 再优化
    - **验收**：`tsc --noEmit` 0 错 / `playwright 2 passed 26.9s`（test 1 minimal_market **18 step** / test 2 three_party_negotiation 4 step）：

      ```text
      验收对象：PR5.5 跑完页副区 5 tabs
      对应验收项：mockup §4.5 + PR5.5-spec 全 8 节
      输入：跑完 minimal_market 后的 /runs/:id/finished 页面
      执行方式：playwright step 15-17（5 tab 切换 + 属性折线验证 + 下载触发）
      实际输出：
        - step 15: 默认 📈 tab aria-selected=true → 依次点 🕸/📊/🎬/📋 每个 aria-selected 切换成功 + 500ms 给 recharts/cytoscape 挂载
        - step 16: 📈 tab 下 `.recharts-surface` svg 可见 + "实体：" filter 标签可见
        - step 17: 📋 tab 下点 "📥 下载 events.jsonl" → downloadPromise resolve → suggestedFilename 匹配 `events_*.jsonl`
        - 18 step 全 passed in 21.4s（test 1）+ 3.1s（test 2）= 26.9s
      是否通过：通过
      备注：RawDataView disabled 初版 bug 修复后一次过；无其他踩坑
      ```

    - **测试影响**：**0 后端测试变动 / 814 passed 不变**（纯前端 + E2E 增量）；playwright 从 2 passed 23.7s（session 41 末）→ 2 passed 26.9s（+3.2s 为新 3 step + recharts/cytoscape 挂载等待）
    - **设计纪律遵守**：
      - **MUST NOT 全员遵守**——0 v0.1 内核改动 / 0 server 改动 / 0 mockup §8.1 之外新依赖（cytoscape 已在 PR4.5 装完）
      - **schema-first 胜利**——Session 41 P5 纪律 + AGENTS.md 3.1 § 在 EventDistributionChart 写作前触发，避免按 mockup 文字猜 `Record<>` 写错后再 tsc 报错
      - **AGENTS.md 落点纪律**——所有新增在 `hooks/` + `components/` + `i18n/` + `routes/`（挂载），无新顶层目录
      - **PR5.5-spec.md 作为开发前权威**——session 41 末花 1h 起草，session 42 开发按 8 子步 1:1 落地，减少 session 42 内决策分叉
      - **pitfalls.md 纪律**——踩坑立记 P2 条目（disabled + loading 语义混淆）
    - **新踩坑（pitfalls.md 已加 1 条 P2）**：RawDataView 按钮 `disabled={downloading || events.length === 0}` 混淆 loading 与业务空值，playwright 10s 超时
72. **v0.2 架构清债 F1-F10**（session 43，2026-05-06）：类比 session 33 模式扫 PR4 / PR4.5 / PR5 / PR5.5 增量代码（session 38-42 共 5 PR），出 F1-F10 问题清单 + 全部修复 + 跑回归。**0 业务功能改动 / 0 v0.1 内核改动 / 0 server 改动**——纯前端代码健康度提升。
    - **F-list 清单**：
      - **F1-F2 [P2] 顶层 route docstring 严重过期**：`routes/Running.tsx` 4 处过期标注（"PR4.1 唯一可用" / "relation_graph / event_stream → 占位" / "不在本组件做（PR4.2+）"）+ `routes/Finished.tsx` 3 处过期（"v0.2 PR5 简化：不实现副区 tabs"）—— 实际 PR4.5 + PR5.5 后全部已实现。重写两份 docstring 反映当前真实结构 + 真实"暂未实现 v0.3+"段
      - **F3 [P2] schema.ts 3 dead alias**：`WorldState` / `AnalyzeRequest` / `HealthResponse` 各自仅自身 export 无业务消费方（grep 结果 0 命中）。删 3 行
      - **F4 [P2] i18n 4 dead/过期 keys**：(a) `placeholder.pr1_notice` / `running.layout_not_implemented` / `entity_card.intervene_pr_4_2` 三个 dead key（grep 唯一命中是 i18n 自己）→ 全删；(b) `llm_thought.view_prompt_pr_4_2` 文案过期但 LLMThoughtBubble.tsx 仍作 title 用（disabled hover hint）→ 改为 `view_prompt_no_context` + 文案"本次决策未附带 prompt 上下文（可能为非 LLM 决策或 D-016 prompt_context 未持久化）"+ LLMThoughtBubble.tsx 改 `title` 仅在 disabled 时显示
      - **F5 [P3] cytoscape 工具函数 ~30 行重复**：`FinalRelationGraph` 与 `RelationGraphLayout` 重复 COLORS（11 字段）/ edgeColorByTrust / edgeWidthByTrust / RelationEntry / register guard。**抽 `web/src/components/_relation_graph_shared.ts`**——5 项工具集 + 注释充分；stylesheet 因字号/节点尺寸不同**未抽**（参数化收益 < 复杂度增加）。两文件接通；layouts/RelationGraphLayout.tsx re-export RelationEntry 保持 Running.tsx import 路径向后兼容
      - **F6 [P3] recharts 工具函数重复**：`MiniDashboard` 与 `AttributeChart` 重复 ENTITY_PALETTE（5 行）+ collectNumericAttributes（10 行）。**抽 `web/src/components/_chart_shared.ts`**——2 项工具集；AttributeChart 原 collectNumericAttrs 改为复用 collectNumericAttributes
      - **F7-F10 [P3] 措辞 / 注释清理**：(a) `PreRun.tsx` advancedValue state 写不读 → docstring 标"展示位 disabled=true; v0.3+ 接通重建 run"；(b) `i18n.advanced_options.tip` 文案"v0.2 占位/下个 PR 接通"→ "高级选项展示位/v0.3+ 将接通"；(c) `EntityCardLayout.tsx` "PR4.1 范围 / 不在本组件里 PR4.2" → 改"职责"中性表述；(d) `AdvancedOptionsPanel.tsx` "PR3 默认 true" → 当前 PreRun 默认 true; v0.3+ 接通"重创 run"路径再 disabled=false；(e) `FinishedSidePanel.tsx` 注释"分页循环"→ 实际单调用 limit=5000；(f) `LLMThoughtBubble.tsx` "PR4.1 范围"→ 中性"范围"
    - **新文件清单**：
      - `web/src/components/_relation_graph_shared.ts`（80 行，5 export：RELATION_GRAPH_COLORS / edgeColorByTrust / edgeWidthByTrust / ensureCytoscapeRegistered / RelationEntry）
      - `web/src/components/_chart_shared.ts`（60 行，2 export：ENTITY_PALETTE / collectNumericAttributes）
      - 文件名 `_xxx_shared.ts` 前缀表"内部共用工具"——不暴露给 routes / hooks，仅 components/ 内消费
    - **playwright spec race 修复（同 session 第 2 阶段）**：跑回归时 step 5 失败：4 档循环 `1x→2x→4x→0.5x` 在 4x 期间 5 tick 跑完 → 自动 navigate /finished → 0.5x 按钮找不到。session 41/42 跑通是机器/vite optimize 偶然组合；session 43 重启服务后 first-run race 显形。修：进 /run 等 tick 1 + **立即 pause** + 再 4 档切档（aria-pressed 是纯 zustand state，paused 下完全可验证）。**spec 解锁 race 依赖，从 timing-sensitive 转 deterministic**
    - **验收**：`tsc --noEmit` 0 错 / `playwright 2 passed 32.8s`（test 1 minimal_market 18 step / test 2 three_party_negotiation 4 step）：

      ```text
      验收对象：v0.2 架构清债 F1-F10 + spec race fix
      对应验收项：类比 session 33 架构审查；F1-F2 docstring 反映真实状态 / F3 alias / F4 i18n / F5+F6 抽公用 / F7-F10 措辞 / playwright race
      输入：手动启动 server (8000) + vite dev (5173) 后跑 npx playwright test
      执行方式：tsc --noEmit + playwright 2 test
      实际输出：
        - tsc 0 错（含 cytoscape 类型 cast 在 IDE 显示警告但 tsc 实际通过；session 41 已确认 PR4.5 同状态）
        - playwright 2 passed 32.8s（21.4s test1 + 3.7s test2 + spec re-encoding 缓冲；test1 step 1-18 全部通过含步 5 重构）
      是否通过：通过
      备注：F-list 全部修复 + 引入 2 个共用工具文件 + 修了一个 timing-sensitive race spec
      ```

    - **测试影响**：**0 后端测试变动 / 814 passed 不变**；playwright 2 passed 26.9s（session 42 末）→ 32.8s（session 43 末，+5.9s 因 step 5 加 pause + service restart 后 vite re-optimize first-run + recharts/cytoscape 挂载等待）
    - **设计纪律遵守**：
      - **MUST NOT 全员遵守**——0 v0.1 内核改动 / 0 server 改动 / 0 业务功能改动 / 0 mockup 之外新依赖
      - **AGENTS.md 落点纪律**——抽公用文件落 `components/_xxx_shared.ts`（前缀 `_` 表内部工具），无新顶层目录 / 无 utils 垃圾桶
      - **类比 session 33 模式**——扫问题 + 出 F-list + 全量修复 + 回归测试，0 引入新功能（避免清债与新功能交叉）
      - **pitfalls.md 纪律**——race 现象立即记 P2 条目（playwright auto-step + UI 交互 race + page snapshot 诊断捷径）
    - **新踩坑（pitfalls.md +1 P2）**：playwright spec step 5 4 档循环切档遇 auto-step race，机器/vite 状态变化时 finished 页提前出现；解法：先 pause 后切档，从 timing-sensitive 转 deterministic

**进行中**：

- v0.2 session 43 **架构清债（类比 session 33 模式）**全部交付——F1-F10 清单 + 修复 + 抽 2 共用文件 + 修 playwright race。`tsc 0 错 / playwright 2 passed 32.8s（test 1 minimal_market 18 step + step 5 重构 / test 2 three_party_negotiation 4 step） / pitfalls.md +2 条 P2（playwright race + LLMThoughtBubble title）`。**v0.2 R 前端代码债清算阶段完成**，核心功能已 session 42 闭环；session 44+ 入口任务剩余 3 选 1（生产部署 / info_cascade 第三场景 / 第二阶段 LLM 辅助建模 PoC）。
- **PR3 关键文件清单**（session 37 落地，全在 `web/src/`）：
  - `routes/Gallery.tsx`（重写——useScenarios + 3 段 grid）
  - `routes/PreRun.tsx`（重写——useRun + ScenarioIntroPanel + AdvancedOptionsPanel + 上下按钮）
  - `components/ScenarioCard.tsx`（三 kind discriminated union + ui_layout 图标）
  - `components/ScenarioIntroPanel.tsx`（描述 + 实体列表 + 预设事件）
  - `components/AdvancedOptionsPanel.tsx`（折叠 + ticks_override + llm_provider）
  - `api/schema.ts`（+ 6 嵌套子类型别名）
  - `i18n/{zh,en}.json`（+ 4 组 keys: gallery / scenario_card / pre_run / advanced_options）
- **PR2 关键文件清单**（session 36 落地，全在 `web/src/`）：
  - `api/types.gen.ts`（openapi-typescript 自动生成，2493 行 / 77 KB）
  - `api/schema.ts`（type aliases helper，14 个常用类型暴露）
  - `api/client.ts`（axios + ApiError + apiGet/apiPost/apiDelete helper）
  - `api/ws.ts`（connectRunStream + 4 typed event + 指数退避重连）
  - `hooks/useScenarios.ts` + `hooks/useRun.ts`（react-query useQuery）
  - `hooks/useCreateRun.ts`（react-query useMutation + onSuccess 插缓存）
  - `hooks/useStep.ts` + `hooks/usePause.ts` + `hooks/useResume.ts`（mutation 模式）
  - `hooks/useRunStream.ts`（核心 8 状态 + 7 字段状态机）
  - `components/ErrorBoundary.tsx`（class component + RenderErrorFallback）
  - `main.tsx`（加 QueryClientProvider + Toaster + ErrorBoundary）
  - `i18n/{zh,en}.json`（+ error.boundary + error.toast）
  - `package.json`（gen:types URL 修为 `/api/v1/openapi.json`）

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
4. 在"会话历史"最顶端追加一条（格式：`### YYYY-MM-DD session N`），保持最多 5 条，老的删掉
5. 如踩坑了，去 `docs/03-implementation/pitfalls.md` 追加

## 七、本文件不做什么

- ❌ 不记录完整实现细节（那是代码和 docstring 的事）
- ❌ 不复述设计文档内容（那些在 `docs/02-design/`）
- ❌ 不存放决策的完整论证（待决策区只写"问题+候选+倾向"）
- ❌ 不当 TODO 垃圾桶（多于 10 条待办说明粒度太细，该合并）
