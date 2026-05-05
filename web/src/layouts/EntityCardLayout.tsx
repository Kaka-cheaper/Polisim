/**
 * EntityCardLayout —— 跑中主区"实体卡片"布局（mockup §4.3.1 + §11.3 L1）。
 *
 * PR4.1 范围：
 *   - 渲染 entries[]（已由 Running 组件预组装好，含 type / decision_mode / 当前+上一
 *     tick 属性 / 最新 decision/action event）—— 见 EntityCardEntry 定义
 *   - 底部 environment 行：列出环境变量 key=value
 *
 * 不在本组件里：
 *   - 数据组装（runDetail / stream → entries） —— Running 负责（避免 Layout 耦合 hooks）
 *   - 干预浮层（InterventionDrawer） —— PR4.2
 *   - prevSnapshotByRunId 跨页缓存（uiStore） —— PR4 后续阶段
 *
 * 网格策略：1 列（mobile）/ 2 列（>=tablet 1024px）/ 3 列（>=desktop 1280px）。
 */
import { useTranslation } from "react-i18next";

import { EntityCard, type EntityCardEntry } from "../components/EntityCard";

interface Props {
  entries: EntityCardEntry[];
  /** Snapshot.environment_state；可能为空。*/
  environment?: Record<string, unknown> | null | undefined;
  /** 点击实体卡片回调（PR4.2 接通暂停 + 干预）。*/
  onEntityClick?: (id: string) => void;
}

function formatEnvValue(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") {
    return Number.isInteger(v) ? String(v) : v.toFixed(2);
  }
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "string") return v;
  return JSON.stringify(v);
}

export function EntityCardLayout({ entries, environment, onEntityClick }: Props) {
  const { t } = useTranslation();
  const envEntries = environment ? Object.entries(environment) : [];

  return (
    <div>
      <div className="grid grid-cols-1 gap-4 tablet:grid-cols-2 desktop:grid-cols-3">
        {entries.map((entry) => (
          <EntityCard
            key={entry.id}
            entry={entry}
            onIntervene={
              onEntityClick ? () => onEntityClick(entry.id) : undefined
            }
          />
        ))}
      </div>

      {envEntries.length > 0 && (
        <section className="mt-6 rounded-lg border border-border-subtle bg-canvas px-4 py-3">
          <h3 className="text-md font-medium uppercase tracking-wide text-fg-tertiary">
            🌐 environment
          </h3>
          <ul className="mt-2 flex flex-wrap gap-x-6 gap-y-1">
            {envEntries.map(([k, v]) => (
              <li
                key={k}
                className="flex items-center gap-2 font-mono text-base"
              >
                <span className="text-fg-tertiary">{k}</span>
                <span className="text-fg-secondary">=</span>
                <span className="text-fg-primary">{formatEnvValue(v)}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {entries.length === 0 && (
        <p className="mt-12 text-center text-fg-tertiary">
          {t("running.loading")}
        </p>
      )}
    </div>
  );
}

export default EntityCardLayout;
