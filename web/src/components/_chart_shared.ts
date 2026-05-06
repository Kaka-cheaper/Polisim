/**
 * _chart_shared —— recharts 图表组件共用工具集。
 *
 * 抽离动机（session 43 架构清债 F6）：
 *   - MiniDashboard / AttributeChart 之间存在 ENTITY_PALETTE 与 collectNumericAttrs 重复
 *   - tooltip / cartesianGrid 风格也部分重复（保留各自 inline 写法，token 已统一）
 *
 * 设计纪律：
 *   - 文件名 `_xxx_shared` 前缀表示"内部共用工具"——不暴露给 routes / hooks
 *   - 仅 components/ 内的图表组件 import
 *   - 颜色值用 CSS variables `var(--polisim-line-N)` —— recharts 接受 var() 字符串
 */
import type { Snapshot } from "../api/schema";

/**
 * Polisim 业务色板（来自 design-system semantic tokens；循环用以区分实体）。
 *
 * 5 色循环——超出 5 实体时 modulo 复用；mockup §11.4 确认场景一般不超过 10 实体，
 * 5 色已足够区分；v0.3+ 可换 d3 chromatic schemes（PR4.3 评估过未做）。
 */
export const ENTITY_PALETTE: readonly string[] = [
  "var(--polisim-line-1, #3B82F6)",
  "var(--polisim-line-2, #10B981)",
  "var(--polisim-line-3, #F59E0B)",
  "var(--polisim-line-4, #EF4444)",
  "var(--polisim-line-5, #8B5CF6)",
];

/**
 * 推断 snapshots 集合中的所有 numeric attribute 名（来自最新 snapshot 而非 World Definition——
 * 允许场景对属性 schema 演化）。返回排序后的数组以保稳定渲染顺序。
 *
 * 用途：
 *   - MiniDashboard：跑中态从 useRunStream 累积的 snapshots
 *   - AttributeChart：跑完态从 useAllSnapshots 拉的全量 snapshots
 *
 * 行为：
 *   - 空 snapshots 返 `[]`
 *   - 仅检视末位 snapshot（性能优化；假设属性集合在跑中不会动态新增——v0.1 内核约束）
 *   - 仅 `Number.isFinite` 通过的值入选（NaN / Infinity / null / undefined 跳过）
 */
export function collectNumericAttributes(snapshots: Snapshot[]): string[] {
  const set = new Set<string>();
  const last = snapshots.at(-1);
  if (!last) return [];
  const summary = last.entity_state_summary ?? {};
  for (const attrs of Object.values(summary)) {
    if (!attrs) continue;
    for (const [k, v] of Object.entries(attrs)) {
      if (typeof v === "number" && Number.isFinite(v)) {
        set.add(k);
      }
    }
  }
  return Array.from(set).sort();
}
