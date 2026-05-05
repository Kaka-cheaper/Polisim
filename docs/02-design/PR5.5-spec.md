# PR5.5：跑完页副区实施 spec

> **位置**：`docs/02-design/PR5.5-spec.md`
>
> **创建时间**：session 42 初（2026-05-05）
>
> **本文档性质**：**pre-implementation spec**（不是 D-decision 级别——无新架构决策，仅整合 mockup §11.5 C7-C12 + §11.7 H8/H9/H10 到一份可直接落地的实施清单）
>
> **依赖 spec**：`docs/02-design/v0.2-前端-UI-mockup.md` §4.5 / §10.5 M1 / §10.5 M2 / §11.5 / §11.7 / `docs/02-design/decisions/D-017-v0.2-API契约与Server架构.md`
>
> **前置条件**：PR5（routes/Finished + NarrativeReport + FinishedMetricsCard）已交付（session 41 第 5 阶段）；PR4.5 cytoscape + cose-bilkent 装包 + RelationGraphLayout 已交付（session 41 第 6 阶段）

## 一、范围

本 PR 补齐 mockup §4.5 跑完页副区的 5 tabs 完整数据可视化 + events.jsonl 客户端下载。完成后 **v0.2 R 前端核心功能全部交付**，可对外演示全流程（画廊 → 跑前 → 跑中 → 跑完 → 数据审查）。

**本 PR 不做**：

- ❌ 重跑模式（ReplayPlayer 真正回放）——`ReplayPanel` tab 只做**静态 tick 时间轴 + 当前 tick 事件列表**，不做真正的"重新播放动画"（§9.7 留 v0.3+）
- ❌ 自定义场景 LLM 生成对话框（§4.1 C11 占位）
- ❌ server-side events.jsonl 文件下载 endpoint（§10.5 M2 明确客户端路径）
- ❌ 干预面板改动（PR4 完成）
- ❌ 4 段报告 Markdown 的"点击 tick 引用自动跳副区高亮"（§9.6 决议 B——只要可点击，不自动跳）

## 二、目录结构（新建 7 文件 + 修 3 文件）

```text
web/src/
  components/
    FinishedSidePanel.tsx          # 新建——副区容器 + tabs 切换
    AttributeChart.tsx             # 新建——📈 recharts 折线
    FinalRelationGraph.tsx         # 新建——🕸 cytoscape 静态图（复用 RelationGraphLayout 底层）
    EventDistributionChart.tsx     # 新建——📊 recharts bar
    ReplayPanel.tsx                # 新建——🎬 tick 时间轴 + 当前 tick 事件列表
    RawDataView.tsx                # 新建——📋 events.jsonl 前 200 行 + 下载按钮
  hooks/
    useDownloadEventsJsonl.ts      # 新建——客户端 Blob 下载
    useEvents.ts                   # 新建——GET /events 分页（H8）
    useSnapshot.ts                 # 新建——GET /snapshots/:tick（H9）
  routes/
    Finished.tsx                   # 修改——挂载 FinishedSidePanel 到右侧
  i18n/
    zh.json                        # 修改——+finished_side_panel.*
    en.json                        # 修改——同上
  tests/e2e/
    mockup-flow.spec.ts            # 修改——加 step 16-18
```

## 三、5 tabs 详细 wireframe + 数据源

### 3.1 📈 AttributeChart（默认选中 tab）

**wireframe**：

```text
┌─ 📈 属性折线 ────────────────────────────────────────┐
│  实体：[company_a ▼] [regulator_main ▼]              │
│  属性：[cash ▼] [reputation ▼] [☐ market_pressure]  │
│                                                       │
│  100 ┤                                                │
│      │ ●──●                                           │
│   80 ┤      ●──●                                      │
│      │           ●                                    │
│   60 ┤ ○──○──○──○─┐                                   │
│      │             ●                                  │
│   40 ┤──────────────                                  │
│      │                                                │
│    0 └──1──2──3──4──5────── tick                      │
│                                                       │
│  图例：● company_a.cash   ○ regulator.reputation     │
│  ── highlight tick 3（来自 NarrativeReport 点击）     │
└──────────────────────────────────────────────────────┘
```

**数据源**：

