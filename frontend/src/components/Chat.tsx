import { useState } from 'react'
import { api } from '../api/client'

export function Chat({ traceId }: { traceId: string }) {
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

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
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ fontSize: 12, color: '#94a3b8', padding: '8px 16px', borderBottom: '1px solid #1e293b' }}>
        Chat with Claude about this trace
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
        {messages.length === 0 && (
          <div style={{ color: '#475569', fontSize: 13 }}>
            Ask anything about this trace. E.g. "Why did the agent loop?" or "How can I fix the latency?"
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} style={{
            alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
            background: m.role === 'user' ? '#1e40af' : '#1e293b',
            color: '#f1f5f9', borderRadius: 8, padding: '8px 12px',
            maxWidth: '85%', fontSize: 13, lineHeight: 1.5,
            whiteSpace: 'pre-wrap',
          }}>
            {m.content || (loading && m.role === 'assistant' ? '▋' : '')}
          </div>
        ))}
      </div>
      <div style={{ padding: 12, borderTop: '1px solid #1e293b', display: 'flex', gap: 8 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder="Ask about this trace..."
          style={{
            flex: 1, background: '#0f172a', border: '1px solid #334155',
            color: '#f1f5f9', borderRadius: 6, padding: '8px 12px', fontSize: 13,
          }}
        />
        <button
          onClick={send}
          disabled={loading}
          style={{
            background: '#3b82f6', color: 'white', border: 'none',
            borderRadius: 6, padding: '8px 16px', cursor: loading ? 'not-allowed' : 'pointer',
          }}
        >
          {loading ? '...' : 'Send'}
        </button>
      </div>
    </div>
  )
}
