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

### [P2] 2026-04-29 mockup 文档与 schema enum 漂移——event_templates EventKind 名按 mockup 文字写错 3 处（session 41 PR4.5 踩坑）

**✅ 已修**（session 41 第 6 阶段）：`@web/src/components/event_templates.ts` 第一版按 mockup §4.3.3 文字写 `attribute_changed` / `relation_value_changed` / `environment_event` 三个 case，schema 真实 enum（`@web/src/api/types.gen.ts:997`）是 `relation_changed` / `environment_changed`（无 `attribute_changed`，属性变化通过 `action_executed` 体现）。tsc 立即报"类型不可与 EventKind 联合比较" 3 错；改 case 名 + 删 `attribute_changed` 通过。

- **现象**：写 PR4.5 `event_templates.ts` 时直接抄 mockup §4.3.3 第 426 行附近的"💰 {actor}.cash {before}→{after}"模板，对应 `attribute_changed`。tsc 报 `类型 "attribute_changed" 不可与类型 "decision_proposed" | ... 比较`。
- **根因**：mockup 是 session 30/34 写的，schema enum 是 D-013/D-015 落地时定的——**双源 spec 漂移**。session 27 F3 已发现的"schema vs spec 漂移"问题在前端代码上**重新发生**。
  - mockup 是产品意图文档，写于 server 还没落地时
  - schema 是 server-client 契约的事实源（自动从 Pydantic 生成 OpenAPI 再生成 ts）
- **本质**：双源文档没有"自动一致性"机制——mockup 用文字描述事件名，schema 用 enum；改一边不会自动同步另一边。
- **解法**（已落地）：写 client 代码涉及 enum / 字段名时，**优先看 `@web/src/api/types.gen.ts`**（自动生成）或 `@web/src/api/schema.ts`（人写的别名层）；mockup 仅作 wireframe + 用户故事参考。
- **相关文件**：`@web/src/components/event_templates.ts:67,93`（修后正确 enum 名）、`@web/src/api/types.gen.ts:997`（EventKind 全部 15 值的事实源）
- **防再犯**：
  - **AGENTS.md 第 3.1 节文档优先级**已增补一条：「**字段名 / enum 值**冲突时，以 schema (`@web/src/api/types.gen.ts`) 为准——schema 是 server-client 契约的事实源」
  - 写 client 代码涉及枚举时，先 `grep_search EventKind` schema 看实际值，**不要从 mockup 文字猜**
  - 长期：v0.3+ 考虑给 mockup 加自动校验脚本（解析 mockup mention 的事件名 vs schema enum 对照）

### [P3] 2026-04-29 v0.2 跑完页 LLM 增强必须双查询模式 fallback——单查询 enhance=true 在 mock provider 下整页 502（session 41 PR5 第一版踩坑）

**✅ 已修**（session 41 第 5 阶段）：`@web/src/routes/Finished.tsx` 第一版用单 `useAnalysis(runId, { enhance: true })`，mock provider 跑 narrative 生成失败 → server `/runs/:id/analysis?enhance=true` 返 502 → react-query 进 error 状态 → 跑完页整页渲染「分析报告加载失败」red banner，无任何数据可见。改双查询：`useAnalysis(enhance=false)` 拿 phaseA 渲染 6 指标（必然成功）+ `useAnalysis(enhance=true)` 异步拿 4 段 narrative（失败时 ⚠️ banner + phaseA fallback）。E2E spec step 14 一次过。

- **现象**：跑 e2e step 14 在 finished 页找 6 指标卡片标签——找不到。trace.zip 看 H1 = "分析报告加载失败"，整页 error 渲染。server log 显示 `GET /api/v1/runs/.../analysis?enhance=true HTTP/1.1" 502 Bad Gateway`。
- **根因**：mockup §10.5 M1 早已写明 4 段 LLM 报告**异步获取**而非 ws 直送的标准流程：
  1. tick 跑完 → server 自动 analyze_run（Phase A，必然成功）→ 推 RunFinishedEvent + close ws
  2. 前端进入跑完页时优先用 RunFinishedEvent.data 的 Phase A 字段先渲染（事件分布 / 实体比较）+ 在 4 段叙事区域显示 loading skeleton + 异步发起 GET enhance=true
  3. 失败处理：enhance=true 调用失败 → 显示 banner + 重试按钮 → 不阻塞 phaseA 渲染
