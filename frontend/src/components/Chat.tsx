import { useState, useRef, useEffect } from 'react'
import { Send } from 'lucide-react'
import { api } from '../api/client'
import { cn } from '../lib/utils'

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
    <div className="flex flex-col h-full">
      {/* Message list */}
      <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-3">
        {messages.length === 0 && (
          <div className="text-[#475569] text-[13px] mt-4">
            Ask anything about this trace. E.g. "Why did the agent loop?" or "How can I fix the latency?"
          </div>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={cn(
              'max-w-[85%] text-[13px] leading-relaxed rounded-xl px-4 py-2.5 whitespace-pre-wrap text-[#f1f5f9]',
              m.role === 'user'
                ? 'self-end bg-[#1e40af]'
                : 'self-start bg-[#1e293b]'
            )}
          >
            {m.content || (loading && m.role === 'assistant' ? (
              <span className="animate-pulse">▋</span>
            ) : '')}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <div className="px-5 py-4 border-t border-[#1e293b] flex gap-2.5 flex-shrink-0">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), send())}
          placeholder="Ask about this trace…"
          className="flex-1 bg-[#0f172a] border border-[#334155] text-[#f1f5f9] rounded-lg px-3.5 py-2 text-[13px] placeholder-[#475569] outline-none focus:border-[#3b82f6] transition-colors"
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          className="flex items-center justify-center w-9 h-9 bg-[#3b82f6] text-white rounded-lg disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#2563eb] transition-colors flex-shrink-0"
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  )
}
