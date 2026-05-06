/**
 * RelationGraphLayout —— 跑中主区"关系图"布局（mockup §4.3.2 + §11.3 L2）。
 *
 * 用 cytoscape.js + cose-bilkent 力导向布局展示实体（节点）+ 关系（边）。
 *
 * - 节点颜色 ← decision_mode：llm / rule / random
 * - 节点点击 ← onEntityClick（与 EntityCardLayout 干预入口对齐）
 * - 边粗细 ← relation.value（线性映射 1-4px）
 * - 边颜色 ← relation.value 阈值（绿/黄/红）
 * - 边箭头 ← `worldDef.relation_types[type].directed`
 * - 底部 LLM 气泡 ← 最近一次 decision_proposed
 *
 * cytoscape 集成（mockup §9.2 + §8.1 决议）：
 *   - `cytoscape` 主库
 *   - `react-cytoscapejs` 包装组件
 *   - `cytoscape-cose-bilkent` 高质量力导向 layout
 *
 * 不在本组件做：
 *   - 数据组装 → Running 负责
 *   - 干预浮层 / PromptContextModal → Running + 现有组件
 *   - 边动态过渡动画 → cytoscape 默认 + future tween（PR4.5+）
 */
import { useEffect, useMemo, useRef } from "react";
import { useTranslation } from "react-i18next";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import CytoscapeComponent from "react-cytoscapejs";

import type { EntityCardEntry } from "../components/EntityCard";
import {
  RELATION_GRAPH_COLORS as COLORS,
  edgeColorByTrust,
  edgeWidthByTrust,
  ensureCytoscapeRegistered,
  type RelationEntry as SharedRelationEntry,
} from "../components/_relation_graph_shared";
import type { EventRecord, RelationTypeSchema } from "../api/schema";

ensureCytoscapeRegistered();

/** Snapshot.relation_state_summary 的实际形状（D-017 server 保证）。
 *  re-export 仅为保持 PR4.5 阶段的外部 import 路径向后兼容（Running.tsx 从本文件 import）。 */
export type RelationEntry = SharedRelationEntry;

interface Props {
  entries: EntityCardEntry[];
  relations: RelationEntry[];
  /** WorldDefinition.relation_types —— 用于读 directed。*/
  relationTypes: Record<string, RelationTypeSchema> | null | undefined;
  /** 最近一次 decision_proposed 事件（任一实体）—— 用于底部气泡。*/
  latestDecision?: EventRecord | null;
  onEntityClick?: (id: string) => void;
}

export function RelationGraphLayout({
  entries,
  relations,
  relationTypes,
  latestDecision,
  onEntityClick,
}: Props) {
  const { t } = useTranslation();
  const cyRef = useRef<Core | null>(null);

  // ---- 组装 cytoscape elements ----
  const elements = useMemo<ElementDefinition[]>(() => {
    const nodes: ElementDefinition[] = entries.map((e) => ({
      data: {
        id: e.id,
        label: e.id,
        decisionMode: e.decisionMode,
        type: e.type,
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
  }, [entries, relations, relationTypes]);

  // ---- 节点点击委派 ----
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !onEntityClick) return;
    const handler = (evt: cytoscape.EventObject) => {
      const id = evt.target.id();
      onEntityClick(id);
    };
    cy.on("tap", "node", handler);
    return () => {
      cy.off("tap", "node", handler);
    };
  }, [onEntityClick, elements]);

  // ---- cytoscape stylesheet ----
  const stylesheet: cytoscape.StylesheetCSS[] = [
    {
      selector: "node",
      style: {
        "background-color": (ele: cytoscape.NodeSingular) => {
          const mode = ele.data("decisionMode") as string;
          return (
            COLORS[mode as keyof typeof COLORS] ?? COLORS.rule
          );
        },
        label: "data(label)",
        color: COLORS.fgPrimary,
        "text-valign": "center",
        "text-halign": "center",
        "font-size": "14px",
        "font-weight": "bold",
        "border-width": 2,
        "border-color": COLORS.borderDefault,
        width: 60,
        height: 60,
      } as unknown as cytoscape.Css.Node,
    },
    {
      selector: "node:active",
      style: { "overlay-opacity": 0.2 } as cytoscape.Css.Node,
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
        "font-size": "10px",
        "text-rotation": "autorotate" as unknown as number,
        "text-margin-y": -8,
        "text-background-color": COLORS.bgSurface,
        "text-background-opacity": 0.85,
        "text-background-padding": "2px",
      } as unknown as cytoscape.Css.Edge,
    },
  ];

  const layout = {
    name: "cose-bilkent",
    animate: false,
    nodeRepulsion: 8000,
    idealEdgeLength: 120,
    edgeElasticity: 0.45,
    randomize: false,
    fit: true,
    padding: 30,
  };

  // ---- 底部气泡：最近 decision_proposed ----
  const decisionPayload = latestDecision?.payload as
    | { reason?: string; action?: { type?: string } }
    | undefined;
  const decisionReason = decisionPayload?.reason ?? null;
  const actionType = decisionPayload?.action?.type ?? null;

  return (
    <div className="flex flex-col gap-4">
      <div
        className="rounded-lg border border-border-subtle bg-canvas"
        style={{ height: "60vh", minHeight: "400px" }}
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

      {/* 图例 */}
      <section className="flex flex-wrap gap-x-6 gap-y-2 rounded-md border border-border-subtle bg-surface px-4 py-2 text-md text-fg-tertiary">
        <span>
          <span
            className="mr-1 inline-block h-3 w-3 rounded-full align-middle"
            style={{ backgroundColor: COLORS.llm }}
          />
          {t("relation_graph.legend.llm")}
        </span>
        <span>
          <span
            className="mr-1 inline-block h-3 w-3 rounded-full align-middle"
            style={{ backgroundColor: COLORS.rule }}
          />
          {t("relation_graph.legend.rule")}
        </span>
        <span>
          <span
            className="mr-1 inline-block h-3 w-3 rounded-full align-middle"
            style={{ backgroundColor: COLORS.random }}
          />
          {t("relation_graph.legend.random")}
        </span>
        <span className="ml-2">{t("relation_graph.legend.edge_hint")}</span>
      </section>

      {/* 底部 LLM 气泡 */}
      {latestDecision && (decisionReason || actionType) && (
        <section
          className="rounded-lg border border-status-info bg-surface px-4 py-3"
          aria-label={t("relation_graph.decision_aria")}
        >
          <p className="text-md font-medium text-fg-primary">
            💭{" "}
            <span className="text-fg-tertiary">{latestDecision.actor_id}</span>{" "}
            {actionType && (
              <span className="font-mono text-fg-secondary">
                → {actionType}
              </span>
            )}
          </p>
          {decisionReason && (
            <p className="mt-1 text-md text-fg-secondary">"{decisionReason}"</p>
          )}
        </section>
      )}

      {entries.length === 0 && (
        <p className="text-center text-fg-tertiary">{t("running.loading")}</p>
      )}
    </div>
  );
}

export default RelationGraphLayout;