- **本质**：PR5 第一版**没读 mockup §10.5 M1**，按"4 段叙事页"字面意思写单查询。Phase C LLM 增强是**可选**的——mock provider 不能生成 narrative 是 by design 不是 bug。UI 必须在 fallback 模式下完整工作。
- **影响范围**：所有用 mock provider 跑的场景跑完后整页错（即开发/测试场景全 broken）；只有真 OpenAI 跑成功才能看 finished 页。
- **解法**（已落地，session 41 第 5 阶段）：`@web/src/routes/Finished.tsx` 改双查询模式
  - phaseAError 才进 error 分支（致命：连 Phase A 都失败）
  - enhanceError 显示 ⚠️ banner 但不阻塞渲染
  - NarrativeReport 接 enhanced ?? phaseA fallback
- **相关文件**：`@web/src/routes/Finished.tsx:36-51,71-97,141-162`、`@web/src/hooks/useAnalysis.ts`（hook 本身简单，复杂度在 route 双查询）
- **防再犯**：
  - **v0.2 LLM 增强 UI 路径设计纪律**：所有"可选 LLM 增强"路径必须**双查询**——必然成功 query（rule-based 数据） + 可选增强 query（LLM 生成）；UI 必须在 enhance fail 模式下能完整工作
  - mock provider 不能生成 narrative / structured suggestion 是 by design，**测试场景 enhance=true 必失败应当假设而非异常**
  - 写 PR5 类型组件前必须**先读对应 mockup §10.5 校准段**（mockup 自带 server-side 实际行为对照表）

### [P3] 2026-04-29 v0.2 简化协议漏洞：resume 不推 ws 事件 → client 死锁（session 41 user 报 bug → 同 session 修复）

- **现象**：手动 click [⏸ 暂停] → 状态变 `已暂停` → 再 click [▶ 恢复] → **界面无任何反应**。tick 不推进、状态 badge 不变、auto-step 不启动。需要刷新页面才能恢复。
- **根因链**：
  1. **server `RunService.resume`**（修复前 `@server/services/run_service.py:213-221`）：仅 `runtime.resume()` 设 `_paused=False`，**不推任何 ws 事件**（v0.2 简化协议设计："下一次 step 自然推 tick_advanced，足以告知客户端"）
  2. **client `useRunStream`**（`@web/src/hooks/useRunStream.ts:96-174`）：状态机**仅靠 ws 推送驱动** status 切换。无 ws 事件 → status 永远 paused
  3. **Running.tsx auto-step useEffect**（`@web/src/routes/Running.tsx:75-93`）：仅 `status === "running"` 才启动 step loop
  4. **死锁**：status=paused → auto-step 不启动 → step 不发 → server 不推 tick_advanced → status 永远 paused
- **本质**：v0.2 协议设计的**对称性漏洞**——pause 推 `PausedEvent` 但 resume 不推对应事件，client 状态机依赖 ws 推送但没数据可拉。设计假设"下一次 step 推 tick_advanced 足以告知"忽略了 client side **auto-step 仅 status=running 才发**这个前置条件。
- **影响范围**：
  - 任何"暂停后想恢复"的用户操作流（核心交互）
  - 干预面板的 wasPaused=true 路径（drawer 提交后想 resume，理论上同样卡）—— 但 PR4.2 实测能 work，**因 InterventionDrawer 提交后由 Running.tsx 调 resumeMut + 隐式触发 ws 重连？**未深查（已修，问题消失）
  - 单步按钮工作（PR4-fix 已修）但走的是 step 路径不经过 resume，所以单步功能不受此 bug 影响
- **解法**（已落地，session 41 第 4 阶段）：与 PausedEvent **对称设计**——加 `RunResumedEvent` ws 事件，server resume 推、client 切 status=running。改动 5 处：
  1. `@server/api/v1/ws_events.py:113-137` 加 `RunResumedEvent` + `RunResumedPayload` + 加入 `WSServerEvent` 联合
  2. `@server/services/run_service.py:260-282` `resume()` 推 `RunResumedEvent`（仅 `was_paused=True` 时推，幂等）
  3. `@web/src/api/ws.ts:44-60,75-80,91-92,184-186` 加 typed schema + `onResumed` callback + handleMessage case
  4. `@web/src/hooks/useRunStream.ts:138-146` `onResumed` handler 切 `status="running"` + 清 `pausedInfo`
  5. `@tests/test_server_ws.py:117-178` 新建 `TestResumeBroadcast` 类 3 个单测 + 修原 `test_repeated_pause_no_duplicate_event`（resume 现在推 ws）
