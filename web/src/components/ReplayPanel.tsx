/**
 * ReplayPanel —— 跑完页副区 🎬 tab（mockup §4.5 + PR5.5-spec §3.4）。
 *
 * v0.2 简版：
 *   - tick slider + ◀▶⏮⏭ 4 按钮
 *   - 当前 tick 事件列表（复用 event_templates.formatEvent）
 *   - **不做**真正的"自动播放动画"（留 v0.3+；mockup §9.7）
 *   - 共享 useAllEvents 与 RawDataView 避免重复拉取
 */
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { formatEvent } from "./event_templates";
import type { EventRecord } from "../api/schema";

interface Props {
  /** 已全部拉回的 events（由 FinishedSidePanel 上层从 useEvents 共享）。*/
  events: EventRecord[];
  /** run 的 total_ticks（从 AnalysisResult.summary.total_ticks 或 RunDetail）。*/
  totalTicks: number;
}

export function ReplayPanel({ events, totalTicks }: Props) {
  const { t } = useTranslation();
  const [currentTick, setCurrentTick] = useState(0);

  const eventsByTick = useMemo(() => {
    const map = new Map<number, EventRecord[]>();
    for (const e of events) {
      const bucket = map.get(e.tick) ?? [];
      bucket.push(e);
      map.set(e.tick, bucket);
    }
    return map;
  }, [events]);

  const currentEvents = eventsByTick.get(currentTick) ?? [];

  const clampedMax = Math.max(totalTicks, 0);

  const go = (delta: number) => {
    setCurrentTick((prev) => Math.max(0, Math.min(clampedMax, prev + delta)));
  };

  return (
    <div className="flex flex-col gap-3">
      {/* 时间轴 */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => setCurrentTick(0)}
          disabled={currentTick === 0}
          className="rounded-md border border-border-default bg-surface px-2 py-1 text-md text-fg-primary hover:border-accent disabled:opacity-50"
          aria-label={t("finished_side_panel.replay.first_tick")}
        >
          {t("finished_side_panel.replay.first_tick")}
        </button>
        <button
          type="button"
          onClick={() => go(-1)}
          disabled={currentTick === 0}
          className="rounded-md border border-border-default bg-surface px-2 py-1 text-md text-fg-primary hover:border-accent disabled:opacity-50"
        >
          {t("finished_side_panel.replay.prev_tick")}
        </button>
        <input
          type="range"
          min={0}
          max={clampedMax}
          step={1}
          value={currentTick}
          onChange={(e) => setCurrentTick(Number(e.target.value))}
          className="flex-1"
          aria-label={t("finished_side_panel.final_relation_graph.time_axis")}
        />
        <button
          type="button"
          onClick={() => go(1)}
          disabled={currentTick === clampedMax}
          className="rounded-md border border-border-default bg-surface px-2 py-1 text-md text-fg-primary hover:border-accent disabled:opacity-50"
        >
          {t("finished_side_panel.replay.next_tick")}
        </button>
        <button
          type="button"
          onClick={() => setCurrentTick(clampedMax)}
          disabled={currentTick === clampedMax}
          className="rounded-md border border-border-default bg-surface px-2 py-1 text-md text-fg-primary hover:border-accent disabled:opacity-50"
          aria-label={t("finished_side_panel.replay.last_tick")}
        >
          {t("finished_side_panel.replay.last_tick")}
        </button>
      </div>

      {/* tick 标签 */}
      <p className="font-mono text-base text-fg-tertiary">
        {t("finished_side_panel.final_relation_graph.tick_label", {
          tick: currentTick,
          total: clampedMax,
        })}
      </p>

      {/* 当前 tick 事件 */}
      <section
        aria-label={t("finished_side_panel.replay.current_tick_events", {
          tick: currentTick,
          count: currentEvents.length,
        })}
        className="flex flex-col gap-1 rounded-md border border-border-subtle bg-canvas p-3"
      >
        <h4 className="mb-1 text-md font-medium text-fg-secondary">
          {t("finished_side_panel.replay.current_tick_events", {
            tick: currentTick,
            count: currentEvents.length,
          })}
        </h4>
        {currentEvents.length === 0 ? (
          <p className="text-base text-fg-tertiary">
            {t("finished_side_panel.replay.no_events")}
          </p>
        ) : (
          <ul className="flex flex-col gap-1">
            {currentEvents.map((ev, i) => {
              const formatted = formatEvent(ev, t);
              return (
                <li
                  key={`${ev.tick}-${ev.kind}-${i}`}
                  className="text-md text-fg-secondary"
                >
                  {formatted.text}
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </div>
  );
}

export default ReplayPanel;
