# TraceIQ UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all inline `style={{}}` objects with Tailwind CSS, add Lucide icons, polish the sidebar and diagnostics panel per the approved design spec.

**Architecture:** Pure frontend change — backend, API, and `api/client.ts` types are untouched. Each component is rewritten in place, using Tailwind utility classes and a small set of shared helpers (`cn`, token constants). No new routes, no schema changes.

**Tech Stack:** React 19, TypeScript, Vite 8, Tailwind CSS v4 (`@tailwindcss/vite`), Lucide React, date-fns, sonner (toasts), clsx, tailwind-merge.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `frontend/package.json` | Modify | Add new deps |
| `frontend/vite.config.ts` | Modify | Add Tailwind Vite plugin |
| `frontend/src/index.css` | Rewrite | Tailwind v4 import + CSS vars |
| `frontend/src/lib/utils.ts` | **Create** | `cn()` helper |
| `frontend/src/lib/tokens.ts` | **Create** | Named color/status constants |
| `frontend/src/App.tsx` | Rewrite | Layout shell, state, tabs |
| `frontend/src/components/TraceList.tsx` | Rewrite | Sidebar: header, stats grid, trace items |
| `frontend/src/components/IssuePanel.tsx` | Rewrite | RCA card + diagnostic cards |
| `frontend/src/components/Chat.tsx` | Rewrite | Debug chat tab |
| `frontend/src/components/Settings.tsx` | Rewrite | Settings modal |
| `frontend/src/App.css` | **Delete** | Unused legacy styles |

---

## Task 1: Install dependencies and configure Tailwind

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`
- Rewrite: `frontend/src/index.css`

- [ ] **Step 1: Install dependencies**

```bash
cd frontend
npm install tailwindcss @tailwindcss/vite lucide-react date-fns sonner clsx tailwind-merge
```

Expected: `added N packages` with no errors.

- [ ] **Step 2: Update vite.config.ts to add Tailwind plugin**

Read the current `frontend/vite.config.ts` first, then add the tailwindcss import and plugin. The result should look like:

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
})
```

(Keep any existing `server.proxy` config — only add the import and `tailwindcss()` plugin.)

- [ ] **Step 3: Rewrite src/index.css**

```css
@import "tailwindcss";

@theme {
  --color-background:   #0a0f1e;
  --color-sidebar:      #080d1a;
  --color-surface:      #0c1220;
  --color-surface-2:    #0f172a;
  --color-border:       #1e293b;
  --color-border-2:     #334155;
  --color-text:         #f1f5f9;
  --color-text-muted:   #64748b;
  --color-text-subtle:  #334155;
  --color-accent:       #3b82f6;
  --color-accent-light: #60a5fa;
  --color-failing:      #f87171;
  --color-degraded:     #fbbf24;
  --color-healthy:      #4ade80;
  --color-tokens-high:  #f87171;
  --color-tokens-ok:    #818cf8;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html, body, #root {
  height: 100%;
  overflow: hidden;
  background: #0a0f1e;
  font-family: -apple-system, BlinkMacSystemFont, 'Inter', system-ui, sans-serif;
  color: #f1f5f9;
}
```

- [ ] **Step 4: Verify Tailwind is working**

```bash
cd frontend && npm run build 2>&1 | tail -5
```

Expected: build succeeds with no errors (ignore warnings about unused CSS).

- [ ] **Step 5: Commit**

```bash
cd frontend && cd ..
git add frontend/package.json frontend/vite.config.ts frontend/src/index.css frontend/package-lock.json
git commit -m "feat: install Tailwind v4, lucide-react, date-fns, sonner"
```

---

## Task 2: Create shared utilities

**Files:**
- Create: `frontend/src/lib/utils.ts`
- Create: `frontend/src/lib/tokens.ts`

- [ ] **Step 1: Create src/lib/utils.ts**

```ts
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

- [ ] **Step 2: Create src/lib/tokens.ts**

```ts
import type { TraceInfo } from '../api/client'

export type TraceStatus = 'failing' | 'degraded' | 'healthy'

export function traceStatus(t: TraceInfo): TraceStatus {
  if (t.has_errors) return 'failing'
  if (t.issue_count > 0) return 'degraded'
  return 'healthy'
}

export const STATUS_LABEL: Record<TraceStatus, string> = {
  failing: 'Failing',
  degraded: 'Degraded',
  healthy: 'Healthy',
}