- **方式 A（首选）**：`useEvents(runId, { kind: "action_executed" })` 分页全拉 → 客户端 reduce 构造"每 tick 每实体每属性"的时间序列（Runtime 每次 action_executed 事件的 `payload.effects[].new_value` 含 attribute 变更，但**不含未变更 tick 的快照**）。问题：不变的 tick 无数据点 → 折线间断。
- **方式 B（备选）**：`useSnapshot(runId, tick)` 对每个 tick 逐个拉快照（`/runs/:id/snapshots/:tick`）。稳但 N 次 HTTP 调用（minimal_market 5 tick OK / 大场景 100 tick 慢）。
- **v0.2 决议（本 spec 采用）**：**方式 B**，理由：
  - 正确性：所有 tick 的快照都有完整 attribute state，折线连续
  - 性能：v0.2 所有 walkthrough 场景 ≤ 20 tick，5-20 次 HTTP 调用 <2s
  - 简单：无需在客户端重放 action_executed 事件构造状态
- **未来 v0.3+ 优化**：`GET /runs/:id/snapshots?from_tick=0&to_tick=N` 批量 endpoint（server 侧加）

**实施要点**：

1. `useEffect` 在 finalSnapshot.tick 已知后，循环调 `useSnapshot` 拉 tick 0 到 tick N 的快照 → 存 local state `snapshots: Snapshot[]`
2. 实体下拉 / 属性 checkbox 用 `useMemo` 从 finalSnapshot.entity_state_summary 提取所有可选 entity_id + attribute 名
3. recharts `<LineChart>` + `<Line>` 按选中的 entity × attribute 笛卡尔积画线
4. `highlightTick` prop 来自 NarrativeReport 点击 tick 引用 → 画一条垂直 `<ReferenceLine>` 在该 tick

**验收**：

- 跑完 minimal_market → 切到 📈 tab → 看到 company_a.cash 从 100 降到 40 的折线 + regulator_main 属性折线
- 点击实体下拉取消勾选 regulator → 折线消失
- 从 NarrativeReport 点 `[tick 3]` → 📈 tab 自动选中 + tick 3 位置出现黄色垂直 highlight 线

### 3.2 🕸 FinalRelationGraph

**wireframe**：

```text
┌─ 🕸 关系图 ─────────────────────────────────────────┐
│                                                      │
│   (alice) ───(75,信任)─── (bob)                      │
│      │                       │                       │
│   (62,关心)              (40,警惕)                    │
│      │                       │                       │
│     (charlie) ─(30,防范)────┘                         │
│                                                      │
│  时间轴：tick [0────●────N]  ← 拖动切换查看演化         │
│                                                      │
│  图例：> 70 绿 · 40-69 黄 · < 40 红（同 §4.3.2）      │
└──────────────────────────────────────────────────────┘
```

**数据源**：

- `useSnapshot(runId, selectedTick)` —— 用户拖时间轴改 `selectedTick` state
- 或 **方式 B 共享**：已有 AttributeChart 拉回的 `snapshots: Snapshot[]` → 按 `selectedTick` 从 array 取。推荐共享避免重复拉。

**实施要点**：

1. 底层复用 `layouts/RelationGraphLayout.tsx`——把 cytoscape stylesheet / node / edge 构造函数抽成 `components/RelationGraphBase.tsx`（重构），`RelationGraphLayout.tsx`（跑中）+ `FinalRelationGraph.tsx`（跑完）都调用
2. 时间轴 slider：`<input type="range" min={0} max={N} step={1} value={selectedTick}>`
3. 默认 `selectedTick = finalSnapshot.tick`（终态）

**风险**：`relation_state_summary` 可能为空（如 minimal_market 无 relations）→ 显示占位"此场景无 relation 定义" + tab 仍可点但内容灰

**验收**：

- 跑完 three_party_negotiation → 切 🕸 tab → 看到 3 节点 + 6 边终态
- 拖时间轴到 tick 0 → 边的颜色/粗细变（初态）
- 跑完 minimal_market → 切 🕸 tab → 显示占位（无 relation）

### 3.3 📊 EventDistributionChart

**wireframe**：

```text
┌─ 📊 事件分布 ───────────────────────────────────────┐
│                                                      │
│  按事件类型：                                         │
│    decision_proposed  ████████████ 15               │
│    action_executed    ██████████   12               │
│    relation_changed   █████         6               │
│    environment_changed ██           3               │
│    intervention_applied █           1               │
│                                                      │
│  按 actor：（点柱状切换维度）                          │
│    alice          ████████ 10                        │
│    bob            ██████   8                         │
│    charlie        ████     5                         │
│    [system]       ██       3                         │
│                                                      │
│  [切换维度] kind | actor                             │
└──────────────────────────────────────────────────────┘
```

**数据源**：

