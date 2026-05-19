import { useState, useEffect } from 'react'

type Provider = 'phoenix' | 'langsmith'

interface SettingsState {
  provider:            Provider
  phoenix_url:         string
  phoenix_project:     string
  langsmith_host:      string
  langsmith_api_key:   string
  langsmith_project:   string
}

const DEFAULTS: SettingsState = {
  provider:            'phoenix',
  phoenix_url:         '',
  phoenix_project:     '',
  langsmith_host:      'https://api.smith.langchain.com',
  langsmith_api_key:   '',
  langsmith_project:   'default',
}

export function Settings({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [s, setS]         = useState<SettingsState>(DEFAULTS)
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState('')

  useEffect(() => {
    fetch('/api/settings').then(r => r.json()).then(d => setS({ ...DEFAULTS, ...d })).catch(() => {})
  }, [])

  const set = (k: keyof SettingsState, v: string) => setS(prev => ({ ...prev, [k]: v }))

  const save = async () => {
    setSaving(true); setStatus('')
    try {
      await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(s),
      })
      // Test the connection with the new settings
      const test = await fetch('/api/test-connection', { method: 'POST' })
      const result = await test.json()
      if (!result.ok) {
        setStatus(`❌ ${result.error}`)
        setSaving(false)
        return
      }
      setStatus(`✓ Connected — ${result.count} trace${result.count !== 1 ? 's' : ''} found`)
      setTimeout(() => { onSaved(); onClose() }, 1200)
    } catch {
      setStatus('❌ Failed to connect')
    } finally {
      setSaving(false)
    }
  }

  const inputStyle: React.CSSProperties = {
    display: 'block', width: '100%',
    background: '#050e1c', border: '1px solid #1b3350',
    borderRadius: 8, padding: '10px 14px',
    fontSize: 13, color: '#f1f5f9', outline: 'none',
    fontFamily: 'var(--font)',
  }

  const labelStyle: React.CSSProperties = {
    display: 'block', fontSize: 11, fontWeight: 600,
    textTransform: 'uppercase', letterSpacing: '0.08em',
    color: '#64748b', marginBottom: 8,
  }

  return (
    <div
      onClick={onClose}
      style={{ position: 'fixed', inset: 0, zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(4px)' }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{ width: 460, background: '#0b1a2e', border: '1px solid #1b3350', borderRadius: 16, padding: 28, boxShadow: '0 24px 64px rgba(0,0,0,0.6)' }}
      >
        <p style={{ fontSize: 16, fontWeight: 700, color: '#f1f5f9', marginBottom: 20 }}>Connection Settings</p>

        {/* Provider toggle */}
        <div style={{ marginBottom: 24 }}>
          <p style={labelStyle}>Data Source</p>
          <div style={{ display: 'flex', gap: 8 }}>
            {([
              { id: 'phoenix',   label: '🔥 Phoenix'   },
              { id: 'langsmith', label: '🦜 LangSmith' },
            ] as { id: Provider; label: string }[]).map(p => (
              <button
                key={p.id}
                onClick={() => set('provider', p.id)}
                style={{
                  flex: 1, padding: '9px 0', borderRadius: 8, fontSize: 12, fontWeight: 600,
                  cursor: 'pointer', fontFamily: 'var(--font)', transition: 'all 0.15s',
                  background: s.provider === p.id ? '#3b82f6' : '#0d1f35',
                  border: `1px solid ${s.provider === p.id ? '#3b82f6' : '#1b3350'}`,
                  color: s.provider === p.id ? '#fff' : '#64748b',
                }}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Phoenix fields */}
        {s.provider === 'phoenix' && (
          <>
            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Phoenix URL</label>
              <input value={s.phoenix_url} onChange={e => set('phoenix_url', e.target.value)}
                placeholder="http://localhost:6006" style={inputStyle}
                onFocus={e => (e.target.style.borderColor = '#3b82f6')}
                onBlur={e => (e.target.style.borderColor = '#1b3350')} />
            </div>
            <div style={{ marginBottom: 24 }}>
              <label style={labelStyle}>Project</label>
              <input value={s.phoenix_project} onChange={e => set('phoenix_project', e.target.value)}
                placeholder="default" style={inputStyle}
                onFocus={e => (e.target.style.borderColor = '#3b82f6')}
                onBlur={e => (e.target.style.borderColor = '#1b3350')} />
            </div>
          </>
        )}

        {/* LangSmith fields */}
        {s.provider === 'langsmith' && (
          <>
            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>Host</label>
              <input value={s.langsmith_host} onChange={e => set('langsmith_host', e.target.value)}
                placeholder="https://api.smith.langchain.com" style={inputStyle}
                onFocus={e => (e.target.style.borderColor = '#3b82f6')}
                onBlur={e => (e.target.style.borderColor = '#1b3350')} />
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={labelStyle}>API Key</label>
              <input type="password" value={s.langsmith_api_key} onChange={e => set('langsmith_api_key', e.target.value)}
                placeholder="ls__..." style={inputStyle}
                onFocus={e => (e.target.style.borderColor = '#3b82f6')}
                onBlur={e => (e.target.style.borderColor = '#1b3350')} />
            </div>
            <div style={{ marginBottom: 24 }}>
              <label style={labelStyle}>Project</label>
              <input value={s.langsmith_project} onChange={e => set('langsmith_project', e.target.value)}
                placeholder="default" style={inputStyle}
                onFocus={e => (e.target.style.borderColor = '#3b82f6')}
                onBlur={e => (e.target.style.borderColor = '#1b3350')} />
            </div>
          </>
        )}

        {status && (
          <p style={{ fontSize: 12, color: status.startsWith('F') ? '#f87171' : '#4ade80', marginBottom: 16 }}>
            {status}
          </p>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 12 }}>
          <button onClick={onClose} style={{ fontSize: 13, color: '#64748b', background: 'none', border: 'none', cursor: 'pointer', padding: '8px 12px', fontFamily: 'var(--font)' }}>
            Cancel
          </button>
          <button onClick={save} disabled={saving}
            style={{ fontSize: 13, fontWeight: 600, color: '#fff', background: '#3b82f6', border: 'none', borderRadius: 8, padding: '9px 20px', cursor: 'pointer', opacity: saving ? 0.5 : 1, fontFamily: 'var(--font)' }}>
            {saving ? 'Connecting…' : 'Connect'}
          </button>
        </div>
      </div>
    </div>
  )
}
