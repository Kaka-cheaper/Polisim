/**
 * Finished —— 跑完报告页（PR5 精简版：4 段叙事 + 6 指标 + 重跑/回画廊）。
 *
 * mockup §4.5（精简，副区 tabs / 下载 / 关系图 / 折线 留 PR5.5+PR4.5）。
 *
 * 数据流（mockup §10.5 M1）：
 *   1. useRun(runId)           → RunDetail（summary + scenario）
 *   2. useScenarios()          → 反查 scenario_path（RunSummary 不含 path）
 *   3. useAnalysis(runId, {enhance:true}) → 一次性请求增强版 AnalysisResult
 *
 * 用户交互：
 *   - [← 返回画廊] → navigate("/")
 *   - [🔄 重跑]    → useCreateRun({scenario_path}) + navigate(/runs/:newId/intro)
 *
 * v0.2 PR5 简化：
 *   - 不实现副区 tabs（PR5.5）
 *   - 不实现 enhance 失败回退到 Phase A（一次性请求；失败由 toast 处理）
 *   - 不实现 events.jsonl 下载（PR5.5）
 *   - 不实现 4 段中 tick 引用点击跳副区（依赖副区，PR5.5）
 */
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";

import { FinishedMetricsCard } from "../components/FinishedMetricsCard";
import { FinishedSidePanel } from "../components/FinishedSidePanel";
import { NarrativeReport } from "../components/NarrativeReport";
import { useAnalysis } from "../hooks/useAnalysis";
import { useCreateRun } from "../hooks/useCreateRun";
import { useRun } from "../hooks/useRun";
import { useScenarios } from "../hooks/useScenarios";

export default function Finished() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { runId } = useParams<{ runId: string }>();

  const { data: runDetail, isLoading: runLoading } = useRun(runId);
  const { data: scenarios } = useScenarios();
  // mockup §10.5 M1：双查询模式
  // - phaseA（enhance=false）：必然成功，渲染 6 指标 + 实体比较
  // - enhanced（enhance=true）：可能失败（mock provider 不生成 narrative）→ 4 段 fallback
  const {
    data: phaseA,
    isLoading: phaseALoading,
    error: phaseAError,
  } = useAnalysis(runId, { enhance: false });
  const {
    data: enhanced,
    isLoading: enhanceLoading,
    error: enhanceError,
  } = useAnalysis(runId, { enhance: true });
  const createRun = useCreateRun();

  // 反查 scenario_path（RunSummary 只含 scenario_id，不含 path）
  const scenarioPath = (() => {
    if (!runDetail || !scenarios) return null;
    const match = scenarios.find(
      (s) => s.id === runDetail.summary.scenario_id,
    );
    return match?.path ?? null;
  })();

  const handleBackToGallery = () => {
    void navigate("/");
  };

  const handleRerun = async () => {
    if (!scenarioPath) return; // disable 状态防御
    try {
      const detail = await createRun.mutateAsync({
        scenario_path: scenarioPath,
        llm_provider: "mock",
      });
      void navigate(`/runs/${detail.summary.run_id}/intro`);
    } catch {
      // useCreateRun.onError 已 toast 4xx/5xx
    }
  };

  // ---- error 状态：仅 phaseA 失败才进（致命错误，无任何数据可显示）----
  if (phaseAError) {
    return (
      <main className="mx-auto max-w-layout px-6 py-12">
        <div className="rounded-lg border border-status-danger bg-surface p-6">
          <h1 className="text-3xl font-semibold text-status-danger">
            {t("finished.error.title")}
          </h1>
          <p className="mt-2 text-md text-fg-secondary">
            {phaseAError.message}
          </p>
          <p className="mt-4 text-md text-fg-tertiary">
            {t("finished.error.hint")}
          </p>
        </div>
        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={handleBackToGallery}
            className="rounded-md border border-border-default bg-surface px-4 py-2 text-md font-medium text-fg-primary transition-colors hover:border-accent hover:bg-surface-hover"
          >
            {t("finished.back_to_gallery")}
          </button>
        </div>
      </main>
    );
  }

  // ---- 主体（loading 期间用 null result 触发组件 skeleton）----
  return (
    <main className="mx-auto max-w-layout px-6 py-12">
      {/* 顶部 header */}
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-3 text-4xl font-semibold tracking-tight text-fg-primary">
            <span aria-hidden="true">✓</span>
            {t("finished.header.title")}
          </h1>
          <p className="mt-2 text-md text-fg-tertiary">
            runId:{" "}
            <span className="font-mono text-fg-secondary">{runId}</span>
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleBackToGallery}
            className="rounded-md border border-border-default bg-surface px-4 py-2 text-md font-medium text-fg-primary transition-colors hover:border-accent hover:bg-surface-hover"
          >
            {t("finished.back_to_gallery")}
          </button>
          <button
            type="button"
            onClick={handleRerun}
            disabled={!scenarioPath || createRun.isPending || runLoading}
            className="rounded-md bg-accent px-4 py-2 text-md font-medium text-fg-on-accent transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:bg-surface-active disabled:text-fg-muted"
          >
            {t("finished.rerun")}
          </button>
        </div>
      </header>

      {/* enhance 失败 banner（不阻塞渲染）*/}
      {enhanceError && (
        <div className="mt-6 rounded-lg border border-status-warning bg-surface px-4 py-3 text-md text-fg-secondary">
          ⚠️ {t("finished.narrative.enhance_failed", "LLM 增强失败，仅显示 Phase A 数据")}
        </div>
      )}

      {/* 6 指标卡片（用 phaseA，必然可用）*/}
      <div className="mt-8">
        <FinishedMetricsCard result={phaseALoading ? null : phaseA ?? null} />
      </div>

      {/* 4 段叙事报告（用 enhanced；失败时传 phaseA 让 NarrativeReport 显示 empty fallback）*/}
      <div className="mt-8">
        <NarrativeReport
          result={
            enhanceLoading
              ? null
              : enhanced ?? phaseA ?? null
          }
        />
      </div>

      {/* PR5.5：副区 5 tabs（mockup §4.5）——runId 已由 useParams 保证存在；runDetail 未加载时不渲染 */}
      {runId && runDetail && (
        <div className="mt-10">
          <FinishedSidePanel
            runId={runId}
            runDetail={runDetail}
            result={phaseA}
          />
        </div>
      )}
    </main>
  );
}
