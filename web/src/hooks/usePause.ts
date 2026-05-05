/**
 * usePause —— POST /api/v1/runs/:id/pause。
 *
 * mockup §11.7 H6 / mockup §10.6 M3（PausedEvent ws 监听同步）。
 *
 * 与 ws PausedEvent 的 race：调用方采"乐观更新" —— REST 调用立即触发 UI 切到 paused，
 * ws PausedEvent 抵达时再确认（或纠正 reason）。本 hook 不做 optimistic 状态—调用方
 * 自行管理（mockup §10.6 M4 推荐做法）。
 */
import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { apiPost, type ApiError } from "../api/client";
import type { PauseResumeResponse } from "../api/schema";

export function usePause(runId: string | undefined) {
  const { t } = useTranslation();

  return useMutation<PauseResumeResponse, ApiError, void>({
    mutationFn: () => {
      if (!runId) throw new Error("runId is required");
      return apiPost<PauseResumeResponse>(`/runs/${runId}/pause`);
    },
    onError: (error) => {
      const prefix = error.isServerError()
        ? t("error.toast.5xx_prefix")
        : t("error.toast.4xx_prefix");
      toast.error(`${prefix}: ${error.message}`);
    },
  });
}
