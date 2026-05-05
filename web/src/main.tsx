/**
 * Polisim Web 应用入口（PR2 升级）。
 *
 * 加载顺序：
 *   1. i18n 初始化（本文件 import 触发副作用）—— 必须在 App 渲染前完成
 *   2. index.css —— tokens.css + Tailwind 全局样式
 *   3. ErrorBoundary（最外层）—— catch React 渲染错误，显示降级 UI
 *   4. QueryClientProvider —— react-query 缓存 context（hooks 层依赖）
 *   5. BrowserRouter —— 路由 context
 *   6. Toaster —— sonner toast 容器（mockup §9.8 决策 C：4xx 错误走 toast）
 *
 * StrictMode：dev 双 mount/unmount——useRunStream 等副作用 hook 已适配。
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "sonner";

import { ErrorBoundary } from "./components/ErrorBoundary";
import "./i18n";
import "./index.css";
import App from "./App";

/**
 * 全局 QueryClient —— PR2 默认配置：
 *   - retry=1：4xx 客户端错误重试 1 次（足够覆盖瞬时 race；多了浪费）
 *   - refetchOnWindowFocus=false：演示场景不需要切回浏览器自动刷新
 *   - staleTime=5s：基础 stale 容忍，避免快速切路由重 fetch
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5_000,
    },
    mutations: {
      retry: 0,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
        <Toaster position="top-right" theme="dark" richColors closeButton />
      </QueryClientProvider>
    </ErrorBoundary>
  </StrictMode>,
);
