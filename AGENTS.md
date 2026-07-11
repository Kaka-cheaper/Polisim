# AGENTS.md

> 这份文档是写给 **AI Agent（Cascade / Claude Code / Cursor 等）** 看的。
> 人类读者请先看 `docs/00-overview/如何使用这套文档与配置体系.md`。

## 一、你是谁、在做什么

你正在协助开发 **Polisim**——一个分层驱动的通用多实体仿真引擎。

项目当前处于**v0.1.1 全部交付 + 架构审查清债 + D-015 全量版完成**（截至 session 28）：

- Phase A：分析层纯规则核心（已完成）
- Phase B：接入真实 LLM 协议（B.0 / B.1 / B.2 / B.4 / B.6 已完成；B.3 协议级重试可选延后）
- Phase C：分析层 LLM 增强（已完成；session 26 加入世界概览 + 证据援引）
- v0.1.1 严谨化：D-011 / D-013 / D-014 / D-015 全量版 / D-016 均已交付
- 架构审查（session 27）：F1-F11 清债全量修复

**v0.2 阶段已启动**（session 29 起草 D-017 spec）：单仓库 + FastAPI WebSocket 后端 + React 实时态势前端。**读 `docs/02-design/decisions/D-017-v0.2-API契约与Server架构.md` 了解详细架构**。

剩余可选分支：B.3 重试 / walkthrough 扩章 / 新场景 / 第二阶段 LLM 辅助建模 PoC。**先读 `progress.md` 顶部“当前位置”段获取最新状态再行动**。

一句话说清项目本质：

> 用 **World Definition + Scenario + Rules + Runtime + Event Log + Analysis** 6 层架构（v0.2 补 **Server + Web** 两层变 8 层），让用户通过配置文件定义可推演的复杂世界，由 LLM 参与实体决策，全程可暂停、可干预、可解释。

## 二、每次进入项目，先做 3 件事

1. **读 `docs/00-overview/progress.md`**——知道上次做到哪、下次从哪开始
2. **读本文件后面的 MUST / MUST NOT 条款**——知道什么能做什么不能做
3. **读 `docs/03-implementation/pitfalls.md`**——避免重复踩坑

只有在用户明确提出新功能 / 大改动时，才需要进一步通读 `docs/` 下全部文档。

## 三、MUST（必须遵守）

### 3.1 文档优先级

当实现、设计、验收出现冲突时，按以下顺序决定谁说了算：

1. `docs/01-requirements/验收标准.md`
2. `docs/01-requirements/需求分析.md`
3. `docs/01-requirements/MVP场景定义.md`
4. `docs/02-design/` 下各设计文档
5. 具体实现代码

**实现代码不是验收依据，验收标准才是**。

**v0.2+ 补充规则**（session 41 末加，pitfalls.md P5 教训沉淀）：

- **字段名 / enum 值冲突时**，优先级高于上面 5 项——以 **schema 为准**：
  - server-side 事实源：`models/*` Pydantic 类（`Field(...)` 描述）
  - client-side 事实源：`web/src/api/types.gen.ts`（`openapi-typescript` 自动从 OpenAPI 生成）+ `web/src/api/schema.ts`（人写的别名层）
- 写 client 代码涉及 enum / 字段名 / payload 结构时**必须先 grep schema 确认实际值**，不要从 mockup 文字猜
- mockup（`docs/02-design/v0.2-前端-UI-mockup.md`）只作 wireframe + 用户故事 + 校准表参考，**具体字段名以 schema 为准**
- 这条规则优先级最高的原因：schema 是 server-client 契约的事实源，错了直接跑不起来；mockup 错了只是产品意图与实现 drift

### 3.2 六层架构边界

每一层只能做自己的事，跨层污染立即拒绝：

- `World Definition` 只定义"允许什么存在"，不定义实例、不写业务规则
- `Scenario` 只定义"本次仿真是什么"，不定义新类型
- `Rules` 只定义"动作如何生效"，不推进时间
- `Runtime` 只推进 tick、调度、调用规则层，**不在代码里写死业务逻辑**
- `Event Log` 只记录事实，不做分析
- `Analysis` 只读轨迹和快照，不改状态

### 3.3 实现落点必须对齐 `实现映射设计.md`

