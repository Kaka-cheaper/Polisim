/**
 * useResume —— POST /api/v1/runs/:id/resume。
 *
 * mockup §11.7 H6 / mockup §6 步 3。
 *
 * 调用流程：用户点 [▶ 恢复] / 干预提交后自动 resume → 本 hook → server 推 tick_advanced
 * → useRunStream 自动累积。
 */
import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { apiPost, type ApiError } from "../api/client";
import type { PauseResumeResponse } from "../api/schema";

export function useResume(runId: string | undefined) {
  const { t } = useTranslation();

  return useMutation<PauseResumeResponse, ApiError, void>({
    mutationFn: () => {
      if (!runId) throw new Error("runId is required");
      return apiPost<PauseResumeResponse>(`/runs/${runId}/resume`);
    },
    onError: (error) => {
      const prefix = error.isServerError()
        ? t("error.toast.5xx_prefix")
        : t("error.toast.4xx_prefix");
      toast.error(`${prefix}: ${error.message}`);
    },
  });
}
