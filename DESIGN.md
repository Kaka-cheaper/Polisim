---
version: alpha
name: Polisim
description: >
  Polisim is a layered, multi-entity simulation engine with a real-time situational
  dashboard. The visual language is dark-first, calm, and information-dense — inspired
  by linear.app — designed to make LLM decisions, entity relationships, and tick
  progression all instantly readable on the same screen.

# ---------------------------------------------------------------------------
# Colors (semantic, dark theme primary)
#   Source of truth: web/src/styles/tokens.css :root section.
#   Token references use {colors.<name>} syntax (W3C Design Tokens spec).
# ---------------------------------------------------------------------------
colors:
  # Surfaces (4-step ladder — session 44 强化 Linear 用法语义)
  #   bg-canvas       → 顶级画布（body）；0-elevation，最深
  #   bg-surface      → 默认卡片（resting state）；level 1
  #   bg-surface-hover→ hover 状态；level 1.5（transient only）
  #   bg-surface-active→ 选中 / 激活 / dropdown；level 2
  #   bg-panel        → sidebar / topbar 底色（介于 canvas 与 surface 之间）
  bg-canvas: "#08090a"          # Top-level canvas (body)
  bg-surface: "#1c1c1f"         # Cards / blocks
  bg-surface-hover: "#232326"   # Card hover
  bg-surface-active: "#28282c"  # Card selected / pressed
  bg-panel: "#0f1011"           # Sidebar / topbar base
  bg-overlay: "rgba(0,0,0,0.85)" # Modal scrim
  bg-input: "rgba(255,255,255,0.03)"

  # Inner highlight（Linear-style 顶边白光，session 44 加）
  inner-highlight: "inset 0 1px 0 0 rgba(255,255,255,0.04)"
  inner-highlight-strong: "inset 0 1px 0 0 rgba(255,255,255,0.08)"

  # Text
  fg-primary: "#f7f8f8"         # Main text
  fg-secondary: "#d0d6e0"       # Secondary text
  fg-tertiary: "#8a8f98"        # Caption / meta
  fg-muted: "#62666d"           # Disabled / placeholder
  fg-on-accent: "#f7f8f8"       # Text on accent fill

  # Borders
  border-subtle: "#23252a"      # Block boundaries
  border-default: "#34343a"     # Default border
  border-strong: "#3e3e44"      # Emphasized border
  border-divider: "rgba(255,255,255,0.05)"
  border-focus: "#5e69d1"

  # Accent (Linear purple)
  accent: "#7170ff"             # Primary CTA / focus
  accent-hover: "#828fff"
  accent-tint: "#18182f"        # Selected card background
  accent-brand: "#5e6ad2"

  # Status
  status-success: "#27a644"     # Success / high trust
  status-danger: "#eb5757"      # Error / low trust
  status-warning: "#f0bf00"     # Warning / mid trust
  status-info: "#4ea7fc"        # Info / LLM decision-mode node
  status-accent: "#00b8cc"      # 5th status (rarely used)

  # Polisim business-domain semantic tokens
  polisim-tick-active: "{colors.accent}"          # Current tick highlight
  polisim-llm-bubble: "#232326"                   # LLM decision bubble bg
  polisim-rule-bubble: "#1c1c1f"                  # Rule decision bubble bg
  polisim-paused: "#f0bf00"                       # Paused state indicator
  polisim-breakpoint: "#fc7840"                   # Breakpoint triggered
  polisim-relation-positive: "{colors.status-success}"  # Trust ≥ 70
  polisim-relation-negative: "{colors.status-danger}"   # Trust ≤ 40
  polisim-environment: "{colors.status-info}"     # Environment variables
  polisim-intervention: "#fc7840"                 # Manual intervention marker

