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

export const CATEGORY_PILL: Record<'failure' | 'latency' | 'quality' | 'logic', string> = {
  failure: 'bg-red-500/12 text-[#f87171] border border-red-500/35',
  latency: 'bg-amber-500/10 text-[#fbbf24] border border-amber-500/35',
  quality: 'bg-violet-500/10 text-[#a78bfa] border border-violet-500/35',
  logic:   'bg-blue-500/10 text-[#60a5fa] border border-blue-500/35',
}
