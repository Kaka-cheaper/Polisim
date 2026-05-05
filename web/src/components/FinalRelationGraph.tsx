/**
 * FinalRelationGraph —— 跑完页副区 🕸 tab（mockup §4.5 + PR5.5-spec §3.2）。
 *
 * 用 cytoscape.js + cose-bilkent 力导向布局展示某 tick 的关系快照。
 *
 * 与 `layouts/RelationGraphLayout.tsx` 区别：
 *   - 无"最近 decision_proposed 气泡"（本 tab 不展示 LLM 决策）
 *   - 加 time-axis slider：拖动切换查看 tick 0..N 的关系演化
 *   - 节点点击不触发干预（跑完页无法干预）
 *
 * 设计决策（PR5.5-spec §3.2）：
 *   - 不重构 RelationGraphLayout 抽 RelationGraphBase（避免破 PR4.5 e2e 回归）
 *   - 直接 inline 复制 stylesheet 常量；v0.3+ 可做共享 refactor
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import coseBilkent from "cytoscape-cose-bilkent";
import CytoscapeComponent from "react-cytoscapejs";

import type {
  RelationTypeSchema,
  Scenario,
  Snapshot,
  WorldDefinition,
} from "../api/schema";

// 一次性 register（与 RelationGraphLayout 共存安全——cytoscape.use 幂等）
let registered = false;
if (!registered) {
  cytoscape.use(coseBilkent as unknown as cytoscape.Ext);
  registered = true;
}

const COLORS = {
  llm: "#4ea7fc",
  rule: "#8a8f98",
  random: "#7170ff",
  positive: "#27a644",
  warning: "#f0bf00",
  negative: "#eb5757",
  bgSurface: "#1c1d1f",
  fgPrimary: "#f7f8f8",
  fgTertiary: "#8a8f98",
  borderDefault: "#23262b",
} as const;

function edgeColorByTrust(value: number): string {
  if (value >= 70) return COLORS.positive;
  if (value <= 40) return COLORS.negative;
  return COLORS.warning;
}

function edgeWidthByTrust(value: number): number {
  return Math.max(1, Math.min(4, 1 + (value / 100) * 3));
}

interface RelationEntry {
  type: string;
  source: string;
  target: string;
  value: number;
}

interface Props {
  world: WorldDefinition;
  scenario: Scenario;
  snapshots: Snapshot[];
}

export function FinalRelationGraph({ world, scenario, snapshots }: Props) {
  const { t } = useTranslation();
  const cyRef = useRef<Core | null>(null);

  const maxIdx = Math.max(snapshots.length - 1, 0);
  const [tickIdx, setTickIdx] = useState(maxIdx);

  // maxIdx 变化（snapshots 首次加载）时，重置选中到终态
  useEffect(() => {
    setTickIdx(maxIdx);
  }, [maxIdx]);

  const currentSnap = snapshots[tickIdx];

  const relations = useMemo<RelationEntry[]>(() => {
    const raw = (currentSnap?.relation_state_summary ?? []) as unknown;
    if (!Array.isArray(raw)) return [];
    const result: RelationEntry[] = [];
    for (const r of raw as Array<Record<string, unknown>>) {
      if (
        typeof r.type === "string" &&
        typeof r.source === "string" &&
        typeof r.target === "string" &&
        typeof r.value === "number"
      ) {
        result.push({
          type: r.type,
          source: r.source,
          target: r.target,
          value: r.value,
        });
      }
    }
    return result;
  }, [currentSnap]);

  const relationTypes: Record<string, RelationTypeSchema> | null | undefined =
    world.relation_types;

  // entity decision_mode 表（节点颜色用）
  const entityMode = useMemo(() => {
    const map = new Map<string, string>();
    for (const e of scenario.entities) {
      const typeSchema = world.entity_types[e.type];
      map.set(e.id, typeSchema?.decision_mode ?? "rule");
    }
    return map;
  }, [world, scenario]);

  const elements = useMemo<ElementDefinition[]>(() => {
    // 节点——以 snapshot 中存在的 entity 为主
    const summary = (currentSnap?.entity_state_summary ?? {}) as Record<
      string,
      unknown
    >;
    const entityIds = Array.from(
      new Set([...Object.keys(summary), ...entityMode.keys()]),
    );
    const nodes: ElementDefinition[] = entityIds.map((id) => ({
      data: {
        id,
        label: id,
        decisionMode: entityMode.get(id) ?? "rule",
      },
    }));
    const edges: ElementDefinition[] = relations.map((r, i) => {
      const directed = relationTypes?.[r.type]?.directed ?? false;
      return {
        data: {
          id: `${r.source}-${r.type}-${r.target}-${i}`,
          source: r.source,
          target: r.target,
          relationType: r.type,
          value: r.value,
          color: edgeColorByTrust(r.value),
          width: edgeWidthByTrust(r.value),
          arrowShape: directed ? "triangle" : "none",
          label: `${r.type}:${r.value}`,
        },
      };
    });
    return [...nodes, ...edges];
  }, [currentSnap, relations, relationTypes, entityMode]);

  const stylesheet: cytoscape.StylesheetCSS[] = [
    {
      selector: "node",
      style: {
        "background-color": (ele: cytoscape.NodeSingular) => {
          const mode = ele.data("decisionMode") as string;
          return COLORS[mode as keyof typeof COLORS] ?? COLORS.rule;
        },
        label: "data(label)",
        color: COLORS.fgPrimary,
        "text-valign": "center",
        "text-halign": "center",
        "font-size": "12px",
        "font-weight": "bold",
        "border-width": 2,
        "border-color": COLORS.borderDefault,
        width: 50,
        height: 50,
      } as unknown as cytoscape.Css.Node,
    },
    {
      selector: "edge",
      style: {
        width: "data(width)",
        "line-color": "data(color)",
        "target-arrow-color": "data(color)",
        "target-arrow-shape": "data(arrowShape)",
        "curve-style": "bezier",
        label: "data(label)",
        color: COLORS.fgTertiary,
        "font-size": "9px",
        "text-rotation": "autorotate" as unknown as number,
        "text-margin-y": -6,
        "text-background-color": COLORS.bgSurface,
        "text-background-opacity": 0.85,
        "text-background-padding": "2px",
      } as unknown as cytoscape.Css.Edge,
    },
  ];

  const layout = {
    name: "cose-bilkent",
    animate: false,
    nodeRepulsion: 6000,
    idealEdgeLength: 100,
    edgeElasticity: 0.45,
    randomize: false,
    fit: true,
    padding: 20,
  };

  // 场景无 relation 定义 → 占位
  if (!relationTypes || Object.keys(relationTypes).length === 0) {
    return (
      <p className="rounded-md border border-border-subtle bg-canvas p-6 text-center text-md text-fg-tertiary">
        {t("finished_side_panel.final_relation_graph.no_relations")}
      </p>
    );
  }

  if (snapshots.length === 0) {
    return (
      <p className="rounded-md border border-border-subtle bg-canvas p-6 text-center text-md text-fg-tertiary">
        {t("finished_side_panel.attribute_chart.loading")}
      </p>
    );
  }

  const currentTickNum = currentSnap?.tick ?? 0;
  const finalTickNum = snapshots.at(-1)?.tick ?? 0;

  return (
    <div className="flex flex-col gap-3">
      {/* 时间轴 */}
      <div className="flex items-center gap-2 text-base">
        <span className="text-fg-tertiary">
          {t("finished_side_panel.final_relation_graph.time_axis")}
        </span>
        <input
          type="range"
          min={0}
          max={maxIdx}
          step={1}
          value={tickIdx}
          onChange={(e) => setTickIdx(Number(e.target.value))}
          className="flex-1"
          aria-label={t("finished_side_panel.final_relation_graph.time_axis")}
        />
        <span className="font-mono text-fg-secondary">
          {t("finished_side_panel.final_relation_graph.tick_label", {
            tick: currentTickNum,
            total: finalTickNum,
          })}
        </span>
      </div>

      {/* Cytoscape */}
      <div
        className="rounded-lg border border-border-subtle bg-canvas"
        style={{ height: "400px" }}
      >
        <CytoscapeComponent
          elements={elements}
          stylesheet={stylesheet}
          layout={layout}
          style={{ width: "100%", height: "100%" }}
          cy={(cy) => {
            cyRef.current = cy;
          }}
        />
      </div>
    </div>
  );
}

export default FinalRelationGraph;