新建代码文件前，先查 `docs/02-design/实现映射设计.md` 第四节，确认落点：

**v0.1 内核层**（不变）：

- World Definition → `schemas/` + `models/world_models.py` + `core/definition_loader.py`
- Scenario → `schemas/` + `models/scenario_models.py` + `core/scenario_loader.py`
- Rules → `rules/base.py` + `rules/minimal_market.py`
- Runtime → `models/runtime_models.py` + `core/runtime.py`
- Event Log → `core/events.py`
- LLM 协议 → `models/llm_models.py` + `core/llm_policy.py`
- Analysis → `core/analysis.py`
- 系统配置 → `config/*.yaml` + `models/config_models.py`
- 运行入口 → `cli/run.py`

**v0.2 Server + Web 层**（D-017，session 30+ 实施）：

- API routes → `server/api/v1/routes/*.py`（routes / services / registry 三层抽象）
- API errors → `server/api/v1/errors.py`（`SimEngineError` → HTTP 状态码映射）
- WebSocket 事件 → `server/api/v1/ws_events.py`（typed 消息 schema）
- 业务服务层 → `server/services/*.py`
- Runtime 注册表 → `server/runtime_registry.py`
- FastAPI 应用 → `server/app.py`
- CLI serve 子命令 → `cli/serve.py`
- 前端 → `web/`（Vite + React + TS + Tailwind）

**v0.2 数据 schema 复用纪律**：

- response_model 直接用 `models/*` 中的 Pydantic（`EventRecord` / `Snapshot` / `TickResult` / `AnalysisResult` / `PromptContext` / `Intervention`）
- **不新建** `server/api/schemas.py` 翻译层——避免同步成本（session 27 F3 漂移教训）
- **v0.2 新增平台专有 schema** （CreateRunRequest / ErrorResponse / WSEvent 等）落点在 `server/api/v1/`——不侵入 `models/`

不要自己新发明目录。

### 3.4 实现顺序必须对齐

按 `docs/02-design/实现映射设计.md` 第五节的 6 步顺序推进：

1. ~~配置校验与加载~~ ✅
2. ~~Runtime 最小骨架~~ ✅
3. ~~Rules 最小骨架~~ ✅
4. ~~最小示例跑通~~ ✅
5. ~~接入 LLM 决策协议~~ ✅（含 Phase B 子项 B.0/B.1/B.2/B.4/B.6；B.3 重试可选）
6. ~~分析层~~ ✅（含 Phase A 纯规则 + Phase C LLM 增强）

**全 6 步主路径已通 + v0.1.1 严谨化全部交付 + D-015 全量版完成**。

**v0.2 阶段项目**（D-017 起草中，session 30+ 实施）按以下 5 步推进：

7. **API contract spec 起草** ✅（session 29：`docs/02-design/decisions/D-017-v0.2-API契约与Server架构.md`）
8. **UI mockup**（session 30：文字 wireframe + 反向校验 D-017 完整性）
9. **Server 骨架 + 路由 + service + error map**（session 31：不含 WebSocket）
10. **WebSocket + stream service + 多并发 registry**（session 32）
11. **React 前端**（session 33+：预计 3-5 session）

**剩余可选分支**（不介入 v0.2 主路径）：B.3 重试 / walkthrough 扩章 / 更多场景 / 第二阶段 LLM 辅助建模 PoC。除非用户明确要求跳步或开支线，否则不要主动启动新工作。

### 3.5 每次完成一项实现，必须给验收证据

按 `docs/01-requirements/验收标准.md` 第 6.1 节模板记录：

```text
验收对象：
对应验收项：（引用验收标准第 X.Y 节）
输入：
执行方式：
实际输出：
是否通过：
备注：
```

不接受"代码已写"、"理论上可以"、"看起来没问题"作为验收依据。

### 3.6 每次 session 结束前

- 如果有进展：更新 `docs/00-overview/progress.md`
- 如果踩了坑或发现陷阱：追加到 `docs/03-implementation/pitfalls.md`
- 如果有未决定的设计问题：写进 `progress.md` 的"待决策"段

### 3.7 代码风格

