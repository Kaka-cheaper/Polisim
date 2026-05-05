/**
 * AttributeChart —— 跑完页副区 📈 tab（mockup §4.5 + PR5.5-spec §3.1）。
 *
 * 数据流：
 *   1. useSnapshotsList(runId) → tick 列表
 *   2. useAllSnapshots(runId, tickList) → 每 tick 快照
 *   3. 从末 snapshot 提取所有 entity_id + numeric attribute → 下拉选项
 *   4. 默认全选；用户可取消勾选某实体/属性
 *   5. recharts LineChart 按 (entity, attribute) 笛卡尔积画线
 *
 * 与 MiniDashboard 区别：
 *   - MiniDashboard 在跑中态从 useRunStream 累积快照 → 实时更新
 *   - AttributeChart 在跑完态从 server 一次性拉 → 完整历史
 *   - 两者复用 recharts 配色 palette 与 tooltip 风格
 */
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useAllSnapshots, useSnapshotsList } from "../hooks/useSnapshot";
import type { Snapshot } from "../api/schema";

interface Props {
  runId: string;
  /** 来自 NarrativeReport 点击 tick 引用（PR5 留口）—— null 时不画 highlight 线。*/
  highlightTick?: number | null;
}

const ENTITY_PALETTE = [
  "var(--polisim-line-1, #3B82F6)",
  "var(--polisim-line-2, #10B981)",
  "var(--polisim-line-3, #F59E0B)",
  "var(--polisim-line-4, #EF4444)",
  "var(--polisim-line-5, #8B5CF6)",
];

function collectEntities(snapshots: Snapshot[]): string[] {
  const set = new Set<string>();
  for (const s of snapshots) {
    const summary = s.entity_state_summary ?? {};
    for (const id of Object.keys(summary)) set.add(id);
  }
  return Array.from(set).sort();
}

function collectNumericAttrs(snapshots: Snapshot[]): string[] {
  const set = new Set<string>();
  const last = snapshots.at(-1);
  if (!last) return [];
  const summary = last.entity_state_summary ?? {};
  for (const attrs of Object.values(summary)) {
    if (!attrs) continue;
    for (const [k, v] of Object.entries(attrs)) {
      if (typeof v === "number" && Number.isFinite(v)) set.add(k);
    }
  }
  return Array.from(set).sort();
}

/** 展平为 recharts 友好形态：`[{ tick, ${entity}__${attr}: number, ... }]` */
function buildSeries(
  snapshots: Snapshot[],
  entityIds: string[],
  attrs: string[],
): Array<Record<string, number>> {
  return snapshots.map((snap) => {
    const row: Record<string, number> = { tick: snap.tick };
    const summary = snap.entity_state_summary ?? {};
    for (const eid of entityIds) {
      const attrsObj = summary[eid] as Record<string, unknown> | undefined;
      if (!attrsObj) continue;
      for (const attr of attrs) {
        const v = attrsObj[attr];
        if (typeof v === "number" && Number.isFinite(v)) {
          row[`${eid}__${attr}`] = v;
        }
      }
    }
    return row;
  });
}