- `result.summary.events_by_kind: Record<EventKind, number>` —— `AnalysisResult.summary` 直出
- `result.summary.events_by_actor: Record<string, number>` —— 同上
- 两者都在 Phase A 产出，**必然可用**（无需等 Phase C enhance）

**实施要点**：

1. recharts `<BarChart layout="vertical">` 横向 bar（标签空间大便于事件名）
2. 维度切换：`useState<"kind" | "actor">("kind")` + 2 个 button
3. 点击 bar → prop `onBarClick?: (kind: EventKind) => void` —— PR5.5 本 PR **暂不实现**跳事件流（mockup §4.5 "点事件分布的某条 → 高亮事件流相关行" 依赖 ReplayPanel 的事件列表，留 v0.3+）

**验收**：

- 跑完 minimal_market → 切 📊 tab → 看到按 kind 的柱状图
- 点 [切换维度] actor → 柱状图改 actor 维度
- bar 长度与数值匹配（最大值 bar 占满）

### 3.4 🎬 ReplayPanel

**wireframe**：

```text
┌─ 🎬 重播 ──────────────────────────────────────────┐
│  时间轴： [0──────●────────────N]  tick 3 / 5      │
│  [◀ 上 tick] [▶ 下 tick] [⏮ 开头] [⏭ 结尾]        │
│                                                     │
│  当前 tick 事件（tick 3）：                         │
│  ─────────────────────────                          │
│  💭 alice 决定 reply_curious —— "对 bob 表达关注"   │
│  ✅ alice 执行 reply_curious → bob.trust +2        │
│  📈 alice → bob trust 55 → 57                      │
│  ℹ️ scheduled_event_triggered: 外部信号           │
│                                                     │
│  [跳过动画直接看终态] [开始自动播放 1x]              │
└─────────────────────────────────────────────────────┘
```

**数据源**：

- `useEvents(runId, { tick: selectedTick })` —— 按 tick 过滤（server `/events?tick=N`）
- 或从已拉回的全量 events（如 RawDataView 缓存）`filter(e => e.tick === selectedTick)`

**实施要点**：

1. `useState<selectedTick>(0)` + slider + ◀▶⏮⏭ 4 按钮（PR5.5 最简）
2. 当前 tick 事件列表复用 `components/event_templates.ts`（PR4.5 已有）—— 同 EventStreamLayout 的模板，但**按单 tick 渲染**
3. **不做**真正自动播放动画——只做"静态快进到指定 tick 看当时事件"
4. 按钮 [开始自动播放 1x] 的实现：`setInterval(() => selectedTick++, 1000)` 简版 —— 仅做跑中态感受，不与 main canvas 联动

**风险**：此 tab 需要拉每 tick 的事件 → 如共享全量 events（来自 RawDataView）则 0 额外调用；否则 N 次 API 调用。推荐：`useEffect` 一次性全拉 events 存 local state，被本 tab 和 RawDataView 共享。

**验收**：

- 跑完 minimal_market → 切 🎬 tab → tick 3 位置显示 3-5 条该 tick 事件
- 点 [◀ 上 tick] → 切到 tick 2 事件列表

### 3.5 📋 RawDataView

**wireframe**：

```text
┌─ 📋 原始数据 ──────────────────────────────────────┐
│  [📥 下载 events.jsonl]  进度 ████░░░░ 45%         │
│                                                      │
│  前 200 行预览（events.jsonl 格式）：                 │
│  ┌──────────────────────────────────────────────┐  │
│  │ {"tick":0,"kind":"decision_proposed","actor" │  │
│  │ _id":"alice","payload":{"action":{...}}}     │  │
│  │ {"tick":0,"kind":"action_executed","actor_id │  │
│  │ ":"alice","payload":{...}}                   │  │
│  │ {"tick":1,"kind":"decision_proposed",...}    │  │
│  │ ... (199 more)                                │  │
│  └──────────────────────────────────────────────┘  │
│  [展开全部（可能卡顿）]                              │
│                                                      │
│  总计：events=X / tick=N / 文件大小估算=Y KB         │
└─────────────────────────────────────────────────────┘
```

**数据源**：

- `useEvents(runId, {})` —— 分页全拉 → local state `allEvents: EventRecord[]`
- 预览渲染前 200 条

**实施要点**：

1. `<pre>` + monospace font 显示 JSON
2. 每条事件用 `JSON.stringify(event)`（单行）拼成 jsonl
3. 下载按钮触发 `useDownloadEventsJsonl.trigger()`（见 §四）

**验收**：

