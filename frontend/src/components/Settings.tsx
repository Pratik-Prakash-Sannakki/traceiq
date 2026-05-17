import { useState, useEffect } from 'react'

interface PhoenixSettings {
  phoenix_url: string
  phoenix_project: string
}

export function Settings({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [settings, setSettings] = useState<PhoenixSettings>({ phoenix_url: '', phoenix_project: '' })
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState('')

  useEffect(() => {
    fetch('/api/settings').then(r => r.json()).then(setSettings)
  }, [])

  const save = async () => {
    setSaving(true)
    setStatus('')
    try {
      await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      })
      setStatus('Saved! Refreshing traces...')
      setTimeout(() => { onSaved(); onClose() }, 1000)
    } catch {
      setStatus('Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
    }} onClick={onClose}>
      <div style={{
        background: '#0f172a', border: '1px solid #334155', borderRadius: 12,
        padding: 24, width: 440, boxShadow: '0 25px 50px rgba(0,0,0,0.5)',
      }} onClick={e => e.stopPropagation()}>
        <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 20 }}>
          Phoenix Connection
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', fontSize: 12, color: '#94a3b8', marginBottom: 6, textTransform: 'uppercase' }}>
            Phoenix URL
          </label>
          <input
            value={settings.phoenix_url}
            onChange={e => setSettings(s => ({ ...s, phoenix_url: e.target.value }))}
            placeholder="http://localhost:6006"
            style={{
              width: '100%', background: '#1e293b', border: '1px solid #334155',
              color: '#f1f5f9', borderRadius: 6, padding: '10px 12px', fontSize: 14,
              boxSizing: 'border-box',
            }}
          />
        </div>

        <div style={{ marginBottom: 24 }}>
          <label style={{ display: 'block', fontSize: 12, color: '#94a3b8', marginBottom: 6, textTransform: 'uppercase' }}>
            Project
          </label>
          <input
            value={settings.phoenix_project}
            onChange={e => setSettings(s => ({ ...s, phoenix_project: e.target.value }))}
            placeholder="default"
            style={{
              width: '100%', background: '#1e293b', border: '1px solid #334155',
              color: '#f1f5f9', borderRadius: 6, padding: '10px 12px', fontSize: 14,
              boxSizing: 'border-box',
            }}
          />
        </div>

        {status && (
          <div style={{ color: '#22c55e', fontSize: 13, marginBottom: 12 }}>{status}</div>
        )}

        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button onClick={onClose} style={{
            background: 'transparent', color: '#94a3b8', border: '1px solid #334155',
            borderRadius: 6, padding: '8px 16px', cursor: 'pointer', fontSize: 14,
          }}>Cancel</button>
          <button onClick={save} disabled={saving} style={{
            background: '#3b82f6', color: 'white', border: 'none',
            borderRadius: 6, padding: '8px 16px', cursor: saving ? 'not-allowed' : 'pointer', fontSize: 14,
          }}>
            {saving ? 'Saving...' : 'Connect'}
          </button>
        </div>
      </div>
    </div>
  )
}