# ---------------------------------------------------------------------------
# Typography
#   Sans = Inter Variable (UI). Mono = JetBrains Mono (code, IDs, hex, ticks).
#   Linear's typographic features (cv01, ss03) intentionally enabled.
# ---------------------------------------------------------------------------
typography:
  # Display（session 44 加：Linear/Vercel "minified-engineering" 美学）
  display-xl:
    fontFamily: "Inter Variable"
    fontSize: 4.5rem      # 72px — hero headline
    fontWeight: 590
    lineHeight: 1.0
    letterSpacing: -0.042em  # ≈ -3.0px @ 72px
  display-lg:
    fontFamily: "Inter Variable"
    fontSize: 3.5rem      # 56px — section opener
    fontWeight: 590
    lineHeight: 1.0
    letterSpacing: -0.0375em  # ≈ -2.1px @ 56px
  display-md:
    fontFamily: "Inter Variable"
    fontSize: 2.5rem      # 40px — sub-section
    fontWeight: 590
    lineHeight: 1.0
    letterSpacing: -0.0375em  # ≈ -1.5px @ 40px

  # Headings
  h1:
    fontFamily: "Inter Variable"
    fontSize: 3rem        # 48px
    fontWeight: 590
    lineHeight: 1.0
    letterSpacing: -0.022em
  h2:
    fontFamily: "Inter Variable"
    fontSize: 2rem        # 32px
    fontWeight: 590
    lineHeight: 1.13
    letterSpacing: -0.022em
  h3:
    fontFamily: "Inter Variable"
    fontSize: 1.5rem      # 24px
    fontWeight: 590
    lineHeight: 1.13
  h4:
    fontFamily: "Inter Variable"
    fontSize: 1.25rem     # 20px
    fontWeight: 510
    lineHeight: 1.4
  h5:
    fontFamily: "Inter Variable"
    fontSize: 1.125rem    # 18px
    fontWeight: 510
    lineHeight: 1.4
  h6:
    fontFamily: "Inter Variable"
    fontSize: 1.0625rem   # 17px
    fontWeight: 510
    lineHeight: 1.4

  # Body
  body-lg:
    fontFamily: "Inter Variable"
    fontSize: 1rem        # 16px — primary body / link
    fontWeight: 400
    lineHeight: 1.5
  body-md:
    fontFamily: "Inter Variable"
    fontSize: 0.875rem    # 14px — main UI body / button
    fontWeight: 400
    lineHeight: 1.5
  body-sm:
    fontFamily: "Inter Variable"
    fontSize: 0.8125rem   # 13px — small body
    fontWeight: 400
    lineHeight: 1.4

  # Caption / meta
  caption:
    fontFamily: "Inter Variable"
    fontSize: 0.75rem     # 12px — caption
    fontWeight: 400
    lineHeight: 1.4
  micro:
    fontFamily: "Inter Variable"
    fontSize: 0.6875rem   # 11px — tag / micro caption
    fontWeight: 510
    lineHeight: 1.4
    letterSpacing: 0.025em

  # Code / monospace (entity IDs, run IDs, tick numbers, hex values)
  code-md:
    fontFamily: "JetBrains Mono"
    fontSize: 0.875rem    # 14px
    fontWeight: 400
    lineHeight: 1.5
  code-sm:
    fontFamily: "JetBrains Mono"
    fontSize: 0.75rem     # 12px
    fontWeight: 400
    lineHeight: 1.5

# ---------------------------------------------------------------------------
# Rounded (border-radius)
#   Linear's actual radius distribution: xs/md most frequent, lg/xl for cards.
# ---------------------------------------------------------------------------
rounded:
  none: 0
  xs: 2px      # Tags, chips, micro pills
  sm: 4px      # Buttons, code blocks
  md: 6px      # Primary cards, primary buttons
  lg: 8px      # Medium cards
  xl: 12px     # Large cards, panel headers
  full: 9999px # Pill buttons
  circle: 50%  # Avatars, status dots

# ---------------------------------------------------------------------------
# Spacing (4px-grid base; 8px is the dominant unit per Linear)
# ---------------------------------------------------------------------------
spacing:
  px: 1px
  xs: 4px      # Tight padding
  sm: 8px      # Dominant unit (Linear count=45)
  md: 12px     # Mid-range gap
  lg: 16px     # Standard gap
  xl: 24px     # Card-to-card gap
  2xl: 32px    # Block-to-block gap
  3xl: 48px    # Major block gap
  4xl: 64px    # Hero spacing
  5xl: 96px    # Large breathing room

