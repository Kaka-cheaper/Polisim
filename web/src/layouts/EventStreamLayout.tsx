/**
 * EventStreamLayout —— 跑中主区"事件流"布局（mockup §4.3.3 + §11.3 L3）。
 *
 * 左侧栏：实体小卡片（id / decision_mode / 1-2 关键属性 / [📌 干预] 按钮）
 * 主区：事件瀑布——按 tick 分组，每条事件用 event_templates 格式化为自然语言
 *
 * 数据组装由 Running 完成；本组件只负责渲染 + 干预入口委派。
 *
 * 不在本组件做：
 *   - 数据组装 / 干预浮层 / PromptContext modal → Running + 现有组件
 *   - 自动滚动到最新 tick → ref 滚动行为；当前简化：列表 column-reverse
 */
import { useMemo, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";

import type { EntityCardEntry } from "../components/EntityCard";
import { groupEventsByTick } from "../components/event_templates";
import type { EventRecord } from "../api/schema";

interface Props {
  entries: EntityCardEntry[];
  events: EventRecord[];
  onEntityClick?: (id: string) => void;
}

const MODE_BG: Record<string, string> = {
  llm: "bg-status-info/15 border-status-info/40",
  rule: "bg-fg-tertiary/15 border-fg-tertiary/40",
  random: "bg-accent/15 border-accent/40",
};

const MODE_LABEL: Record<string, string> = {
  llm: "LLM",
  rule: "RULE",
  random: "RAND",
};

function formatAttr(v: unknown): string {
  if (typeof v === "number") {
    return Number.isInteger(v) ? String(v) : v.toFixed(2);
  }
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "string") return v;
  return JSON.stringify(v);
}

export function EventStreamLayout({ entries, events, onEntityClick }: Props) {
  const { t } = useTranslation();
  const grouped = useMemo(() => groupEventsByTick(events, t), [events, t]);
  const streamRef = useRef<HTMLDivElement | null>(null);

  // 自动滚到底部（最新 tick 群）
  useEffect(() => {
    const el = streamRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [grouped.length]);

  return (
    <div className="grid grid-cols-1 gap-4 tablet:grid-cols-[16rem_1fr]">
      {/* 左侧栏：实体小卡片 */}
      <aside className="flex flex-col gap-3">
        <h3 className="text-md font-medium uppercase tracking-wide text-fg-tertiary">
          {t("event_stream.entities_title")}
        </h3>
        {entries.map((entry) => {
          const modeBg = MODE_BG[entry.decisionMode] ?? MODE_BG.rule;
          // 取前 2 个数值属性作 mini summary
          const numericKeys = Object.entries(entry.attributes)
            .filter(([, v]) => typeof v === "number")
            .slice(0, 2);
          return (
            <div
              key={entry.id}
              className={`rounded-lg border bg-surface px-3 py-2 ${modeBg}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-md font-semibold text-fg-primary">
                  {entry.id}
                </span>
                <span className="rounded bg-canvas px-1.5 py-0.5 text-xs font-medium text-fg-tertiary">
                  {MODE_LABEL[entry.decisionMode] ?? entry.decisionMode}
                </span>
              </div>
              {numericKeys.length > 0 && (
                <ul className="mt-1.5 flex flex-col gap-0.5 text-sm font-mono">
                  {numericKeys.map(([k, v]) => (
                    <li key={k} className="text-fg-tertiary">
                      <span>{k}</span>{" "}
                      <span className="text-fg-secondary">
                        = {formatAttr(v)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              {onEntityClick && (
                <button
                  type="button"
                  onClick={() => onEntityClick(entry.id)}
                  className="mt-2 w-full rounded border border-border-default bg-surface px-2 py-1 text-xs font-medium text-fg-primary transition-colors hover:border-accent hover:bg-surface-hover"
                >
                  {t("entity_card.intervene")}
                </button>
              )}
            </div>
          );
        })}
      </aside>

      {/* 主区：事件瀑布 */}
      <section
        ref={streamRef}
        className="rounded-lg border border-border-subtle bg-canvas px-4 py-3"
        style={{ height: "60vh", overflowY: "auto" }}
        aria-label={t("event_stream.stream_aria")}
      >
        {grouped.length === 0 ? (
          <p className="text-center text-fg-tertiary">
            {t("event_stream.no_events")}
          </p>
        ) : (
          <ol className="flex flex-col gap-3">
            {grouped.map(({ tick, items }) => (
              <li key={tick} className="border-l-2 border-border-default pl-3">
                <div className="text-md font-semibold text-fg-tertiary">
                  ⏱ tick {tick}
                </div>
                <ul className="mt-1 flex flex-col gap-1 text-md text-fg-secondary">
                  {items.map((it, i) => (
                    <li key={`${tick}-${i}`} className="font-mono">
                      {it.text}
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}

export default EventStreamLayout;
