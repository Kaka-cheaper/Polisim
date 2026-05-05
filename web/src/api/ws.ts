/**
 * WebSocket 客户端 —— `connectRunStream`（PR2 核心）。
 *
 * 职责（mockup §11.4 / D-017 §4）：
 *   1. 连 `WS /api/v1/runs/:id/stream`
 *   2. 解 server 推送的 typed event（discriminated union 走 `event` 字段）
 *   3. 自动重连（指数退避；正常关闭码 1000 / 4004 不重连）
 *   4. 客户端主动 close 时不重连
 *
 * 不做的事（mockup §11.10 N1/N2 — v0.3+）：
 *   - 不发 Pong（v0.2 server 不发 Ping）
 *   - 不发 ErrorEvent 处理（server v0.2 不会推这个事件）
 *
 * **手动维护的 WS event schema**（与 `server/api/v1/ws_events.py` 同步）：
 *   - openapi-typescript 不生成 WS schema（FastAPI 不把 WS 写进 openapi.json）
 *   - 这里手写一份，与 server 字段一一对应；server 改 ws_events.py 时同步本文件
 */
import { API_BASE, API_PREFIX } from "./client";
import type { AnalysisResult, TickResult } from "./schema";

// =============================================================================
// WS server → client 事件 typed schema
// =============================================================================

/**
 * 暂停事件载荷（对齐 `server/api/v1/ws_events.py:PausedPayload`）。
 */
export interface PausedPayload {
  tick: number;
  breakpoint_ids: string[];
  reason: "manual" | "every_tick" | "breakpoint" | "total_ticks";
}

export interface TickAdvancedEvent {
  event: "tick_advanced";
  data: TickResult;
}

export interface PausedEvent {
  event: "paused";
  data: PausedPayload;
}

/**
 * 恢复载荷（对齐 `server/api/v1/ws_events.py:RunResumedPayload`）。
 */
export interface RunResumedPayload {
  tick: number;
}

/**
 * 恢复事件——server `RunService.resume` 推送（PR4-fix，session 41）。
 *
 * 与 PausedEvent 对称：resume 后推这条让 client useRunStream 切 status="running"，
 * 避免死锁（详细设计说明见 ws_events.py:RunResumedEvent docstring）。
 */
export interface RunResumedEvent {
  event: "run_resumed";
  data: RunResumedPayload;
}

export interface RunFinishedEvent {
  event: "run_finished";
  data: AnalysisResult;
}

/**
 * 错误事件 —— v0.2 server 实际不推（保留 schema 给 v0.3+，mockup §11.10 N1）。
 */
export interface WsErrorEvent {
  event: "error";
  data: { code: string; message: string; detail?: unknown };
}

export type WSServerEvent =
  | TickAdvancedEvent
  | PausedEvent
  | RunResumedEvent
  | RunFinishedEvent
  | WsErrorEvent;

// =============================================================================
// Callbacks 与 Handle
// =============================================================================

export interface RunStreamCallbacks {
  /** 收到 tick_advanced（每 tick 完毕）。*/
  onTick?: (data: TickResult) => void;
  /** 收到 paused（manual / every_tick / breakpoint / total_ticks）。*/
  onPaused?: (data: PausedPayload) => void;
  /** 收到 run_resumed（POST /resume 后 server 推送，PR4-fix session 41）。*/
  onResumed?: (data: RunResumedPayload) => void;
  /** 收到 run_finished（最后一条；含 Phase A AnalysisResult；server 随后 close 1000）。*/
  onFinished?: (data: AnalysisResult) => void;
  /** 收到 error（v0.2 server 不推；保留接口）。*/
  onError?: (data: WsErrorEvent["data"]) => void;
  /** WebSocket open（含重连成功）。*/
  onOpen?: () => void;
  /** WebSocket close（manual close / server close / 网络断开）。*/
  onClose?: (code: number, reason: string, wasClean: boolean) => void;
  /** 即将重连 —— 提供 attempt 序号（从 1 起）和 delay。*/
  onReconnecting?: (attempt: number, delayMs: number) => void;
}

