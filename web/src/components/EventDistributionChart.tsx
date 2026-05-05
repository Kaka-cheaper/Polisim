/**
 * EventDistributionChart —— 跑完页副区 📊 tab（mockup §4.5 + PR5.5-spec §3.2）。
 *
 * 数据源：AnalysisResult.summary.events_by_kind / events_by_actor
 *   - 两者均在 Phase A 产出 → 必然可用（不需要等 LLM 增强）
 *
 * 维度切换：
 *   - "kind"（默认）：按 EventKind 分组
 *   - "actor"：按实体 actor_id 分组（action_count 维度；decision_rejected_count 不单画）
 *
 * 暂不做：
 *   - 点击 bar 跳事件流（依赖 ReplayPanel 完整版；v0.3+）
 */
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { AnalysisResult } from "../api/schema";

interface Props {
  result: AnalysisResult | null | undefined;
}

type Dim = "kind" | "actor";

export function EventDistributionChart({ result }: Props) {
  const { t } = useTranslation();
  const [dim, setDim] = useState<Dim>("kind");

  const data = useMemo(() => {
    if (!result?.summary) return [] as Array<{ label: string; count: number }>;
    if (dim === "kind") {
      return (result.summary.events_by_kind ?? [])
        .map((s) => ({ label: s.kind, count: s.count }))
        .sort((a, b) => b.count - a.count);
    }
    return (result.summary.events_by_actor ?? [])
      .map((s) => ({ label: s.actor_id, count: s.action_count }))
      .sort((a, b) => b.count - a.count);
  }, [result, dim]);

  return (
    <div className="flex flex-col gap-3">
      {/* 维度切换 */}
      <div className="flex items-center gap-2 text-base">
        <span className="text-fg-tertiary">
          {t("finished_side_panel.event_distribution.switch_dim")}
        </span>
        <button
          type="button"
          onClick={() => setDim("kind")}
          className={`rounded-md border px-2 py-0.5 transition-colors ${
            dim === "kind"
              ? "border-accent bg-accent text-fg-on-accent"
              : "border-border-default bg-surface text-fg-secondary hover:border-accent"
          }`}
        >
          {t("finished_side_panel.event_distribution.by_kind")}
        </button>
        <button
          type="button"
          onClick={() => setDim("actor")}
          className={`rounded-md border px-2 py-0.5 transition-colors ${
            dim === "actor"
              ? "border-accent bg-accent text-fg-on-accent"
              : "border-border-default bg-surface text-fg-secondary hover:border-accent"
          }`}
        >
          {t("finished_side_panel.event_distribution.by_actor")}
        </button>
      </div>

      {/* 柱状图 */}
      {data.length === 0 ? (
        <p className="rounded-md border border-border-subtle bg-canvas p-6 text-center text-md text-fg-tertiary">
          {t("finished_side_panel.event_distribution.no_events")}
        </p>
      ) : (
        <ResponsiveContainer
          width="100%"
          height={Math.max(200, data.length * 28 + 40)}
        >
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 4, right: 16, left: 4, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
            <XAxis
              type="number"
              stroke="var(--text-tertiary)"
              tick={{ fontSize: 11 }}
              allowDecimals={false}
            />
            <YAxis
              type="category"
              dataKey="label"
              stroke="var(--text-tertiary)"
              tick={{ fontSize: 11 }}
              width={160}
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
    </div>
  );
}

export default EventDistributionChart;
