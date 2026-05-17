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
import { traceStatus, formatTokens, isHighTokenCount } from './lib/tokens'

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
