export interface TraceInfo {
  trace_id: string
  name: string
  start_time: string
  total_latency_ms: number
  token_count_total: number
  span_count: number
  has_errors: boolean
  issue_count: number
}

export interface Issue {
  id: string
  category: 'failure' | 'latency' | 'quality' | 'logic'
  severity: 'error' | 'warning' | 'info'
  span_id: string
  span_name: string
  explanation: string
  suggestion: string
}

export interface Analysis {
  trace_id: string
  issues: Issue[]
  root_cause: string
  summary: string
  analyzed_at: string
}

export const api = {
  listTraces: async (): Promise<TraceInfo[]> => {
    const r = await fetch('/api/traces')
    if (!r.ok) throw new Error('Failed to fetch traces')
    return r.json()
  },

  getAnalysis: async (traceId: string, reanalyze = false): Promise<Analysis> => {
    const r = await fetch(`/api/traces/${traceId}/analysis${reanalyze ? '?reanalyze=true' : ''}`)
    if (!r.ok) throw new Error('Analysis failed')
    return r.json()
  },

  chat: async (traceId: string, message: string, onChunk: (c: string) => void) => {
    const r = await fetch(`/api/traces/${traceId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    })
    if (!r.ok || !r.body) throw new Error('Chat failed')
    const reader = r.body.getReader()
    const decoder = new TextDecoder()
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      onChunk(decoder.decode(value))
    }
  },
}