export interface RunStreamHandle {
  /** 客户端主动关闭 —— 不再重连，发 close(1000)。*/
  close: () => void;
  /** 当前是否处于 OPEN 状态。*/
  isOpen: () => boolean;
}

// =============================================================================
// 重连参数
// =============================================================================

/** 指数退避 ms（mockup §9.8 决策 C：ws 断开 → 顶部 banner + 自动重连计数）。*/
const RECONNECT_BACKOFF_MS = [500, 1000, 2000, 5000, 10_000] as const;
const MAX_RECONNECT_ATTEMPTS = RECONNECT_BACKOFF_MS.length;
/** 这些 close code 不触发重连——属于"正常结束"或"明确无法恢复"。*/
const NO_RECONNECT_CODES = new Set([
  1000, // 正常关闭（run finished + server close）
  4004, // run 不存在或已归档（D-017 §4.5）
]);

// =============================================================================
// 入口
// =============================================================================

function buildWsUrl(runId: string): string {
  // 把 http(s):// → ws(s)://；保留前缀
  const wsBase = API_BASE.replace(/^http/, "ws");
  return `${wsBase}${API_PREFIX}/runs/${encodeURIComponent(runId)}/stream`;
}

/**
 * 连接到指定 run 的事件流。
 *
 * @param runId  D-017 / D-008 风格 run_id（POST /runs 返回的 `summary.run_id`）
 * @param callbacks  事件回调集合
 * @returns Handle —— 调用方在 unmount 时必须调 `handle.close()`
 */
export function connectRunStream(
  runId: string,
  callbacks: RunStreamCallbacks,
): RunStreamHandle {
  let ws: WebSocket | null = null;
  let attempt = 0;
  let manuallyClosed = false;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  const clearReconnect = () => {
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
  };

  const scheduleReconnect = () => {
    if (manuallyClosed) return;
    if (attempt >= MAX_RECONNECT_ATTEMPTS) return;
    const delay = RECONNECT_BACKOFF_MS[attempt] ?? RECONNECT_BACKOFF_MS[MAX_RECONNECT_ATTEMPTS - 1];
    callbacks.onReconnecting?.(attempt + 1, delay);
    reconnectTimer = setTimeout(() => {
      attempt += 1;
      connect();
    }, delay);
  };

  const handleMessage = (raw: string) => {
    let msg: WSServerEvent;
    try {
      msg = JSON.parse(raw) as WSServerEvent;
    } catch {
      // server 推的应该都是合法 JSON；解析失败忽略，避免抛错断流
      return;
    }
    switch (msg.event) {
      case "tick_advanced":
        callbacks.onTick?.(msg.data);
        break;
      case "paused":
        callbacks.onPaused?.(msg.data);
        break;
      case "run_resumed":
        callbacks.onResumed?.(msg.data);
        break;
      case "run_finished":
        callbacks.onFinished?.(msg.data);
        break;
      case "error":
        callbacks.onError?.(msg.data);
        break;
      default:
        // 未来 server 加新 event 时忽略（前端先升级再用）
        break;
    }
  };

  const connect = () => {
    clearReconnect();

    ws = new WebSocket(buildWsUrl(runId));

    ws.onopen = () => {
      attempt = 0;
      callbacks.onOpen?.();
    };

    ws.onmessage = (e) => {
      if (typeof e.data === "string") handleMessage(e.data);
    };

    ws.onerror = () => {
      // 不主动处理 —— onclose 必随其后；统一在 onclose 里决定是否重连
    };

    ws.onclose = (e) => {
      const wasClean = e.wasClean;
      callbacks.onClose?.(e.code, e.reason, wasClean);
      ws = null;

      if (manuallyClosed) return;
      if (NO_RECONNECT_CODES.has(e.code)) return;
      scheduleReconnect();
    };
  };

  const close = () => {
    manuallyClosed = true;
    clearReconnect();
    ws?.close(1000, "client closed");
    ws = null;
  };

  const isOpen = () =>
    ws !== null && ws.readyState === WebSocket.OPEN;

  // 立即建连
  connect();

  return { close, isOpen };
}