- **副发现 + 子修正**：调试中发现 `_broadcast_tick` 在 `paused_after=True` 时推 `every_tick` PausedEvent，service step 末尾又显式推 `manual` PausedEvent → **双推 + reason 错乱**。修：`_broadcast_tick` 加 `skip_paused_broadcast` 参数（`@server/services/run_service.py:290-302`），让 service step 包装路径自己接管 paused 推送。
- **验收**：`pytest 811 → 814 passed`（+3 单测），`playwright 13 step 1 passed 14.9s`（regression）
- **相关文件**：`@server/api/v1/ws_events.py:113-137`、`@server/services/run_service.py:260-302`、`@web/src/api/ws.ts:44-60`、`@web/src/hooks/useRunStream.ts:138-146`、`@tests/test_server_ws.py:117-178`
- **防再犯**：
  - **v0.2+ 协议设计纪律**：所有"状态变迁"（pause/resume/cancel/retry）都必须有**对称的 ws 事件**——client 状态机靠 ws 驱动，缺事件即死锁
  - **审视 D-017 §4 ws 事件清单**：补 `RunResumedEvent` 后是否还缺其他对称事件（如 cancel / abort / restart）？v0.3+ 设计时检查
  - **不要在协议设计中省事件**：即使"看起来下次 step 会带"，client side 可能根本没机会发"下次 step"

### [P3] 2026-04-29 v0.2 UI 单步功能与 v0.1 runtime.step() 语义错位（session 41 E2E 调试发现 → 同 session 修复）

**✅ 已修**（session 41 PR4-fix，server side 包装路线 1）：`@server/services/run_service.py:176-243` `RunService.step` 加 paused 单步包装：`if was_paused: resume → step → manual_repause + 注入 paused_after=True 到 broadcast result + 补推 PausedEvent(reason="manual")`。**关键避坑**：仅 server `is_paused()`+`pause()` 不够——还要把 broadcast 的 TickResult.paused_after 改 True（`result.model_copy(update={"paused_after": True})`），否则 client `useRunStream.onTick` 看到 `paused_after=False` 会把 status 切 running 触发 auto-step useEffect race，把 run 一路跑到 finished（实测过——session 41 spec step 6 第 1 版强断言时这个 race 跑到 /finished 页）。验收：`tests/test_server_runs.py` 加 2 单测，全 **811 passed**；E2E spec step 6 从弱断言（tick≥1 best-effort）升级为强断言（paused click 单步 → tick++ + 仍 paused），13 step 1 passed 15.4s。

- **现象**：Playwright E2E spec 13 step 版的 step 6 用单步按钮（paused 状态）click 3 次推进 tick，每次 click 后 `tick 1/5` 文本不变，`step button` `[active]` focus 但 server 实际未推 `tick_advanced`。日志看 server 返回 4xx error，前端 toast 一闪即过没截到。
- **根因链**：
  1. **UI 设计**（`@web/src/components/ControlBar.tsx:116`）：`disabled={!isPaused}` —— 单步按钮**仅 paused 时启用**，对应用户故事「暂停后单步看一眼」
  2. **server `step` 路由**（`@server/services/run_service.py:176-192`）：`runtime.step()` 直接调用，**不前置 resume**
  3. **v0.1 runtime**（`@core/runtime.py:380-381`）：`if self._paused: raise PausedError("Runtime 处于暂停状态；请先调用 resume()")` —— **paused 时禁止 step**
  4. server `PausedError` → 4xx → `useStep.onError` toast → client tick 不变
- **本质**：v0.1 内核「paused = 完全阻塞」与 v0.2 UI「paused = 可单步审查」两种语义直接冲突。PR4.1 设计 ControlBar 时漏了 v0.1 接口契约校验。
- **影响范围**：
  - 单步按钮在 paused 时 click 全部失败（用户操作流断裂）
  - 测试中 step 6 强行用单步推进 tick 链路全断；改为弱断言（auto-step 推进的 tick≥1）兜底
  - 不影响 auto-step / pause / resume / 干预 / 副区折线 / prompt modal 等路径
