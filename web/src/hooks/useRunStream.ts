/**
 * useRunStream —— PR2 的核心 hook（mockup §11.7 H4 / §11.9 数据流图）。
 *
 * 职责：
 *   1. 管 WebSocket 生命周期（mount 时连，unmount 时关）
 *   2. 累积 events / snapshots / latestTick
 *   3. 处理 PausedEvent / RunFinishedEvent / WsErrorEvent / 重连
 *   4. 把内部状态机 status 暴露给组件层
 *
 * 状态机（mockup §10.6 M3 + §11.9）：
 *   `idle` → connect 调用前的初态
 *   `connecting` → ws 正在握手
 *   `running` → ws OPEN，最近一条事件不是 paused / finished
 *   `paused` → 收到 PausedEvent 或 tick_advanced.data.paused_after=true
 *   `finished` → 收到 RunFinishedEvent
 *   `reconnecting` → ws 异常断开，正在按指数退避重连
 *   `closed` → 客户端主动关闭 / server close 1000 / 4004
 *   `error` → 收到 WsErrorEvent（v0.2 实际不会触发）
 *
 * 调用方典型用法（PR3+ Running 组件）：
 *   ```tsx
 *   const stream = useRunStream(runId);
 *   if (stream.status === "finished") navigate(`/runs/${runId}/finished`);
 *   ```
 *
 * 注意：
 *   - StrictMode dev 双 mount —— effect 会跑两次；ws 也会连两次。这是 dev only。
 *   - prevSnapshotByRunId（mockup §10.7 #41）由 zustand uiStore 维护，不在本 hook
 *     里 —— EntityCard PR4 阶段从 uiStore 读 + 本 hook 推送的 snapshots 算 diff
 */
import { useEffect, useRef, useState } from "react";

import type {
  AnalysisResult,
  EventRecord,
  Snapshot,
  TickResult,
} from "../api/schema";
import {
  connectRunStream,
  type PausedPayload,
  type RunStreamHandle,
  type WsErrorEvent,
} from "../api/ws";

export type RunStreamStatus =
  | "idle"
  | "connecting"
  | "running"
  | "paused"
  | "finished"
  | "reconnecting"
  | "closed"
  | "error";

export interface RunStreamState {
  status: RunStreamStatus;
  /** 最近一次 tick_advanced 的 snapshot.tick；未收到任何 tick 时为 null。*/
  latestTick: number | null;
  /** 累积 events（按 ws 推送顺序）。*/
  events: EventRecord[];
  /** 累积 snapshots（按 tick 升序）—— v0.2 server 每 tick 推送一份。*/
  snapshots: Snapshot[];
  /** 最近一次 PausedEvent 数据；status 切到 paused 时同步更新。*/
  pausedInfo: PausedPayload | null;
  /** RunFinishedEvent 携带的 Phase A AnalysisResult（不含 LLM 增强）。*/
  finishedAnalysis: AnalysisResult | null;
  /** 收到 WsErrorEvent 时的错误体（v0.2 不会有；保留接口）。*/
  errorInfo: WsErrorEvent["data"] | null;
  /** 当前正在尝试的重连次数（0 表示无重连）。*/
  reconnectAttempt: number;
}

export interface UseRunStreamReturn extends RunStreamState {
  /** 客户端主动关闭流 —— 不再重连；调用方在跳转跑完页时使用。*/
  close: () => void;
}

const INITIAL_STATE: RunStreamState = {
  status: "idle",
  latestTick: null,
  events: [],
  snapshots: [],
  pausedInfo: null,
  finishedAnalysis: null,
  errorInfo: null,
  reconnectAttempt: 0,
};

/**
 * 订阅指定 run 的事件流。
 *
 * @param runId  运行 id；undefined 时 hook 进入 idle，不连任何 ws
 */
export function useRunStream(runId: string | undefined): UseRunStreamReturn {
  const [state, setState] = useState<RunStreamState>(INITIAL_STATE);
  const handleRef = useRef<RunStreamHandle | null>(null);

  useEffect(() => {
    if (!runId) {
      setState(INITIAL_STATE);
      return;
    }

    // 切到新 runId 时清空累积态——避免上 run 的 events/snapshots 残留
    setState({ ...INITIAL_STATE, status: "connecting" });

    const handle = connectRunStream(runId, {
      onOpen: () => {
        setState((s) => ({
          ...s,
          status: s.status === "finished" ? s.status : "running",
          reconnectAttempt: 0,
        }));
      },
      onTick: (tick: TickResult) => {
        setState((s) => {
          // snapshot_mode=final_only / never 时 server 推 null —— 仅累加非空
          const nextSnapshots = tick.snapshot
            ? [...s.snapshots, tick.snapshot]
            : s.snapshots;
          return {
            ...s,
            status: tick.paused_after ? "paused" : "running",
            latestTick: tick.tick,
            events: [...s.events, ...(tick.events ?? [])],
            snapshots: nextSnapshots,
          };
        });
      },
      onPaused: (payload) => {
        setState((s) => ({
          ...s,
          status: "paused",
          pausedInfo: payload,
        }));
      },
      onResumed: () => {
        // PR4-fix（session 41）：server resume 推 run_resumed → 切 status=running
        // 触发 Running.tsx auto-step useEffect 启动 step loop
        setState((s) => ({
          ...s,
          status: "running",
          pausedInfo: null,
        }));
      },
      onFinished: (analysis) => {
        setState((s) => ({
          ...s,
          status: "finished",
          finishedAnalysis: analysis,
        }));
      },
      onError: (data) => {
        setState((s) => ({
          ...s,
          status: "error",
          errorInfo: data,
        }));
      },
      onReconnecting: (attempt) => {
        setState((s) => ({
          ...s,
          status: "reconnecting",
          reconnectAttempt: attempt,
        }));
      },
      onClose: (code) => {
        // 1000 / 4004 走 closed；其他场景由 onReconnecting 接管
        if (code === 1000 || code === 4004) {
          setState((s) => ({
            ...s,
            // 已 finished 时不覆盖 status —— finished 优先级高于 closed
            status: s.status === "finished" ? "finished" : "closed",
          }));
        }
      },
    });

    handleRef.current = handle;

    return () => {
      handle.close();
      handleRef.current = null;
    };
  }, [runId]);

  const close = () => {
    handleRef.current?.close();
  };

  return { ...state, close };
}