export const STATUS_DOT: Record<TraceStatus, string> = {
  failing:  'bg-[#ef4444] shadow-[0_0_6px_rgba(239,68,68,0.5)]',
  degraded: 'bg-[#f59e0b] shadow-[0_0_6px_rgba(245,158,11,0.4)]',
  healthy:  'bg-[#22c55e] shadow-[0_0_6px_rgba(34,197,94,0.3)]',
}

export const STATUS_PILL: Record<TraceStatus, string> = {
  failing:  'bg-red-500/10 text-[#f87171] border border-red-500/20',
  degraded: 'bg-amber-500/10 text-[#fbbf24] border border-amber-500/20',
  healthy:  'bg-green-500/10 text-[#4ade80] border border-green-500/20',
}

/** Token count is "high" when it exceeds 2× the median of all visible traces */
export function isHighTokenCount(tokenCount: number, allTraces: TraceInfo[]): boolean {
  if (allTraces.length === 0) return false
  const sorted = [...allTraces].map(t => t.token_count_total).sort((a, b) => a - b)
  const median = sorted[Math.floor(sorted.length / 2)]
  return median > 0 && tokenCount > 2 * median
}

/** Format token count: 1940000 → "1.94M tok", 84000 → "84K tok" */
export function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M tok`
  if (n >= 1_000)     return `${Math.round(n / 1_000)}K tok`
  return `${n} tok`
}

export const CATEGORY_PILL: Record<string, string> = {
  failure: 'bg-red-500/12 text-[#f87171] border border-red-500/35',
  latency: 'bg-amber-500/10 text-[#fbbf24] border border-amber-500/35',
  quality: 'bg-violet-500/10 text-[#a78bfa] border border-violet-500/35',
  logic:   'bg-blue-500/10 text-[#60a5fa] border border-blue-500/35',
}
```

- [ ] **Step 3: Verify TypeScript**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/
git commit -m "feat: add cn() utility and trace token helpers"
```

---

## Task 3: Rewrite App.tsx

**Files:**
- Rewrite: `frontend/src/App.tsx`
- Delete: `frontend/src/App.css`

- [ ] **Step 1: Delete App.css**

```bash
rm frontend/src/App.css
```

- [ ] **Step 2: Rewrite src/App.tsx**

```tsx
import { useEffect, useState } from 'react'
import { RotateCcw } from 'lucide-react'
import { Toaster, toast } from 'sonner'
import { api } from './api/client'
import type { TraceInfo, Analysis } from './api/client'
import { TraceList } from './components/TraceList'
import { IssuePanel } from './components/IssuePanel'
import { Chat } from './components/Chat'
import { Settings } from './components/Settings'
import { cn } from './lib/utils'
import { traceStatus, STATUS_LABEL, formatTokens, isHighTokenCount } from './lib/tokens'