- **修复选项**（按上游修最小排序）：
  1. **server side（推荐）**：`RunService.step` 增加包装：`if runtime.is_paused(): runtime.resume(); result = runtime.step(); runtime.pause(); return result` —— 5-10 行 server 改动；UI/v0.1 runtime 不变；保持 paused 状态对客户端透明
  2. **runtime side**：`step(force_single: bool = False)` 参数；force=True 时跳过 paused 检查；end 自动恢复 _paused 标志 —— v0.1 内核改动 + step_once 路径单测
  3. **UI side**：Running.tsx onStep 改为 `await resume + step + pause` 三调用 —— 三 round-trip，最不优雅
- **临时绕开**（已落地 spec）：spec step 6 改为 best-effort 验证 step 5 期间 auto-step 已推进的 tick≥1 + EntityCard diff 箭头 best-effort；不强制单步
- **相关文件**：`@core/runtime.py:380-381`（PausedError 抛点）、`@server/services/run_service.py:176-192`（step 路由 + _broadcast_tick）、`@web/src/components/ControlBar.tsx:113-119`（单步 button + disabled 逻辑）、`@web/src/hooks/useStep.ts`、`@web/tests/e2e/mockup-flow.spec.ts:130-141`（弱断言绕开）
- **防再犯**：
  - **v0.2 server 接口设计前**——必须**走完一遍 v0.1 runtime 接口契约**（`docs/02-design/运行时与事件轨迹设计.md` 第三节）；任何用户操作映射到 v0.1 API 时检查"paused 时是否允许 X"
  - **PR4-fix（待开）**：server 侧补 step 包装。补完后扩 spec 加 step 6.5: `paused 状态点单步 → tick++ → 仍 paused`，强断言取代弱断言
  - **架构纪律**：v0.2 server 是 v0.1 内核的**包装层**，要么**遵守 v0.1 契约**，要么**显式包装兼容**；不能让 UI 直接踩 v0.1 raw API 不一致

### [P3] 2026-04-29 写 Playwright E2E 凭印象假设页面文案/路由/数据，5 处 selector 全错（session 41）

- **现象**：mockup §6 全流程 Playwright E2E spec 一稿写完跑，**4 次 fail 4 个不同 step**，每次都是 selector 不匹配。
- **根因**：写 spec 时直接按 mockup ASCII 的"心理模型"猜测 selector，没有去查实际代码 / API 返回 / 文件名。5 处错误：
  1. **H1 文案**：以为是 `Polisim`（topbar），实际 Gallery `<h1>` = `gallery.title` = "场景画廊"
  2. **scenario id**：以为是 `minimal_market`（**目录名**），实际 server 返回 `scenario.id` = `walkthrough-min`（来自 `scenarios/minimal_market/scenario.yaml` 第 19 行）—— 目录名 ≠ scenario.id
  3. **entity 文案**：以为跑前页用 `entity.id`（如 `company_a`），实际 `ScenarioIntroPanel:77` 用 `entity.name ?? entity.id`，scenario.yaml 给了 `name: A 公司` → 跑前显示 "A 公司"，跑中页 EntityCard 才用 entity.id
  4. **没有 company_b**：以为 minimal_market 有两个公司，实际是 `company_a` + `regulator_main`（A 公司 + 监管方）
  5. **路由**：以为 Gallery → 跑前是 `/scenarios/:scenarioId/pre-run`，实际是 `/runs/:runId/intro`（Gallery 触发 useCreateRun + navigate `/runs/${runId}/intro`）
- **解法**（已落地）：测试通过后总结——**写 selector 前先查 3 个权威源**：
  1. `useScenarios` hook 实际返回（`curl /api/v1/scenarios` 看 JSON `id`/`name`）
  2. 目标组件源码（如 `ScenarioIntroPanel.tsx:77` 显示 `entity.name ?? id`）
  3. `react-router` route 配置（main.tsx 实际 path 而不是 mockup 文字描述）
- **相关文件**：`web/tests/e2e/mockup-flow.spec.ts`（5 处修复）、`scenarios/minimal_market/scenario.yaml:19`（id=walkthrough-min）、`web/src/components/ScenarioIntroPanel.tsx:77`（displayName fallback）
- **防再犯**：
  - 写 E2E 测试 selector 前 **先 manual goto + F12 看 DOM**，或拉 server API 看实际数据
  - mockup 文档是"产品意图"，**真实文案 = i18n.json + 组件 source 双查**
  - playwright 失败时**先看 `error-context.md`**（playwright 自动生成 page snapshot）—— 比反复改 selector 快 10 倍

### [P3] 2026-04-29 recharts 装包用 `--legacy-peer-deps` 漏装 react-is，PR4.3 跑中页直接 vite plugin 报错（session 41）

