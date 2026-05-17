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
                    <Zap size={10} className="opacity-80" />
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
