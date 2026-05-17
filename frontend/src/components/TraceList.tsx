import type { TraceInfo } from '../api/client'

function Badge({ count, hasErrors }: { count: number; hasErrors: boolean }) {
  if (count === 0) return <span style={{ color: '#22c55e', fontSize: 12 }}>✓ Clean</span>
  return (
    <span style={{
      background: hasErrors ? '#ef4444' : '#f59e0b',
      color: 'white', borderRadius: 4, padding: '2px 6px', fontSize: 12
    }}>
      {count} issue{count !== 1 ? 's' : ''}
    </span>
  )
}

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
  return (
    <div style={{ width: 320, borderRight: '1px solid #333', overflowY: 'auto', height: '100vh' }}>
      <div style={{ padding: '16px', borderBottom: '1px solid #333', fontWeight: 600, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>Traces ({traces.length})</span>
        <button onClick={onSettings} title="Connection settings" style={{
          background: 'transparent', border: 'none', color: '#475569',
          cursor: 'pointer', fontSize: 18, padding: 0, lineHeight: 1,
        }}>⚙</button>
      </div>
      {traces.map(t => (
        <div
          key={t.trace_id}
          onClick={() => onSelect(t.trace_id)}
          style={{
            padding: '12px 16px',
            cursor: 'pointer',
            background: selectedId === t.trace_id ? '#1e293b' : 'transparent',
            borderBottom: '1px solid #1e293b',
          }}
        >
          <div style={{ fontWeight: 500, marginBottom: 4, fontSize: 14 }}>
            {t.name || t.trace_id.slice(0, 12)}
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: '#94a3b8', fontSize: 12 }}>
              {(t.total_latency_ms / 1000).toFixed(1)}s · {t.token_count_total} tok
            </span>
            <Badge count={t.issue_count} hasErrors={t.has_errors} />
          </div>
        </div>
      ))}
    </div>
  )
}