# ---------------------------------------------------------------------------
# Components (Polisim domain components — referenced from React code)
# ---------------------------------------------------------------------------
components:
  # Buttons
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.fg-on-accent}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    typography: "{typography.body-md}"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-secondary:
    backgroundColor: "{colors.bg-surface}"
    textColor: "{colors.fg-primary}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
    border: "1px solid {colors.border-default}"
  button-secondary-hover:
    backgroundColor: "{colors.bg-surface-hover}"

  # Entity card (mockup §4.3.1)
  entity-card:
    backgroundColor: "{colors.bg-surface}"
    textColor: "{colors.fg-primary}"
    rounded: "{rounded.lg}"
    padding: "16px"
    border: "1px solid {colors.border-subtle}"
  entity-card-active:
    backgroundColor: "{colors.bg-surface-active}"
    border: "1px solid {colors.accent}"

  # LLM thought bubble (mockup §4.3.1)
  llm-thought-bubble:
    backgroundColor: "{colors.polisim-llm-bubble}"
    textColor: "{colors.fg-secondary}"
    rounded: "{rounded.md}"
    padding: "12px"
    border: "1px solid {colors.border-subtle}"

  # Control bar (mockup §4.4.1, run-time top bar)
  control-bar:
    backgroundColor: "{colors.bg-panel}"
    textColor: "{colors.fg-primary}"
    height: 64px
    border: "1px solid {colors.border-subtle}"

  # Topbar (mockup §5.1)
  topbar:
    backgroundColor: "{colors.bg-panel}"
    textColor: "{colors.fg-primary}"
    height: 56px
    border: "1px solid {colors.border-subtle}"

  # Scenario card (mockup §4.1, gallery)
  scenario-card:
    backgroundColor: "{colors.bg-surface}"
    textColor: "{colors.fg-primary}"
    rounded: "{rounded.lg}"
    padding: "20px"
    border: "1px solid {colors.border-subtle}"
  scenario-card-hover:
    backgroundColor: "{colors.bg-surface-hover}"
    border: "1px solid {colors.accent}"

  # Modal (intervention drawer / prompt context modal)
  modal:
    backgroundColor: "{colors.bg-surface}"
    textColor: "{colors.fg-primary}"
    rounded: "{rounded.xl}"
    padding: "24px"
    border: "1px solid {colors.border-default}"

  # Status badge (running / paused / finished / failed)
  badge-running:
    backgroundColor: "{colors.status-success}"
    textColor: "{colors.fg-on-accent}"
    rounded: "{rounded.full}"
    padding: "2px 8px"
    typography: "{typography.micro}"
  badge-paused:
    backgroundColor: "{colors.polisim-paused}"
    textColor: "#08090a"
    rounded: "{rounded.full}"
    padding: "2px 8px"
    typography: "{typography.micro}"
  badge-finished:
    backgroundColor: "{colors.status-info}"
    textColor: "{colors.fg-on-accent}"
    rounded: "{rounded.full}"
    padding: "2px 8px"
    typography: "{typography.micro}"

  # Input (advanced options panel, intervention forms)
  input:
    backgroundColor: "{colors.bg-input}"
    textColor: "{colors.fg-primary}"
    rounded: "{rounded.sm}"
    padding: "8px 12px"
    border: "1px solid {colors.border-default}"
  input-focus:
    border: "1px solid {colors.border-focus}"

  # Toast (sonner)
  toast:
    backgroundColor: "{colors.bg-surface}"
    textColor: "{colors.fg-primary}"
    rounded: "{rounded.md}"
    padding: "12px 16px"
    border: "1px solid {colors.border-default}"
---

## Overview

**Calm Density meets Real-Time Telemetry.** The UI evokes a high-end engineer's
control room: cold dark canvas, purple accent reserved for the single most important
action per screen, monospace numerals for anything quantitative (ticks, hex, IDs).
The aesthetic is dark-first because LLM decisions, entity relationships, and tick
progression need to coexist in high information density without visual fatigue.

Reference product: **linear.app** (the dashboard, not the marketing page). Polisim
extends Linear's vocabulary with a small set of domain-semantic tokens (`polisim-*`)
covering simulation primitives — LLM thought bubbles, relation graph trust polarity,
intervention markers, breakpoint highlights — that have no Linear equivalent.

The visual language must:

- **Make LLM reasoning legible.** Decision bubbles get a dedicated background
  (`polisim-llm-bubble`) that visually distinguishes them from rule-based decisions.
- **Make trust polarity scannable.** Relation graph edges use a 3-step color scale
  (positive / warning / negative) tied to numeric trust value, never just hue.
