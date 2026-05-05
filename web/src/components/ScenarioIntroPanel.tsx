/**
 * ScenarioIntroPanel —— 跑前页"场景叙事"主区（mockup §4.2 + §11.6 C14）。
 *
 * 三段：
 *   1. 场景描述：`runDetail.scenario.scenario.description`（多行 whitespace-pre-line）
 *   2. 参与实体：`runDetail.scenario.entities[]` + 查 `world.entity_types[type].decision_mode`
 *      显示 emoji / name / type / decision_mode 标签
 *   3. 预设事件：`runDetail.scenario.scheduled_events[]?` 摘要（"第 N tick · type"）
 *
 * 不在本组件做：
 *   - LLM 决策 prompt 预览（PR4 PromptContextModal）
 *   - 实体属性详情面板（PR4 EntityCardLayout）
 *   - relation 初始拓扑（PR4 RelationGraphLayout）
 */
import { useTranslation } from "react-i18next";

import type {
  EntityInstance,
  RunDetail,
  ScheduledEvent,
} from "../api/schema";

interface Props {
  runDetail: RunDetail;
}

/** 按 entity type 名关键词匹配 emoji；未命中走默认。 */
function entityTypeEmoji(type: string): string {
  const lower = type.toLowerCase();
  if (lower.includes("compan")) return "🏢";
  if (lower.includes("regul")) return "👮";
  if (lower.includes("negotiat")) return "🤝";
  if (lower.includes("agent")) return "🤖";
  return "▪️";
}

/** decision_mode 取值守卫：仅 llm/rule/random 走 i18n 子 key，其余 fallback default。*/
function decisionModeKey(mode: string | null | undefined): string {
  if (mode === "llm" || mode === "rule" || mode === "random") return mode;
  return "default";
}

export function ScenarioIntroPanel({ runDetail }: Props) {
  const { t } = useTranslation();
  const { scenario, world } = runDetail;
  const description = scenario.scenario.description ?? "";
  const entities = scenario.entities;
  const scheduledEvents = scenario.scheduled_events ?? [];
  const entityTypes = world.entity_types;

  return (
    <article className="rounded-xl border border-border-default bg-surface p-8 shadow-md">
      <h2 className="text-4xl font-semibold tracking-tight text-fg-primary">
        {t("pre_run.story_title")}
      </h2>

      {/* 描述 */}
      <section className="mt-6">
        <h3 className="text-md font-medium uppercase tracking-wide text-fg-tertiary">
          {t("pre_run.section.description")}
        </h3>
        <p className="mt-2 whitespace-pre-line text-lg leading-relaxed text-fg-secondary">
          {description.length > 0 ? description : t("pre_run.no_description")}
        </p>
      </section>

      {/* 实体列表 */}
      <section className="mt-6">
        <h3 className="text-md font-medium uppercase tracking-wide text-fg-tertiary">
          {t("pre_run.section.entities")}
        </h3>
        <ul className="mt-3 space-y-2">
          {entities.map((e: EntityInstance) => {
            const typeSchema = entityTypes[e.type];
            const mode = typeSchema?.decision_mode;
            const modeKey = decisionModeKey(mode);
            const displayName = e.name ?? e.id;
            return (
              <li
                key={e.id}
                className="flex items-center gap-3 rounded-md border border-border-subtle bg-canvas px-3 py-2"
              >
                <span className="text-xl" aria-hidden="true">
                  {entityTypeEmoji(e.type)}
                </span>
                <span className="font-semibold text-fg-primary">
                  {displayName}
                </span>
                <span className="font-mono text-base text-fg-tertiary">
                  {e.type}
                </span>
                <span className="ml-auto rounded-sm bg-surface-active px-2 py-0.5 font-mono text-base text-fg-tertiary">
                  {t(`pre_run.decision_mode.${modeKey}`)}
                </span>
              </li>
            );
          })}
        </ul>
      </section>

      {/* scheduled events */}
      <section className="mt-6">
        <h3 className="text-md font-medium uppercase tracking-wide text-fg-tertiary">
          {t("pre_run.section.schedule")}
        </h3>
        {scheduledEvents.length === 0 ? (
          <p className="mt-2 text-md text-fg-tertiary">
            {t("pre_run.no_scheduled_events")}
          </p>
        ) : (
          <ul className="mt-3 space-y-1">
            {scheduledEvents.map((ev: ScheduledEvent, i: number) => (
              <li
                key={`${ev.tick}-${ev.type}-${i}`}
                className="flex items-baseline gap-2 text-md text-fg-secondary"
              >
                <span aria-hidden="true">📅</span>
                <span>
                  {t("pre_run.scheduled_event", {
                    tick: ev.tick,
                    type: ev.type,
                  })}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </article>
  );
}

export default ScenarioIntroPanel;
