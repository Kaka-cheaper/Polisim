/**
 * Tailwind config（v3） —— PR1 落地：把 design-system/tokens.css 的 semantic 层桥接到
 * theme.extend.colors / fontFamily / spacing / borderRadius / boxShadow / fontSize /
 * lineHeight / letterSpacing / transitionDuration / transitionTimingFunction / zIndex /
 * screens。
 *
 * 设计规则（mockup §8.4）：
 *   - 业务组件代码只允许引用 semantic 层（`bg-canvas` / `text-primary` / `accent` 等）
 *   - 严禁直接用 primitives 层的 `--color-bg-primary` / `--color-text-primary`
 *   - 主题切换通过 [data-theme="light"] 块覆盖 semantic 层即可（v0.3+ 启用，本 PR 不实施）
 *
 * Tailwind v3 不支持把 CSS variables 与 opacity-modifier 一起用（`bg-canvas/50` 不工作）；
 * 后续若需要透明度可改写为 `var(<token> / <alpha-value>)` 函数式形态。本 PR 直接用字符串。
 */
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // 背景
        canvas: "var(--bg-canvas)",
        surface: "var(--bg-surface)",
        "surface-hover": "var(--bg-surface-hover)",
        "surface-active": "var(--bg-surface-active)",
        panel: "var(--bg-panel)",
        overlay: "var(--bg-overlay)",
        header: "var(--bg-header)",
        input: "var(--bg-input)",
        "input-hover": "var(--bg-input-hover)",
        // 文字（用 fg-* 命名空间避免与 Tailwind 内置 text-* 冲突）
        "fg-primary": "var(--text-primary)",
        "fg-secondary": "var(--text-secondary)",
        "fg-tertiary": "var(--text-tertiary)",
        "fg-muted": "var(--text-muted)",
        "fg-on-accent": "var(--text-on-accent)",
        "fg-link": "var(--text-link)",
        "fg-link-hover": "var(--text-link-hover)",
        // 边框
        "border-subtle": "var(--border-subtle)",
        "border-default": "var(--border-default)",
        "border-strong": "var(--border-strong)",
        "border-divider": "var(--border-divider)",
        "border-divider-strong": "var(--border-divider-strong)",
        "border-focus": "var(--border-focus)",
        // Accent
        accent: "var(--accent)",
        "accent-hover": "var(--accent-hover)",
        "accent-tint": "var(--accent-tint)",
        "accent-brand": "var(--accent-brand)",
        // Status
        "status-success": "var(--status-success)",
        "status-danger": "var(--status-danger)",
        "status-warning": "var(--status-warning)",
        "status-info": "var(--status-info)",
        "status-accent": "var(--status-accent)",
        // Polisim 业务专属
        "polisim-tick-active": "var(--polisim-tick-active)",
        "polisim-llm-bubble": "var(--polisim-llm-bubble)",
        "polisim-rule-bubble": "var(--polisim-rule-bubble)",
        "polisim-paused": "var(--polisim-paused)",
        "polisim-breakpoint": "var(--polisim-breakpoint)",
        "polisim-relation-positive": "var(--polisim-relation-positive)",
        "polisim-relation-negative": "var(--polisim-relation-negative)",
        "polisim-environment": "var(--polisim-environment)",
        "polisim-intervention": "var(--polisim-intervention)",
      },
      fontFamily: {
        sans: "var(--font-sans)",
        mono: "var(--font-mono)",
      },
      fontSize: {
        // 字号映射 tokens.css 的 --text-* scale（10/11/12/13/14/15/16/17/18/20/24/32/48/64/72px）
        // 注意命名错位：tokens.css 的 --text-md 是 14px（高于 base 13px），与 Tailwind 默认 md=16px 不同。
        // 这里直接 1:1 桥接，不改 Tailwind 默认（默认体系仍可用，业务组件优先用语义类如 text-base 表 13px body）。
        xs: "var(--text-xs)",
        "2xs": "var(--text-2xs)",
        sm: "var(--text-sm)",
        base: "var(--text-base)",
        md: "var(--text-md)",
        lg: "var(--text-lg)",
        xl: "var(--text-xl)",
        "2xl": "var(--text-2xl)",
        "3xl": "var(--text-3xl)",
        "4xl": "var(--text-4xl)",
        "5xl": "var(--text-5xl)",
        "6xl": "var(--text-6xl)",
        "7xl": "var(--text-7xl)",
        "8xl": "var(--text-8xl)",
        "9xl": "var(--text-9xl)",
      },
      fontWeight: {
        light: "var(--weight-light)",
        normal: "var(--weight-regular)",
        medium: "var(--weight-medium)",
        semibold: "var(--weight-semibold)",
      },
      lineHeight: {
        tight: "var(--leading-tight)",
        snug: "var(--leading-snug)",
        normal: "var(--leading-normal)",
        relaxed: "var(--leading-relaxed)",
        loose: "var(--leading-loose)",
      },
      letterSpacing: {
        // session 44 加：display 三档极致负 tracking（Linear/Vercel "minified-engineering" 美学）
        "display-xl": "var(--tracking-display-xl)",
        "display-lg": "var(--tracking-display-lg)",
        "display-md": "var(--tracking-display-md)",
        tight: "var(--tracking-tight)",
        normal: "var(--tracking-normal)",
        wide: "var(--tracking-wide)",
      },
      spacing: {
        "1.5": "var(--space-1-5)",
      },
      borderRadius: {
        none: "var(--radius-none)",
        xs: "var(--radius-xs)",
        sm: "var(--radius-sm)",
        DEFAULT: "var(--radius-md)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
        "2xl": "var(--radius-2xl)",
        full: "var(--radius-full)",
        circle: "var(--radius-circle)",
      },
      boxShadow: {
        none: "var(--shadow-none)",
        xs: "var(--shadow-xs)",
        sm: "var(--shadow-sm)",
        DEFAULT: "var(--shadow-md)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
        xl: "var(--shadow-xl)",
        "2xl": "var(--shadow-2xl)",
        focus: "var(--shadow-focus)",
        // session 44 加：Linear-style 顶边白光（用法：shadow-inner-highlight 或叠加在 card 上）
        "inner-highlight": "var(--inner-highlight)",
        "inner-highlight-strong": "var(--inner-highlight-strong)",
      },
      transitionDuration: {
        instant: "var(--motion-duration-instant)",
        fast: "var(--motion-duration-fast)",
        normal: "var(--motion-duration-normal)",
        slow: "var(--motion-duration-slow)",
        slower: "var(--motion-duration-slower)",
      },
      transitionTimingFunction: {
        out: "var(--motion-ease-out)",
        in: "var(--motion-ease-in)",
        "in-out": "var(--motion-ease-in-out)",
        bounce: "var(--motion-ease-bounce)",
      },
      zIndex: {
        base: "var(--z-base)",
        elevated: "var(--z-elevated)",
        sticky: "var(--z-sticky)",
        overlay: "var(--z-overlay)",
        modal: "var(--z-modal)",
        toast: "var(--z-toast)",
        tooltip: "var(--z-tooltip)",
      },
      maxWidth: {
        layout: "var(--layout-max-width)",
      },
      screens: {
        // tokens.css §10 的断点：tablet=1024 / desktop=1280 / wide=1536
        // 与 Tailwind 默认 lg=1024 / xl=1280 / 2xl=1536 一致；显式重声明保证语义对齐 mockup §5。
        tablet: "1024px",
        desktop: "1280px",
        wide: "1536px",
      },
    },
  },
  plugins: [],
};

export default config;