- 跑完 minimal_market → 切 📋 tab → 看到前 N 行（<200）JSON
- 点 [📥 下载] → 浏览器触发下载 `events_<runId>.jsonl`

## 四、useDownloadEventsJsonl hook 细节

**签名**（§11.7 H10）：

```ts
function useDownloadEventsJsonl(runId: string): {
  trigger: () => Promise<void>;
  progress: number; // 0-100
  downloading: boolean;
  error: string | null;
};
```

**实现**：

```ts
async function trigger() {
  setDownloading(true);
  setProgress(0);
  const allEvents: EventRecord[] = [];
  let offset = 0;
  const limit = 1000;
  while (true) {
    const res = await apiGet<EventsListResponse>(
      `/runs/${runId}/events?limit=${limit}&offset=${offset}`
    );
    allEvents.push(...res.events);
    offset += res.events.length;
    setProgress(Math.min((offset / res.total) * 100, 99));
    if (!res.has_more) break;
  }
  const jsonl = allEvents.map((e) => JSON.stringify(e)).join("\n");
  const blob = new Blob([jsonl], { type: "application/x-ndjson" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `events_${runId}.jsonl`;
  a.click();
  URL.revokeObjectURL(url);
  setProgress(100);
  setDownloading(false);
}
```

**风险**：

- **超大场景**（万级 events）客户端循环拉可能超时。v0.2 walkthrough ≤ 100 tick × ~10 events/tick = 1000 events OK
- 未来 v0.3+ 可加 server-side `/runs/:id/events.jsonl` 流式 endpoint（mockup §10.5 M2 已留口子）

## 五、i18n keys 清单

```json
{
  "finished_side_panel": {
    "tabs": {
      "attribute_chart": "📈 属性折线",
      "final_relation_graph": "🕸 关系图",
      "event_distribution": "📊 事件分布",
      "replay": "🎬 重播",
      "raw_data": "📋 原始数据"
    },
    "attribute_chart": {
      "entity_filter": "实体：",
      "attribute_filter": "属性：",
      "x_axis": "tick",
      "highlight_tick": "高亮 tick {{tick}}",
      "no_data": "暂无快照数据"
    },
    "final_relation_graph": {
      "time_axis": "时间轴",
      "tick_label": "tick {{tick}} / {{total}}",
      "no_relations": "此场景无 relation 定义"
    },
    "event_distribution": {
      "by_kind": "按事件类型",
      "by_actor": "按 actor",
      "switch_dim": "切换维度",
      "no_events": "无事件"
    },
    "replay": {
      "prev_tick": "◀ 上 tick",
      "next_tick": "▶ 下 tick",
      "first_tick": "⏮ 开头",
      "last_tick": "⏭ 结尾",
      "auto_play": "开始自动播放 1x",
      "stop": "暂停",
      "current_tick_events": "当前 tick 事件（tick {{tick}}）"
    },
    "raw_data": {
      "download": "📥 下载 events.jsonl",
      "progress": "进度 {{percent}}%",
      "preview_title": "前 {{n}} 行预览（events.jsonl 格式）",
      "expand_all": "展开全部（可能卡顿）",
      "summary": "总计：events={{total}} / tick={{ticks}} / 预估 {{kb}} KB",
      "downloading": "下载中..."
    }
  }
}
```

## 六、E2E spec 扩展（step 16-18）

当前 spec `tests/e2e/mockup-flow.spec.ts` 第一个 test 已走到 15 step（PR5 跑完页验证）。加 3 step：

### step 16：切换 5 tabs 全部可见

```ts
await test.step("step 16: 5 tabs switch and verify visible", async () => {
  // 验证默认 tab（📈 属性折线）已选中
  await expect(
    page.getByRole("tab", { name: /属性折线|Attribute/i })
  ).toHaveAttribute("aria-selected", "true");

  // 依次点 4 个其他 tab
  for (const tabName of [
    /关系图|Relation/i,
    /事件分布|Distribution/i,
    /重播|Replay/i,
    /原始|Raw/i,
  ]) {
    await page.getByRole("tab", { name: tabName }).click();
    await expect(
      page.getByRole("tab", { name: tabName })
    ).toHaveAttribute("aria-selected", "true");
    await page.waitForTimeout(300); // 等 recharts / cytoscape 渲染
  }

  await page.screenshot({
    path: `${SCREENSHOT_DIR}/14-finished-tabs-all-switched.png`,
    fullPage: true,
  });
});
```

### step 17：属性折线 tab 实体下拉 + highlight tick

