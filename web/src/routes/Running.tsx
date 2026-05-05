/**
 * Running 路由 —— 跑中态势页（mockup §4.3 + §4.4 + §11.2 P3 + PR4.1 实施）。
 *
 * 数据流（mockup §11.9）：
 *   1. URL 拿 runId → useRun(runId) cache hit RunDetail
 *   2. useRunStream(runId) 订阅 ws → status 状态机 + events / snapshots / latestTick 累积
 *   3. status="running" 时启动 auto-step loop：每 1000/speed ms 调 useStep.mutateAsync
 *   4. server step → 推 ws tick_advanced → useRunStream 更新 → 组件重渲染
 *   5. ws 推 paused（断点 / pause）→ stop loop（status 切到 paused 时 effect 自动 cleanup）
 *   6. ws 推 run_finished → navigate /runs/:id/finished
 *
 * Layout dispatch：按 `runDetail.scenario.ui_layout`：
 *   - entity_card → EntityCardLayout（PR4.1 唯一可用）
 *   - relation_graph / event_stream → 占位提示「PR4.5 实施」
 *
 * 退出：fire-and-forget DELETE /runs/:id + navigate('/')
 *
 * 不在本组件做（PR4.2+）：
 *   - 干预面板（点实体卡片 → 自动暂停 → InterventionDrawer 表单 → 提交 → 恢复）
 *   - PromptContextModal（[📋 看完整 prompt] 展开 D-016 6 段）
 *   - MiniDashboard（属性折线 + 事件分布）副区
 *   - PausedEvent reason toast（mockup §10.6 M3）
 */
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { apiDelete } from "../api/client";
import { ControlBar } from "../components/ControlBar";
import type { EntityCardEntry } from "../components/EntityCard";
import { InterventionDrawer } from "../components/InterventionDrawer";
import { MiniDashboard } from "../components/MiniDashboard";
import type { Intervention } from "../api/schema";
import { useIntervene } from "../hooks/useIntervene";
import { useRun } from "../hooks/useRun";
import { useRunStream } from "../hooks/useRunStream";
import { usePause } from "../hooks/usePause";
import { useResume } from "../hooks/useResume";
import { useStep } from "../hooks/useStep";
import { EntityCardLayout } from "../layouts/EntityCardLayout";
import { EventStreamLayout } from "../layouts/EventStreamLayout";
import {
  RelationGraphLayout,
  type RelationEntry,
} from "../layouts/RelationGraphLayout";
import { useUiStore } from "../store/ui_store";