- **Make tick progression obvious.** The current tick is the *only* element that
  uses `polisim-tick-active` — it should never compete with another emphasis.

## Colors

The color system is dark-first with a single accent. Status and domain-specific
hues are reserved for semantic meaning, never decoration.

- **`bg-canvas` (#08090a):** Top-level canvas. The 0-elevation surface.
- **`bg-surface` (#1c1c1f):** Cards, blocks, modals — anything that floats above
  the canvas.
- **`bg-surface-hover` (#232326):** Hover state for any clickable surface.
- **`bg-surface-active` (#28282c):** Selected / pressed state. Pair with an
  accent border to indicate "this is the chosen one".
- **`bg-panel` (#0f1011):** Topbar and sidebar background. Slightly darker than
  canvas to recede; use with `border-subtle` to delineate.
- **`fg-primary` (#f7f8f8):** Main text. Headlines, body emphasis.
- **`fg-secondary` (#d0d6e0):** Secondary text. Entity attributes, narrative body.
- **`fg-tertiary` (#8a8f98):** Captions, meta, tick numbers, "rule" decision-mode
  labels.
- **`fg-muted` (#62666d):** Disabled / placeholder. Never use for primary content.
- **`accent` (#7170ff):** Linear purple. **Reserved for the single primary action
  per screen** — `[▶ Start Simulation]`, `[Apply Intervention]`, focus rings,
  `polisim-tick-active`. Overuse defeats its purpose.
- **`status-success` / `status-danger` / `status-warning` / `status-info`:**
  Status with mandatory semantic meaning. Success = completion / high trust.
  Danger = errors / low trust. Warning = pause / mid trust. Info = LLM-mode nodes.
- **`polisim-relation-positive` / `polisim-relation-negative`:** Aliases for
  status colors when applied to relation graph edges. Always pair with the
  numeric trust value — color alone is not accessible.
- **`polisim-paused` (#f0bf00):** The single yellow on screen during a paused
  state. Avoid using `status-warning` simultaneously to prevent visual collision.
- **`polisim-breakpoint` / `polisim-intervention` (#fc7840):** Orange reserved
  for "user-driven exceptional event". Distinct from `polisim-paused` (auto-pause)
  and from accent (planned action).

## Typography

**Sans:** Inter Variable. **Mono:** JetBrains Mono. Linear's `cv01` and `ss03`
font features are intentionally enabled at the body level for character clarity
in dense data (`f7f8f8` vs `f7f8f0` distinguishable, `0` vs `O` distinguishable).

- **Headlines (display-xl/lg/md):** Inter Semibold (590), extreme negative tracking
  (-0.042em to -0.0375em). Reserve for page-level hero titles. This is the
  "minified-engineering" aesthetic borrowed from Linear and Vercel — text that
  feels compressed like production code. Use `display-lg` (56px) for Gallery
  and `display-md` (40px) for Finished page.
- **Headlines (h1–h3):** Inter Semibold (590), tight tracking (-0.022em).
  Reserve h1 for page-level titles; h2/h3 for section headers within a page.
- **Subheads (h4–h6):** Inter Medium (510), normal tracking. Used for section
  titles within a page (e.g. "📈 Attribute trends" inside the side panel).
- **Body (body-lg / body-md / body-sm):** Inter Regular (400). Use `body-md`
  (14px) for the dominant UI body; `body-lg` (16px) only for marketing-style
  text in the gallery; `body-sm` (13px) for compact lists (entity attributes).
- **Caption / micro:** Inter Regular at 12px, or Medium at 11px with
  `wide` letter-spacing for uppercase labels (decision-mode badges: LLM / RULE
  / RAND).
- **Code (code-md / code-sm):** JetBrains Mono. Used for *anything* with stable
  identity: entity IDs (`company_a`), run IDs, tick numbers, hex values,
  attribute values displayed as exact numbers, JSONL previews. Never put a
  hex code in sans-serif.

## Layout

- **Max content width:** 1440px (`layout-max-width`). Centered on the canvas.
- **Topbar height:** 56px. Fixed at the top, semi-transparent
  (`bg-header` with `backdrop-filter`).
- **Control bar height:** 64px (run-time, mockup §4.4.1). Sticky below the topbar.
- **Side panel width:** 280px (`layout-sidebar-width`) for sidebars and side
  data panels.
- **Breakpoints:**
  - `tablet`: ≥1024px
  - `desktop`: ≥1280px
  - `wide`: ≥1536px
  - Phone (<1024px) is **not yet supported** — Polisim is a desktop-first
    demonstration tool in v0.2.
- **Spacing scale:** 4px-grid base. The dominant unit is `sm` (8px) — every
  inter-element gap not specified otherwise should default to 8px. Card-to-card
  gap is `xl` (24px). Block-to-block (e.g. metric grid → narrative report) is
  `2xl` (32px). Major section dividers (e.g. narrative report → side panel) is
  `3xl` (48px).
- **Grid strategies:**
  - Gallery: 1 col (mobile fallback) / 2 col (≥tablet) / 3 col (≥desktop).
  - Entity card layout: 1 / 2 / 3 col same scale.
  - Side panel during run: 22rem fixed-width column on `xl:grid-cols-[1fr_22rem]`,
    collapsible.

## Elevation & Depth

Depth is conveyed primarily through **tonal layering, 1px borders, and inner
highlight rings**, not heavy shadows. Linear's actual elevation pattern is
borrowed:

- **Canvas (level 0):** `bg-canvas` (#08090a). Flat, no shadow, no border.
- **Surface (level 1):** `bg-surface` (#1c1c1f) + `border-subtle` 1px +
  `inner-highlight` (inset 0 1px 0 0 rgba(255,255,255,0.04)). The top-edge
  white highlight gives dark cards a subtle "pixel-rendered" feel — this is
  Linear's signature depth cue on dark surfaces.
- **Elevated surface (level 2):** `bg-surface` + `inner-highlight-strong` +
  `shadow-sm`. Used for hovered cards, dropdowns, popovers.
- **Modal (level 3):** `bg-surface` + `shadow-lg` (4px blur, 12px y-offset)
  on top of `bg-overlay` (rgba(0,0,0,0.85)) full-screen scrim.
- **Toast / tooltip (level 4):** `bg-surface` + `shadow-xl` (12px blur,
  32px y-offset). z-index `--z-toast` = 1200, `--z-tooltip` = 1300.

**Never** use shadows to compensate for low contrast — if a surface is hard to
read, the fix is to adjust `bg-` token, not pile on shadow blur.

## Shapes

The shape language is **moderately rounded**, never sharp, never very-rounded:

- **`rounded-xs` (2px):** Tags, chips, micro pills (decision-mode labels,
  scenario type badges).
- **`rounded-sm` (4px):** Buttons, code blocks, inputs.
- **`rounded-md` (6px):** Primary cards (Scenario card content area), primary
  buttons (`[▶ Start]`).
- **`rounded-lg` (8px):** Medium cards (Entity card, MetricsCard panels).
- **`rounded-xl` (12px):** Large containers (Modal, side-panel section
  containers, gallery scenario card outer).
- **`rounded-full` (9999px):** Pill buttons (status badges, tab pills in
  the FinishedSidePanel header).
- **`rounded-circle` (50%):** Avatars (none in v0.2 yet) and status dots.

Mixing `rounded-sm` (sharp) and `rounded-full` (pill) in the same view is
**explicitly allowed** — pill is reserved for badges, sharp for actions, and
they read as different element classes. Mixing `rounded-xs` and `rounded-xl`
on adjacent siblings (e.g. tag inside a card) is also fine — the size
hierarchy makes scale obvious.

## Motion

Polisim uses **subtle, purposeful motion** — never decorative, always
functional. The motion system is defined in `tokens.css` and bridged to
Tailwind via `transitionDuration` and `transitionTimingFunction`.

### Duration Scale

| Token | Value | Use |
| --- | --- | --- |
| `instant` | 50ms | Instant feedback (checkbox toggle, copy-to-clipboard) |
| `fast` | 150ms | Hover transitions, button press feedback, focus ring appearance |
| `normal` | 250ms | Card hover lift, panel expand/collapse, modal open/close |
| `slow` | 500ms | Page-level transitions, large content reveal |
| `slower` | 1000ms | Background animations (marquee, ambient glow) |

### Easing Curves

| Token | Curve | Use |
| --- | --- | --- |
| `ease-out` | `cubic-bezier(0.16, 1, 0.3, 1)` | **Default for all UI transitions.** Linear-style deceleration — fast start, gentle settle. |
| `ease-in` | `cubic-bezier(0.4, 0, 1, 1)` | Elements entering the screen (modals, drawers). |
| `ease-in-out` | `cubic-bezier(0.65, 0, 0.35, 1)` | Symmetric transitions (accordion expand/collapse). |
| `bounce` | `cubic-bezier(0.175, 0.885, 0.32, 1.275)` | Overshoot for celebratory moments (simulation complete checkmark). Rare. |

### Micro-Interaction Patterns

- **Button hover:** `hover:-translate-y-px` (1px lift) + `active:translate-y-0`
  (return). Duration: `fast` (150ms). Creates physical "press" feel.
- **Primary CTA hover:** `hover:scale-[1.015]` + `active:scale-[0.985]`.
  Subtle scale feedback — never exceeds 2% to avoid layout shift.
- **Card hover:** `hover:-translate-y-1` (4px lift) + inner-highlight
  transition to `inner-highlight-strong`. Duration: `normal` (250ms).
- **Status pulse:** `animate-pulse` on running (green dot) and paused
  (yellow dot) status indicators. Signals "alive" without distracting.
- **Focus ring:** `focus-visible:shadow-focus` — instant (`instant` 50ms)
  appearance, no animation. Focus must be immediate for accessibility.
- **Backdrop blur:** TopBar and ControlBar use `backdrop-blur-md` (12px)
  for frosted-glass depth. The blur is static (no animation) — it's a
  spatial cue, not a temporal one.

### Principles

- **Motion is earned.** Every animation must answer "what changed?" — state
  transition (idle→hover), spatial relationship (card lifted above canvas),
  or temporal status (running→paused pulse).
- **Respect `prefers-reduced-motion`.** All animations must be wrapped in
  `@media (prefers-reduced-motion: no-preference)` or use Tailwind's
  `motion-safe:` prefix. (Not yet enforced in v0.2 — deferred to v0.3
  accessibility pass.)
- **No animation on critical path.** Focus rings appear instantly (0ms
  transition on `shadow-focus`). Error states render immediately — never
  fade in an error message.
- **Duration hierarchy matches spatial distance.** Small elements (buttons)
  use `fast`; medium elements (cards) use `normal`; large elements (pages)
  use `slow`. This creates a natural physics feel.

## Components

The component tokens above are the canonical specs. A handful of important
notes on usage:

- **Single primary action per screen.** Only one `button-primary` instance
  should be visible at any moment — typically the action that advances the
  user's main flow (`[▶ Start]` in PreRun, `[Apply Intervention]` in the
  drawer, `[🔄 Rerun]` in Finished). Secondary actions use `button-secondary`.
- **Entity card states.** `entity-card` is the resting state. `entity-card-active`
  is reserved for "this entity is currently being intervened on" — never use it
  to mean "selected" outside of intervention flow.
- **Modal scrim opacity.** The 0.85 opacity on `bg-overlay` is intentional —
  high enough to dim background content but low enough that the canvas color
  bleeds through, anchoring the user spatially.
- **Status badges.** All four badges use `rounded-full` and `typography.micro`
  for consistency. `badge-paused` uses dark text on yellow because yellow is
  the only color where `fg-primary` (#f7f8f8) fails contrast.
- **Toast.** Uses `bg-surface` (not a bright accent fill) so toasts don't
  visually compete with the run-time control bar. Status is conveyed by an
  inline icon, not by toast background.

## Do's and Don'ts

- **Do** use `ease-out` (`cubic-bezier(0.16, 1, 0.3, 1)`) as the default
  transition timing function for all UI interactions. This is the Linear-style
  deceleration curve — fast start, gentle settle.
- **Do** apply `shadow-inner-highlight` to every card and button on
  `bg-surface`. The 1px top-edge white glow is the signature depth cue.
- **Do** use `backdrop-blur-md` on sticky bars (TopBar, ControlBar) for
  frosted-glass depth against scrolling content.
- **Don't** animate focus rings — they must appear instantly (`duration-instant`
  50ms or no transition) for accessibility compliance.
- **Don't** use `hover:scale` > 2% on interactive elements — larger values
  cause layout shift and feel cartoonish in a precision engineering tool.
- **Do** reserve `accent` (#7170ff) for the single most important action on
  the current screen. The `polisim-tick-active` highlight uses the same color
  intentionally — there is only one "current tick" at any moment.
- **Don't** mix `polisim-paused` (yellow) and `status-warning` (also yellow)
  in the same view. They are visually identical; choose based on semantics
  (paused-state UI vs. validation warning toast) and use only one.
- **Do** maintain WCAG AA contrast — 4.5:1 for body, 3:1 for large text.
  The token pairs `fg-primary` on `bg-canvas` (15.9:1) and `fg-secondary` on
  `bg-surface` (10.2:1) are pre-verified.
- **Don't** use `fg-muted` (#62666d) on `bg-canvas` — only on `bg-surface`
  or lighter. Contrast on canvas drops below 4.5:1.
- **Do** monospace any quantitative or identifier text: tick numbers,
  run IDs, entity IDs, hex values, JSONL previews. Use `typography.code-md`
  or `code-sm`.
- **Don't** italicize anything in the UI. Linear doesn't, and the variable
  font slant is not enabled in this stack.
- **Do** use the 3-step color scale on relation graph edges (positive /
  warning / negative) **and** show the numeric trust value as a label.
  Color alone is inaccessible to users with color vision deficiency.
- **Don't** apply `shadow-lg` or larger to a card sitting on `bg-canvas` —
  shadow-on-canvas reads as a visual error in dark UI. Use border-1px
  instead, or move the card to `bg-surface-hover` to express elevation
  through tonal contrast.
- **Do** keep `polisim-breakpoint` and `polisim-intervention` orange visually
  distinct from `accent` purple. Both signal "user attention required" but
  via different channels (system-triggered vs user-triggered).
- **Don't** introduce new domain colors without naming them under the
  `polisim-*` namespace. Generic Tailwind colors (e.g. `bg-blue-500`) are
  prohibited in business components — only token references.
- **Do** prefer 1px solid borders over shadows for delineation in
  data-dense regions (entity cards, tab content, side-panel sections).
  Linear does this consistently; it scales better than nested shadows.
- **Don't** use `bg-input` (`rgba(255,255,255,0.03)`) outside of form
  controls. The 3% white tint is calibrated for input-on-surface; on
  `bg-canvas` it disappears.
- **Do** use `rounded-full` (pill) for all primary accent CTAs. Secondary
  actions keep `rounded-md`. This is the Framer vocabulary: pill = primary,
  squared = secondary.
- **Do** apply `hover:shadow-glow-accent` on primary CTAs — the accent
  radial glow is the signature hover feedback (Framer spotlight style).
- **Don't** use `shadow-glow-accent` on secondary/ghost buttons — glow is
  exclusively for the single primary action per screen.
- **Do** use the `--gradient-hero-glow` radial gradient as a subtle
  atmospheric backdrop on hero sections (Gallery page). Keep it restrained —
  one per page maximum (Framer's "gradient spotlight cards are scarce by
  design" rule).
- **Do** enable Inter OpenType features (`calt`, `kern`, `liga`, `cv01`,
  `cv05`, `cv11`, `ss03`) via `--font-features`. The `ss03` alternate `g`
  and `cv11` dotted `0` are brand-voice details for a simulation data tool.

## Session 45: Visual Upgrade Changelog (Raycast + Framer Hybrid)

Changes applied to elevate visual premium feel:

1. **Font features enhanced** — `--font-features` now includes `calt`,
   `kern`, `liga`, `cv01`, `cv05`, `cv11`, `ss03` (was `cv01`, `ss03`).
   Branded Inter glyphs for simulation data readability.
2. **Surface ladder deepened** — `--color-bg-primary` darkened from
   `#08090a` to `#050506`; `--color-bg-panel` from `#0f1011` to `#0c0d0e`.
   Greater delta between canvas and card surfaces.
3. **Hero glow** — `--gradient-hero-glow` radial gradient token added;
   applied to Gallery page header as atmospheric accent.
4. **Primary CTA → pill** — All `bg-accent` buttons changed from
   `rounded-md` to `rounded-full`. Framer pill vocabulary.
5. **Ambient glow** — `--shadow-glow-accent` / `--shadow-glow-accent-strong`
   tokens added; applied as `hover:shadow-glow-accent` on primary CTAs.
6. **Inner highlight strengthened** — `--inner-highlight-strong` bumped to
   `rgba(255,255,255,0.12)` for more visible card edge on deeper canvas.
