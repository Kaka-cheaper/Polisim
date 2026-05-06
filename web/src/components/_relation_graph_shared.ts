/**
 * _relation_graph_shared —— RelationGraphLayout 与 FinalRelationGraph 共用工具集。
 *
 * 抽离动机（session 43 架构清债 F5）：
 *   - 两个 cytoscape 关系图组件之间存在 ~30 行字面相同的代码
 *   - 颜色 token 表 / 边粗细线性映射 / 边颜色阈值 / register 守卫 / RelationEntry 类型
 *   - stylesheet 因字号/节点尺寸不同**未抽**——参数化收益 < 复杂度增加
 *
 * 设计纪律：
 *   - 文件名 `_xxx_shared` 前缀表示"内部共用工具"——不暴露给 routes / hooks
 *   - 仅 components/ 内的两个 cytoscape 组件 import
 *   - 颜色值取自 `web/src/styles/tokens.css` 的具体颜色（cytoscape stylesheet 不支持 CSS var()）
 */
import cytoscape from "cytoscape";
import coseBilkent from "cytoscape-cose-bilkent";

/**
 * cytoscape extension 注册守卫——重复调用安全（cytoscape.use 内部已有 if-not-registered 检查，
 * 但外层包装一层避免每次组件 mount 都调）。
 */
let _registered = false;
export function ensureCytoscapeRegistered(): void {
  if (_registered) return;
  cytoscape.use(coseBilkent as unknown as cytoscape.Ext);
  _registered = true;
}

/**
 * 关系图调色板——值取自 tokens.css :root 段。cytoscape stylesheet 必须用具体颜色字符串，
 * 不支持 CSS variables（`var(--xxx)` 在 cytoscape 内层 canvas 渲染上下文找不到 :root）。
 *
 * 来源：
 *   - llm/rule/random：tokens.css decision_mode 三色
 *   - positive/warning/negative：polisim-relation-* 业务 token
 *   - bg/fg/border：tokens.css 中性色
 */
export const RELATION_GRAPH_COLORS = {
  llm: "#4ea7fc", // status-info
  rule: "#8a8f98", // text-tertiary
  random: "#7170ff", // accent
  positive: "#27a644", // polisim-relation-positive
  warning: "#f0bf00", // status-warning
  negative: "#eb5757", // polisim-relation-negative
  bgSurface: "#1c1d1f",
  fgPrimary: "#f7f8f8",
  fgTertiary: "#8a8f98",
  borderDefault: "#23262b",
} as const;

/**
 * 边颜色按 trust value 阈值映射：
 *   - >= 70  → 绿（高信任）
 *   - <= 40  → 红（低信任）
 *   - 其他   → 黄（中性）
 */
export function edgeColorByTrust(value: number): string {
  if (value >= 70) return RELATION_GRAPH_COLORS.positive;
  if (value <= 40) return RELATION_GRAPH_COLORS.negative;
  return RELATION_GRAPH_COLORS.warning;
}

/**
 * 边粗细按 trust value 线性映射 0-100 → 1-4px。
 */
export function edgeWidthByTrust(value: number): number {
  return Math.max(1, Math.min(4, 1 + (value / 100) * 3));
}

/**
 * Snapshot.relation_state_summary 单条关系的统一形状（D-017 server 保证）。
 */
export interface RelationEntry {
  type: string;
  source: string;
  target: string;
  value: number;
}
