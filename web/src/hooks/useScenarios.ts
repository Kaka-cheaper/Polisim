/**
 * useScenarios —— GET /api/v1/scenarios（场景画廊数据源）。
 *
 * mockup §11.7 H1。
 *
 * 缓存策略：staleTime=30s（场景列表变动频率低；用户切回画廊时不必重 fetch）；
 * 重要：该数据**不**含 Scenario 完整内容，仅 ScenarioSummary 7 字段。
 */
import { useQuery } from "@tanstack/react-query";

import { apiGet, type ApiError } from "../api/client";
import type { ScenarioSummary } from "../api/schema";

export const SCENARIOS_QUERY_KEY = ["scenarios"] as const;

export function useScenarios() {
  return useQuery<ScenarioSummary[], ApiError>({
    queryKey: SCENARIOS_QUERY_KEY,
    queryFn: () => apiGet<ScenarioSummary[]>("/scenarios"),
    staleTime: 30_000,
    retry: 1,
  });
}
