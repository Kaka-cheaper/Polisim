/**
 * App —— 顶层组件（PR1）。
 *
 * 职责：
 *   1. 渲染 TopBar（顶栏 + 中英切换）
 *   2. 注册 4 条路由（mockup §11.2）
 *   3. 把 zustand store.locale 同步到 i18n（单一真理纪律见 i18n/index.ts）
 *
 * 不在本组件里做：
 *   - 数据获取（hooks 在 PR2 起进 routes 内部）
 *   - WebSocket 订阅（PR2 起）
 *   - 全局 ErrorBoundary（PR2 起）
 */
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Route, Routes } from "react-router-dom";

import TopBar from "./components/TopBar";
import Finished from "./routes/Finished";
import Gallery from "./routes/Gallery";
import PreRun from "./routes/PreRun";
import Running from "./routes/Running";
import { useUiStore } from "./store/ui_store";

export default function App() {
  const { i18n } = useTranslation();
  const locale = useUiStore((s) => s.locale);

  useEffect(() => {
    if (i18n.language !== locale) {
      void i18n.changeLanguage(locale);
    }
  }, [locale, i18n]);

  return (
    <div className="min-h-screen bg-canvas text-fg-primary antialiased">
      <TopBar />
      <Routes>
        <Route path="/" element={<Gallery />} />
        <Route path="/runs/:runId/intro" element={<PreRun />} />
        <Route path="/runs/:runId/run" element={<Running />} />
        <Route path="/runs/:runId/finished" element={<Finished />} />
      </Routes>
    </div>
  );
}