export function AttributeChart({ runId, highlightTick }: Props) {
  const { t } = useTranslation();

  const { data: ticksList, isLoading: listLoading } = useSnapshotsList(runId);
  const ticks = ticksList?.ticks ?? [];
  const {
    data: snapshots,
    isLoading: snapshotsLoading,
  } = useAllSnapshots(runId, ticks);

  const allEntities = useMemo(
    () => collectEntities(snapshots ?? []),
    [snapshots],
  );
  const allAttrs = useMemo(
    () => collectNumericAttrs(snapshots ?? []),
    [snapshots],
  );

  const [selectedEntities, setSelectedEntities] = useState<Set<string> | null>(
    null,
  );
  const [selectedAttrs, setSelectedAttrs] = useState<Set<string> | null>(null);

  // 默认全选（首次 data ready 时）—— 通过 null 表示"未初始化，走全选"
  const activeEntities =
    selectedEntities ?? new Set(allEntities);
  const activeAttrs = selectedAttrs ?? new Set(allAttrs);

  const series = useMemo(
    () =>
      buildSeries(
        snapshots ?? [],
        Array.from(activeEntities),
        Array.from(activeAttrs),
      ),
    [snapshots, activeEntities, activeAttrs],
  );

  const toggleEntity = (eid: string) => {
    const next = new Set(activeEntities);
    if (next.has(eid)) next.delete(eid);
    else next.add(eid);
    setSelectedEntities(next);
  };

  const toggleAttr = (attr: string) => {
    const next = new Set(activeAttrs);
    if (next.has(attr)) next.delete(attr);
    else next.add(attr);
    setSelectedAttrs(next);
  };

  if (listLoading || snapshotsLoading) {
    return (
      <p className="rounded-md border border-border-subtle bg-canvas p-6 text-center text-md text-fg-tertiary">
        {t("finished_side_panel.attribute_chart.loading")}
      </p>
    );
  }

  if (!snapshots || snapshots.length === 0 || allAttrs.length === 0) {
    return (
      <p className="rounded-md border border-border-subtle bg-canvas p-6 text-center text-md text-fg-tertiary">
        {t("finished_side_panel.attribute_chart.no_data")}
      </p>
    );
  }

  // 画线：为 (entity, attr) 每个组合画一条
  const lines: Array<{ key: string; label: string; color: string }> = [];
  let colorIdx = 0;
  for (const eid of allEntities) {
    if (!activeEntities.has(eid)) continue;
    for (const attr of allAttrs) {
      if (!activeAttrs.has(attr)) continue;
      lines.push({
        key: `${eid}__${attr}`,
        label: `${eid}.${attr}`,
        color: ENTITY_PALETTE[colorIdx % ENTITY_PALETTE.length],
      });
      colorIdx += 1;
    }
  }

  return (
    <div className="flex flex-col gap-3">
      {/* 实体 checkbox */}
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-base">
        <span className="text-fg-tertiary">
          {t("finished_side_panel.attribute_chart.entity_filter")}
        </span>
        {allEntities.map((eid) => (
          <label key={eid} className="flex items-center gap-1 text-fg-secondary">
            <input
              type="checkbox"
              checked={activeEntities.has(eid)}
              onChange={() => toggleEntity(eid)}
            />
            <span className="font-mono">{eid}</span>
          </label>
        ))}
      </div>

      {/* 属性 checkbox */}
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-base">
        <span className="text-fg-tertiary">
          {t("finished_side_panel.attribute_chart.attribute_filter")}
        </span>
        {allAttrs.map((attr) => (
          <label key={attr} className="flex items-center gap-1 text-fg-secondary">
            <input
              type="checkbox"
              checked={activeAttrs.has(attr)}
              onChange={() => toggleAttr(attr)}
            />
            <span className="font-mono">{attr}</span>
          </label>
        ))}
      </div>

      {/* 折线图 */}
      <ResponsiveContainer width="100%" height={320}>
        <LineChart
          data={series}
          margin={{ top: 8, right: 12, left: -12, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
          <XAxis
            dataKey="tick"
            stroke="var(--text-tertiary)"
            tick={{ fontSize: 11 }}
            label={{
              value: t("finished_side_panel.attribute_chart.x_axis"),
              position: "insideBottom",
              offset: -2,
              fontSize: 10,
            }}
          />
          <YAxis stroke="var(--text-tertiary)" tick={{ fontSize: 11 }} />
          <Tooltip
            contentStyle={{
              backgroundColor: "var(--bg-surface)",
              border: "1px solid var(--border-default)",
              borderRadius: "0.375rem",
              fontSize: "12px",
            }}
          />
          <Legend wrapperStyle={{ fontSize: "11px" }} />
          {highlightTick !== null && highlightTick !== undefined && (
            <ReferenceLine
              x={highlightTick}
              stroke="var(--status-warning, #F59E0B)"
              strokeDasharray="4 2"
            />
          )}
          {lines.map((ln) => (
            <Line
              key={ln.key}
              type="monotone"
              dataKey={ln.key}
              name={ln.label}
              stroke={ln.color}
              strokeWidth={2}
              dot={{ r: 2 }}
              isAnimationActive={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default AttributeChart;
