import { Settings as SettingsIcon } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useState } from 'react'
import type { TraceInfo } from '../api/client'
import { traceStatus, STATUS_LABEL, STATUS_DOT, STATUS_PILL, formatTokens, isHighTokenCount } from '../lib/tokens'
import { cn } from '../lib/utils'

const STAT_ROWS = [
  { key: 'failing'  as const, label: 'Failing',      color: '#ef4444', text: '#f87171' },
  { key: 'degraded' as const, label: 'Degraded',     color: '#f59e0b', text: '#fbbf24' },
  { key: 'healthy'  as const, label: 'Healthy',      color: '#22c55e', text: '#4ade80' },
  { key: 'total'    as const, label: 'Total Traces', color: '#6366f1', text: '#818cf8' },
]

export function TraceList({ traces, selectedId, onSelect, onSettings, project }: {
  traces:     TraceInfo[]
  selectedId: string | null
  onSelect:   (id: string) => void
  onSettings: () => void
  project:    { name: string; url: string }
}) {
  const [query, setQuery]               = useState('')
  const [statusFilter, setStatusFilter] = useState<'failing' | 'degraded' | 'healthy' | null>(null)

  const counts = {
    failing:  traces.filter(t => traceStatus(t) === 'failing').length,
    degraded: traces.filter(t => traceStatus(t) === 'degraded').length,
    healthy:  traces.filter(t => traceStatus(t) === 'healthy').length,
    total:    traces.length,
  }

  const toggleFilter = (key: string) => {
    if (key === 'total') { setStatusFilter(null); return }
    const s = key as 'failing' | 'degraded' | 'healthy'
    setStatusFilter(prev => prev === s ? null : s)
  }

  const filtered = traces
    .filter(t => !statusFilter || traceStatus(t) === statusFilter)
    .filter(t => !query.trim() ||
      t.trace_id.toLowerCase().includes(query.toLowerCase()) ||
      (t.name ?? '').toLowerCase().includes(query.toLowerCase())
    )

  return (
    <aside style={{ width: 272, background: 'var(--sidebar)', borderRight: '1px solid var(--line)', display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden', flexShrink: 0 }}>

      {/* ── Logo row ── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '18px 20px', borderBottom: '1px solid var(--line)', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 28, height: 28, borderRadius: 8, background: 'linear-gradient(135deg,#3b82f6,#6366f1)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 12, color: '#fff', flexShrink: 0 }}>T</div>
          <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--t1)', letterSpacing: '-0.3px' }}>TraceIQ</span>
          <span style={{ fontSize: 9, fontWeight: 700, background: '#0d2040', color: '#60a5fa', padding: '2px 6px', borderRadius: 4 }}>beta</span>
        </div>
        <button onClick={onSettings} style={{ width: 32, height: 32, borderRadius: 8, border: '1px solid var(--line)', background: 'transparent', color: 'var(--t3)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'var(--card)'; (e.currentTarget as HTMLElement).style.color = 'var(--t2)' }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; (e.currentTarget as HTMLElement).style.color = 'var(--t3)' }}>
          <SettingsIcon size={14} />
        </button>
      </div>

      {/* ── Project display ── */}
      <div style={{ margin: '16px 16px 0', background: 'var(--card)', border: '1px solid var(--line-hi)', borderRadius: 12, padding: '12px 14px', display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#22c55e', flexShrink: 0 }} />
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--t1)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{project.name}</div>
          <div style={{ fontSize: 11, color: 'var(--t3)', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{project.url}</div>
        </div>
      </div>

      {/* ── Stats 2×2 grid (filterable) ── */}
      <div style={{ margin: '16px 16px 0', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, flexShrink: 0 }}>
        {STAT_ROWS.map(s => {
          const isActive  = s.key === 'total' ? statusFilter === null : statusFilter === s.key
          const isDimmed  = s.key !== 'total' && statusFilter !== null && statusFilter !== s.key
          return (
            <div
              key={s.key}
              onClick={() => toggleFilter(s.key)}
              style={{
                background: isActive ? 'var(--card-hi)' : 'var(--card)',
                border: `1px solid ${isActive ? s.color : 'var(--line-hi)'}`,
                borderRadius: 10, padding: '10px 12px',
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                cursor: 'pointer', transition: 'all 0.15s',
                opacity: isDimmed ? 0.45 : 1,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{ width: 6, height: 6, borderRadius: '50%', background: s.color, flexShrink: 0 }} />
                <span style={{ fontSize: 11, color: isActive ? 'var(--t1)' : 'var(--t2)', fontWeight: isActive ? 600 : 400 }}>{s.label}</span>
              </div>
              <span style={{ fontSize: 16, fontWeight: 700, color: s.text }}>{counts[s.key]}</span>
            </div>
          )
        })}
      </div>

      {/* ── Search (functional) ── */}
      <div style={{ margin: '12px 16px 0', background: 'var(--card)', border: '1px solid var(--line)', borderRadius: 10, padding: '0 14px', display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--t3)', flexShrink: 0 }}>
          <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
        </svg>
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search traces…"
          style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', fontSize: 12, color: 'var(--t1)', padding: '9px 0', fontFamily: 'var(--font)' }}
        />
        {query ? (
          <button onClick={() => setQuery('')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--t3)', fontSize: 14, lineHeight: 1, padding: 0 }}>×</button>
        ) : (
          <span style={{ fontSize: 10, color: 'var(--t3)', fontFamily: 'var(--mono)', opacity: 0.6 }}>⌘K</span>
        )}
      </div>

      {/* ── Section label ── */}
      <div style={{ padding: '16px 20px 8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
        <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--t3)' }}>Traces</span>
        <span style={{ fontSize: 10, color: 'var(--t3)' }}>{filtered.length} {query ? 'results' : 'total'}</span>
      </div>

      {/* ── Trace list ── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '0 10px 16px' }}>
        {filtered.length === 0 && (
          <div style={{ padding: '24px 10px', textAlign: 'center', color: 'var(--t3)', fontSize: 12 }}>
            No traces match "{query}"
          </div>
        )}
        {filtered.map(t => {
          const status   = traceStatus(t)
          const tokHigh  = isHighTokenCount(t.token_count_total, traces)
          const ago      = t.start_time ? formatDistanceToNow(new Date(t.start_time), { addSuffix: true }) : ''
          const selected = selectedId === t.trace_id

          return (
            <div
              key={t.trace_id}
              onClick={() => onSelect(t.trace_id)}
              style={{
                padding: '12px 10px',
                borderRadius: 10,
                cursor: 'pointer',
                border: `1px solid ${selected ? 'var(--line-hi)' : 'transparent'}`,
                background: selected ? 'var(--card)' : 'transparent',
                marginBottom: 2,
                transition: 'background 0.15s, border-color 0.15s',
              }}
              onMouseEnter={e => { if (!selected) { (e.currentTarget as HTMLElement).style.background = 'var(--card)' } }}
              onMouseLeave={e => { if (!selected) { (e.currentTarget as HTMLElement).style.background = 'transparent' } }}
            >
              {/* Row 1: name + status pill */}
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8, marginBottom: 4 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                  <div className={cn('rounded-full flex-shrink-0', STATUS_DOT[status])} style={{ width: 7, height: 7, marginTop: 2 }} />
                  <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--t1)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {t.name || t.trace_id}
                  </span>
                </div>
                <span className={cn('rounded-full flex-shrink-0', STATUS_PILL[status])} style={{ fontSize: 10, fontWeight: 600, padding: '2px 8px', whiteSpace: 'nowrap' }}>
                  {STATUS_LABEL[status]}
                </span>
              </div>
              {/* Row 2: full trace ID */}
              <div style={{ paddingLeft: 15, marginBottom: 6 }}>
                <span style={{ fontSize: 10, fontFamily: 'var(--mono)', color: 'var(--t3)', wordBreak: 'break-all' }}>
                  {t.trace_id}
                </span>
              </div>
              {/* Row 3: meta */}
              <div style={{ paddingLeft: 15, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 11, color: tokHigh ? '#f87171' : 'var(--t3)' }}>
                  {(t.total_latency_ms / 1000).toFixed(1)}s · {t.span_count} spans · {formatTokens(t.token_count_total)}
                </span>
                {ago && <span style={{ fontSize: 10, color: 'var(--t3)', flexShrink: 0 }}>{ago}</span>}
              </div>
            </div>
          )
        })}
      </div>
    </aside>
  )
}
