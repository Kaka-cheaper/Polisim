/**
 * ControlBar —— 跑中页顶部控制条（mockup §4.4.1 + §11.4 C2）。
 *
 * PR4.1 范围：
 *   - tick 计数 + 状态 badge
 *   - 暂停 / 恢复 切换按钮（按 status 自动切换文案）
 *   - 单步按钮（仅 paused 时启用）
 *   - 速度选择（4 档 0.5x / 1x / 2x / 4x，对接 zustand uiStore.speed）
 *   - 副区按钮（PR5 启用，当前 disabled 占位）
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
      className="sticky top-[var(--layout-header-height)] z-sticky flex flex-wrap items-center gap-3 border-b border-border-subtle bg-panel px-4 py-3"
      style={{ height: "var(--layout-control-bar-height)" }}
    >
      {/* tick 计数 */}
      <span className="font-mono text-md text-fg-primary">
        {t("control_bar.tick_label", {
          current: currentTick,
          total: totalTicks,
        })}
      </span>

      {/* 状态 badge */}
      <span
        className={`rounded-sm bg-surface-active px-2 py-0.5 text-base font-medium ${STATUS_TONE[status]}`}
      >
        {statusLabel}
      </span>

      {/* 暂停 / 恢复 切换 */}
      {isRunning && (
        <button
          type="button"
          onClick={onPause}
          className="rounded-md border border-border-default bg-surface px-3 py-1.5 text-base font-medium text-fg-primary transition-colors duration-fast hover:border-accent hover:bg-surface-hover"
        >
          ⏸ {t("control_bar.pause")}
        </button>
      )}
      {!isRunning && !isTerminal && (
        <button
          type="button"
          onClick={onResume}
          disabled={status === "connecting"}
          className="rounded-md bg-accent px-3 py-1.5 text-base font-medium text-fg-on-accent transition-colors duration-fast hover:bg-accent-hover disabled:cursor-not-allowed disabled:bg-surface-active disabled:text-fg-muted"
        >
          ▶ {t("control_bar.resume")}
        </button>
      )}

      {/* 单步：paused 时可用 */}
      <button
        type="button"
        onClick={onStep}
        disabled={!isPaused}
        className="rounded-md border border-border-default bg-surface px-3 py-1.5 text-base font-medium text-fg-primary transition-colors duration-fast hover:border-accent hover:bg-surface-hover disabled:cursor-not-allowed disabled:opacity-50"
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
              className={`rounded-sm px-2 py-1 text-base font-mono transition-colors duration-fast ${
                active
                  ? "bg-accent text-fg-on-accent"
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

      {/* 副区按钮（PR4.3 接通 MiniDashboard） */}
      <button
        type="button"
        onClick={onSidePanelToggle}
        aria-pressed={!sidePanelCollapsed}
        title={
          sidePanelCollapsed
            ? t("control_bar.side_panel_show")
            : t("control_bar.side_panel_hide")
        }
        className={`rounded-md border px-3 py-1.5 text-base font-medium transition-colors duration-fast ${
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
        className="rounded-md border border-border-default bg-surface px-3 py-1.5 text-base font-medium text-fg-secondary transition-colors duration-fast hover:border-status-danger hover:bg-surface-hover hover:text-status-danger"
      >
        🚪 {t("control_bar.exit")}
      </button>
    </div>
  );
}

export default ControlBar;
