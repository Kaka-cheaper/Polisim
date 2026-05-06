/**
 * EntityCard —— 单个实体卡片（mockup §4.3.1 + §11.4）。
 *
 * PR4.1 范围：
 *   - 头部：emoji + entity_id + decision_mode 标签
 *   - 属性列表 + diff 箭头（数值型属性比较 prev vs current）
 *   - LLM 模式：渲染 LLMThoughtBubble（reason 取自最新 decision_proposed event）
 *   - rule / random 模式：单行简化提示（不渲染气泡）
 *   - 刚执行动作：取自最新 action_executed event 的 payload.action
 *   - [📌 干预] 按钮：PR4.1 disabled 占位（PR4.2 接通 InterventionDrawer）
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { EntityTypeSchema, EventRecord } from "../api/schema";
import { LLMThoughtBubble } from "./LLMThoughtBubble";
import { PromptContextModal } from "./PromptContextModal";

export interface EntityCardEntry {
  /** 实体 id（场景 entities[].id）。*/
  id: string;
  /** 实体类型名（场景 entities[].type）。*/
  type: string;
  /** 决策模式（来自 worldDef.entity_types[type].decision_mode）。*/
  decisionMode: EntityTypeSchema["decision_mode"];
  /** 当前 tick 的属性快照。*/
  attributes: Record<string, unknown>;
  /** 上一 tick 的属性快照（用于 diff）；首 tick 或 snapshot 缺失时为 null。*/
  prevAttributes: Record<string, unknown> | null;
  /** 最新一条 decision_proposed event（按 actor_id 过滤）。*/
  latestDecision: EventRecord | undefined;
  /** 最新一条 action_executed event（按 actor_id 过滤）。*/
  latestAction: EventRecord | undefined;
}

interface Props {
  entry: EntityCardEntry;
  onIntervene?: () => void;
}

/** 按 entity type 名关键词匹配 emoji；未命中走默认。*/
function entityTypeEmoji(type: string): string {
  const lower = type.toLowerCase();
  if (lower.includes("compan")) return "🏢";
  if (lower.includes("regul")) return "👮";
  if (lower.includes("negotiat")) return "🤝";
  if (lower.includes("agent")) return "🤖";
  return "▪️";
}

/** 按属性名关键词匹配 emoji（cash / reputation / trust / strictness 等）。*/
function attributeEmoji(name: string): string {
  const lower = name.toLowerCase();
  if (lower.includes("cash") || lower.includes("money")) return "💰";
  if (lower.includes("reputation") || lower.includes("repu")) return "📈";
  if (lower.includes("trust")) return "🤝";
  if (lower.includes("strict") || lower.includes("regul")) return "🔒";
  if (lower.includes("press") || lower.includes("stress")) return "📊";
  return "▫️";
}

interface DiffArrow {
  sign: "↑" | "↓" | null;
  delta: number | null;
}

function computeDiff(prev: unknown, curr: unknown): DiffArrow {
  if (typeof prev === "number" && typeof curr === "number") {
    const d = curr - prev;
    if (d === 0) return { sign: null, delta: null };
    return { sign: d > 0 ? "↑" : "↓", delta: Math.abs(d) };
  }
  return { sign: null, delta: null };
}

function formatValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") {
    return Number.isInteger(v) ? String(v) : v.toFixed(2);
  }
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "string") return v;
  return JSON.stringify(v);
}

function extractDecisionReason(event: EventRecord | undefined): string {
  if (!event) return "";
  const payload = event.payload ?? {};
  const reason = payload.reason;
  return typeof reason === "string" ? reason : "";
}

function extractActionLabel(event: EventRecord | undefined): string {
  if (!event) return "";
  const payload = event.payload ?? {};
  const action = payload.action;
  if (typeof action !== "string") return "";
  const params = payload.params;
  if (params && typeof params === "object" && Object.keys(params).length > 0) {
    // 简单 key=value 拼接（不深嵌）
    const parts = Object.entries(params).map(
      ([k, v]) => `${k}=${formatValue(v)}`,
    );
    return `${action}(${parts.join(", ")})`;
  }
  return action;
}

