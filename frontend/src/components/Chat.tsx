import { useState, useRef, useEffect } from 'react'
import { Send } from 'lucide-react'
import { toast } from 'sonner'
import { api } from '../api/client'

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
    try {
      await api.chat(traceId, msg, chunk => {
        reply += chunk
        setMessages(prev => {
          const next = [...prev]
          next[next.length - 1] = { role: 'assistant', content: reply }
          return next
        })
      })
    } catch {
      toast.error('Chat failed')
      setMessages(prev => prev.slice(0, -1))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '32px 40px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        {messages.length === 0 && (
          <div style={{ margin: 'auto', textAlign: 'center', paddingBottom: 80 }}>
            <div style={{ width: 48, height: 48, borderRadius: 12, background: 'var(--card)', border: '1px solid var(--line-hi)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--t3)' }}>
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
            </div>
            <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--t1)', marginBottom: 6 }}>Ask about this trace</p>
            <p style={{ fontSize: 12, color: 'var(--t2)', lineHeight: 1.6 }}>
              "Why did the agent loop?" · "How do I fix the latency?" · "What caused the token spike?"
            </p>
          </div>
        )}

        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              maxWidth: '80%',
              alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
              background: m.role === 'user' ? '#1d4ed8' : 'var(--card)',
              border: m.role === 'user' ? 'none' : '1px solid var(--line)',
              borderRadius: m.role === 'user' ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
              padding: '10px 16px',
              fontSize: 13,
              lineHeight: 1.7,
              color: 'var(--t1)',
              whiteSpace: 'pre-wrap',
            }}
          >
            {m.content || (loading && m.role === 'assistant'
              ? <span style={{ animation: 'pulse 1s infinite', opacity: 0.6 }}>▋</span>
              : null
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div style={{ padding: '16px 32px 20px', borderTop: '1px solid var(--line)', display: 'flex', gap: 10, alignItems: 'center', flexShrink: 0 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), send())}
          placeholder="Ask about this trace…"
          style={{
            flex: 1,
            background: 'var(--card)',
            border: '1px solid var(--line)',
            borderRadius: 10,
            padding: '11px 16px',
            fontSize: 13,
            color: 'var(--t1)',
            outline: 'none',
            fontFamily: 'var(--font)',
          }}
          onFocus={e => (e.target.style.borderColor = '#3b82f6')}
          onBlur={e => (e.target.style.borderColor = 'var(--line)')}
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          style={{
            width: 40, height: 40,
            borderRadius: 10,
            background: '#3b82f6',
            border: 'none',
            cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            opacity: loading || !input.trim() ? 0.4 : 1,
            flexShrink: 0,
            transition: 'opacity 0.15s',
          }}
        >
          <Send size={15} color="#fff" />
        </button>
      </div>
    </div>
  )
}
