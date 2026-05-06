/**
 * MiniDashboard —— 副区两段图表（mockup §4.4.2 + §11.4）。
 *
 * 数据来源：从 `useRunStream` 累积的 `snapshots` + `events`，本组件不直接发请求。
 *
 * 两段：
 *   1. 📈 属性趋势：每个 numeric 属性一张 LineChart，所有实体并列（Line × N entities），
 *                  X = tick / Y = value。仅展示数值型属性（filter typeof === 'number'）。
 *   2. 📊 事件分布：BarChart by EventKind，X = kind / Y = count。
 *
 * 兜底（mockup §10.6 M5 反向校验过的边界）：
 *   - snapshots < 2 → "至少需要 2 个 tick 数据才能绘制趋势线"
 *   - 无 numeric 属性 → "本场景无数值属性"（如纯叙事场景）
 *   - 0 events → "暂无事件"（启动瞬间）
 *
 * PR4.3 简化：
 *   - 颜色 palette 直接用 5 个 token CSS variables 循环（v0.3+ 可换用 d3 chromatic schemes）
 *   - 不开启 brush / zoom（mockup 只要求 latest N tick 趋势，超出 N 由 useRunStream 滑窗保留）
 *   - 折叠状态由 Running 在外层 conditional render，本组件不感知 collapsed
 */
import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { ENTITY_PALETTE, collectNumericAttributes } from "./_chart_shared";
import type { EntityCardEntry } from "./EntityCard";
import type { EventRecord, Snapshot } from "../api/schema";

interface Props {
  entries: EntityCardEntry[];
  snapshots: Snapshot[];
  events: EventRecord[];
}

/** 把 snapshots × entities × attribute=A 的数据展平成 recharts 友好的形态：
 *  `[{ tick: 0, company_a: 100, company_b: 80 }, { tick: 1, ... }]` */
function buildAttributeSeries(
  snapshots: Snapshot[],
  attrName: string,
  entityIds: string[],
): Array<Record<string, number>> {
  const idSet = new Set(entityIds);
  return snapshots.map((snap) => {
    const row: Record<string, number> = { tick: snap.tick };
    const summary = snap.entity_state_summary ?? {};
    for (const [entityId, attrs] of Object.entries(summary)) {
      if (!idSet.has(entityId)) continue;
      const v = (attrs as Record<string, unknown> | undefined)?.[attrName];
      if (typeof v === "number" && Number.isFinite(v)) {
        row[entityId] = v;
      }
    }
    return row;
  });
}

/** 按 EventKind 计数。返回按 count 降序的数组（top-N 可读性最佳）。 */
function buildEventDistribution(
  events: EventRecord[],
): Array<{ kind: string; count: number }> {
  const counts = new Map<string, number>();
  for (const e of events) {
    counts.set(e.kind, (counts.get(e.kind) ?? 0) + 1);
  }
  return Array.from(counts.entries())
    .map(([kind, count]) => ({ kind, count }))
    .sort((a, b) => b.count - a.count);
}

export function MiniDashboard({ entries, snapshots, events }: Props) {
  const { t } = useTranslation();

  const entityIds = useMemo(() => entries.map((e) => e.id), [entries]);

  const numericAttrs = useMemo(
    () => collectNumericAttributes(snapshots),
    [snapshots],
  );

  const eventDistribution = useMemo(
    () => buildEventDistribution(events),
    [events],
  );

  return (
    <aside
      aria-label={t("mini_dashboard.title")}
      className="flex flex-col gap-4 overflow-y-auto rounded-lg border border-border-subtle bg-surface p-4"
    >
      <h3 className="text-md font-semibold text-fg-primary">
        {t("mini_dashboard.title")}
      </h3>

      {/* ── 属性趋势 ── */}
      <section>
        <h4 className="mb-2 text-base font-medium text-fg-secondary">
          {t("mini_dashboard.section.attributes")}
        </h4>
        {snapshots.length < 2 ? (
          <p className="rounded-md border border-border-subtle bg-canvas p-3 text-base text-fg-tertiary">
            {t("mini_dashboard.no_snapshots")}
          </p>
        ) : numericAttrs.length === 0 ? (
          <p className="rounded-md border border-border-subtle bg-canvas p-3 text-base text-fg-tertiary">
            {t("mini_dashboard.no_numeric_attrs")}
          </p>
        ) : (
          <ul className="flex flex-col gap-3">
            {numericAttrs.map((attr) => {
              const data = buildAttributeSeries(snapshots, attr, entityIds);
              return (
                <li key={attr}>
                  <p className="mb-1 font-mono text-base text-fg-tertiary">
                    {attr}
                  </p>
                  <ResponsiveContainer width="100%" height={140}>
                    <LineChart
                      data={data}
                      margin={{ top: 4, right: 8, left: -16, bottom: 0 }}
                    >
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="var(--border-subtle)"
                      />
                      <XAxis
                        dataKey="tick"
                        stroke="var(--text-tertiary)"
                        tick={{ fontSize: 11 }}
                      />
                      <YAxis
                        stroke="var(--text-tertiary)"
                        tick={{ fontSize: 11 }}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "var(--bg-surface)",
                          border: "1px solid var(--border-default)",
                          borderRadius: "0.375rem",
                          fontSize: "12px",
                        }}
                        labelFormatter={(tick) =>
                          `${t("mini_dashboard.tooltip_tick")} ${tick}`
                        }
                      />
                      <Legend wrapperStyle={{ fontSize: "11px" }} />
                      {entityIds.map((eid, idx) => (
                        <Line
                          key={eid}
                          type="monotone"
                          dataKey={eid}
                          stroke={ENTITY_PALETTE[idx % ENTITY_PALETTE.length]}
                          strokeWidth={2}
                          dot={{ r: 2 }}
                          isAnimationActive={false}
                        />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      {/* ── 事件分布 ── */}
      <section>
        <h4 className="mb-2 text-base font-medium text-fg-secondary">
          {t("mini_dashboard.section.events")}
        </h4>
        {eventDistribution.length === 0 ? (
          <p className="rounded-md border border-border-subtle bg-canvas p-3 text-base text-fg-tertiary">
            {t("mini_dashboard.no_events")}
          </p>
        ) : (
          <ResponsiveContainer
            width="100%"
            height={Math.max(140, eventDistribution.length * 22 + 40)}
          >
            <BarChart
              data={eventDistribution}
              layout="vertical"
              margin={{ top: 4, right: 16, left: 4, bottom: 0 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="var(--border-subtle)"
              />
              <XAxis
                type="number"
                stroke="var(--text-tertiary)"
                tick={{ fontSize: 11 }}
                allowDecimals={false}
              />
              <YAxis
                type="category"
                dataKey="kind"
                stroke="var(--text-tertiary)"
                tick={{ fontSize: 11 }}
                width={140}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "var(--bg-surface)",
                  border: "1px solid var(--border-default)",
                  borderRadius: "0.375rem",
                  fontSize: "12px",
                }}
              />
              <Bar
                dataKey="count"
                fill="var(--accent, #3B82F6)"
                isAnimationActive={false}
              />
            </BarChart>
          </ResponsiveContainer>
        )}
      </section>
    </aside>
  );
}

export default MiniDashboard;
