/**
 * Schema type aliases —— 把 `types.gen.ts` 自动生成的 `components["schemas"][X]` 简化为
 * 业务可直接 import 的 type。
 *
 * **设计纪律**（mockup §11 + AGENTS.md 3.3）：
 *   - 业务层（hooks / components / routes）一律从本文件 import type
 *   - 不直接 `import type { components } from "./types.gen"`——通过本文件包一层
 *   - 不在本文件添加 server schema 之外的"DTO"——平台专有类型放 `client.ts` / `ws.ts`
 *
 * **同步策略**：每次 server Pydantic schema 变化后跑 `npm run gen:types`；本文件按需
 * 加 alias（不是所有 100+ schemas 都暴露——只暴露 routes / hooks 实际用到的）。
 */
import type { components, operations } from "./types.gen";

export type Schemas = components["schemas"];
export type ApiOperations = operations;

// === Run 元信息 ===
export type RunDetail = Schemas["RunDetail"];
export type RunSummary = Schemas["RunSummary"];

// === 控制响应 ===
export type PauseResumeResponse = Schemas["PauseResumeResponse"];

// === 运行时数据 ===
export type TickResult = Schemas["TickResult"];
export type Snapshot = Schemas["Snapshot"];
export type WorldState = Schemas["WorldState"];
export type EventRecord = Schemas["EventRecord"];
export type Intervention = Schemas["Intervention"];

// === 静态结构（World / Scenario 嵌套子类型） ===
export type WorldDefinition = Schemas["WorldDefinition"];
export type EntityTypeSchema = Schemas["EntityTypeSchema"];
export type RelationTypeSchema = Schemas["RelationTypeSchema"];
export type Scenario = Schemas["Scenario"];
export type ScenarioInfo = Schemas["ScenarioInfo"];
export type EntityInstance = Schemas["EntityInstance"];
export type ScheduledEvent = Schemas["ScheduledEvent"];

// === 配置 ===
export type CreateRunRequest = Schemas["CreateRunRequest"];
export type AnalyzeRequest = Schemas["AnalyzeRequest"];

// === 元信息 ===
export type ScenarioSummary = Schemas["ScenarioSummary"];
export type HealthResponse = Schemas["HealthResponse"];

// === 分析层 ===
export type AnalysisResult = Schemas["AnalysisResult"];
export type KindStat = Schemas["KindStat"];
export type ActorStat = Schemas["ActorStat"];
export type TurningPoint = Schemas["TurningPoint"];
export type EntityComparison = Schemas["EntityComparison"];

// === PR5.5 副区数据 ===
export type EventListResponse = Schemas["EventListResponse"];
export type SnapshotsListResponse = Schemas["SnapshotsListResponse"];
