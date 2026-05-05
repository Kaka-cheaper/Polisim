/**
 * useRun —— GET /api/v1/runs/:id（RunDetail：summary + world + scenario + runtime_config）。
 *
 * mockup §11.7 H2。
 *
 * 用途：跑前页 / 跑中页加载时拿完整 world + scenario 配置；
 * 跑中态势的实时更新走 `useRunStream`，不靠本 hook 的 refetch。
 *
 * runId 为 undefined 时 disabled —— 路由 useParams 还没 hydrate 的瞬间安全。
 */
import { useQuery } from "@tanstack/react-query";

import { apiGet, type ApiError } from "../api/client";
import type { RunDetail } from "../api/schema";

export const runQueryKey = (runId: string) => ["run", runId] as const;

export function useRun(runId: string | undefined) {
  return useQuery<RunDetail, ApiError>({
    queryKey: runId ? runQueryKey(runId) : ["run", "__pending__"],
    queryFn: () => apiGet<RunDetail>(`/runs/${runId}`),
    enabled: Boolean(runId),
    staleTime: 30_000,
    retry: 1,
  });
}
