/**
 * InterventionDrawer —— 人工干预侧抽屉（mockup §4.4.3 + §11.4 + 需求分析 8.3）。
 *
 * 入口：EntityCard 点击 [📌 干预] → Running 持有 drawer state（pause-open / submit-resume / cancel-resume 三流程）。
 *
 * Drawer 三 tab（对齐 Intervention.kind discriminated union）：
 *   1. ⚡ force_action：覆盖某实体下一 tick 决策
 *      - target_actor（已锁定 = selectedEntityId）
 *      - action_type（候选 = world.entity_types[type].actions 名单；UI 用文本输入避免静态依赖）
 *      - params（JSON textarea；提交前 JSON.parse + 校验）
 *   2. 💬 inject_message：注入消息事件
 *      - target_actor（默认 selectedEntityId；可改 None = 广播）
 *      - message_type（候选 = world.message_types.keys；UI 用 select）
 *      - payload（JSON textarea）
 *   3. ✏️ override_attribute：直接改属性
 *      - target_actor（已锁定）
 *      - attribute_changes（JSON textarea；keys 为属性名，value 为新值；可一次改多个）
 *
 * 通用字段：
 *   - tick：默认 max(latestTick, 0) + 1（下一 tick）；可改
 *   - reason：可选 textarea
 *
 * 提交：本组件仅做表单 + 校验，submit 通过 `onSubmit(intervention)` 回调上抛 Running；
 *      Running 负责调 useIntervene + useResume + 关闭流程。
 *
 * PR4.2 简化（v0.3+ 可补）：
 *   - params / payload / attribute_changes 用 JSON textarea（不按 D-014 ParamSchema 自动生成 form fields）
 *   - 不展示 server 端 validation error 详情（依赖 useIntervene.onError toast）
 */
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import type { Intervention, WorldDefinition } from "../api/schema";

interface Props {
  open: boolean;
  selectedEntityId: string;
  selectedEntityType: string;
  selectedAttributes: Record<string, unknown>;
  worldDef: WorldDefinition;
  defaultTick: number;
  isSubmitting: boolean;
  onSubmit: (intervention: Intervention) => void;
  onCancel: () => void;
}

type Kind = Intervention["kind"];

const KINDS: readonly Kind[] = [
  "force_action",
  "inject_message",
  "override_attribute",
] as const;

interface FormState {
  kind: Kind;
  tick: string;
  reason: string;
  // force_action
  actionType: string;
  paramsJson: string;
  // inject_message
  messageType: string;
  payloadJson: string;
  broadcastMessage: boolean;
  // override_attribute
  attributeChangesJson: string;
}

function initialFormState(defaultTick: number): FormState {
  return {
    kind: "force_action",
    tick: String(defaultTick),
    reason: "",
    actionType: "",
    paramsJson: "{}",
    messageType: "",
    payloadJson: "{}",
    broadcastMessage: false,
    attributeChangesJson: "{}",
  };
}

function parseJsonObject(
  raw: string,
): { ok: true; value: Record<string, unknown> } | { ok: false; error: string } {
  const trimmed = raw.trim();
  if (trimmed.length === 0) {
    return { ok: true, value: {} };
  }
  try {
    const parsed = JSON.parse(trimmed);
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
      return { ok: false, error: "must be a JSON object" };
    }
    return { ok: true, value: parsed as Record<string, unknown> };
  } catch (err) {
    return { ok: false, error: err instanceof Error ? err.message : "invalid JSON" };
  }
}

