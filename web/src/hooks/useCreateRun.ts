/**
 * useCreateRun —— POST /api/v1/runs（创建新 run）。
 *
 * mockup §11.7 H3 / mockup §6 步 2。
 *
 * 成功时把 RunDetail 注入到 `["run", runId]` 缓存 —— 路由跳到跑前页时可立即用，
 * 不必再发 GET /runs/:id。
 *
 * 错误处理：4xx → toast（mockup §9.8 决策 C）；5xx 调用方按需处理（默认 toast）。
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { apiPost, type ApiError } from "../api/client";
import type { CreateRunRequest, RunDetail } from "../api/schema";
import { runQueryKey } from "./useRun";

export function useCreateRun() {
  const queryClient = useQueryClient();
  const { t } = useTranslation();

  return useMutation<RunDetail, ApiError, CreateRunRequest>({
    mutationFn: (req) => apiPost<RunDetail, CreateRunRequest>("/runs", req),
    onSuccess: (data) => {
      queryClient.setQueryData(runQueryKey(data.summary.run_id), data);
      // 列表缓存失效 —— 用户回画廊看不到新 run 列表项时重新拉
      void queryClient.invalidateQueries({ queryKey: ["runs"] });
    },
    onError: (error) => {
      const prefix = error.isServerError()
        ? t("error.toast.5xx_prefix")
        : t("error.toast.4xx_prefix");
      toast.error(`${prefix}: ${error.message}`);
    },
  });
}
