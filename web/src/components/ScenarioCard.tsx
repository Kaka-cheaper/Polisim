/**
 * ScenarioCard —— 场景画廊卡片（mockup §4.1 + §11.6 C13）。
 *
 * 三种 kind：
 *   - `production`：现成可跑场景，渲染 ScenarioSummary 字段（id / name / description /
 *     total_ticks / ui_layout / world_id）；右上角 ui_layout 图标提示主区风格（§10.6 M6）；
 *     [▶ 开始] 触发父组件 onStart（典型为调 useCreateRun + 跳转）。
 *   - `upcoming`：即将到来场景占位（信息级联 / 组织决策），灰色虚线边框 + [v0.3+] 标。
 *   - `custom`：自定义场景占位（LLM 辅助建模），形态同 upcoming。
 *
 * 设计纪律：
 *   - 只用 PR1 桥接的 semantic token utility（bg-surface / text-fg-* / border-* 等），
 *     不直接引 primitives 也不用 token 的 opacity-modifier（var-based 不支持 /<alpha>）
 *   - 三种 kind 共用同一外形（rounded-xl + p-6 + 标题 + 描述 + 主按钮区），仅颜色 + 边框
 *     不同—保证视觉一致性
 */
import { useTranslation } from "react-i18next";

import type { ScenarioSummary } from "../api/schema";

const UI_LAYOUT_ICON: Record<ScenarioSummary["ui_layout"], string> = {
  entity_card: "🎴",
  relation_graph: "🕸️",
  event_stream: "📜",
};

interface BaseProps {
  onStart: () => void;
  disabled?: boolean;
}

interface ProductionProps extends BaseProps {
  kind: "production";
  scenario: ScenarioSummary;
}

interface PlaceholderProps extends BaseProps {
  kind: "upcoming" | "custom";
  emoji: string;
  name: string;
  description: string;
}

export type ScenarioCardProps = ProductionProps | PlaceholderProps;

export function ScenarioCard(props: ScenarioCardProps) {
  const { t } = useTranslation();

  if (props.kind === "production") {
    const { scenario, onStart, disabled } = props;
    const layoutIcon = UI_LAYOUT_ICON[scenario.ui_layout];
    const layoutHint = t(`scenario_card.ui_layout_hint.${scenario.ui_layout}`);

    return (
      <div className="group liquid-glass flex flex-col rounded-xl border border-border-default p-6 transition-all duration-normal ease-out hover:-translate-y-1 hover:border-accent hover:shadow-[var(--inner-highlight-strong),var(--shadow-lg)]">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 className="truncate text-3xl font-semibold tracking-tight text-fg-primary">
              {scenario.name}
            </h3>
            <p className="mt-1 truncate font-mono text-base text-fg-tertiary">
              {scenario.id}
            </p>
          </div>
          <span
            className="text-3xl"
            title={layoutHint}
            aria-label={layoutHint}
          >
            {layoutIcon}
          </span>
        </div>

        <hr className="my-4 border-border-divider" />

        <p className="text-md text-fg-secondary line-clamp-3">
          {scenario.description || t("pre_run.no_description")}
        </p>

        <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-1 text-base text-fg-tertiary">
          <span>
            {t("scenario_card.ticks_label", { count: scenario.total_ticks })}
          </span>
          <span aria-hidden="true">·</span>
          <span className="truncate font-mono">
            {t("scenario_card.world_id_label", { id: scenario.world_id })}
          </span>
        </div>

        <button
          type="button"
          onClick={onStart}
          disabled={disabled}
          className="mt-6 self-start rounded-full bg-accent px-4 py-2 text-md font-medium text-fg-on-accent shadow-inner-highlight transition-all duration-fast ease-out hover:scale-[1.015] hover:bg-accent-hover hover:shadow-glow-accent focus-visible:shadow-focus focus-visible:outline-none active:scale-[0.985] disabled:cursor-not-allowed disabled:bg-surface-active disabled:text-fg-muted disabled:hover:scale-100"
        >
          {t("scenario_card.start")}
        </button>
      </div>
    );
  }

  // upcoming / custom 占位卡片
  const { emoji, name, description, onStart } = props;
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onStart}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onStart();
        }
      }}
      className="flex cursor-pointer flex-col rounded-xl border border-dashed border-border-subtle bg-canvas p-6 transition-all duration-fast ease-out hover:-translate-y-0.5 hover:border-border-default hover:bg-surface focus-visible:shadow-focus focus-visible:outline-none"
    >
      <h3 className="text-3xl font-semibold tracking-tight text-fg-tertiary">
        <span aria-hidden="true">{emoji}</span> {name}
      </h3>
      <hr className="my-4 border-border-divider" />
      <p className="flex-1 text-md text-fg-tertiary">{description}</p>
      <span className="mt-6 self-start rounded-md border border-border-subtle bg-surface px-4 py-2 text-md font-medium text-fg-muted">
        {t("scenario_card.v0_3_label")}
      </span>
    </div>
  );
}

export default ScenarioCard;
