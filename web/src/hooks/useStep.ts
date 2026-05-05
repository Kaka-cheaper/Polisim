/**
 * useStep —— POST /api/v1/runs/:id/step（推进一 tick）。
 *
 * mockup §11.7 H6。
 *
 * 注意 —— ws 流：本 mutation 调用后，server 会推 `tick_advanced` 给 ws 订阅者；
 * `useRunStream` 会自动累积到 events / snapshots。本 hook 的返回值（TickResult）
 * 在跑中页**通常不需要直接用** —— ws 推送即可；调用方主要用 mutate 触发副作用。
 */
import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { apiPost, type ApiError } from "../api/client";
import type { TickResult } from "../api/schema";

export function useStep(runId: string | undefined) {
  const { t } = useTranslation();

  return useMutation<TickResult, ApiError, void>({
    mutationFn: () => {
      if (!runId) throw new Error("runId is required");
      return apiPost<TickResult>(`/runs/${runId}/step`);
    },
    onError: (error) => {
      const prefix = error.isServerError()
        ? t("error.toast.5xx_prefix")
        : t("error.toast.4xx_prefix");
      toast.error(`${prefix}: ${error.message}`);
    },
  });
}
