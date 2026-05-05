/**
 * useAnalysis —— GET /api/v1/runs/:id/analysis?enhance=...
 *
 * mockup §11.7 H7（精简版 useFinishedRun，PR5 第一阶段；FinishedSidePanel / 副区
 * 数据加载留 PR5.5）。
 *
 * 流程（mockup §10.5 M1）：
 *   - `enhance=false`（默认）→ 立即返回 Phase A 结果（已在 server 跑完时缓存）
 *   - `enhance=true` → server 触发 LLM 增强；同步等待结果（含 4 段 narrative）
 *
 * v0.2 PR5 简化：跑完页一次性请求 enhance=true；增强失败由 react-query
 * onError 处理（toast + Phase A fallback 由 Finished route 内手动 fetch enhance=false）。
 *
 * runId 为 undefined 时 disabled —— 路由 useParams hydrate 期间安全。
 */
import { useQuery } from "@tanstack/react-query";

import { apiGet, type ApiError } from "../api/client";
import type { AnalysisResult } from "../api/schema";

export const analysisQueryKey = (runId: string, enhance: boolean) =>
  ["analysis", runId, enhance] as const;

export function useAnalysis(
  runId: string | undefined,
  options: { enhance?: boolean } = {},
) {
  const enhance = options.enhance ?? false;
  return useQuery<AnalysisResult, ApiError>({
    queryKey: runId
      ? analysisQueryKey(runId, enhance)
      : ["analysis", "__pending__", enhance],
    queryFn: () =>
      apiGet<AnalysisResult>(
        `/runs/${runId}/analysis${enhance ? "?enhance=true" : ""}`,
      ),
    enabled: Boolean(runId),
    // Phase A 数据稳定（runtime 跑完后不变）；enhance=true 也只在 server 主动重跑时变
    staleTime: 5 * 60_000,
    retry: 1,
  });
}