- 严格遵循现有 `models/world_models.py` 的风格：Pydantic v2 + `ConfigDict(extra="forbid")` + 中文 docstring + `Field(..., description=...)`
- 模块顶部必须有 docstring，说明该模块的职责边界与**不负责什么**
- 永远不要在类型声明里写 `# type: ignore` 之类的临时绕过

## 四、MUST NOT（禁止做的事）

### 4.1 禁止跨层污染

- ❌ 在 `core/runtime.py` 里硬编码某场景的激活规则（必须从 `World Definition.activation` 读）
- ❌ 在 `core/runtime.py` 里解释动作效果（必须调 `Rules`）
- ❌ 让 LLM 直接修改状态（只能返回 `ActionProposal`，由 `Runtime + Rules` 落地）
- ❌ 在 `Scenario` 文件里放规则逻辑
- ❌ 在 `World Definition` 里放实例数据

### 4.2 禁止第一版做的事

明确禁止，不要"顺手帮个忙"：

- ❌ 规则 DSL（见 `规则层设计.md` 第六节）
- ❌ 分布式运行、跨进程消息总线（见 `运行时与事件轨迹设计.md` 第十三节）
- ❌ 回滚型事件溯源
- ❌ 自动建模助手 / 一句话生成 YAML（见 `LLM辅助建模方案.md`：第一版只做引导式）
- ❌ 语义增强层 / 知识图谱（属于第三阶段）
- ~~❌ UI、可视化大屏~~——v0.2 阶段已解禁，按 D-017 设计实现 React 实时态势面板
- ❌ 多场景模板库
- ❌ 参数搜索 / 批量实验框架

### 4.3 禁止造新文件/目录的情况

- ❌ 在 `models/` 里新建 `*_schema.py`——schema 走 JSON Schema 文件，Pydantic 模型走 `*_models.py`
- ❌ 新建顶层目录——所有新增落点必须对应 `实现映射设计.md` 第三节的结构（v0.2 已预留 `server/` + `web/`）
- ❌ 新建 `utils/` 之类的垃圾桶目录
- ❌ 在没看过对应设计文档前，新建 `core/` 下的新模块
- ❌ 在 v0.2 server 层新建 `server/api/schemas.py` 翻译层（D-017 明确反模式）——直接复用 `models/*` 作为 response_model

### 4.4 禁止的验收方式

- ❌ "我写好了，你跑一下看看"
- ❌ 不贴输入/输出就声称通过
- ❌ 仅靠人工读代码判断完成度（见 `验收标准.md` 第十八节）

### 4.5 禁止的通用 AI 习惯

- ❌ 创建 README 之外的自娱自乐型 `.md` 文件（进度/踩坑只用本文件指定的两份）
- ❌ 在代码里写"TODO"而不在 `progress.md` 里登记
- ❌ 不读现有 `models/world_models.py` 就写新 model
- ❌ 把 schema 和 Pydantic 模型的约束写得不一致（两者必须等价）
- ❌ 在 debug 阶段大改架构——先在 `pitfalls.md` 记录现象

## 五、上下文恢复快速通道

如果你是**新开的 session**，按下面顺序 30 秒内进入状态：

1. 读 `AGENTS.md`（本文件）
2. 读 `docs/00-overview/progress.md` 的"当前位置"和"下一步"段
3. 读 `docs/03-implementation/pitfalls.md` 的最近 5 条
4. 用户会告诉你本次任务，你再按任务决定读哪些设计文档

这 4 步总 token 预算应 < 4k。如果远超，说明 `progress.md` 或本文件已经膨胀，需要精简。

## 六、文档导航速查

| 我想知道 | 去哪看 |
|---|---|
| 项目是什么、为什么做 | `docs/00-overview/可用性与价值评估.md` |
| 整体架构与 6 层关系 | `docs/00-overview/如何使用这套文档与配置体系.md` |
| 当前开发阶段 | `docs/00-overview/开发流程.md` |
| 要做什么、优先级 | `docs/01-requirements/需求分析.md` |
| 第一版做什么场景 | `docs/01-requirements/MVP场景定义.md` |
| 怎么证明做完了 | `docs/01-requirements/验收标准.md` |
| 当前有哪些风险 | `docs/01-requirements/需求分析审查.md` |
| World / Scenario 文件怎么写 | `docs/02-design/世界定义文件格式设计.md` / `场景文件格式设计.md` |
| 规则 / Runtime / LLM / Analysis 怎么设计 | `docs/02-design/` 对应文件 |
| 设计怎么映射成代码 | `docs/02-design/实现映射设计.md` |
| 最小例子长啥样 | `docs/01-requirements/最小示例Walkthrough.md` |
| LLM 辅助建模长期规划 | `docs/00-overview/LLM辅助建模方案.md` |
| 视觉设计系统（DESIGN.md spec） | `DESIGN.md`（仓库根；与本文件并列） |