export default function Running() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { runId } = useParams<{ runId: string }>();
  const speed = useUiStore((s) => s.speed);
  const setSpeed = useUiStore((s) => s.setSpeed);
  const sidePanelCollapsed = useUiStore((s) => s.sidePanelCollapsed);
  const toggleSidePanel = useUiStore((s) => s.toggleSidePanel);

  const { data: runDetail, error: runError } = useRun(runId);
  const stream = useRunStream(runId);
  const stepMut = useStep(runId);
  const pauseMut = usePause(runId);
  const resumeMut = useResume(runId);
  const interveneMut = useIntervene(runId);
  const stepAsync = stepMut.mutateAsync;
  const interveneAsync = interveneMut.mutateAsync;
  const streamClose = stream.close;

  // ============================================================
  // InterventionDrawer state（mockup §10.6 M4 流程）
  // ============================================================
  const [drawer, setDrawer] = useState<{
    open: boolean;
    entityId: string | null;
    wasPaused: boolean;
  }>({ open: false, entityId: null, wasPaused: false });

  // ============================================================
  // Auto-step loop —— status="running" 时每 1000/speed ms 调一次 step
  // ============================================================
  useEffect(() => {
    if (stream.status !== "running" || !runId) return;

    let cancelled = false;
    const interval = Math.max(50, Math.round(1000 / speed));

    const loop = async () => {
      while (!cancelled) {
        try {
          await stepAsync();
        } catch {
          // useStep.onError 已 toast；break 出循环避免无限错误
          break;
        }
        if (cancelled) break;
        await new Promise<void>((resolve) => setTimeout(resolve, interval));
      }
    };
    void loop();

    return () => {
      cancelled = true;
    };
  }, [stream.status, speed, runId, stepAsync]);

  // ============================================================
  // finished 跳转 —— ws 推 run_finished → 关闭流 + 导航跑完页
  // ============================================================
  useEffect(() => {
    if (stream.status === "finished" && runId) {
      streamClose();
      navigate(`/runs/${runId}/finished`);
    }
  }, [stream.status, runId, navigate, streamClose]);

  // ============================================================
  // PausedEvent reason toast —— mockup §10.6 M3 简化版（PR4.1 仅 toast，不做 banner）
  // ============================================================
  useEffect(() => {
    const info = stream.pausedInfo;
    if (!info) return;
    const reasonText =
      info.reason === "breakpoint"
        ? t("control_bar.paused_reason.breakpoint", {
            ids: info.breakpoint_ids.join(", "),
          })
        : t(`control_bar.paused_reason.${info.reason}`);
    toast.info(reasonText);
    // pausedInfo 是同一 PausedPayload 引用直到下次 paused —— 不会重复触发
  }, [stream.pausedInfo, t]);

  // ============================================================
  // 组装 EntityCardEntry[] —— 把 runDetail / stream 拼成 Layout 需要的形状
  // ============================================================
  const entries = useMemo<EntityCardEntry[]>(() => {
    if (!runDetail) return [];

    const latestSnapshot = stream.snapshots.at(-1);
    const prevSnapshot =
      stream.snapshots.length >= 2 ? stream.snapshots.at(-2) : null;
    const summary = latestSnapshot?.entity_state_summary ?? {};
    const prevSummary = prevSnapshot?.entity_state_summary ?? {};

    return runDetail.scenario.entities.map((e) => {
      const typeSchema = runDetail.world.entity_types[e.type];
      const decisionMode = typeSchema?.decision_mode ?? "rule";
      // 当前属性：优先取 ws snapshot；snapshot 缺失（如尚未推 tick 1）回退场景声明
      const attrs =
        summary[e.id] ?? (e.attributes as Record<string, unknown>) ?? {};
      const prevAttrs = prevSummary[e.id] ?? null;
      const latestDecision = stream.events.findLast(
        (ev) => ev.kind === "decision_proposed" && ev.actor_id === e.id,
      );
      const latestAction = stream.events.findLast(
        (ev) => ev.kind === "action_executed" && ev.actor_id === e.id,
      );
      return {
        id: e.id,
        type: e.type,
        decisionMode,
        attributes: attrs,
        prevAttributes: prevAttrs,
        latestDecision,
        latestAction,
      };
    });
  }, [runDetail, stream.snapshots, stream.events]);

  const environment =
    stream.snapshots.at(-1)?.environment_state ??
    (runDetail?.scenario.environment as Record<string, unknown> | undefined);

  // ============================================================
  // RelationGraphLayout 数据：relations + latestDecision
  // ============================================================
  const relations = useMemo<RelationEntry[]>(() => {
    const latestSnapshot = stream.snapshots.at(-1);
    const raw = latestSnapshot?.relation_state_summary;
    if (!Array.isArray(raw)) {
      // snapshot 还没推时回退场景声明
      const fallback = runDetail?.scenario.relations ?? [];
      return fallback.map((r) => ({
        type: r.type,
        source: r.source,
        target: r.target,
        value: typeof r.value === "number" ? r.value : 0,
      }));
    }
    return raw
      .filter((r): r is Record<string, unknown> => typeof r === "object" && r !== null)
      .map((r) => ({
        type: String(r.type ?? "?"),
        source: String(r.source ?? "?"),
        target: String(r.target ?? "?"),
        value: typeof r.value === "number" ? r.value : 0,
      }));
  }, [stream.snapshots, runDetail]);

  const latestDecision = useMemo(
    () =>
      [...stream.events]
        .reverse()
        .find((ev) => ev.kind === "decision_proposed") ?? null,
    [stream.events],
  );

  // ============================================================
  // EntityCard 干预入口 + Drawer 三流程（mockup §6 步 4 / §10.6 M4）
  // ============================================================
  const selectedEntity = useMemo(
    () => entries.find((e) => e.id === drawer.entityId) ?? null,
    [entries, drawer.entityId],
  );

  const handleEntityClick = (id: string) => {
    const wasPaused =
      stream.status === "paused" || stream.status === "finished";
    setDrawer({ open: true, entityId: id, wasPaused });
    // 仅 running 时主动 pause；paused/finished 不重复 pause
    if (stream.status === "running") {
      pauseMut.mutate();
    }
  };

  const closeDrawer = () => {
    setDrawer({ open: false, entityId: null, wasPaused: false });
  };

  const handleDrawerCancel = () => {
    // 用户原本不是手动暂停 → 自动恢复；原本暂停 → 保持
    if (!drawer.wasPaused && stream.status === "paused") {
      resumeMut.mutate();
    }
    closeDrawer();
  };

  const handleDrawerSubmit = async (intervention: Intervention) => {
    try {
      const event = await interveneAsync(intervention);
      toast.success(
        t("intervention.success", {
          kind: intervention.kind,
          target: intervention.target_actor ?? "*",
          tick: event.tick,
        }),
      );
      if (drawer.wasPaused) {
        toast.info(t("intervention.auto_resume_skipped"));
      } else if (stream.status === "paused") {
        resumeMut.mutate();
      }
      closeDrawer();
    } catch {
      // useIntervene.onError 已 toast；保持 drawer 打开让用户修正后重试
    }
  };

  // ============================================================
  // 控制条回调
  // ============================================================
  const handleExit = async () => {
    streamClose();
    if (runId) {
      try {
        await apiDelete(`/runs/${runId}`);
      } catch {
        // 静默：用户已在切走的路上
      }
    }
    navigate("/");
  };

  // ============================================================
  // 渲染
  // ============================================================
  if (runError) {
    return (
      <main className="mx-auto max-w-layout px-6 py-8">
        <div
          role="alert"
          className="rounded-lg border border-status-danger bg-surface p-6"
        >
          <h2 className="text-2xl font-semibold text-status-danger">
            {t("running.error_title")}
          </h2>
          <p className="mt-2 font-mono text-base text-fg-tertiary">
            {runError.message}
          </p>
          <button
            type="button"
            onClick={() => navigate("/")}
            className="mt-4 rounded-md border border-border-default bg-surface px-4 py-2 text-md font-medium text-fg-primary transition-colors duration-fast hover:border-accent hover:bg-surface-hover"
          >
            {t("pre_run.back_to_gallery")}
          </button>
        </div>
      </main>
    );
  }

  if (!runDetail) {
    return (
      <main className="mx-auto max-w-layout px-6 py-8">
        <p className="text-fg-tertiary">{t("running.loading")}</p>
      </main>
    );
  }

  const layout = runDetail.scenario.ui_layout;

  return (
    <>
      <ControlBar
        status={stream.status}
        currentTick={stream.latestTick ?? 0}
        totalTicks={runDetail.summary.total_ticks}
        speed={speed}
        reconnectAttempt={stream.reconnectAttempt}
        sidePanelCollapsed={sidePanelCollapsed}
        onPause={() => pauseMut.mutate()}
        onResume={() => resumeMut.mutate()}
        onStep={() => stepMut.mutate()}
        onSpeedChange={setSpeed}
        onSidePanelToggle={toggleSidePanel}
        onExit={() => void handleExit()}
      />

      <main className="mx-auto max-w-layout px-6 py-6">
        <div
          className={
            sidePanelCollapsed
              ? ""
              : "grid gap-4 xl:grid-cols-[1fr_22rem]"
          }
        >
          <div className="min-w-0">
            {layout === "entity_card" && (
              <EntityCardLayout
                entries={entries}
                environment={environment}
                onEntityClick={handleEntityClick}
              />
            )}
            {layout === "relation_graph" && (
              <RelationGraphLayout
                entries={entries}
                relations={relations}
                relationTypes={runDetail.world.relation_types}
                latestDecision={latestDecision}
                onEntityClick={handleEntityClick}
              />
            )}
            {layout === "event_stream" && (
              <EventStreamLayout
                entries={entries}
                events={stream.events}
                onEntityClick={handleEntityClick}
              />
            )}
          </div>

          {/* MiniDashboard 副区——所有 layout 共用（PR4.5：放开三个 layout 都显示）*/}
          {!sidePanelCollapsed && (
            <MiniDashboard
              entries={entries}
              snapshots={stream.snapshots}
              events={stream.events}
            />
          )}
        </div>
      </main>

      {/* InterventionDrawer —— page-level singleton；selectedEntity 为 null 不渲染 */}
      {selectedEntity && (
        <InterventionDrawer
          open={drawer.open}
          selectedEntityId={selectedEntity.id}
          selectedEntityType={selectedEntity.type}
          selectedAttributes={selectedEntity.attributes}
          worldDef={runDetail.world}
          defaultTick={(stream.latestTick ?? 0) + 1}
          isSubmitting={interveneMut.isPending}
          onSubmit={(intervention) => void handleDrawerSubmit(intervention)}
          onCancel={handleDrawerCancel}
        />
      )}
    </>
  );
}