export function InterventionDrawer({
  open,
  selectedEntityId,
  selectedEntityType,
  selectedAttributes,
  worldDef,
  defaultTick,
  isSubmitting,
  onSubmit,
  onCancel,
}: Props) {
  const { t } = useTranslation();
  const [form, setForm] = useState<FormState>(() =>
    initialFormState(defaultTick),
  );
  const [errors, setErrors] = useState<string[]>([]);

  // open 时重置表单（带新 defaultTick）；close 时不动避免动画期间空白
  useEffect(() => {
    if (open) {
      setForm(initialFormState(defaultTick));
      setErrors([]);
    }
  }, [open, defaultTick, selectedEntityId]);

  // Esc 取消
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !isSubmitting) onCancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, isSubmitting, onCancel]);

  const messageTypeOptions = useMemo(() => {
    const types = worldDef?.message_types;
    if (!types || typeof types !== "object") return [] as string[];
    return Object.keys(types as Record<string, unknown>);
  }, [worldDef]);

  const attributeOptions = useMemo(
    () => Object.keys(selectedAttributes ?? {}),
    [selectedAttributes],
  );

  if (!open) return null;

  const update = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = () => {
    const validationErrors: string[] = [];

    const tickNum = Number(form.tick);
    if (!Number.isInteger(tickNum) || tickNum < 0) {
      validationErrors.push(t("intervention.validation.tick_required"));
    }

    let intervention: Intervention | null = null;

    if (form.kind === "force_action") {
      if (!form.actionType.trim()) {
        validationErrors.push(t("intervention.validation.action_type_required"));
      }
      const parsed = parseJsonObject(form.paramsJson);
      if (!parsed.ok) {
        validationErrors.push(
          t("intervention.json_parse_error", { message: parsed.error }),
        );
      }
      if (validationErrors.length === 0 && parsed.ok) {
        intervention = {
          tick: tickNum,
          kind: "force_action",
          target_actor: selectedEntityId,
          action: {
            action_type: form.actionType.trim(),
            params: parsed.value,
          },
          reason: form.reason.trim() || null,
        };
      }
    } else if (form.kind === "inject_message") {
      if (!form.messageType.trim()) {
        validationErrors.push(
          t("intervention.validation.message_type_required"),
        );
      }
      const parsed = parseJsonObject(form.payloadJson);
      if (!parsed.ok) {
        validationErrors.push(
          t("intervention.json_parse_error", { message: parsed.error }),
        );
      }
      if (validationErrors.length === 0 && parsed.ok) {
        intervention = {
          tick: tickNum,
          kind: "inject_message",
          target_actor: form.broadcastMessage ? null : selectedEntityId,
          message: {
            message_type: form.messageType.trim(),
            payload: parsed.value,
          },
          reason: form.reason.trim() || null,
        };
      }
    } else {
      // override_attribute
      const parsed = parseJsonObject(form.attributeChangesJson);
      if (!parsed.ok) {
        validationErrors.push(
          t("intervention.json_parse_error", { message: parsed.error }),
        );
      } else if (Object.keys(parsed.value).length === 0) {
        validationErrors.push(
          t("intervention.validation.attribute_changes_empty"),
        );
      }
      if (validationErrors.length === 0 && parsed.ok) {
        intervention = {
          tick: tickNum,
          kind: "override_attribute",
          target_actor: selectedEntityId,
          attribute_changes: parsed.value,
          reason: form.reason.trim() || null,
        };
      }
    }

    if (validationErrors.length > 0 || intervention === null) {
      setErrors(validationErrors);
      return;
    }
    setErrors([]);
    onSubmit(intervention);
  };

  return (
    <>
      {/* Overlay */}
      <div
        role="presentation"
        onClick={isSubmitting ? undefined : onCancel}
        className="fixed inset-0 z-modal bg-overlay backdrop-blur-sm"
      />

      {/* Drawer panel —— 右侧滑出 */}
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="intervention-title"
        className="fixed inset-y-0 right-0 z-modal flex w-full max-w-xl flex-col border-l border-border-default bg-surface shadow-2xl"
      >
        {/* Header */}
        <header className="flex items-start justify-between gap-4 border-b border-border-subtle bg-panel px-5 py-3">
          <div>
            <h2
              id="intervention-title"
              className="text-lg font-semibold text-fg-primary"
            >
              {t("intervention.title")}
            </h2>
            <p className="font-mono text-base text-fg-tertiary">
              {t("intervention.subtitle", { entityId: selectedEntityId })}
              <span className="ml-2 text-fg-muted">[{selectedEntityType}]</span>
            </p>
          </div>
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            aria-label={t("intervention.cancel")}
            className="rounded-md p-1 text-fg-tertiary transition-colors duration-fast hover:bg-surface-hover hover:text-fg-primary disabled:cursor-not-allowed disabled:opacity-50"
          >
            ✕
          </button>
        </header>

        {/* Tab 切换 */}
        <nav
          role="tablist"
          aria-label={t("intervention.title")}
          className="flex border-b border-border-subtle bg-canvas"
        >
          {KINDS.map((k) => {
            const active = form.kind === k;
            return (
              <button
                key={k}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => update("kind", k)}
                disabled={isSubmitting}
                className={`flex-1 border-b-2 px-3 py-2 text-md font-medium transition-colors duration-fast ${
                  active
                    ? "border-accent text-fg-primary"
                    : "border-transparent text-fg-tertiary hover:text-fg-primary"
                } disabled:cursor-not-allowed disabled:opacity-50`}
              >
                {t(`intervention.tab.${k}`)}
              </button>
            );
          })}
        </nav>

        {/* Body */}
        <section className="flex-1 overflow-y-auto px-5 py-4">
          <div className="space-y-4">
            {/* 通用字段：tick */}
            <Field
              label={t("intervention.field.tick_label")}
              hint={t("intervention.field.tick_hint")}
            >
              <input
                type="number"
                min={0}
                step={1}
                value={form.tick}
                onChange={(e) => update("tick", e.target.value)}
                disabled={isSubmitting}
                className="w-full rounded-md border border-border-default bg-canvas px-3 py-1.5 font-mono text-md text-fg-primary disabled:opacity-50"
              />
            </Field>

            {/* kind 特化字段 */}
            {form.kind === "force_action" && (
              <>
                <Field label={t("intervention.field.target_actor_locked")}>
                  <p className="rounded-md border border-border-subtle bg-canvas px-3 py-1.5 font-mono text-md text-fg-tertiary">
                    {selectedEntityId}{" "}
                    <span className="text-fg-muted">[{selectedEntityType}]</span>
                  </p>
                </Field>
                <Field label={t("intervention.field.action_type")}>
                  <input
                    type="text"
                    value={form.actionType}
                    onChange={(e) => update("actionType", e.target.value)}
                    placeholder={t(
                      "intervention.field.action_type_placeholder",
                    )}
                    disabled={isSubmitting}
                    className="w-full rounded-md border border-border-default bg-canvas px-3 py-1.5 font-mono text-md text-fg-primary disabled:opacity-50"
                  />
                </Field>
                <Field label={t("intervention.field.params_json")}>
                  <textarea
                    rows={5}
                    value={form.paramsJson}
                    onChange={(e) => update("paramsJson", e.target.value)}
                    placeholder={t(
                      "intervention.field.params_json_placeholder",
                    )}
                    disabled={isSubmitting}
                    className="w-full rounded-md border border-border-default bg-canvas px-3 py-2 font-mono text-base leading-relaxed text-fg-primary disabled:opacity-50"
                  />
                </Field>
              </>
            )}

            {form.kind === "inject_message" && (
              <>
                <Field label={t("intervention.field.target_actor")}>
                  <label className="flex items-center gap-2 text-md text-fg-secondary">
                    <input
                      type="checkbox"
                      checked={form.broadcastMessage}
                      onChange={(e) =>
                        update("broadcastMessage", e.target.checked)
                      }
                      disabled={isSubmitting}
                    />
                    {t("intervention.field.target_actor_broadcast")}
                  </label>
                  {!form.broadcastMessage && (
                    <p className="mt-1 rounded-md border border-border-subtle bg-canvas px-3 py-1.5 font-mono text-md text-fg-tertiary">
                      {selectedEntityId}{" "}
                      <span className="text-fg-muted">
                        [{selectedEntityType}]
                      </span>
                    </p>
                  )}
                </Field>
                <Field
                  label={t("intervention.field.message_type")}
                  hint={t("intervention.field.message_type_hint")}
                >
                  {messageTypeOptions.length > 0 ? (
                    <select
                      value={form.messageType}
                      onChange={(e) => update("messageType", e.target.value)}
                      disabled={isSubmitting}
                      className="w-full rounded-md border border-border-default bg-canvas px-3 py-1.5 font-mono text-md text-fg-primary disabled:opacity-50"
                    >
                      <option value="">--</option>
                      {messageTypeOptions.map((mt) => (
                        <option key={mt} value={mt}>
                          {mt}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="text"
                      value={form.messageType}
                      onChange={(e) => update("messageType", e.target.value)}
                      disabled={isSubmitting}
                      className="w-full rounded-md border border-border-default bg-canvas px-3 py-1.5 font-mono text-md text-fg-primary disabled:opacity-50"
                    />
                  )}
                </Field>
                <Field label={t("intervention.field.payload_json")}>
                  <textarea
                    rows={5}
                    value={form.payloadJson}
                    onChange={(e) => update("payloadJson", e.target.value)}
                    placeholder={t(
                      "intervention.field.payload_json_placeholder",
                    )}
                    disabled={isSubmitting}
                    className="w-full rounded-md border border-border-default bg-canvas px-3 py-2 font-mono text-base leading-relaxed text-fg-primary disabled:opacity-50"
                  />
                </Field>
              </>
            )}

            {form.kind === "override_attribute" && (
              <>
                <Field label={t("intervention.field.target_actor_locked")}>
                  <p className="rounded-md border border-border-subtle bg-canvas px-3 py-1.5 font-mono text-md text-fg-tertiary">
                    {selectedEntityId}{" "}
                    <span className="text-fg-muted">[{selectedEntityType}]</span>
                  </p>
                </Field>
                <Field
                  label={t("intervention.field.attribute_changes_json")}
                  hint={t("intervention.field.attribute_changes_json_hint")}
                >
                  <textarea
                    rows={6}
                    value={form.attributeChangesJson}
                    onChange={(e) =>
                      update("attributeChangesJson", e.target.value)
                    }
                    placeholder={t(
                      "intervention.field.attribute_changes_json_placeholder",
                    )}
                    disabled={isSubmitting}
                    className="w-full rounded-md border border-border-default bg-canvas px-3 py-2 font-mono text-base leading-relaxed text-fg-primary disabled:opacity-50"
                  />
                  {attributeOptions.length > 0 && (
                    <p className="mt-1 text-base text-fg-muted">
                      {attributeOptions.join(" / ")}
                    </p>
                  )}
                </Field>
              </>
            )}

            {/* 通用：reason */}
            <Field label={t("intervention.field.reason_label")}>
              <textarea
                rows={2}
                value={form.reason}
                onChange={(e) => update("reason", e.target.value)}
                placeholder={t("intervention.field.reason_placeholder")}
                disabled={isSubmitting}
                className="w-full rounded-md border border-border-default bg-canvas px-3 py-2 text-md text-fg-primary disabled:opacity-50"
              />
            </Field>

            {/* 校验错误 */}
            {errors.length > 0 && (
              <ul
                role="alert"
                className="rounded-md border border-status-danger bg-surface p-3 text-md text-status-danger"
              >
                {errors.map((e, i) => (
                  <li key={i}>• {e}</li>
                ))}
              </ul>
            )}
          </div>
        </section>

        {/* Footer */}
        <footer className="flex items-center justify-end gap-2 border-t border-border-subtle bg-panel px-5 py-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="rounded-md border border-border-default bg-surface px-4 py-1.5 text-md font-medium text-fg-secondary transition-colors duration-fast hover:bg-surface-hover hover:text-fg-primary disabled:cursor-not-allowed disabled:opacity-50"
          >
            {t("intervention.cancel")}
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="rounded-full bg-accent px-4 py-1.5 text-md font-medium text-fg-on-accent transition-all duration-fast ease-out hover:bg-accent-hover hover:shadow-glow-accent disabled:cursor-not-allowed disabled:bg-surface-active disabled:text-fg-muted"
          >
            {isSubmitting
              ? t("intervention.submitting")
              : t("intervention.submit")}
          </button>
        </footer>
      </aside>
    </>
  );
}

interface FieldProps {
  label: string;
  hint?: string;
  children: React.ReactNode;
}

function Field({ label, hint, children }: FieldProps) {
  return (
    <div>
      <label className="mb-1 block text-base font-medium text-fg-secondary">
        {label}
      </label>
      {children}
      {hint && <p className="mt-1 text-base text-fg-muted">{hint}</p>}
    </div>
  );
}

export default InterventionDrawer;