- **现象**：PR4.3 装 recharts 后跑中页打开 → vite 抛 `[plugin:vite:import-analysis] Failed to resolve import "react-is" from "node_modules/.vite/deps/recharts.js"`，全页 error overlay 遮挡，React app 完全不渲染。**PR4.3 提交时 tsc 0 错 + 路由 200 没暴露此 bug**（vite 优化时才解析 recharts 内部依赖；浏览器实际 import 才触发）。
- **根因**：recharts@2.x 的 `package.json` 把 `react-is` 列为 dependency 而非 peerDependency。但用 `npm install recharts --save --legacy-peer-deps` 时 npm 漏装传递依赖（react-is 应自动装但因 legacy-peer-deps 跳过部分校验路径，未拉到）。**vite 静态分析 recharts.js 发现 `import { isFragment } from "react-is"` → 找不到 → plugin error**。
- **解法**：手动 `npm install react-is --save --legacy-peer-deps` 补装；kill vite 5173 + 重启触发 deps re-optimize。
- **相关文件**：`web/package.json`（含 react-is dep）、PR4.3 第 69 条目漏掉的依赖项
- **防再犯**：
  - **装第三方图表库 / DOM 库 / d3 系列时**——装完后**必跑一次 vite dev** 确认无 plugin error，再认为装包成功（不能仅靠 `npm install` exit 0）
  - 同样规则：装 cytoscape（PR4.5 计划）/ react-markdown（PR5 计划）时也先验证
  - 若 `--legacy-peer-deps` 装的包在 vite 报"找不到 X"，**先单独装 X**，再考虑其他根因

### [P3] 2026-04-29 openapi-typescript v7 把 Pydantic v2 default 字段视为 TS required（session 37）

- **现象**：PR3 实施 `routes/Gallery.tsx` 调 `useCreateRun.mutateAsync({ scenario_path })` 报 TS 编译错：`类型 "{ scenario_path: string; }" 中缺少属性 "llm_provider"`。但 server 端 Pydantic schema `CreateRunRequest.llm_provider: Literal["mock", "openai"] = Field(default="mock")` —— 调用方理论上可以省略。
- **根因**：FastAPI 把 Pydantic v2 模型转 OpenAPI schema 时，**有 default 的字段仍会进入 `required` 数组**（FastAPI/Pydantic 视角："用户可以省略，但模型保证有值"）。openapi-typescript@7 看到 `required` 就生成非 optional TS 字段（`llm_provider: "mock" | "openai"` 而非 `llm_provider?:`）。这是 openapi-typescript 与 Pydantic 哲学差异——工具层不区分 "API 必填" 与 "模型必有"。
- **影响范围**：
  - `CreateRunRequest`：`llm_provider` / `runtime_config` 等 default 字段都会命中
  - 任何 server 端 Pydantic 模型用 `Field(default=...)` 的 default 值字段
  - PR4 干预面板 / 高级选项接通业务时再遇（`Intervention` 子字段 + `RuntimeConfig` 字段）
- **解法**（PR3 已落地，最小改动）：调用方显式传 default 值。`Gallery.handleStartProduction`：
  - `await createRun.mutateAsync({ scenario_path: scenario.path, llm_provider: "mock" })`
- **未来选项**（按上游修最小排序）：
  1. 现状（已采用）：调用方显式传 —— 0 改 hook / server，简单稳
  2. `useCreateRun` hook 包默认值——所有调用方省心，但 hook 不再"纯薄包装"
  3. server 改 `llm_provider: Literal[...] | None = Field(default=None)` + 路由 service 填 default —— 让 OpenAPI 真把它列 optional；侵入后端
  4. 改 openapi-typescript 配置——v7 似乎无 flag 让 default 字段自动 optional；可能需要 patch generator
- **相关文件**：`web/src/routes/Gallery.tsx:60-73`（已落地的显式传值）、`web/src/api/types.gen.ts:716-756`（生成的 TS 类型）、`server/api/v1/schemas.py:CreateRunRequest`
- **防再犯**：
  - PR4+ 用任何 hook 调用方传 CreateRunRequest / Intervention / RuntimeConfig 等含 default 字段的 Pydantic 模型时，**先看 types.gen.ts 实际类型**而不是看 Pydantic 源
  - 未来若有可观察 default 字段冲突频次提升（>5 次），考虑升级到方案 2 或 3

