/**
 * useEvents —— GET /api/v1/runs/:id/events（分页查询 + 可选过滤）。
 *
 * mockup §11.7 H8。
 *
 * 设计要点：
 *   - server `EventListResponse.events` 已类型化为 `EventRecord[]`（session 45 F1 修复
 *     bare list → list[EventRecord]，前端无需 cast）
 *   - staleTime 5 min：跑完后 events 不会再变（append-only）
 *   - filters 变化会产生新 queryKey → react-query 自动并行缓存多套过滤结果
 *
 * 用途（PR5.5）：
 *   - RawDataView 一次性全拉 events 做预览 + 下载
 *   - ReplayPanel 按 tick 过滤
 *   - EventDistributionChart 不需要本 hook（走 AnalysisResult.summary 聚合字段）
 */
import { useQuery } from "@tanstack/react-query";

import { apiGet, type ApiError } from "../api/client";
import type { EventListResponse, EventRecord } from "../api/schema";

export interface EventsFilters {
  tick?: number;
  kind?: string;
  actor_id?: string;
  limit?: number;
  offset?: number;
  until_tick?: number;
}

export interface EventsResult {
  events: EventRecord[];
  total: number;
  has_more: boolean;
}

export const eventsQueryKey = (runId: string, filters: EventsFilters) =>
  ["events", runId, filters] as const;

export function useEvents(
  runId: string | undefined,
  filters: EventsFilters = {},
) {
  return useQuery<EventsResult, ApiError>({
    queryKey: runId
      ? eventsQueryKey(runId, filters)
      : ["events", "__pending__", filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.tick !== undefined) params.set("tick", String(filters.tick));
      if (filters.kind) params.set("kind", filters.kind);
      if (filters.actor_id) params.set("actor_id", filters.actor_id);
      if (filters.limit !== undefined)
        params.set("limit", String(filters.limit));
      if (filters.offset !== undefined)
        params.set("offset", String(filters.offset));
      if (filters.until_tick !== undefined)
        params.set("until_tick", String(filters.until_tick));
      const qs = params.toString();
      const raw = await apiGet<EventListResponse>(
        `/runs/${runId}/events${qs ? `?${qs}` : ""}`,
      );
      return {
        events: raw.events ?? [],
        total: raw.total,
        has_more: raw.has_more,
      };
    },
    enabled: Boolean(runId),
    staleTime: 5 * 60_000,
    retry: 1,
  });
}
