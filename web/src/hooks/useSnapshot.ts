/**
 * useSnapshot —— GET /api/v1/runs/:id/snapshots/:tick（指定 tick 的快照）。
 *
 * mockup §11.7 H9。
 *
 * 设计要点：
 *   - staleTime: 5 min（跑完后 snapshot 不变）
 *   - runId / tick 任一 undefined 时 disabled
 *
 * 用途（PR5.5）：
 *   - AttributeChart 循环拉所有 tick 的 snapshot（方式 B，见 PR5.5-spec §3.1）
 *   - FinalRelationGraph 在时间轴拖动时按 tick 取 snapshot（共享同一批缓存）
 *
 * 未来 v0.3+：server 加 `GET /snapshots?from_tick&to_tick` 批量 endpoint 替代 N 次调用。
 */
import { useQuery } from "@tanstack/react-query";

import { apiGet, type ApiError } from "../api/client";
import type { Snapshot, SnapshotsListResponse } from "../api/schema";

export const snapshotQueryKey = (runId: string, tick: number) =>
  ["snapshot", runId, tick] as const;

export function useSnapshot(
  runId: string | undefined,
  tick: number | undefined,
) {
  return useQuery<Snapshot, ApiError>({
    queryKey:
      runId !== undefined && tick !== undefined
        ? snapshotQueryKey(runId, tick)
        : ["snapshot", "__pending__", tick ?? -1],
    queryFn: () => apiGet<Snapshot>(`/runs/${runId}/snapshots/${tick}`),
    enabled: Boolean(runId) && tick !== undefined,
    staleTime: 5 * 60_000,
    retry: 1,
  });
}

/**
 * useSnapshotsList —— GET /runs/:id/snapshots（已存的 tick 列表）。
 *
 * 用途：AttributeChart / FinalRelationGraph 先拿 tick 列表，再决定拉哪些 snapshot。
 */
export const snapshotsListQueryKey = (runId: string) =>
  ["snapshots-list", runId] as const;

export function useSnapshotsList(runId: string | undefined) {
  return useQuery<SnapshotsListResponse, ApiError>({
    queryKey: runId
      ? snapshotsListQueryKey(runId)
      : ["snapshots-list", "__pending__"],
    queryFn: () =>
      apiGet<SnapshotsListResponse>(`/runs/${runId}/snapshots`),
    enabled: Boolean(runId),
    staleTime: 5 * 60_000,
    retry: 1,
  });
}

/**
 * useAllSnapshots —— 一次性批量拉指定 tick 列表的所有 Snapshot。
 *
 * 设计要点：
 *   - React hooks 不能动态调用（rules-of-hooks），所以不能循环 useSnapshot
 *   - 改为单 useQuery 内 Promise.all 并行拉取所有 tick
 *   - queryKey 含 tick 列表 → tick 列表变化时自动重取
 *   - 部分 tick 失败（404）会整个 query 失败——server `/snapshots/:tick` 对不存在 tick
 *     返 404 即可，enable 条件要求 tickList 来自 useSnapshotsList 已知存在的 tick
 *
 * 用途（PR5.5）：AttributeChart / FinalRelationGraph 共享
 */
export const allSnapshotsQueryKey = (runId: string, ticks: number[]) =>
  ["all-snapshots", runId, ticks] as const;

export function useAllSnapshots(
  runId: string | undefined,
  ticks: number[] | undefined,
) {
  return useQuery<Snapshot[], ApiError>({
    queryKey:
      runId && ticks
        ? allSnapshotsQueryKey(runId, ticks)
        : ["all-snapshots", "__pending__", ticks ?? []],
    queryFn: async () => {
      if (!runId || !ticks) return [];
      const results = await Promise.all(
        ticks.map((t) =>
          apiGet<Snapshot>(`/runs/${runId}/snapshots/${t}`),
        ),
      );
      // tick 升序排序（server 已升序，但防御）
      return results.slice().sort((a, b) => a.tick - b.tick);
    },
    enabled: Boolean(runId) && Array.isArray(ticks) && ticks.length > 0,
    staleTime: 5 * 60_000,
    retry: 1,
  });
}