### [P3] 2026-04-29 mockup §8.3 默认 `gen:types` URL 与 server 实际 openapi.json 路径不一致（session 36）

- **现象**：PR2 第一次跑 `npm run gen:types` 报 `ResolveError: Failed to load http://localhost:8000/openapi.json: 404 Not Found`。Server 已正常起在 8000，但 `GET /openapi.json` 返 404。
- **根因**：`server/app.py:139` 的 FastAPI 配置 `openapi_url="/api/v1/openapi.json"`（v0.2 server 全部业务路径都在 `/api/v1` 前缀下，`openapi.json` 也跟随），与 mockup §8.3 默认假设的 `/openapi.json` 不一致。session 34 第二轮 API 反向校验（mockup §10）发现 35 项偏差但**漏抓本项**——它在 §8.3 技术约定段，不在 §10 反向校验对比表里。
- **影响范围**：
  - 本 session（PR2）首次跑 `gen:types` 必命中——已发现 + 已修
  - 未来任何 fork / 重新部署 Polisim 后跑 `npm run gen:types` 不会再命中（脚本已修）
  - 极少数情况：用户手动改 `package.json` 想用其他 openapi.json 来源（如另一台 host）—— 用 `VITE_API_BASE` env var 就够
- **解法**（已落地）：修 `web/package.json` 的 `gen:types` 脚本：
  ```json
  "gen:types": "openapi-typescript http://localhost:8000/api/v1/openapi.json -o src/api/types.gen.ts"
  ```
- **相关文件**：`web/package.json:11`（gen:types 脚本）、`server/app.py:139`（openapi_url 配置）、`docs/02-design/v0.2-前端-UI-mockup.md` §8.3（待回填修正）
- **防再犯**：
  - mockup §10 反向校验下次扩展时，把"§8 技术约定"段也纳入校验范围（不仅校 endpoint 列表，还校配置 URL / 默认值）
  - 未来若 server 改 `openapi_url` 路径（不太可能；`/api/v1` 前缀很稳定），需同步改 `web/package.json` `gen:types` 脚本
  - 文档与代码漂移时**优先信代码**——server `app.py` 才是 ground truth，mockup §8.3 是辅助

### [P3] 2026-04-29 web/ 模板 TS 6.0 与 openapi-typescript@7 peer dep 冲突（session 35）

- **现象**：`npm install -D openapi-typescript` 在新 Vite 8 + React 19 模板创建的 `web/` 里报 `ERESOLVE`：模板自带 `typescript@~6.0.2` (devDep)，但 `openapi-typescript@7.13.0` 的 peer 是 `typescript@^5.x`。`tailwindcss / postcss / autoprefixer` 同批次安装一并失败（命令是原子的）。
- **根因**：Vite 8（2026-04 release）模板提前 bump TypeScript 到 6.0；openapi-typescript 7.13.0 还在 TS 5.x 兼容窗。peer dep 是 npm 强约束，整批 install fail。
- **解法**（已落地）：`npm install -D --legacy-peer-deps tailwindcss@^3 postcss autoprefixer openapi-typescript`——绕开 peer 校验。openapi-typescript 是 type-generation 工具（读 OpenAPI JSON 输出 .ts），TS 6 在类型层面是 5.x 超集，不会触发实际语法不兼容；类型生成产物（PR2 才会跑）落 `src/api/types.gen.ts` 也只用基础 type aliases（不依赖 TS 6 / 5 差异）。
- **影响范围**：
  - PR1 build / dev server 0 影响（PR1 不跑 gen:types）
  - PR2 跑 `npm run gen:types` 时若 openapi-typescript 内部用了不兼容 TS 6 的 API 才会显形——届时再决定
  - 未来若 openapi-typescript 升 8.x 适配 TS 6，可去 --legacy-peer-deps；若 Vite 模板回退 TS 5（不太可能），同样可去
- **相关文件**：`web/package.json`（已记 openapi-typescript 7.13.0 + typescript 6.0.3）、`web/package-lock.json`
- **防再犯**：
  - 后续 `npm install -D` 若再撞 TS peer 问题，**首选 `--legacy-peer-deps`**——type 层面的 peer 警告通常无害
  - PR2 跑 `gen:types` 时若产物有真实运行时错（不是 type warning），再升级处理（升 openapi-typescript 8.x prerelease / 降 TS 5.x / 报 upstream issue）
  - 不要因 peer 警告就**升级 / 降级 TypeScript**——会牵连 ESLint / TS 编译器本身配置

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
