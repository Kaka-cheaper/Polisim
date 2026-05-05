/**
 * FinishedMetricsCard —— 跑完页 6 类指标卡片（mockup §4.5 数据概览，PR5）。
 *
 * 6 指标取自 `AnalysisResult.summary` + `turning_points`：
 *   1. total_ticks                  仿真总 tick 数
 *   2. total_events                 事件总数
 *   3. events_by_kind.length        事件类型种数
 *   4. events_by_actor.length       参与实体数
 *   5. turning_points.length        关键转折点数
 *   6. breakpoints_triggered.length 断点触发次数（含重复）
 *
 * 设计意图：让用户在 4 段叙事之上**先看到全局数字**，定位本 run 的"规模 / 复杂度"。
 *
 * loading：result=null 时显示骨架卡片（6 个灰块）。
 */
import { useTranslation } from "react-i18next";

import type { AnalysisResult } from "../api/schema";

interface Props {
  result: AnalysisResult | null;
}

interface MetricItem {
  emoji: string;
  labelKey: string;
  value: number;
}

export function FinishedMetricsCard({ result }: Props) {
  const { t } = useTranslation();

  if (result === null) {
    return (
      <section className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <div
            key={i}
            className="h-24 animate-pulse rounded-lg bg-surface-active"
          />
        ))}
      </section>
    );
  }

  const metrics: MetricItem[] = [
    {
      emoji: "⏱️",
      labelKey: "finished.metrics.total_ticks",
      value: result.summary.total_ticks,
    },
    {
      emoji: "📋",
      labelKey: "finished.metrics.total_events",
      value: result.summary.total_events,
    },
    {
      emoji: "🏷️",
      labelKey: "finished.metrics.event_kinds",
      value: result.summary.events_by_kind.length,
    },
    {
      emoji: "👥",
      labelKey: "finished.metrics.entities",
      value: result.summary.events_by_actor.length,
    },
    {
      emoji: "📈",
      labelKey: "finished.metrics.turning_points",
      value: result.turning_points.length,
    },
    {
      emoji: "🔔",
      labelKey: "finished.metrics.breakpoints",
      value: result.summary.breakpoints_triggered.length,
    },
  ];

  return (
    <section
      className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6"
      aria-label={t("finished.metrics.aria_label")}
    >
      {metrics.map((m) => (
        <div
          key={m.labelKey}
          className="rounded-lg border border-border-subtle bg-surface px-4 py-3 shadow-sm"
        >
          <div className="flex items-center gap-2 text-md text-fg-tertiary">
            <span aria-hidden="true">{m.emoji}</span>
            <span>{t(m.labelKey)}</span>
          </div>
          <div className="mt-1 text-3xl font-bold tabular-nums text-fg-primary">
            {m.value}
          </div>
        </div>
      ))}
    </section>
  );
}

export default FinishedMetricsCard;