export function EntityCard({ entry, onIntervene }: Props) {
  const { t } = useTranslation();
  const [showPromptModal, setShowPromptModal] = useState(false);
  const {
    id,
    type,
    decisionMode,
    attributes,
    prevAttributes,
    latestDecision,
    latestAction,
  } = entry;

  const reason = extractDecisionReason(latestDecision);
  const actionLabel = extractActionLabel(latestAction);
  const modeLabel = t(`entity_card.decision_mode_label.${decisionMode}`);

  // D-016：decision_proposed event payload 含 prompt_context；rule / random 无此字段。
  const promptContextRaw = latestDecision?.payload?.prompt_context;
  const promptContext =
    promptContextRaw && typeof promptContextRaw === "object"
      ? (promptContextRaw as Record<string, unknown>)
      : null;

  return (
    <div className="liquid-glass flex flex-col rounded-xl border border-border-default p-4 transition-shadow duration-normal ease-out">
      {/* 头部 */}
      <header className="flex items-center gap-2">
        <span className="text-2xl" aria-hidden="true">
          {entityTypeEmoji(type)}
        </span>
        <span className="font-semibold text-fg-primary">{id}</span>
        <span className="font-mono text-base text-fg-tertiary">{type}</span>
        <span className="ml-auto rounded-sm bg-surface-active px-2 py-0.5 font-mono text-base text-fg-tertiary">
          {modeLabel}
        </span>
      </header>

      <hr className="my-3 border-border-divider" />

      {/* 属性列表 */}
      <ul className="space-y-1">
        {Object.entries(attributes).map(([name, value]) => {
          const diff = computeDiff(prevAttributes?.[name], value);
          return (
            <li
              key={name}
              className="flex items-center gap-2 text-md text-fg-secondary"
            >
              <span aria-hidden="true">{attributeEmoji(name)}</span>
              <span className="font-mono text-fg-tertiary">{name}</span>
              <span className="ml-auto font-mono text-fg-primary">
                {formatValue(value)}
              </span>
              {diff.sign && diff.delta !== null && (
                <span
                  className={`font-mono text-base ${diff.sign === "↑" ? "text-status-success" : "text-status-danger"}`}
                  aria-label={`${diff.sign}${diff.delta}`}
                >
                  {diff.sign}
                  {diff.delta}
                </span>
              )}
            </li>
          );
        })}
      </ul>

      {/* 决策气泡（LLM）/ 简化提示（rule / random）*/}
      {decisionMode === "llm" && latestDecision && (
        <div className="mt-3">
          <LLMThoughtBubble
            reason={reason}
            onClickViewPrompt={
              promptContext ? () => setShowPromptModal(true) : undefined
            }
          />
        </div>
      )}
      {decisionMode === "rule" && (
        <p className="mt-3 text-base text-fg-tertiary">
          {t("rule_thought.title")}
        </p>
      )}
      {decisionMode === "random" && (
        <p className="mt-3 text-base text-fg-tertiary">
          {t("rule_thought.random_title")}
        </p>
      )}

      {/* 刚执行动作 */}
      {actionLabel && (
        <p className="mt-3 text-base text-fg-tertiary">
          ⚡ {t("entity_card.just_executed")}:{" "}
          <span className="font-mono text-fg-secondary">{actionLabel}</span>
        </p>
      )}
      {!actionLabel && (
        <p className="mt-3 text-base text-fg-muted">
          {t("entity_card.no_action_yet")}
        </p>
      )}

      {/* 干预按钮（PR4.2 接通 InterventionDrawer，通过 Running 传入 onIntervene） */}
      <button
        type="button"
        onClick={onIntervene}
        disabled={!onIntervene}
        className="mt-4 self-start rounded-md border border-border-default bg-surface px-3 py-1.5 text-base font-medium text-fg-secondary transition-all duration-fast ease-out hover:-translate-y-px hover:border-accent hover:bg-surface-hover hover:text-fg-primary focus-visible:shadow-focus focus-visible:outline-none active:translate-y-0 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
      >
        {t("entity_card.intervene")}
      </button>

      {/* PromptContext modal（mounted only when open；EntityCard local state） */}
      {showPromptModal && (
        <PromptContextModal
          promptContext={promptContext}
          entityId={id}
          tick={latestDecision?.tick ?? 0}
          onClose={() => setShowPromptModal(false)}
        />
      )}
    </div>
  );
}

export default EntityCard;
