/**
 * ControlBar —— 跑中页顶部控制条（mockup §4.4.1 + §11.4 C2）。
 *
 * 职责：
 *   - tick 计数 + 状态 badge（paused 时 pulse 呼吸灯）
 *   - 暂停 / 恢复 切换按钮（按 status 自动切换文案）
 *   - 单步按钮（仅 paused 时启用；session 41 PR4-fix 后 server 自动 resume+step+pause）
 *   - 速度选择（4 档 0.5x / 1x / 2x / 4x，对接 zustand uiStore.speed）
 *   - 副区按钮（toggle FinishedSidePanel / MiniDashboard）
 *   - 退出按钮（fire-and-forget DELETE + navigate '/'）
 */
import { useTranslation } from "react-i18next";

import type { Speed } from "../store/ui_store";
import type { RunStreamStatus } from "../hooks/useRunStream";

interface Props {
  status: RunStreamStatus;
  currentTick: number;
  totalTicks: number;
  speed: Speed;
  reconnectAttempt?: number;
  sidePanelCollapsed: boolean;
  onPause: () => void;
  onResume: () => void;
  onStep: () => void;
  onSpeedChange: (s: Speed) => void;
  onSidePanelToggle: () => void;
  onExit: () => void;
}

const SPEED_OPTIONS: readonly Speed[] = [0.5, 1, 2, 4] as const;

const STATUS_TONE: Record<RunStreamStatus, string> = {
  idle: "text-fg-tertiary",
  connecting: "text-fg-tertiary",
  running: "text-status-success",
  paused: "text-polisim-paused",
  finished: "text-fg-tertiary",
  reconnecting: "text-status-warning",
  closed: "text-fg-tertiary",
  error: "text-status-danger",
};

export function ControlBar({
  status,
  currentTick,
  totalTicks,
  speed,
  reconnectAttempt = 0,
  sidePanelCollapsed,
  onPause,
  onResume,
  onStep,
  onSpeedChange,
  onSidePanelToggle,
  onExit,
}: Props) {
  const { t } = useTranslation();

  const isRunning = status === "running";
  const isPaused = status === "paused";
  const isTerminal = status === "finished" || status === "closed" || status === "error";
  const statusKey = status === "reconnecting"
    ? `control_bar.status.${status}`
    : `control_bar.status.${status}`;
  const statusLabel = status === "reconnecting"
    ? t(statusKey, { attempt: reconnectAttempt })
    : t(statusKey);

  return (
    <div
      className="sticky top-[var(--layout-header-height)] z-sticky flex flex-wrap items-center gap-3 border-b border-border-subtle bg-panel/90 px-4 py-3 shadow-inner-highlight backdrop-blur-md"
      style={{ height: "var(--layout-control-bar-height)" }}
    >
      {/* tick 计数 */}
      <span className="font-mono text-md text-fg-primary">
        {t("control_bar.tick_label", {
          current: currentTick,
          total: totalTicks,
        })}
      </span>

      {/* 状态 badge —— paused 时 yellow pulse 呼吸灯（session 44 视觉升级） */}
      <span
        className={`flex items-center gap-1.5 rounded-sm bg-surface-active px-2 py-0.5 text-base font-medium transition-colors duration-normal ease-out ${STATUS_TONE[status]}`}
      >
        {isPaused && (
          <span
            className="inline-block h-1.5 w-1.5 animate-pulse rounded-circle bg-polisim-paused"
            aria-hidden="true"
          />
        )}
        {isRunning && (
          <span
            className="inline-block h-1.5 w-1.5 animate-pulse rounded-circle bg-status-success"
            aria-hidden="true"
          />
        )}
        {statusLabel}
      </span>

      {/* 暂停 / 恢复 切换 */}
      {isRunning && (
        <button
          type="button"
          onClick={onPause}
          className="rounded-md border border-border-default bg-surface px-3 py-1.5 text-base font-medium text-fg-primary shadow-inner-highlight transition-all duration-fast ease-out hover:-translate-y-px hover:border-accent hover:bg-surface-hover focus-visible:shadow-focus focus-visible:outline-none active:translate-y-0"
        >
          ⏸ {t("control_bar.pause")}
        </button>
      )}
      {!isRunning && !isTerminal && (
        <button
          type="button"
          onClick={onResume}
          disabled={status === "connecting"}
          className="rounded-full bg-accent px-3 py-1.5 text-base font-medium text-fg-on-accent shadow-inner-highlight transition-all duration-fast ease-out hover:scale-[1.015] hover:bg-accent-hover hover:shadow-glow-accent focus-visible:shadow-focus focus-visible:outline-none active:scale-[0.985] disabled:cursor-not-allowed disabled:bg-surface-active disabled:text-fg-muted disabled:hover:scale-100"
        >
          ▶ {t("control_bar.resume")}
        </button>
      )}

      {/* 单步：paused 时可用 */}
      <button
        type="button"
        onClick={onStep}
        disabled={!isPaused}
        className="rounded-md border border-border-default bg-surface px-3 py-1.5 text-base font-medium text-fg-primary shadow-inner-highlight transition-all duration-fast ease-out hover:-translate-y-px hover:border-accent hover:bg-surface-hover focus-visible:shadow-focus focus-visible:outline-none active:translate-y-0 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
      >
        ⏭ {t("control_bar.step")}
      </button>

      {/* 速度选择 */}
      <div
        role="group"
        aria-label={t("control_bar.speed_label")}
        className="flex items-center gap-1 rounded-md border border-border-subtle bg-canvas p-0.5"
      >
        {SPEED_OPTIONS.map((opt) => {
          const active = opt === speed;
          return (
            <button
              key={opt}
              type="button"
              onClick={() => onSpeedChange(opt)}
              className={`rounded-sm px-2 py-1 text-base font-mono transition-all duration-fast ease-out focus-visible:shadow-focus focus-visible:outline-none ${
                active
                  ? "bg-accent text-fg-on-accent shadow-inner-highlight"
                  : "text-fg-tertiary hover:bg-surface-hover hover:text-fg-primary"
              }`}
              aria-pressed={active}
            >
              {opt}x
            </button>
          );
        })}
      </div>

      {/* 右侧 spacer */}
      <span className="ml-auto" aria-hidden="true" />

      {/* 副区按钮（toggle MiniDashboard） */}
      <button
        type="button"
        onClick={onSidePanelToggle}
        aria-pressed={!sidePanelCollapsed}
        title={
          sidePanelCollapsed
            ? t("control_bar.side_panel_show")
            : t("control_bar.side_panel_hide")
        }
        className={`rounded-md border px-3 py-1.5 text-base font-medium shadow-inner-highlight transition-all duration-fast ease-out hover:-translate-y-px focus-visible:shadow-focus focus-visible:outline-none active:translate-y-0 ${
          !sidePanelCollapsed
            ? "border-accent bg-accent text-fg-on-accent hover:bg-accent-hover"
            : "border-border-default bg-surface text-fg-secondary hover:border-accent hover:bg-surface-hover hover:text-fg-primary"
        }`}
      >
        📊
      </button>

      {/* 退出 */}
      <button
        type="button"
        onClick={onExit}
        className="rounded-md border border-border-default bg-surface px-3 py-1.5 text-base font-medium text-fg-secondary shadow-inner-highlight transition-all duration-fast ease-out hover:-translate-y-px hover:border-status-danger hover:bg-surface-hover hover:text-status-danger focus-visible:shadow-focus focus-visible:outline-none active:translate-y-0"
      >
        🚪 {t("control_bar.exit")}
      </button>
    </div>
  );
}

export default ControlBar;
