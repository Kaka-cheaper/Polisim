/**
 * Gallery 路由 —— 场景画廊页（mockup §4.1 + §11.2 P1 + PR3 实施）。
 *
 * 三段：
 *   1. **现成场景**（production）：`useScenarios()` → `GET /api/v1/scenarios` 列出
 *      ScenarioSummary[]，每个走 ScenarioCard kind="production"，[▶ 开始] 调
 *      `useCreateRun.mutateAsync` 创建 run + 跳转 `/runs/:id/intro`
 *   2. **即将到来**（upcoming）：硬编码 2 张占位卡片（信息级联 / 组织决策）—— 不调 API；
 *      点击触发 `toast.info("v0.3+...")`
 *   3. **自定义**（custom）：1 张占位卡片（LLM 辅助建模）—— 同上 toast 提示
 *
 * 状态：
 *   - `useScenarios` loading → skeleton
 *   - `useScenarios` error → banner + 重试按钮
 *   - `useScenarios` empty → 文案提示（mockup §4.1 兼容 server scenarios/ 为空场景）
 *   - `useCreateRun.isPending` → 所有 production 卡片按钮 disabled，避免双击
 */
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import type { ScenarioSummary } from "../api/schema";
import { ScenarioCard } from "../components/ScenarioCard";
import BlurText from "../components/BlurText";
import { useCreateRun } from "../hooks/useCreateRun";
import { useScenarios } from "../hooks/useScenarios";

interface PlaceholderCard {
  id: string;
  emoji: string;
  nameKey: string;
  descKey: string;
}

const UPCOMING_CARDS: readonly PlaceholderCard[] = [
  {
    id: "info_cascade",
    emoji: "📰",
    nameKey: "gallery.upcoming.info_cascade.name",
    descKey: "gallery.upcoming.info_cascade.description",
  },
  {
    id: "organization_decision",
    emoji: "🏛",
    nameKey: "gallery.upcoming.organization_decision.name",
    descKey: "gallery.upcoming.organization_decision.description",
  },
] as const;

export default function Gallery() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const {
    data: scenarios,
    isLoading,
    error,
    refetch,
  } = useScenarios();
  const createRun = useCreateRun();

  const handleStartProduction = async (scenario: ScenarioSummary) => {
    try {
      const detail = await createRun.mutateAsync({
        scenario_path: scenario.path,
        // 显式 mock —— Pydantic 端 default="mock"，但 openapi-typescript v7 把
        // 带 default 的字段也列入 required 数组。后续 PR4 高级选项接通业务时改读
        // AdvancedOptionsPanel 的 value.llm_provider。
        llm_provider: "mock",
      });
      navigate(`/runs/${detail.summary.run_id}/intro`);
    } catch {
      // useCreateRun.onError 已 toast 4xx/5xx；此处静默
    }
  };

  const handleClickPlaceholder = () => {
    toast.info(t("gallery.coming_soon_toast"));
  };

  return (
    <main className="mx-auto max-w-layout px-6 py-12">
      {/* Hero section: radial glow + BlurText + glass badge (session 45) */}
      <header
        className="relative pb-8 pt-4 text-center"
        style={{ background: "var(--gradient-hero-glow)" }}
      >
        {/* Glass badge */}
        <div className="mb-6 inline-flex items-center gap-2 liquid-glass rounded-full px-1 py-1">
          <span className="rounded-full bg-accent px-3 py-1 text-xs font-semibold text-fg-on-accent">
            {t("gallery.badge_new", "New")}
          </span>
          <span className="pr-3 text-xs font-medium text-fg-secondary">
            {t("gallery.badge_text", "AI-powered multi-agent simulation")}
          </span>
        </div>

        <BlurText
          text={t("gallery.title")}
          className="mx-auto max-w-3xl font-heading text-7xl text-fg-primary leading-[0.9] tracking-tight"
          italic
          delay={100}
        />
        <p className="mt-5 text-xl text-fg-secondary">
          {t("gallery.subtitle")}
        </p>
        <p className="mt-2 text-md text-fg-tertiary">{t("gallery.tagline")}</p>
      </header>

      {/* loading skeleton */}
      {isLoading && (
        <section className="mt-12 grid grid-cols-1 gap-6 desktop:grid-cols-2">
          {[0, 1].map((i) => (
            <div
              key={i}
              className="h-64 animate-pulse rounded-xl bg-surface-hover"
            />
          ))}
        </section>
      )}

      {/* error banner */}
      {error && (
        <div
          role="alert"
          className="mt-12 rounded-lg border border-status-danger bg-surface p-6"
        >
          <h2 className="text-2xl font-semibold text-status-danger">
            {t("gallery.error_title")}
          </h2>
          <p className="mt-2 text-md text-fg-secondary">
            {t("gallery.error_hint")}
          </p>
          <p className="mt-2 font-mono text-base text-fg-tertiary">
            {error.message}
          </p>
          <button
            type="button"
            onClick={() => void refetch()}
            className="mt-4 rounded-md border border-border-default bg-surface px-4 py-2 text-md font-medium text-fg-primary shadow-inner-highlight transition-all duration-fast ease-out hover:-translate-y-px hover:border-accent hover:bg-surface-hover focus-visible:shadow-focus focus-visible:outline-none active:translate-y-0"
          >
            {t("gallery.retry")}
          </button>
        </div>
      )}

      {/* production scenarios */}
      {scenarios && scenarios.length > 0 && (
        <section className="mt-12">
          <h2 className="text-md font-medium uppercase tracking-wide text-fg-tertiary">
            {t("gallery.section.production")}
          </h2>
          <div className="mt-4 grid grid-cols-1 gap-6 desktop:grid-cols-2">
            {scenarios.map((s) => (
              <ScenarioCard
                key={s.id}
                kind="production"
                scenario={s}
                onStart={() => void handleStartProduction(s)}
                disabled={createRun.isPending}
              />
            ))}
          </div>
        </section>
      )}

      {scenarios && scenarios.length === 0 && (
        <p className="mt-12 text-center text-fg-tertiary">
          {t("gallery.empty")}
        </p>
      )}

      {/* upcoming */}
      <section className="mt-12">
        <h2 className="text-md font-medium uppercase tracking-wide text-fg-tertiary">
          {t("gallery.section.upcoming")}
        </h2>
        <div className="mt-4 grid grid-cols-1 gap-6 desktop:grid-cols-2">
          {UPCOMING_CARDS.map((c) => (
            <ScenarioCard
              key={c.id}
              kind="upcoming"
              emoji={c.emoji}
              name={t(c.nameKey)}
              description={t(c.descKey)}
              onStart={handleClickPlaceholder}
            />
          ))}
        </div>
      </section>

      {/* custom */}
      <section className="mt-8">
        <h2 className="text-md font-medium uppercase tracking-wide text-fg-tertiary">
          {t("gallery.section.custom")}
        </h2>
        <div className="mt-4">
          <ScenarioCard
            kind="custom"
            emoji="✨"
            name={t("gallery.custom.title")}
            description={t("gallery.custom.description")}
            onStart={handleClickPlaceholder}
          />
        </div>
      </section>
    </main>
  );
}