```ts
await test.step("step 17: attribute chart interaction", async () => {
  await page.getByRole("tab", { name: /属性折线/i }).click();
  // 验证折线 svg 存在
  await expect(page.locator("svg.recharts-surface")).toBeVisible();
  // 验证至少 1 个实体 checkbox / select 可见
  await expect(page.getByText(/company_a/)).toBeVisible();
});
```

### step 18：点 [📥 下载] 触发浏览器下载

```ts
await test.step("step 18: download events.jsonl", async () => {
  await page.getByRole("tab", { name: /原始/i }).click();
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: /下载.*events|Download/i }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toMatch(/events_.*\.jsonl/);
});
```

**新增截图**：`14-finished-tabs-all-switched.png`（1 张；对应 step 16 末）

## 七、验收样例

按 `docs/01-requirements/验收标准.md` 第 6.1 模板：

```text
验收对象：PR5.5 跑完页副区
对应验收项：mockup §4.5 跑完阶段 5 tabs + §10.5 M2 events.jsonl 客户端下载
输入：pytest + playwright + 浏览器手动验证
执行方式：
  1. cd web && npm test（如有 unit test）
  2. cd web && npx playwright test（should pass 2 tests，test 1 从 15 → 18 step）
  3. npm run dev → 画廊 → minimal_market → 跑到完 → 切 5 tabs 全验证
实际输出：
  - playwright 2 passed（test 1 18 step / test 2 4 step / 14 截图）
  - 手动验证：5 tabs 全部可点；AttributeChart 折线显示；RawDataView 下载成功
是否通过：待实施后填
备注：暂不做 ReplayPlayer 真正播放（§9.7 留 v0.3+）；EventDistributionChart 点击 bar 不跳事件流（依赖 ReplayPanel 完整版）
```

## 八、实施顺序（session 42 推进）

1. **子步 1（30 min）**：写 3 新 hooks（`useEvents` / `useSnapshot` / `useDownloadEventsJsonl`）+ i18n keys 占位
2. **子步 2（30 min）**：写 5 tab 组件（`AttributeChart` / `FinalRelationGraph` / `EventDistributionChart` / `ReplayPanel` / `RawDataView`）
3. **子步 3（20 min）**：写 `FinishedSidePanel` 容器 + 挂到 `Finished.tsx` 主区右侧
4. **子步 4（30 min）**：playwright 加 step 16-18 + 跑 2 passed
5. **子步 5（10 min）**：浏览器手动验证 + 截图（如需）+ 更新 progress.md

**总预估**：2-3 小时（一个 session 可完成）

## 九、风险 & 回退

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| `useSnapshot` N 次 HTTP 慢 | 中 | 📈 tab 加载时间 >3s | 加 loading skeleton；v0.3+ 做批量 endpoint |
| cytoscape 底层重构（抽 RelationGraphBase）破 PR4.5 | 低 | 跑中页力导向图失效 | 重构完立跑 playwright test 2 回归 |
| recharts bar 横向 label 空间不够 | 低 | 长事件名截断 | 加 `tickFormatter` 或 tooltip 展开 |
| events.jsonl 下载超 10MB 触发浏览器警告 | 低 | 用户体验 | 加 "文件 >5MB 可能慢" warning；v0.3+ server 流式 |
| `useEvents` 分页 total 字段不准 → progress 算错 | 中 | 进度条显示异常 | fallback 到"已拉条数"显示 |

**回退策略**：若某 tab 实施卡住 >1h，可先交付其他 4 tabs + 该 tab 占位"施工中"（不 block PR 合入）。

## 十、完成后状态

**v0.2 R 前端核心功能 100% 交付**：

```text
画廊（PR3）→ 跑前（PR3）→ 跑中（PR4 + PR4.3 + PR4.5）→ 跑完（PR5 + PR5.5） ✅
```

**剩余 v0.2 R 支线**（可选）：

- D-018：Running.tsx layout 切换器（mockup §决策 7 deviation）
- PR6：客户演示打磨（桌面响应式 1024 / 平板 / 中英切换验证）
- 场景扩展：添加 2-3 个新 production scenarios（mockup §4.1 "3 个+" 目标）

**v0.2 正式 release 前要做**：

- **验收全表**：遍历 mockup §6 全 5 步 + 每步贴截图
- **CI 补**：playwright 在 GitHub Actions 上跑
- **README 补**：v0.2 启动指南（`python -m cli.serve` + `cd web && npm run dev`）
- **Git tag**：`v0.2.0` on main
