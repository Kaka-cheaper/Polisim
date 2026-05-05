/**
 * useDownloadEventsJsonl —— 客户端分页全拉 events + 拼 jsonl + Blob 下载。
 *
 * mockup §10.5 M2 + §11.7 H10。
 *
 * 设计要点（为什么不走 server endpoint）：
 *   - v0.2 server 无 `/runs/:id/events.jsonl` 流式下载 endpoint
 *   - 只有 GET /events 分页 JSON 响应
 *   - 客户端 while(has_more) 循环拉 → Blob + URL.createObjectURL → 触发浏览器下载
 *   - v0.3+ 可加 server-side 流式 endpoint（mockup §10.5 M2 明确留口）
 *
 * 用途（PR5.5）：
 *   - RawDataView 上的 [📥 下载 events.jsonl] 按钮
 *
 * 暂不做：
 *   - 并行分页（v0.2 场景 ≤1000 events 串行 <2s 可接受）
 *   - 进度条精确控制（total 字段估算 progress，has_more=false 时置 100）
 */
import { useCallback, useState } from "react";

import { apiGet, ApiError } from "../api/client";
import type { EventListResponse, EventRecord } from "../api/schema";

const PAGE_SIZE = 1000;

export interface DownloadState {
  trigger: () => Promise<void>;
  progress: number; // 0-100
  downloading: boolean;
  error: string | null;
}

export function useDownloadEventsJsonl(
  runId: string | undefined,
): DownloadState {
  const [progress, setProgress] = useState(0);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trigger = useCallback(async () => {
    if (!runId || downloading) return;
    setDownloading(true);
    setProgress(0);
    setError(null);

    const allEvents: EventRecord[] = [];
    let offset = 0;
    try {
      while (true) {
        const res = await apiGet<EventListResponse>(
          `/runs/${runId}/events?limit=${PAGE_SIZE}&offset=${offset}`,
        );
        const page = (res.events ?? []) as EventRecord[];
        allEvents.push(...page);
        offset += page.length;
        // total 作 progress 分母；total=0（空 run）直接 100
        if (res.total > 0) {
          setProgress(Math.min(Math.round((offset / res.total) * 100), 99));
        }
        if (!res.has_more || page.length === 0) break;
      }
      const jsonl = allEvents.map((e) => JSON.stringify(e)).join("\n");
      const blob = new Blob([jsonl], { type: "application/x-ndjson" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `events_${runId}.jsonl`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setProgress(100);
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? `${e.code}: ${e.message}`
          : e instanceof Error
            ? e.message
            : "下载失败";
      setError(msg);
    } finally {
      setDownloading(false);
    }
  }, [runId, downloading]);

  return { trigger, progress, downloading, error };
}
