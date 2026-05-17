import { useEffect, useState } from 'react'
import { api } from './api/client'
import type { TraceInfo, Analysis } from './api/client'
import { TraceList } from './components/TraceList'
import { IssuePanel } from './components/IssuePanel'
import { Chat } from './components/Chat'

export default function App() {
  const [traces, setTraces] = useState<TraceInfo[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [activeTab, setActiveTab] = useState<'issues' | 'chat'>('issues')

  useEffect(() => {
    api.listTraces().then(setTraces).catch(console.error)
  }, [])

  const selectTrace = async (id: string) => {
    setSelectedId(id)
    setAnalysis(null)
    setAnalyzing(true)
    try {
      const result = await api.getAnalysis(id)
      setAnalysis(result)
    } catch (e) {
      console.error(e)
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
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <div style={{
      display: 'flex', height: '100vh', background: '#0a0f1e',
      color: '#f1f5f9', fontFamily: 'system-ui, sans-serif',
    }}>
      <TraceList traces={traces} selectedId={selectedId} onSelect={selectTrace} />

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {!selectedId ? (
          <div style={{
            flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#475569'
          }}>
            Select a trace to analyze
          </div>
        ) : (
          <>
            <div style={{
              padding: '12px 16px', borderBottom: '1px solid #1e293b',
              display: 'flex', alignItems: 'center', gap: 12,
            }}>
              <span style={{ fontWeight: 600 }}>{selectedId.slice(0, 16)}...</span>
              {(['issues', 'chat'] as const).map(tab => (
                <button key={tab} onClick={() => setActiveTab(tab)} style={{
                  background: activeTab === tab ? '#1e40af' : 'transparent',
                  color: activeTab === tab ? 'white' : '#94a3b8',
                  border: '1px solid #334155', borderRadius: 6,
                  padding: '4px 12px', cursor: 'pointer', fontSize: 13,
                }}>
                  {tab === 'issues' ? 'Issues' : 'Chat'}
                </button>
              ))}
              <button onClick={reanalyze} style={{
                marginLeft: 'auto', background: 'transparent',
                color: '#60a5fa', border: '1px solid #334155',
                borderRadius: 6, padding: '4px 12px', cursor: 'pointer', fontSize: 13,
              }}>
                Re-analyze
              </button>
            </div>

            <div style={{ flex: 1, overflowY: 'auto' }}>
              {analyzing && (
                <div style={{ padding: 24, color: '#60a5fa' }}>
                  Analyzing trace with Claude...
                </div>
              )}
              {!analyzing && analysis && activeTab === 'issues' && (
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
