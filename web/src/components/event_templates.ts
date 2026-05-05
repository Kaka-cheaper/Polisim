/**
 * event_templates —— EventStreamLayout 用的 i18n 自然语言模板表（mockup §4.3.3）。
 *
 * 输入：EventRecord（含 kind / actor_id / payload / ...）
 * 输出：emoji + 自然语言字符串（按当前 i18n locale 渲染）
 *
 * 约定：
 *   - 模板按 EventKind 分组，缺省走 fallback
 *   - i18n keys 在 `event_stream.template.{kind}` 下
 *   - 占位符语法：`{{actor}}` / `{{attribute}}` / `{{before}}` / `{{after}}`
 *   - 不可读字段（payload 嵌套对象）用 JSON.stringify 兜底
 */
import type { TFunction } from "i18next";

import type { EventRecord } from "../api/schema";

export interface FormattedEvent {
  /** Tick 编号 */
  tick: number;
  /** Emoji + 自然语言文本 */
  text: string;
  /** 原始事件 kind（CSS 样式区分用）*/
  kind: string;
  /** 主体实体 id（侧栏 highlight 用），可能为 null（如 environment_event）*/
  actorId: string | null;
}

function num(v: unknown): string {
  if (typeof v === "number") {
    return Number.isInteger(v) ? String(v) : v.toFixed(2);
  }
  if (v === null || v === undefined) return "—";
  return String(v);
}

export function formatEvent(
  ev: EventRecord,
  t: TFunction,
): FormattedEvent {
  const payload = (ev.payload ?? {}) as Record<string, unknown>;
  const baseKey = `event_stream.template.${ev.kind}`;

  let text: string;
  switch (ev.kind) {
    case "decision_proposed": {
      const reason = (payload.reason as string) ?? "";
      const actionType =
        ((payload.action as { type?: string } | undefined)?.type) ?? "?";
      text = t(baseKey, {
        actor: ev.actor_id ?? "?",
        action: actionType,
        reason: reason.length > 80 ? `${reason.slice(0, 80)}…` : reason,
        defaultValue: `💭 ${ev.actor_id} → ${actionType}`,
      });
      break;
    }
    case "action_executed": {
      const actionType =
        ((payload.action as { type?: string } | undefined)?.type) ?? "?";
      text = t(baseKey, {
        actor: ev.actor_id ?? "?",
        action: actionType,
        defaultValue: `⚡ ${ev.actor_id} → ${actionType}`,
      });
      break;
    }
    case "relation_changed": {
      text = t(baseKey, {
        source: (payload.source as string) ?? "?",
        target: (payload.target as string) ?? "?",
        relationType: (payload.type as string) ?? "?",
        before: num(payload.before),
        after: num(payload.after),
        defaultValue: `🤝 ${payload.source as string}.${payload.type as string}(${payload.target as string}) ${num(payload.before)}→${num(payload.after)}`,
      });
      break;
    }
    case "breakpoint_triggered": {
      text = t(baseKey, {
        id: (payload.breakpoint_id as string) ?? "?",
        defaultValue: `🔔 breakpoint ${payload.breakpoint_id as string}`,
      });
      break;
    }
    case "intervention_applied": {
      text = t(baseKey, {
        kind: (payload.kind as string) ?? "?",
        target: (payload.target_actor as string) ?? "*",
        defaultValue: `📌 intervention ${payload.kind as string} → ${payload.target_actor as string}`,
      });
      break;
    }
    case "scheduled_event_triggered":
    case "environment_changed": {
      text = t(baseKey, {
        name: (payload.name as string) ?? (payload.variable as string) ?? ev.kind,
        before: num(payload.before),
        after: num(payload.after),
        defaultValue: `🌐 ${(payload.name as string) ?? (payload.variable as string) ?? ev.kind}`,
      });
      break;
    }
    case "decision_rejected": {
      text = t(baseKey, {
        actor: ev.actor_id ?? "?",
        reason: (payload.reason as string) ?? "?",
        defaultValue: `🚫 ${ev.actor_id} rejected: ${(payload.reason as string) ?? ""}`,
      });
      break;
    }
    default:
      // fallback：ℹ️ <kind>
      text = `ℹ️ ${ev.kind}${ev.actor_id ? ` · ${ev.actor_id}` : ""}`;
  }

  return {
    tick: ev.tick,
    text,
    kind: ev.kind,
    actorId: ev.actor_id ?? null,
  };
}

/**
 * 把 EventRecord[] 按 tick 分组（保持 tick 内顺序）。
 * 用于 EventStreamLayout 主区瀑布渲染。
 */
export function groupEventsByTick(
  events: EventRecord[],
  t: TFunction,
): { tick: number; items: FormattedEvent[] }[] {
  const groups = new Map<number, FormattedEvent[]>();
  for (const ev of events) {
    const formatted = formatEvent(ev, t);
    const arr = groups.get(formatted.tick) ?? [];
    arr.push(formatted);
    groups.set(formatted.tick, arr);
  }
  return Array.from(groups.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([tick, items]) => ({ tick, items }));
}
