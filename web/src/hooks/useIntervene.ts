/**
 * useIntervene —— 应用人工干预（mockup §11.7 + D-008 / 需求分析 8.3）。
 *
 * 对应 server endpoint：`POST /api/v1/runs/{run_id}/intervene`，
 * body 为 `Intervention`（三种 kind：inject_message / force_action / override_attribute），
 * response 为 `EventRecord(kind=intervention_applied)`。
 *
 * 调用语义：
 *   - 通常在调用前**先 POST /pause**（让 tick 在用户填表期间不推进）
 *   - 提交成功后**调用方负责 POST /resume**（如果原本不是手动暂停）
 *   - 失败：toast 由本 hook 处理；调用方需 catch（避免 unresolved promise rejection）
 *
 * 副作用：
 *   - 不主动失活 React Query 缓存——干预效果会在下一 tick ws 推送时体现，
 *     useRunStream 自动累积 events / snapshots。
 */
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";

import { apiPost, ApiError } from "../api/client";
import type { EventRecord, Intervention } from "../api/schema";

export interface UseInterveneResult {
  mutate: (intervention: Intervention) => void;
  mutateAsync: (intervention: Intervention) => Promise<EventRecord>;
  isPending: boolean;
  error: ApiError | Error | null;
}

export function useIntervene(runId: string | undefined): UseInterveneResult {
  const mutation = useMutation<EventRecord, ApiError, Intervention>({
    mutationFn: async (intervention) => {
      if (!runId) {
        throw new Error("useIntervene: runId is required");
      }
      return apiPost<EventRecord>(
        `/runs/${encodeURIComponent(runId)}/intervene`,
        intervention,
      );
    },
    onError: (err) => {
      const message =
        err instanceof ApiError ? err.message : "Intervention failed";
      toast.error(message);
    },
  });

  return {
    mutate: mutation.mutate,
    mutateAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    error: mutation.error,
  };
}
