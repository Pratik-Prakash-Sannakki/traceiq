import { useEffect, useState } from 'react'
import { RotateCcw } from 'lucide-react'
import { Toaster, toast } from 'sonner'
import { api } from './api/client'
import type { TraceInfo, Analysis } from './api/client'
import { TraceList } from './components/TraceList'
import { IssuePanel } from './components/IssuePanel'
import { Chat } from './components/Chat'
import { Settings } from './components/Settings'
import { formatTokens, isHighTokenCount } from './lib/tokens'

export default function App() {
  const [traces, setTraces]             = useState<TraceInfo[]>([])
  const [selectedId, setSelectedId]     = useState<string | null>(null)
  const [analysis, setAnalysis]         = useState<Analysis | null>(null)
  const [analyzing, setAnalyzing]       = useState(false)
  const [activeTab, setActiveTab]       = useState<'diagnostics' | 'chat'>('diagnostics')
  const [showSettings, setShowSettings] = useState(false)
  const [project, setProject]           = useState({ name: 'default', url: 'Phoenix' })

  const selected = traces.find(t => t.trace_id === selectedId) ?? null

  const refreshAll = async () => {
    await Promise.all([
      api.listTraces().then(setTraces).catch(() => toast.error('Failed to load traces')),
      fetch('/api/settings').then(r => r.json()).then(s => setProject({
        name: s.phoenix_project || 'default',
        url:  s.phoenix_url     || 'Phoenix',
      })).catch(() => {}),
    ])
  }

  useEffect(() => { refreshAll() }, [])

  const selectTrace = async (id: string) => {
    setSelectedId(id); setAnalysis(null); setActiveTab('diagnostics'); setAnalyzing(true)
    try   { setAnalysis(await api.getAnalysis(id)) }
    catch { toast.error('Analysis failed') }
    finally { setAnalyzing(false) }
  }

  const reanalyze = async () => {
    if (!selectedId) return
    setAnalysis(null); setAnalyzing(true)
    try   { setAnalysis(await api.getAnalysis(selectedId, true)) }
    catch { toast.error('Re-analysis failed') }
    finally { setAnalyzing(false) }
  }

  const issueCount = analysis?.issues.length ?? 0
  const tokenHigh  = selected ? isHighTokenCount(selected.token_count_total, traces) : false

  // Project-level aggregate stats
  const sortedMs = [...traces].map(t => t.total_latency_ms).sort((a, b) => a - b)
  const p50Ms    = sortedMs.length ? sortedMs[Math.floor((sortedMs.length - 1) * 0.50)] : 0
  const p99Ms    = sortedMs.length ? sortedMs[Math.floor((sortedMs.length - 1) * 0.99)] : 0
  const fmtSec   = (ms: number) => ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--page)', color: 'var(--t1)', fontFamily: 'var(--font)' }}>
      <Toaster theme="dark" position="bottom-right" />

      <TraceList traces={traces} selectedId={selectedId} onSelect={selectTrace} onSettings={() => setShowSettings(true)} project={project} />

      {showSettings && (
        <Settings onClose={() => setShowSettings(false)} onSaved={refreshAll} />
      )}

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden' }}>

        {!selectedId ? (
          /* Empty state */
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ width: 52, height: 52, borderRadius: 14, background: 'var(--card)', border: '1px solid var(--line-hi)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
                <svg width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--t3)' }}>
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
                </svg>
              </div>
              <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--t1)', marginBottom: 6 }}>Select a trace</p>
              <p style={{ fontSize: 12, color: 'var(--t2)' }}>Choose a trace from the panel to analyze</p>
            </div>
          </div>
        ) : (
          <>
            {/* Header */}
            <div style={{ padding: '20px 32px', borderBottom: '1px solid var(--line)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
              <div>
                <h1 style={{ fontSize: 16, fontWeight: 700, color: 'var(--t1)', marginBottom: 8, letterSpacing: '-0.2px' }}>
                  {selected?.name ?? selectedId.slice(0, 16)}
                </h1>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
                  <Chip>{selectedId.slice(0, 12)}…</Chip>
                  {selected && selected.span_count >= 50 && <Chip accent>Large Trace · Tier 2</Chip>}
                  {selected && <>
                    <Chip>{selected.span_count} spans</Chip>
                    <Chip>{(selected.total_latency_ms / 1000).toFixed(1)}s</Chip>
                    <Chip warn={tokenHigh}>{formatTokens(selected.token_count_total)}</Chip>
                  </>}
                  <Chip dim>Cost —</Chip>
                  <Chip dim>P50 {traces.length ? fmtSec(p50Ms) : '—'}</Chip>
                  <Chip dim>P99 {traces.length ? fmtSec(p99Ms) : '—'}</Chip>
                </div>
              </div>
              <button
                onClick={reanalyze}
                disabled={analyzing}
                style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 14px', borderRadius: 8, border: '1px solid var(--line-hi)', background: 'transparent', color: 'var(--t2)', fontSize: 12, fontWeight: 500, cursor: 'pointer', opacity: analyzing ? 0.4 : 1, fontFamily: 'var(--font)' }}
              >
                <RotateCcw size={13} /> Re-analyze
              </button>
            </div>

            {/* Tabs */}
            <div style={{ display: 'flex', gap: 4, padding: '0 32px', borderBottom: '1px solid var(--line)', flexShrink: 0 }}>
              {([
                { id: 'diagnostics' as const, label: 'Diagnostics', badge: !analyzing && issueCount > 0 ? issueCount : null },
                { id: 'chat'        as const, label: 'Debug Chat',  badge: null },
              ]).map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '12px 16px',
                    fontSize: 13, fontWeight: 500,
                    background: 'transparent', border: 'none', cursor: 'pointer',
                    borderBottom: `2px solid ${activeTab === tab.id ? 'var(--accent)' : 'transparent'}`,
                    marginBottom: -1,
                    color: activeTab === tab.id ? '#60a5fa' : 'var(--t2)',
                    fontFamily: 'var(--font)',
                    transition: 'color 0.15s',
                  }}
                >
                  {tab.label}
                  {tab.badge != null && (
                    <span style={{ fontSize: 10, fontWeight: 700, background: 'rgba(239,68,68,0.15)', color: '#f87171', padding: '1px 6px', borderRadius: 4 }}>
                      {tab.badge}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {/* Content */}
            <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
              {analyzing && (
                <div style={{ padding: '40px 48px', maxWidth: 880 }}>
                  {[180, 320, 320, 320].map((w, i) => (
                    <div key={i} style={{ height: 16, borderRadius: 6, background: 'var(--card)', width: w, marginBottom: 16, animation: 'pulse 1.5s ease-in-out infinite' }} />
                  ))}
                </div>
              )}
              {!analyzing && analysis && activeTab === 'diagnostics' && (
                <div style={{ flex: 1, overflowY: 'auto' }}>
                  <IssuePanel issues={analysis.issues} rootCause={analysis.root_cause} summary={analysis.summary} />
                </div>
              )}
              {!analyzing && selectedId && activeTab === 'chat' && (
                <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
                  <Chat traceId={selectedId} />
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function Chip({ children, accent, warn, dim }: { children: React.ReactNode; accent?: boolean; warn?: boolean; dim?: boolean }) {
  return (
    <span style={{
      fontSize: 11, fontWeight: 500,
      padding: '3px 8px', borderRadius: 5,
      background: warn ? 'rgba(239,68,68,0.1)' : accent ? 'rgba(99,102,241,0.12)' : 'var(--card)',
      border: `1px solid ${warn ? 'rgba(239,68,68,0.3)' : accent ? 'rgba(99,102,241,0.35)' : 'var(--line)'}`,
      color: warn ? '#f87171' : accent ? '#818cf8' : dim ? 'var(--t3)' : 'var(--t2)',
      fontFamily: dim ? 'var(--mono)' : 'var(--font)',
    }}>
      {children}
    </span>
  )
}
