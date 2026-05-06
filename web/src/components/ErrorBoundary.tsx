/**
 * ErrorBoundary —— React 渲染错误兜底（mockup §9.8 决策 C 部分）。
 *
 * 单一职责：catch React render / lifecycle 抛出的未捕获异常，显示降级 UI；
 * 业务错误（API 4xx/5xx）由各 hook 的 onError → toast/modal 处理，**不**经此组件。
 *
 * 设计：
 *   - class component（React 仅在 class 形态提供 getDerivedStateFromError）
 *   - fallback UI 用 useTranslation 的函数子组件，内部访问 i18n
 *   - 提供 reset() 方法 —— 调用方可在 banner 上加"重试"按钮触发
 */
import { Component, type ErrorInfo, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    // 控制台记录 —— 生产环境可加上报
    console.error("[ErrorBoundary] React render crashed:", error, info);
  }

  reset = (): void => {
    this.setState({ error: null });
  };

  override render(): ReactNode {
    if (this.state.error) {
      return <RenderErrorFallback error={this.state.error} onReset={this.reset} />;
    }
    return this.props.children;
  }
}

interface FallbackProps {
  error: Error;
  onReset: () => void;
}

function RenderErrorFallback({ error, onReset }: FallbackProps) {
  const { t } = useTranslation();
  const handleReload = () => {
    window.location.reload();
  };

  return (
    <div
      role="alert"
      className="mx-auto max-w-layout px-6 py-12"
      style={{ minHeight: "60vh" }}
    >
      <div className="rounded-lg border border-status-danger bg-surface p-8 shadow-lg">
        <h1 className="text-3xl font-semibold text-status-danger">
          {t("error.boundary.title")}
        </h1>
        <p className="mt-3 text-fg-secondary">{t("error.boundary.description")}</p>
        <pre className="mt-4 overflow-auto rounded-md border border-border-subtle bg-canvas p-4 font-mono text-base text-fg-tertiary">
          {error.message}
        </pre>
        <div className="mt-6 flex gap-3">
          <button
            type="button"
            onClick={onReset}
            className="rounded-md border border-border-default bg-surface px-4 py-2 text-md font-medium text-fg-primary transition-colors duration-fast hover:border-accent hover:bg-surface-hover"
          >
            {t("error.boundary.retry")}
          </button>
          <button
            type="button"
            onClick={handleReload}
            className="rounded-full bg-accent px-4 py-2 text-md font-medium text-fg-on-accent transition-all duration-fast ease-out hover:bg-accent-hover hover:shadow-glow-accent"
          >
            {t("error.boundary.reload")}
          </button>
        </div>
      </div>
    </div>
  );
}