> **DESIGN.md 是什么**：基于 Google Stitch / `google-labs-code/design.md` 开源 spec 的 Polisim 视觉系统正式声明（YAML front matter tokens + 8 节 Markdown rationale）。**任何接手 UI 工作的 agent（重设计页面 / 加新场景 layout / 写新组件）必须先读它**——它取代了散落在 `tokens.css` + mockup §8.4 的视觉规范。Token 实际值的事实源仍是 `web/src/styles/tokens.css`；DESIGN.md 是给 AI agent 读的"为什么 + 怎么用"层。

## 七、本文件与 Harness 的关系

本文件是 Harness（<https://github.com/xwtro0tk1t-cloud/harness>）"Layer 1 知识管理 + Layer 2 架构约束"的极简落地版。

项目选择**不安装 Harness**，原因：

1. Harness 的 Hook 层只在 Claude Code 有效，Windsurf 用不上
2. Polisim 的文档体系已足够完整，再套一层会覆盖现有结构
3. 本文件 + `pitfalls.md` + `progress.md` 三件套已能覆盖 Harness 对本项目的 70% 价值

如果未来切换到 Claude Code 作为主开发环境，可以再考虑装 Harness 补上 Hook 强制门禁。

<!-- BEGIN: CodeSee integration -->
## CodeSee 功能图维护

本项目接入了 CodeSee — 把功能逻辑以语义流程图呈现的工具。

### 触发规则

**触发 1：首次扫描**
若 `.codesee/features.json` 不存在或缺少 `version` 字段：
→ 执行 `.codesee/prompts/scan.md`（会自动判断走 light / heavy / planning 哪一档）

**触发 2：每轮代码改动后**
完成改动后，在回复用户前主动：
→ 执行 `.codesee/prompts/sync.md`

跳过条件：纯样式/重构/重命名（无语义变化），或用户明确要求跳过。

**触发 3：用户显式要求**
"刷新功能图""更新 codesee""扫一下" → 按上述策略执行。

### 项目阶段

- **SDD 项目**（有 `.specify/`、`.trellis/`、`.bmad-core/` 等 spec-driven 目录）→ 走 sdd 模式，从 spec/PRD 正向投影
- **规划阶段**（只有文档）→ 走 planning 模式，产出 `tags: ['planned']` 的功能图
- **实现阶段**（有代码）→ 走 light/heavy 模式，产出正式功能图
- **混合阶段**（部分实现）→ sync 自动把 `planned` 升级为 `implemented`

### Checkpoint 协议

大任务（涉及 5+ 文件）必须拆 checkpoint，每完成一个逻辑闭环立即 sync，不要等全部写完才一次性更新。全部完成后做最终整体核查（覆盖度、关系、epic_flow、refs、校验器）。详见 `.codesee/prompts/sync.md`。

### 核心约束

- ❌ 不修改 `.codesee/prompts/` 与 `.codesee/scripts/` 下的文件
- ❌ 不修改 `locked: true` 的 feature
- ❌ 不重命名既有 id（废弃用 tags: ['deprecated']）
- ❌ 不跳过校验（`node .codesee/scripts/validate-features.mjs`）
- ✓ step.name 必须中文动词短语，不要写代码标识符
- ✓ flow.kind 必填，不能省略
- ✓ 写入后必须跑校验，退出码 1 必须修复

### 参考文件

- Schema + 示例：`.codesee/prompts/_schema.md`
- 规则详情：`.codesee/prompts/_rules.md`
- 扫描：`.codesee/prompts/scan.md`
- 同步：`.codesee/prompts/sync.md`
- 校验：`.codesee/scripts/validate-features.mjs`
- 数据：`.codesee/features.json`

> 执行 scan/sync 前先告诉用户你要做什么。
<!-- END: CodeSee integration -->
