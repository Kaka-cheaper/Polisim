/**
 * NarrativeReport —— 跑完页主区 4 段 LLM 报告（mockup §4.5 + §11.5 C6）。
 *
 * 4 段对应 `AnalysisResult` 的 Phase C 字段：
 *   - 📖 world_overview
 *   - 📜 narrative_summary
 *   - ⚖️ situation_judgement
 *   - 💡 next_action_suggestions（list<str>，渲染为 numbered list）
 *
 * 每段 fallback：
 *   - null/空 → 显示「LLM 未生成此段（Phase A 模式）」提示
 *
 * react-markdown 默认配置：
 *   - GFM 暂不开（v0.2 不需 table / strikethrough）
 *   - tick 引用 `[tick 3](#tick-3)` 由 onTickRefClick 处理（PR5.5 副区高亮接通；
 *     当前 PR5 仅渲染为普通链接，点击无效）
 *
 * 不在本组件做：
 *   - 副区 tabs（PR5.5 FinishedSidePanel）
 *   - LLM 增强失败重试（PR5.5 useFinishedRun retryEnhance）
 */
import { useTranslation } from "react-i18next";
import ReactMarkdown from "react-markdown";

import type { AnalysisResult } from "../api/schema";

interface Props {
  result: AnalysisResult | null;
}

interface Section {
  emoji: string;
  titleKey: string;
  content: string | null;
}

export function NarrativeReport({ result }: Props) {
  const { t } = useTranslation();

  if (result === null) {
    // loading skeleton —— 四段灰色块
    return (
      <article className="rounded-xl border border-border-default bg-surface p-8 shadow-md">
        <p className="text-md text-fg-tertiary">
          {t("finished.narrative.loading")}
        </p>
        <div className="mt-6 space-y-6">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="space-y-2">
              <div className="h-5 w-1/3 animate-pulse rounded bg-surface-active" />
              <div className="h-4 w-full animate-pulse rounded bg-surface-active" />
              <div className="h-4 w-5/6 animate-pulse rounded bg-surface-active" />
            </div>
          ))}
        </div>
      </article>
    );
  }

  // 把 next_action_suggestions list 拼成 markdown numbered list
  const suggestionsMd =
    result.next_action_suggestions && result.next_action_suggestions.length > 0
      ? result.next_action_suggestions
          .map((s, i) => `${i + 1}. ${s}`)
          .join("\n")
      : null;

  const sections: Section[] = [
    {
      emoji: "📖",
      titleKey: "finished.narrative.world_overview",
      content: result.world_overview ?? null,
    },
    {
      emoji: "📜",
      titleKey: "finished.narrative.summary",
      content: result.narrative_summary ?? null,
    },
    {
      emoji: "⚖️",
      titleKey: "finished.narrative.judgement",
      content: result.situation_judgement ?? null,
    },
    {
      emoji: "💡",
      titleKey: "finished.narrative.suggestions",
      content: suggestionsMd,
    },
  ];

  return (
    <article className="rounded-xl border border-border-default bg-surface p-8 shadow-md">
      <h2 className="text-4xl font-semibold tracking-tight text-fg-primary">
        {t("finished.narrative.title")}
      </h2>
      <div className="mt-8 space-y-10">
        {sections.map((section) => (
          <section key={section.titleKey}>
            <h3 className="flex items-center gap-2 text-xl font-semibold text-fg-primary">
              <span aria-hidden="true">{section.emoji}</span>
              {t(section.titleKey)}
            </h3>
            <hr className="mt-2 border-border-subtle" />
            {section.content ? (
              <div className="prose prose-invert mt-4 max-w-none text-md leading-relaxed text-fg-secondary [&_a]:text-accent [&_a]:underline [&_li]:my-1 [&_p]:my-3">
                <ReactMarkdown>{section.content}</ReactMarkdown>
              </div>
            ) : (
              <p className="mt-4 text-md italic text-fg-tertiary">
                {t("finished.narrative.empty_section")}
              </p>
            )}
          </section>
        ))}
      </div>
    </article>
  );
}

export default NarrativeReport;