export default function App() {
  const [traces, setTraces]         = useState<TraceInfo[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [analysis, setAnalysis]     = useState<Analysis | null>(null)
  const [analyzing, setAnalyzing]   = useState(false)
  const [activeTab, setActiveTab]   = useState<'diagnostics' | 'chat'>('diagnostics')
  const [showSettings, setShowSettings] = useState(false)

  const selectedTrace = traces.find(t => t.trace_id === selectedId) ?? null

  useEffect(() => {
    api.listTraces().then(setTraces).catch(() => toast.error('Failed to load traces'))
  }, [])

  const selectTrace = async (id: string) => {
    setSelectedId(id)
    setAnalysis(null)
    setActiveTab('diagnostics')
    setAnalyzing(true)
    try {
      const result = await api.getAnalysis(id)
      setAnalysis(result)
    } catch {
      toast.error('Analysis failed')
    } finally {
      setAnalyzing(false)
    }
  }

  const reanalyze = async () => {
    if (!selectedId) return
    setAnalysis(null)
    setAnalyzing(true)
    try {
      const result = await api.getAnalysis(selectedId, true)
      setAnalysis(result)
    } catch {
      toast.error('Re-analysis failed')
    } finally {
      setAnalyzing(false)
    }
  }

  const issueCount = analysis?.issues.length ?? 0
  const tokenHigh  = selectedTrace ? isHighTokenCount(selectedTrace.token_count_total, traces) : false

  return (
    <div className="flex h-screen overflow-hidden bg-[#0a0f1e] text-[#f1f5f9]">
      <Toaster theme="dark" position="bottom-right" />

      <TraceList
        traces={traces}
        selectedId={selectedId}
        onSelect={selectTrace}
        onSettings={() => setShowSettings(true)}
      />

      {showSettings && (
        <Settings
          onClose={() => setShowSettings(false)}
          onSaved={() => api.listTraces().then(setTraces).catch(() => toast.error('Failed to refresh traces'))}
        />
      )}

      <div className="flex flex-1 flex-col min-w-0 overflow-hidden">
        {!selectedId ? (
          <div className="flex flex-1 items-center justify-center text-[#475569] text-sm">
            Select a trace to analyze
          </div>
        ) : (
          <>
            {/* Main header */}
            <div className="flex items-center justify-between px-7 py-4 border-b border-[#1e293b] flex-shrink-0">
              <div>
                <div className="text-base font-bold tracking-tight text-[#f1f5f9]">
                  {selectedTrace?.name ?? selectedId.slice(0, 16)}
                </div>
                <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                  <span className="text-[10px] font-medium bg-[#0f172a] border border-[#1e293b] rounded px-2 py-0.5 text-[#64748b]">
                    {selectedId.slice(0, 12)}…
                  </span>
                  {selectedTrace && selectedTrace.span_count >= 50 && (
                    <span className="text-[10px] font-medium bg-indigo-500/6 border border-indigo-500/25 rounded px-2 py-0.5 text-[#818cf8]">
                      Large Trace · Tier 2
                    </span>
                  )}
                  {selectedTrace && (
                    <>
                      <span className="text-[10px] font-medium bg-[#0f172a] border border-[#1e293b] rounded px-2 py-0.5 text-[#64748b]">
                        {selectedTrace.span_count} spans
                      </span>
                      <span className="text-[10px] font-medium bg-[#0f172a] border border-[#1e293b] rounded px-2 py-0.5 text-[#64748b]">
                        {(selectedTrace.total_latency_ms / 1000).toFixed(1)}s
                      </span>
                      <span className={cn(
                        'text-[10px] font-medium rounded px-2 py-0.5',
                        tokenHigh
                          ? 'bg-red-500/6 border border-red-500/20 text-[#f87171]'
                          : 'bg-[#0f172a] border border-[#1e293b] text-[#64748b]'
                      )}>
                        {formatTokens(selectedTrace.token_count_total)}
                      </span>
                    </>
                  )}
                </div>
              </div>
              <button
                onClick={reanalyze}
                disabled={analyzing}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#94a3b8] bg-transparent border border-[#1e293b] rounded-md hover:border-[#334155] hover:text-[#e2e8f0] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <RotateCcw size={12} />
                Re-analyze
              </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-[#1e293b] px-7 flex-shrink-0">
              {([
                { id: 'diagnostics' as const, label: 'Diagnostics', badge: !analyzing && issueCount > 0 ? issueCount : null },
                { id: 'chat' as const, label: 'Debug Chat', badge: null },
              ]).map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'flex items-center gap-1.5 px-4 py-3.5 text-[13px] font-medium border-b-2 -mb-px transition-colors',
                    activeTab === tab.id
                      ? 'text-[#60a5fa] border-[#3b82f6]'
                      : 'text-[#64748b] border-transparent hover:text-[#94a3b8]'
                  )}
                >
                  {tab.label}
                  {tab.badge != null && (
                    <span className="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded bg-red-500/18 text-[#f87171] text-[10px] font-bold">
                      {tab.badge}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <div className="flex-1 overflow-y-auto">
              {analyzing && (
                <div className="p-8 space-y-3">
                  <div className="h-4 bg-[#1e293b] rounded animate-pulse w-1/3" />
                  <div className="h-20 bg-[#1e293b] rounded animate-pulse" />
                  <div className="h-24 bg-[#1e293b] rounded animate-pulse" />
                  <div className="h-24 bg-[#1e293b] rounded animate-pulse" />
                </div>
              )}
              {!analyzing && analysis && activeTab === 'diagnostics' && (
                <IssuePanel
                  issues={analysis.issues}
                  rootCause={analysis.root_cause}
                  summary={analysis.summary}
                />
              )}
              {!analyzing && selectedId && activeTab === 'chat' && (
                <Chat traceId={selectedId} />
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Verify build**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx
git rm frontend/src/App.css
git commit -m "feat: rewrite App.tsx with Tailwind, skeleton loader, error toasts"
```

---

## Task 4: Rewrite TraceList.tsx

**Files:**
- Rewrite: `frontend/src/components/TraceList.tsx`

- [ ] **Step 1: Rewrite TraceList.tsx**

```tsx
import { Settings as SettingsIcon, Clock, Layers, Zap } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import type { TraceInfo } from '../api/client'
import { cn } from '../lib/utils'
import {
  traceStatus, STATUS_LABEL, STATUS_DOT, STATUS_PILL,
  formatTokens, isHighTokenCount,
} from '../lib/tokens'

export function TraceList({
  traces,
  selectedId,
  onSelect,
  onSettings,
}: {
  traces: TraceInfo[]
  selectedId: string | null
  onSelect: (id: string) => void
  onSettings: () => void
}) {
  const failing  = traces.filter(t => traceStatus(t) === 'failing').length
  const degraded = traces.filter(t => traceStatus(t) === 'degraded').length
  const healthy  = traces.filter(t => traceStatus(t) === 'healthy').length

  return (
    <div className="w-[300px] flex-shrink-0 bg-[#080d1a] border-r border-[#1e293b] flex flex-col h-screen overflow-hidden">

      {/* App header */}
      <div className="flex items-center justify-between px-[18px] py-4 border-b border-[#1e293b] flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-[5px] bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center text-[11px] font-extrabold text-white flex-shrink-0">
            T
          </div>
          <span className="text-[15px] font-bold tracking-tight text-[#f1f5f9]">TraceIQ</span>
          <span className="text-[9px] font-semibold bg-[#1e3a5f] text-[#60a5fa] px-1.5 py-0.5 rounded">beta</span>
        </div>
        <button
          onClick={onSettings}
          className="w-[30px] h-[30px] rounded-lg border border-[#1e293b] flex items-center justify-center text-[#64748b] hover:text-[#94a3b8] hover:bg-[#0f172a] transition-colors"
        >
          <SettingsIcon size={14} />
        </button>
      </div>

      {/* Project selector */}
      <div className="mx-3.5 mt-3 bg-[#0f172a] border border-[#1e293b] rounded-lg px-3.5 py-2.5 flex items-center justify-between cursor-pointer hover:border-[#334155] transition-colors flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-2.5 h-2.5 rounded-full bg-gradient-to-br from-blue-500 to-indigo-500 flex-shrink-0" />
          <div>
            <div className="text-[13px] font-semibold text-[#e2e8f0]">default</div>
            <div className="text-[11px] text-[#475569] mt-0.5">Phoenix · default</div>
          </div>
        </div>
        <span className="text-[11px] text-[#475569]">⌄</span>
      </div>

      {/* 2×2 stats grid */}
      <div className="mx-3.5 mt-2.5 grid grid-cols-2 gap-1.5 flex-shrink-0">
        {([
          { label: 'Failing',  value: failing,  dot: 'bg-[#ef4444] shadow-[0_0_5px_rgba(239,68,68,0.45)]', val: 'text-[#f87171]' },
          { label: 'Degraded', value: degraded, dot: 'bg-[#f59e0b] shadow-[0_0_5px_rgba(245,158,11,0.35)]', val: 'text-[#fbbf24]' },
          { label: 'Healthy',  value: healthy,  dot: 'bg-[#22c55e] shadow-[0_0_5px_rgba(34,197,94,0.35)]',  val: 'text-[#4ade80]' },
          { label: 'Total',    value: traces.length, dot: 'bg-indigo-500', val: 'text-[#818cf8]' },
        ]).map(s => (
          <div key={s.label} className="bg-[#0c1220] border border-[#1e293b] rounded-lg px-3 py-2.5 flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <div className={cn('w-1.5 h-1.5 rounded-full flex-shrink-0', s.dot)} />
              <span className="text-[11px] font-medium text-[#64748b]">{s.label}</span>
            </div>
            <span className={cn('text-[15px] font-extrabold', s.val)}>{s.value}</span>
          </div>
        ))}
      </div>

      {/* Search */}
      <div className="mx-3.5 mt-2.5 mb-1.5 bg-[#0f172a] border border-[#1e293b] rounded-lg px-3 py-2 flex items-center gap-2 text-[#475569] text-[12px] flex-shrink-0">
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" className="opacity-40 flex-shrink-0"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <span>Search traces…</span>
        <span className="ml-auto text-[10px] opacity-30 font-mono">⌘K</span>
      </div>

      {/* Section label */}
      <div className="px-4 pt-2 pb-1 text-[10px] font-semibold text-[#334155] uppercase tracking-widest flex items-center justify-between flex-shrink-0">
        <span>Traces</span>
        <span className="normal-case font-medium text-[#1e3a5f] tracking-normal">{traces.length} total</span>
      </div>

      {/* Trace list */}
      <div className="flex-1 overflow-y-auto px-2.5 pb-3 space-y-0.5">
        {traces.map(t => {
          const status  = traceStatus(t)
          const tokHigh = isHighTokenCount(t.token_count_total, traces)
          const ago     = t.start_time
            ? formatDistanceToNow(new Date(t.start_time), { addSuffix: true })
            : ''

          return (
            <div
              key={t.trace_id}
              onClick={() => onSelect(t.trace_id)}
              className={cn(
                'px-2.5 py-3 rounded-lg cursor-pointer flex items-start gap-2.5 border transition-colors',
                selectedId === t.trace_id
                  ? 'bg-[#0f172a] border-[#1e3a5f]'
                  : 'border-transparent hover:bg-[#0d1425]'
              )}
            >
              {/* Status dot */}
              <div className={cn('w-[7px] h-[7px] rounded-full mt-[5px] flex-shrink-0', STATUS_DOT[status])} />

              {/* Name + meta */}
              <div className="flex-1 min-w-0">
                <div className="text-[12px] font-semibold text-[#e2e8f0] truncate mb-1.5">
                  {t.name || t.trace_id.slice(0, 12)}
                </div>
                <div className="flex items-center gap-2.5">
                  <span className="flex items-center gap-1 text-[11px] text-[#64748b]">
                    <Clock size={10} className="opacity-70" />
                    {(t.total_latency_ms / 1000).toFixed(1)}s
                  </span>
                  <span className="flex items-center gap-1 text-[11px] text-[#64748b]">
                    <Layers size={10} className="opacity-70" />
                    {t.span_count} spans
                  </span>
                  <span className={cn('flex items-center gap-1 text-[11px] font-semibold', tokHigh ? 'text-[#f87171]' : 'text-[#818cf8]')}>
                    <Zap size={10} className="opacity-80" style={{ stroke: tokHigh ? '#f87171' : '#818cf8' }} />
                    {formatTokens(t.token_count_total)}
                  </span>
                </div>
              </div>

              {/* Status pill + time */}
              <div className="flex flex-col items-end gap-1 flex-shrink-0">
                <span className={cn('text-[10px] font-semibold px-2 py-0.5 rounded-full', STATUS_PILL[status])}>
                  {STATUS_LABEL[status]}
                </span>
                {ago && <span className="text-[10px] text-[#334155]">{ago}</span>}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors.

- [ ] **Step 3: Smoke test in browser**

```bash
cd frontend && npm run dev
```

Open http://localhost:5173. Sidebar should render with logo, stats grid, trace items with status pills and token counts.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/TraceList.tsx
git commit -m "feat: rewrite TraceList with Tailwind, stats grid, token colors, timestamps"
```

---

## Task 5: Rewrite IssuePanel.tsx

**Files:**
- Rewrite: `frontend/src/components/IssuePanel.tsx`

- [ ] **Step 1: Rewrite IssuePanel.tsx**

```tsx
import { XCircle, AlertTriangle, Info } from 'lucide-react'
import type { Issue } from '../api/client'
import { cn } from '../lib/utils'
import { CATEGORY_PILL } from '../lib/tokens'

function SevIcon({ severity }: { severity: Issue['severity'] }) {
  const base = 'w-10 h-10 rounded-[9px] flex-shrink-0 flex items-center justify-center'
  if (severity === 'error') return (
    <div className={cn(base, 'bg-red-500/13 border border-red-500/25')}>
      <XCircle size={17} className="text-[#f87171]" />
    </div>
  )
  if (severity === 'warning') return (
    <div className={cn(base, 'bg-amber-500/11 border border-amber-500/25')}>
      <AlertTriangle size={17} className="text-[#fbbf24]" />
    </div>
  )
  return (
    <div className={cn(base, 'bg-blue-500/10 border border-blue-500/22')}>
      <Info size={17} className="text-[#60a5fa]" />
    </div>
  )
}

export function IssuePanel({ issues, rootCause, summary }: {
  issues: Issue[]
  rootCause: string
  summary: string
}) {
  if (issues.length === 0) {
    return (
      <div className="p-8">
        <div className="text-[#4ade80] font-semibold mb-2">✓ No issues found</div>
        <p className="text-[#94a3b8] text-sm">{summary}</p>
      </div>
    )
  }

  return (
    <div className="p-7 space-y-6">

      {/* Root cause card */}
      <div className="bg-gradient-to-br from-red-500/6 to-red-500/2 border border-red-500/20 rounded-[10px] p-5">
        <div className="flex items-center gap-1.5 mb-2">
          <div className="w-[5px] h-[5px] rounded-full bg-[#ef4444] flex-shrink-0" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-[#f87171]">Root Cause Identified</span>
        </div>
        <div className="text-[14px] font-semibold text-[#fca5a5] mb-2">{rootCause}</div>
        <div className="text-[13px] text-[#94a3b8] leading-relaxed">{summary}</div>
      </div>

      {/* Diagnostics section */}
      <div>
        <div className="flex items-center justify-between mb-3.5">
          <span className="text-[11px] font-bold text-[#475569] uppercase tracking-widest">Diagnostics</span>
          <span className="text-[11px] text-[#334155]">{issues.length} issue{issues.length !== 1 ? 's' : ''} found</span>
        </div>

        <div className="space-y-3">
          {issues.map(issue => (
            <div key={issue.id} className="bg-[#0c1220] border border-[#1e293b] rounded-[11px] p-[18px] flex gap-4 items-start hover:border-[#334155] transition-colors">
              <SevIcon severity={issue.severity} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-2">
                  <span className={cn('text-[11px] font-bold px-2.5 py-0.5 rounded-full flex-shrink-0', CATEGORY_PILL[issue.category])}>
                    {issue.category.charAt(0).toUpperCase() + issue.category.slice(1)}
                  </span>
                  <span className="text-[14px] font-semibold text-[#f1f5f9]">{issue.explanation.split('.')[0]}</span>
                  <span className="text-[11px] text-[#475569] font-mono bg-[#0f172a] border border-[#1e293b] rounded px-2 py-0.5 whitespace-nowrap">
                    {issue.span_name}
                  </span>
                </div>
                <div className="text-[13px] text-[#64748b] leading-[1.65]">{issue.explanation}</div>
                {issue.suggestion && (
                  <div className="mt-3 p-3 bg-blue-500/4 border border-blue-500/14 rounded-lg">
                    <div className="flex items-center gap-1.5 mb-1.5 text-[10px] font-extrabold uppercase tracking-widest text-[#3b82f6]">
                      <Info size={9} />
                      Recommended Fix
                    </div>
                    <div className="text-[13px] text-[#7dd3fc] leading-[1.65]">{issue.suggestion}</div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/IssuePanel.tsx
git commit -m "feat: rewrite IssuePanel with Tailwind, SVG icons, RCA card, Recommended Fix blocks"
```

---

## Task 6: Rewrite Chat.tsx

**Files:**
- Rewrite: `frontend/src/components/Chat.tsx`

- [ ] **Step 1: Rewrite Chat.tsx**

```tsx
import { useState, useRef, useEffect } from 'react'
import { Send } from 'lucide-react'
import { api } from '../api/client'
import { cn } from '../lib/utils'

export function Chat({ traceId }: { traceId: string }) {
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([])
  const [input, setInput]       = useState('')
  const [loading, setLoading]   = useState(false)
  const bottomRef               = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async () => {
    if (!input.trim() || loading) return
    const msg = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: msg }])
    setLoading(true)

    let reply = ''
    setMessages(prev => [...prev, { role: 'assistant', content: '' }])

    await api.chat(traceId, msg, chunk => {
      reply += chunk
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = { role: 'assistant', content: reply }
        return updated
      })
    })
    setLoading(false)
  }

  return (
    <div className="flex flex-col h-full">
      {/* Message list */}
      <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-3">
        {messages.length === 0 && (
          <div className="text-[#475569] text-[13px] mt-4">
            Ask anything about this trace. E.g. "Why did the agent loop?" or "How can I fix the latency?"
          </div>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={cn(
              'max-w-[85%] text-[13px] leading-relaxed rounded-xl px-4 py-2.5 whitespace-pre-wrap text-[#f1f5f9]',
              m.role === 'user'
                ? 'self-end bg-[#1e40af]'
                : 'self-start bg-[#1e293b]'
            )}
          >
            {m.content || (loading && m.role === 'assistant' ? (
              <span className="animate-pulse">▋</span>
            ) : '')}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="px-5 py-4 border-t border-[#1e293b] flex gap-2.5 flex-shrink-0">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), send())}
          placeholder="Ask about this trace…"
          className="flex-1 bg-[#0f172a] border border-[#334155] text-[#f1f5f9] rounded-lg px-3.5 py-2 text-[13px] placeholder-[#475569] outline-none focus:border-[#3b82f6] transition-colors"
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          className="flex items-center justify-center w-9 h-9 bg-[#3b82f6] text-white rounded-lg disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#2563eb] transition-colors flex-shrink-0"
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Chat.tsx
git commit -m "feat: rewrite Chat with Tailwind, Send icon, auto-scroll"
```

---

## Task 7: Rewrite Settings.tsx

**Files:**
- Rewrite: `frontend/src/components/Settings.tsx`

- [ ] **Step 1: Rewrite Settings.tsx**

```tsx
import { useState, useEffect } from 'react'

interface PhoenixSettings {
  phoenix_url: string
  phoenix_project: string
}

export function Settings({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [settings, setSettings] = useState<PhoenixSettings>({ phoenix_url: '', phoenix_project: '' })
  const [saving, setSaving]     = useState(false)
  const [status, setStatus]     = useState('')

  useEffect(() => {
    fetch('/api/settings').then(r => r.json()).then(setSettings).catch(() => {})
  }, [])

  const save = async () => {
    setSaving(true)
    setStatus('')
    try {
      await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      })
      setStatus('Connected! Refreshing traces…')
      setTimeout(() => { onSaved(); onClose() }, 1000)
    } catch {
      setStatus('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-[#0f172a] border border-[#334155] rounded-xl p-6 w-[440px] shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="text-[16px] font-semibold text-[#f1f5f9] mb-5">Phoenix Connection</div>

        <div className="mb-4">
          <label className="block text-[11px] font-semibold text-[#94a3b8] uppercase tracking-wider mb-2">
            Phoenix URL
          </label>
          <input
            value={settings.phoenix_url}
            onChange={e => setSettings(s => ({ ...s, phoenix_url: e.target.value }))}
            placeholder="http://localhost:6006"
            className="w-full bg-[#1e293b] border border-[#334155] text-[#f1f5f9] rounded-lg px-3.5 py-2.5 text-[14px] placeholder-[#475569] outline-none focus:border-[#3b82f6] transition-colors"
          />
        </div>

        <div className="mb-6">
          <label className="block text-[11px] font-semibold text-[#94a3b8] uppercase tracking-wider mb-2">
            Project
          </label>
          <input
            value={settings.phoenix_project}
            onChange={e => setSettings(s => ({ ...s, phoenix_project: e.target.value }))}
            placeholder="default"
            className="w-full bg-[#1e293b] border border-[#334155] text-[#f1f5f9] rounded-lg px-3.5 py-2.5 text-[14px] placeholder-[#475569] outline-none focus:border-[#3b82f6] transition-colors"
          />
        </div>

        {status && (
          <div className="text-[#4ade80] text-[13px] mb-4">{status}</div>
        )}

        <div className="flex gap-2 justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-[14px] font-medium text-[#94a3b8] bg-transparent border border-[#334155] rounded-lg hover:text-[#e2e8f0] hover:border-[#475569] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={save}
            disabled={saving}
            className="px-4 py-2 text-[14px] font-medium text-white bg-[#3b82f6] rounded-lg hover:bg-[#2563eb] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {saving ? 'Saving…' : 'Connect'}
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Full build check**

```bash
cd frontend && npm run build 2>&1 | tail -10
```

Expected: build succeeds, dist output shown.

- [ ] **Step 3: Final smoke test**

```bash
cd frontend && npm run dev
```

Open http://localhost:5173. Verify:
- Sidebar shows logo, stats grid, trace items with pills and token colors
- Clicking a trace shows skeleton, then RCA card + diagnostic cards
- Issues show `[Failure pill] Title  span-ref` layout
- Chat tab shows input + send button
- Settings gear opens modal

- [ ] **Step 4: Final commit**

```bash
git add frontend/src/components/Settings.tsx frontend/src/lib/
git commit -m "feat: rewrite Settings with Tailwind; UI redesign complete"
```
