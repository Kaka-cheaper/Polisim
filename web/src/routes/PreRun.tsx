/**
 * PreRun 路由 —— 跑前介绍页（mockup §4.2 + §11.2 P2 + PR3 实施）。
 *
 * 入口：用户在 Gallery 点 [▶ 开始]，`useCreateRun` POST /runs 成功后 navigate 到
 * `/runs/:runId/intro`。本页用 `useRun(runId)` 拉 RunDetail——通常命中 react-query
 * 缓存（Gallery 的 useCreateRun.onSuccess 已把 RunDetail setQueryData 进缓存）。
 *
 * 主体：
 *   1. ScenarioIntroPanel —— 场景叙事 + 实体列表 + 预设事件
 *   2. AdvancedOptionsPanel —— 折叠式高级选项（展示位，disabled=true；v0.3+ 接通重建 run）
 *   3. 底部按钮：[▶ 开始仿真] → navigate `/runs/:runId/run`
 *               [← 选其他场景] → fire-and-forget DELETE 当前 run + 回画廊
 *
 * 异常路径：
 *   - URL 无 runId（理论上不可能；router 已限制）→ 显示 error banner
 *   - useRun 报错 → error banner + 返回画廊按钮
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import { apiDelete } from "../api/client";
import type { CreateRunRequest } from "../api/schema";
import { AdvancedOptionsPanel } from "../components/AdvancedOptionsPanel";
import { ScenarioIntroPanel } from "../components/ScenarioIntroPanel";
import { useRun } from "../hooks/useRun";

export default function PreRun() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { runId } = useParams<{ runId: string }>();

  const { data: runDetail, isLoading, error } = useRun(runId);
  const [advancedExpanded, setAdvancedExpanded] = useState(false);
  const [advancedValue, setAdvancedValue] = useState<Partial<CreateRunRequest>>(
    {},
  );

  const handleStart = () => {
    if (!runId) return;
    navigate(`/runs/${runId}/run`);
  };

  const handleBackToGallery = async () => {
    if (runId) {
      try {
        // fire-and-forget：失败不阻塞导航（用户已在切走的路上）
        await apiDelete(`/runs/${runId}`);
      } catch {
        // 静默：DELETE 失败不影响 UX；server-side run 自然 GC
      }
    }
    navigate("/");
  };

  return (
    <main className="mx-auto max-w-layout px-6 py-8">
      {/* 顶部：返回 + run_id */}
      <header className="flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => void handleBackToGallery()}
          className="rounded-md border border-border-default bg-surface px-3 py-1.5 text-md font-medium text-fg-secondary shadow-inner-highlight transition-all duration-fast ease-out hover:-translate-y-px hover:border-accent hover:bg-surface-hover hover:text-fg-primary focus-visible:shadow-focus focus-visible:outline-none active:translate-y-0"
        >
          {t("pre_run.back")}
        </button>
        <span className="font-mono text-base text-fg-tertiary">
          run_id:{" "}
          <span className="text-fg-secondary">{runId ?? "—"}</span>
        </span>
      </header>

      {isLoading && (
        <div
          className="mt-8 h-96 animate-pulse rounded-xl bg-surface-hover"
          aria-busy="true"
        />
      )}

      {error && (
        <div
          role="alert"
          className="mt-8 rounded-lg border border-status-danger bg-surface p-6"
        >
          <h2 className="text-2xl font-semibold text-status-danger">
            {t("pre_run.error_title")}
          </h2>
          <p className="mt-2 font-mono text-base text-fg-tertiary">
            {error.message}
          </p>
          <button
            type="button"
            onClick={() => void handleBackToGallery()}
            className="mt-4 rounded-md border border-border-default bg-surface px-4 py-2 text-md font-medium text-fg-primary shadow-inner-highlight transition-all duration-fast ease-out hover:-translate-y-px hover:border-accent hover:bg-surface-hover focus-visible:shadow-focus focus-visible:outline-none active:translate-y-0"
          >
            {t("pre_run.back_to_gallery")}
          </button>
        </div>
      )}

      {runDetail && (
        <>
          <div className="mt-8">
            <ScenarioIntroPanel runDetail={runDetail} />
          </div>

          <div className="mt-6">
            <AdvancedOptionsPanel
              value={advancedValue}
              onChange={setAdvancedValue}
              expanded={advancedExpanded}
              onExpandedChange={setAdvancedExpanded}
              disabled
            />
          </div>

          {/* 底部按钮 */}
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <button
              type="button"
              onClick={handleStart}
              className="rounded-md bg-accent px-6 py-3 text-lg font-semibold text-fg-on-accent shadow-inner-highlight transition-all duration-fast ease-out hover:scale-[1.015] hover:bg-accent-hover focus-visible:shadow-focus focus-visible:outline-none active:scale-[0.985]"
            >
              {t("pre_run.start")}
            </button>
            <button
              type="button"
              onClick={() => void handleBackToGallery()}
              className="rounded-md border border-border-default bg-surface px-4 py-2 text-md font-medium text-fg-secondary shadow-inner-highlight transition-all duration-fast ease-out hover:-translate-y-px hover:border-accent hover:bg-surface-hover hover:text-fg-primary focus-visible:shadow-focus focus-visible:outline-none active:translate-y-0"
            >
              {t("pre_run.back_to_gallery")}
            </button>
          </div>
        </>
      )}
    </main>
  );
}
