# TraceIQ UI Redesign — Design Spec
**Date:** 2026-05-17
**Status:** Approved, ready for implementation

---

## Goal

Full UI overhaul of the TraceIQ dashboard. Both visual polish and UX patterns. Dark theme only. Stack: Tailwind CSS + shadcn/ui (open source, MIT licensed). All existing functionality preserved — this is a pure frontend change.

---

## Stack

| Layer | Before | After |
|---|---|---|
| Styling | Inline `style={{}}` objects | Tailwind CSS utility classes |
| Components | None (raw HTML elements) | shadcn/ui (copied into `src/components/ui/`) |
| Icons | Emoji (🔴 🟡 💡 ⚙) | Lucide React SVG icons |
| Theme | Dark only (hardcoded hex) | Dark only, tokens extracted to `src/lib/tokens.ts` |

---

## Layout

Two-column flex layout filling 100% of the viewport (`height: 100vh`, no padding wrapper).

```
┌─────────────────────┬────────────────────────────────────┐
│  Sidebar (300px)    │  Main panel (flex: 1)              │
│  fixed width        │  scrollable content                │
└─────────────────────┴────────────────────────────────────┘
```

Both panels use `overflow: hidden` at the shell level; inner scroll is on `.trace-list` and `.main-content` only.

---

## Sidebar

### App Header
- TraceIQ logo icon (gradient blue→indigo, 24px rounded square) + wordmark + `beta` badge
- Gear icon (Lucide `Settings`) on the right → opens Settings modal

### Project Selector
- Rounded card showing project name + Phoenix env label
- Chevron-down icon (Lucide `ChevronDown`) → future: project switcher dropdown
- Gradient dot on the left

### Project Stats — 2×2 Grid
Four cells in a `grid-cols-2` layout, each showing:
```
● Failing     2
● Degraded    2
● Healthy     1
● Total       5
```
- Glowing colored dot (red/amber/green/indigo) on the left
- Large bold number on the right
- Each cell: `background: #0c1220`, rounded, bordered

### Search Bar
- Full-width input with Lucide `Search` icon on the left
- `⌘K` shortcut hint on the right (muted, decorative only — no keyboard shortcut wired in this phase)
- Placeholder: "Search traces…"

### Trace List
Each trace item is a clickable row with:
- **Left**: colored glowing status dot (7px)
- **Center**:
  - Trace name (bold, truncated with ellipsis)
  - Meta row: `⏱ 48.2s  ⬡ 172 spans  ⚡ 1.94M tok`
    - Clock icon (Lucide `Clock`) + latency value
    - Layers icon (Lucide `Layers`) + span count
    - Zap icon (Lucide `Zap`) + token count — **red when unusually high**, indigo otherwise
- **Right**:
  - Status pill: `Failing` / `Degraded` / `Healthy` (colored rounded pill with border)
  - Relative timestamp: "2m ago"

Selected state: `background: #0f172a`, `border-color: #1e3a5f`

---

## Main Panel

### Header
- Trace name (16px bold)
- Chip row: trace ID (truncated) · `Large Trace · Tier 2` (indigo) · span count · latency · token count (red if high)
- `Re-analyze` button (outline style, Lucide `RotateCcw` icon)

### Tabs
- `Diagnostics [3]` — count badge (red) in the tab
- `Debug Chat`
- Active tab: blue bottom border + blue text

### Diagnostics Tab Content

#### Root Cause Card
- Red-tinted card with left-side gradient
- Eyebrow: `● ROOT CAUSE IDENTIFIED` (uppercase, red, 10px)
- Title: one-sentence summary (14px bold, light red)
- Body: full Claude explanation with `<code>` snippets (amber monospace)

#### Diagnostics Section
- Section header: `DIAGNOSTICS` label + `3 issues found` count (right-aligned)
- One card per issue:
  ```
  [icon]  [Failure pill]  Title text   span-ref-chip
          Description text (muted, 13px)
          ┌─ RECOMMENDED FIX ────────────────────┐
          │  Fix text (blue, 13px)               │
          └──────────────────────────────────────┘
  ```
  - **Icon** (standalone, left): 40px rounded square
    - `⊗` circle-X (Lucide `XCircle`) — red — for Failure
    - `△` triangle-warning (Lucide `AlertTriangle`) — amber — for Latency/Warning
    - `ℹ` circle-info (Lucide `Info`) — blue — for Info
  - **Category pill** (first in title row, with border):
    - `Failure` — red bg + red border
    - `Latency` — amber bg + amber border
    - `Quality` — purple bg + purple border
  - **Title** — bold, white, 14px
  - **Span ref chip** — monospace, muted, small pill
  - **Recommended Fix block** — blue-tinted, bordered, with `ℹ` icon label

### Debug Chat Tab Content
- Message list (scrollable):
  - User messages: right-aligned, blue background bubble
  - Assistant messages: left-aligned, dark card background
  - Streaming cursor: blinking `▋` while response loads
- Input bar (fixed bottom):
  - Text input, placeholder: "Ask anything about this trace…"
  - Send button (Lucide `Send` icon)
  - Enter to send, Shift+Enter for newline

---

## Settings Modal
- Semi-transparent backdrop (`rgba(0,0,0,0.6)`)
- Centered card (440px wide, rounded-lg)
- Fields: Phoenix URL + Project name
- `Cancel` (ghost) + `Connect` (primary blue) buttons
- Connection status message after save

---

## UX Patterns Added

| Pattern | Implementation |
|---|---|
| Loading skeleton | Show animated pulse bars while analysis is fetching |
| Error toast | `sonner` toast library for API errors (non-blocking) |
| Empty state | Centered illustration + text when no trace selected |
| Relative timestamps | "2m ago" using `date-fns` `formatDistanceToNow` |
| Token color coding | Red when token count > 2× project median (mirrors AnomalyDetector `token_spike` rule), indigo otherwise |
| Tier badge | `Large Trace · Tier 2` chip when span count ≥ 50 |

---

## Implementation Scope

All changes are in `frontend/src/`. Backend unchanged. API unchanged. Output schema unchanged.

### Files to create
- `src/lib/tokens.ts` — design tokens (colors, spacing)
- `src/components/ui/` — shadcn/ui components (Button, Badge, Card, Input, Dialog, Separator)
- `tailwind.config.js` — Tailwind config with custom dark theme tokens

### Files to rewrite
- `src/App.tsx` — main layout shell
- `src/components/TraceList.tsx` — sidebar
- `src/components/IssuePanel.tsx` — diagnostics tab
- `src/components/Chat.tsx` — debug chat tab
- `src/components/Settings.tsx` — settings modal
- `src/index.css` — global reset + Tailwind base

### Files to delete
- `src/App.css` — unused legacy Vite template styles

---

## Out of Scope
- Responsive / mobile layout
- Light theme
- Backend changes
- New API endpoints
- Chat history persistence per trace
