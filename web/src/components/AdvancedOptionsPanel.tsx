/**
 * AdvancedOptionsPanel —— 跑前页折叠式高级选项（mockup §4.2 + §11.6 C15）。
 *
 * v0.2 PR3 状态：**UI 落地 + 受控 state，但不接通业务**——mockup §4.2 没明确
 * 高级选项的生效路径（POST /runs 已在画廊点 [▶ 开始] 时发出，本页 [▶ 开始仿真] 仅
 * 导航 navigate to /runs/:id/run）。下个 PR/session 可加 [应用并重新创建 run] 按钮
 * 路径：DELETE 当前 run + POST 新 run 用新参数。
 *
 * 当前 props：
 *   - value: Partial<CreateRunRequest> —— 父组件 state 持有
 *   - onChange: 回调写入父 state
 *   - expanded / onExpandedChange: 折叠态受控
 *   - disabled: 父组件传 true 表示展示态（输入框灰色 + tip 文案；当前 PreRun 默认 true，
 *     [▶ 开始仿真] 不消费 advancedValue —— 等 v0.3+ 接通"重创 run"路径再 disabled=false）
 *
 * v0.2 仅暴露两字段：ticks_override（数字）/ llm_provider（mock|openai）。
 * 其他字段（random_seed / max_chain_depth / prompt_history_size 等）留给 PR4+。
 */
import { useTranslation } from "react-i18next";

import type { CreateRunRequest } from "../api/schema";

interface Props {
  value: Partial<CreateRunRequest>;
  onChange: (next: Partial<CreateRunRequest>) => void;
  expanded: boolean;
  onExpandedChange: (next: boolean) => void;
  disabled?: boolean;
}

export function AdvancedOptionsPanel({
  value,
  onChange,
  expanded,
  onExpandedChange,
  disabled = false,
}: Props) {
  const { t } = useTranslation();

  return (
    <details
      className="rounded-xl border border-border-subtle bg-canvas"
      open={expanded}
      onToggle={(e) => onExpandedChange((e.target as HTMLDetailsElement).open)}
    >
      <summary className="cursor-pointer select-none rounded-xl bg-surface px-6 py-4 text-md font-medium text-fg-primary shadow-inner-highlight transition-all duration-fast ease-out hover:bg-surface-hover">
        {t("advanced_options.title")}
      </summary>

      <div className="space-y-5 border-t border-border-divider px-6 py-5">
        <p className="text-base text-fg-tertiary">{t("advanced_options.tip")}</p>

        {/* ticks_override */}
        <div>
          <label
            className="block text-md font-medium text-fg-secondary"
            htmlFor="adv-ticks-override"
          >
            {t("advanced_options.ticks_override")}
          </label>
          <input
            id="adv-ticks-override"
            type="number"
            min={1}
            value={value.ticks_override ?? ""}
            disabled={disabled}
            placeholder={t("advanced_options.ticks_override_placeholder")}
            onChange={(e) => {
              const raw = e.target.value;
              if (raw === "") {
                onChange({ ...value, ticks_override: null });
                return;
              }
              const n = Number(raw);
              if (Number.isFinite(n) && n >= 1) {
                onChange({ ...value, ticks_override: n });
              }
            }}
            className="mt-2 w-40 rounded-md border border-border-default bg-input px-3 py-2 font-mono text-md text-fg-primary placeholder:text-fg-muted transition-all duration-fast ease-out hover:bg-input-hover focus:border-accent focus:shadow-focus focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
          />
        </div>

        {/* llm_provider */}
        <div>
          <label
            className="block text-md font-medium text-fg-secondary"
            htmlFor="adv-llm-provider"
          >
            {t("advanced_options.llm_provider")}
          </label>
          <select
            id="adv-llm-provider"
            value={value.llm_provider ?? "mock"}
            disabled={disabled}
            onChange={(e) =>
              onChange({
                ...value,
                llm_provider: e.target.value as "mock" | "openai",
              })
            }
            className="mt-2 w-40 rounded-md border border-border-default bg-input px-3 py-2 text-md text-fg-primary transition-all duration-fast ease-out hover:bg-input-hover focus:border-accent focus:shadow-focus focus:outline-none disabled:cursor-not-allowed disabled:opacity-60"
          >
            <option value="mock">
              {t("advanced_options.llm_provider_options.mock")}
            </option>
            <option value="openai">
              {t("advanced_options.llm_provider_options.openai")}
            </option>
          </select>
        </div>
      </div>
    </details>
  );
}

export default AdvancedOptionsPanel;
