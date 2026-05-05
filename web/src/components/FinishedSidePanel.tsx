/**
 * FinishedSidePanel —— 跑完页副区 5 tabs 容器（mockup §4.5 + PR5.5-spec §二）。
 *
 * 职责：
 *   - 5 tab 切换（📈 / 🕸 / 📊 / 🎬 / 📋）
 *   - 统一上层 events / snapshots 数据拉取 —— 传给 ReplayPanel / RawDataView / FinalRelationGraph
 *   - events 采取一次性全拉策略（分页循环），共享给 ReplayPanel + RawDataView
 *
 * 不在本组件：
 *   - Tab 组件实现（各自拿自己的数据和展示）
 *   - NarrativeReport / FinishedMetricsCard（由 Finished route 直接渲染）
 */
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { AttributeChart } from "./AttributeChart";
import { EventDistributionChart } from "./EventDistributionChart";
import { FinalRelationGraph } from "./FinalRelationGraph";
import { RawDataView } from "./RawDataView";
import { ReplayPanel } from "./ReplayPanel";
import { useEvents } from "../hooks/useEvents";
import {
  useAllSnapshots,
  useSnapshotsList,
} from "../hooks/useSnapshot";
import type {
  AnalysisResult,
  EventRecord,
  RunDetail,
} from "../api/schema";

type TabKey =
  | "attribute_chart"
  | "final_relation_graph"
  | "event_distribution"
  | "replay"
  | "raw_data";

interface Props {
  runId: string;
  runDetail: RunDetail;
  /** Phase A AnalysisResult —— 必然可用（events_by_kind / events_by_actor 来源）。*/
  result: AnalysisResult | null | undefined;
}

const TABS: { key: TabKey; i18nKey: string }[] = [
  { key: "attribute_chart", i18nKey: "finished_side_panel.tabs.attribute_chart" },
  {
    key: "final_relation_graph",
    i18nKey: "finished_side_panel.tabs.final_relation_graph",
  },
  { key: "event_distribution", i18nKey: "finished_side_panel.tabs.event_distribution" },
  { key: "replay", i18nKey: "finished_side_panel.tabs.replay" },
  { key: "raw_data", i18nKey: "finished_side_panel.tabs.raw_data" },
];

export function FinishedSidePanel({ runId, runDetail, result }: Props) {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<TabKey>("attribute_chart");

  // 一次性全拉 events（limit 大到大多数 v0.2 场景一次就够；大场景由 useDownloadEventsJsonl 单独分页）
  const { data: eventsResp } = useEvents(runId, { limit: 5000 });
  const events: EventRecord[] = eventsResp?.events ?? [];

  // FinalRelationGraph / AttributeChart 共享 snapshots —— 本组件不显式拉 snapshots，
  // 让子组件各自用 useAllSnapshots hook（同 queryKey 自动共享 react-query 缓存）

  // Replay/RawData 共享 events；已通过上面 useEvents 拉回
  // （useDownloadEventsJsonl 单独的分页下载路径，不走这里）

  const totalTicks = useMemo(() => {
    if (typeof result?.summary?.total_ticks === "number") {
      return result.summary.total_ticks;
    }
    // fallback：events 最大 tick
    return events.reduce((max, e) => Math.max(max, e.tick), 0);
  }, [result, events]);

  return (
    <section
      aria-label={t("finished_side_panel.title")}
      className="flex flex-col gap-4 rounded-lg border border-border-default bg-surface p-4"
    >
      <div className="flex flex-wrap items-center gap-2 border-b border-border-subtle pb-2">
        <h3 className="mr-2 text-lg font-semibold text-fg-primary">
          {t("finished_side_panel.title")}
        </h3>
        <div role="tablist" className="flex flex-wrap gap-1">
          {TABS.map((tab) => {
            const selected = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                role="tab"
                aria-selected={selected}
                onClick={() => setActiveTab(tab.key)}
                className={`rounded-md border px-3 py-1.5 text-md transition-colors ${
                  selected
                    ? "border-accent bg-accent text-fg-on-accent"
                    : "border-border-default bg-surface text-fg-secondary hover:border-accent"
                }`}
              >
                {t(tab.i18nKey)}
              </button>
            );
          })}
        </div>
      </div>

      <div role="tabpanel">
        {activeTab === "attribute_chart" && (
          <AttributeChart runId={runId} />
        )}
        {activeTab === "final_relation_graph" && (
          <GraphLoader runId={runId} runDetail={runDetail} />
        )}
        {activeTab === "event_distribution" && (
          <EventDistributionChart result={result} />
        )}
        {activeTab === "replay" && (
          <ReplayPanel events={events} totalTicks={totalTicks} />
        )}
        {activeTab === "raw_data" && (
          <RawDataView runId={runId} events={events} />
        )}
      </div>
    </section>
  );
}

/**
 * GraphLoader —— FinalRelationGraph 需要 snapshots，内部懒加载（仅激活 tab 时拉）。
 * 与 AttributeChart 共享 react-query 缓存（同 queryKey），重复激活不重复请求。
 */
function GraphLoader({
  runId,
  runDetail,
}: {
  runId: string;
  runDetail: RunDetail;
}) {
  const { data: ticksList } = useSnapshotsList(runId);
  const ticks = ticksList?.ticks ?? [];
  const { data: snapshots } = useAllSnapshots(runId, ticks);

  return (
    <FinalRelationGraph
      world={runDetail.world}
      scenario={runDetail.scenario}
      snapshots={snapshots ?? []}
    />
  );
}

export default FinishedSidePanel;
