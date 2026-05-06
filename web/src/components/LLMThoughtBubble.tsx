/**
 * LLMThoughtBubble —— 实体卡片内的 LLM 想法气泡（mockup §4.3.1 + §11.4）。
 *
 * 范围：
 *   - 仅 LLM 模式渲染气泡（rule / random 在 EntityCard 内单独渲染简化提示行）
 *   - reason 来自 EventRecord(kind="decision_proposed").payload.reason
 *   - [📋 看完整 prompt] 按钮：传入 onClickViewPrompt 时启用 → 父组件挂 PromptContextModal
 *     未传时 disabled，hover hint 解释为何无法查看（无 prompt_context）
 *
 * 视觉 token：
 *   - 气泡背景 = `--polisim-llm-bubble`（mockup §8.4 业务专属语义 token）
 *   - 文字主色 = `--text-secondary`
 *   - 与 EntityCard 主体 surface 形成 1 层视觉浮起
 */
import { useTranslation } from "react-i18next";

interface Props {
  reason: string;
  /** PR4.2 加 onClickViewPrompt callback；当前 disabled。*/
  onClickViewPrompt?: () => void;
}

export function LLMThoughtBubble({ reason, onClickViewPrompt }: Props) {
  const { t } = useTranslation();

  return (
    <div className="rounded-md border border-border-subtle bg-polisim-llm-bubble p-3">
      <header className="text-base font-medium text-fg-secondary">
        {t("llm_thought.title")}
      </header>
      <p className="mt-1 whitespace-pre-line text-md text-fg-secondary">
        {reason || t("entity_card.no_decision_yet")}
      </p>
      <button
        type="button"
        onClick={onClickViewPrompt}
        disabled={!onClickViewPrompt}
        title={
          onClickViewPrompt
            ? undefined
            : t("llm_thought.view_prompt_no_context")
        }
        className="mt-2 rounded-sm border border-border-subtle bg-surface px-2 py-0.5 text-base text-fg-tertiary transition-colors duration-fast disabled:cursor-not-allowed disabled:opacity-60"
      >
        {t("llm_thought.view_prompt")}
      </button>
    </div>
  );
}

export default LLMThoughtBubble;
