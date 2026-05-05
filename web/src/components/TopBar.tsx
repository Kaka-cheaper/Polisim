/**
 * TopBar —— 顶栏（PR1 最小版）。
 *
 * 包含：项目名 Link 回画廊 + 中英切换按钮。
 *
 * mockup §5.1 顶栏布局参考；完整顶栏（含场景名 / 状态徽章 / Run ID）见 PR4。
 *
 * 中英切换：写 zustand store.locale；App.tsx 的 useEffect 把变更同步到 i18n.changeLanguage。
 */
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { useUiStore } from "../store/ui_store";

export default function TopBar() {
  const { t } = useTranslation();
  const locale = useUiStore((s) => s.locale);
  const setLocale = useUiStore((s) => s.setLocale);

  const handleToggleLocale = () => {
    setLocale(locale === "zh" ? "en" : "zh");
  };

  return (
    <header
      className="sticky top-0 z-sticky flex items-center justify-between border-b border-border-divider bg-header px-6 backdrop-blur"
      style={{ height: "var(--layout-header-height)" }}
    >
      <Link
        to="/"
        className="text-xl font-semibold tracking-tight text-fg-primary transition-colors duration-fast hover:text-accent"
      >
        {t("topbar.title")}
      </Link>
      <button
        type="button"
        onClick={handleToggleLocale}
        aria-label={t("topbar.lang_toggle_aria")}
        className="rounded-md border border-border-default bg-surface px-3 py-1 text-md font-medium text-fg-secondary transition-colors duration-fast hover:border-accent hover:bg-surface-hover hover:text-fg-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-border-focus"
      >
        {t("topbar.lang_toggle")}
      </button>
    </header>
  );
}
