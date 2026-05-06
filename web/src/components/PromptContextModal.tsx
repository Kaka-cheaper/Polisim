/**
 * PromptContextModal —— LLM 决策 prompt 上下文展开 modal（mockup §11.4 + D-016 §2.1）。
 *
 * 数据来源：
 *   - `EventRecord(kind="decision_proposed").payload.prompt_context`（D-016 §2.2 规定）
 *   - rule / random 决策事件 payload 不含 prompt_context（PR4.1 EntityCard 已对应处理：
 *     非 LLM 模式不渲染 LLMThoughtBubble，[📋 看完整 prompt] 入口不暴露）
 *
 * UI 结构（D-016 §2.1 PromptContext 6 段）：
 *   1. 🎭 system_role —— 角色与身份（str | null）
 *   2. 👤 actor_view —— 自身视图（dict）
 *   3. 🌍 perception —— 外部感知（dict）
 *   4. ⚙️ available_actions —— 可用动作（list[dict]）
 *   5. 💬 language_hint —— 语言指令（str）
 *   6. 📝 custom_segments —— 场景特化段（dict[str, str]）
 *
 * 简化（PR4.2）：
 *   - 字典 / 列表段：`<pre>` JSON pretty-print；非渲染美化
 *   - 字符串段：whitespace-pre-line
 *   - 6 段全部 `<details open>` 默认展开（用户翻看不需要 click 每段）
 *
 * 关闭：Esc / click overlay / 关闭按钮。
 */
import type { ReactElement } from "react";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

interface Props {
  /** D-016 PromptContext 序列化字典；payload.prompt_context 直接传入。*/
  promptContext: Record<string, unknown> | null | undefined;
  entityId: string;
  tick: number;
  onClose: () => void;
}

const SECTION_KEYS = [
  "system_role",
  "actor_view",
  "perception",
  "available_actions",
  "language_hint",
  "custom_segments",
] as const;

type SectionKey = (typeof SECTION_KEYS)[number];

function isEmpty(value: unknown): boolean {
  if (value === null || value === undefined) return true;
  if (typeof value === "string") return value.length === 0;
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === "object") return Object.keys(value).length === 0;
  return false;
}

function renderValue(value: unknown, emptyLabel: string): ReactElement {
  if (isEmpty(value)) {
    return <span className="text-fg-muted italic">{emptyLabel}</span>;
  }
  if (typeof value === "string") {
    return (
      <p className="whitespace-pre-line font-mono text-base text-fg-secondary">
        {value}
      </p>
    );
  }
  // dict / list / number / boolean → JSON pretty
  return (
    <pre className="overflow-x-auto rounded-md border border-border-subtle bg-canvas p-3 font-mono text-base leading-relaxed text-fg-secondary">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

export function PromptContextModal({
  promptContext,
  entityId,
  tick,
  onClose,
}: Props) {
  const { t } = useTranslation();
  const dialogRef = useRef<HTMLDivElement | null>(null);

  // Esc 关闭
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  // 进入时焦点交给 dialog 容器（让 Esc 立即生效，screen reader 也可寻址）
  useEffect(() => {
    dialogRef.current?.focus();
  }, []);

  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div
      role="presentation"
      onClick={handleOverlayClick}
      className="fixed inset-0 z-modal flex items-center justify-center bg-overlay px-4 py-8 backdrop-blur-sm"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="prompt-modal-title"
        tabIndex={-1}
        className="flex max-h-full w-full max-w-3xl flex-col overflow-hidden rounded-lg border border-border-default bg-surface shadow-2xl outline-none"
      >
        {/* Header */}
        <header className="flex items-start justify-between gap-4 border-b border-border-subtle bg-panel px-5 py-3">
          <div>
            <h2
              id="prompt-modal-title"
              className="text-lg font-semibold text-fg-primary"
            >
              {t("prompt_modal.title")}
            </h2>
            <p className="font-mono text-base text-fg-tertiary">
              {t("prompt_modal.subtitle", { entityId, tick })}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label={t("prompt_modal.close")}
            className="rounded-md p-1 text-fg-tertiary transition-colors duration-fast hover:bg-surface-hover hover:text-fg-primary"
          >
            ✕
          </button>
        </header>

        {/* Body */}
        <section className="flex-1 overflow-y-auto px-5 py-4">
          {!promptContext ? (
            <p className="rounded-md border border-border-subtle bg-canvas p-4 text-md text-fg-tertiary">
              {t("prompt_modal.no_data")}
            </p>
          ) : (
            <ul className="space-y-3">
              {SECTION_KEYS.map((key: SectionKey) => {
                const value = promptContext[key];
                return (
                  <li key={key}>
                    <details
                      open
                      className="rounded-md border border-border-subtle bg-canvas"
                    >
                      <summary className="cursor-pointer select-none px-3 py-2 text-md font-medium text-fg-primary hover:bg-surface-hover">
                        {t(`prompt_modal.section.${key}`)}
                      </summary>
                      <div className="border-t border-border-divider px-3 py-3">
                        {renderValue(value, t("prompt_modal.empty_field"))}
                      </div>
                    </details>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        {/* Footer */}
        <footer className="flex items-center justify-between border-t border-border-subtle bg-panel px-5 py-3">
          <span className="text-base text-fg-tertiary">
            {t("prompt_modal.close_hint")}
          </span>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full bg-accent px-4 py-1.5 text-md font-medium text-fg-on-accent transition-all duration-fast ease-out hover:bg-accent-hover hover:shadow-glow-accent"
          >
            {t("prompt_modal.close")}
          </button>
        </footer>
      </div>
    </div>
  );
}

export default PromptContextModal;
