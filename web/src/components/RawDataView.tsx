/**
 * RawDataView —— 跑完页副区 📋 tab（mockup §4.5 + PR5.5-spec §3.5）。
 *
 * 数据源：events 由 FinishedSidePanel 上层提供（与 ReplayPanel 共享，避免重复拉取）。
 *
 * 功能：
 *   - 前 N 行 JSONL 预览（默认 200）
 *   - [📥 下载 events.jsonl] 按钮 → useDownloadEventsJsonl 触发 Blob 下载
 *   - 下载进度条
 *   - 统计摘要（events / ticks / 预估 KB）
 */
import { useMemo } from "react";
import { useTranslation } from "react-i18next";

import { useDownloadEventsJsonl } from "../hooks/useDownloadEventsJsonl";
import type { EventRecord } from "../api/schema";

const PREVIEW_LINES = 200;

interface Props {
  runId: string;
  events: EventRecord[];
}

export function RawDataView({ runId, events }: Props) {
  const { t } = useTranslation();
  const { trigger, progress, downloading, error } = useDownloadEventsJsonl(
    runId,
  );

  const preview = useMemo(
    () =>
      events
        .slice(0, PREVIEW_LINES)
        .map((e) => JSON.stringify(e))
        .join("\n"),
    [events],
  );

  const stats = useMemo(() => {
    const ticks = new Set(events.map((e) => e.tick)).size;
    // 粗略：JSON.stringify 整个数组字节数 ≈ 每行 JSON + '\n'
    const kb = Math.round(
      (events.reduce((sum, e) => sum + JSON.stringify(e).length + 1, 0) || 0) /
        1024,
    );
    return { total: events.length, ticks, kb };
  }, [events]);

  return (
    <div className="flex flex-col gap-3">
      {/* 下载 + 进度 */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => {
            void trigger();
          }}
          disabled={downloading}
          className="rounded-full bg-accent px-3 py-1.5 text-md font-medium text-fg-on-accent transition-all duration-fast ease-out hover:bg-accent-hover hover:shadow-glow-accent disabled:cursor-not-allowed disabled:bg-surface-active disabled:text-fg-muted"
        >
          {downloading
            ? t("finished_side_panel.raw_data.downloading")
            : t("finished_side_panel.raw_data.download")}
        </button>
        {downloading && (
          <span className="text-base text-fg-tertiary">
            {t("finished_side_panel.raw_data.progress", { percent: progress })}
          </span>
        )}
      </div>

      {/* 错误 banner */}
      {error && (
        <p className="rounded-md border border-status-danger bg-surface px-3 py-2 text-base text-status-danger">
          {t("finished_side_panel.raw_data.error", { msg: error })}
        </p>
      )}

      {/* 统计摘要 */}
      <p className="text-base text-fg-tertiary">
        {t("finished_side_panel.raw_data.summary", {
          total: stats.total,
          ticks: stats.ticks,
          kb: stats.kb,
        })}
      </p>

      {/* 预览 */}
      <h4 className="text-md font-medium text-fg-secondary">
        {t("finished_side_panel.raw_data.preview_title", {
          n: Math.min(PREVIEW_LINES, events.length),
        })}
      </h4>
      <pre className="max-h-[400px] overflow-auto rounded-md border border-border-subtle bg-canvas p-3 font-mono text-xs text-fg-secondary">
        {preview}
      </pre>
    </div>
  );
}

export default RawDataView;
