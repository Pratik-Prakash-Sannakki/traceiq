import { useState, useEffect } from 'react'

interface PhoenixSettings {
  phoenix_url: string
  phoenix_project: string
}

export function Settings({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [settings, setSettings] = useState<PhoenixSettings>({ phoenix_url: '', phoenix_project: '' })
  const [saving, setSaving]     = useState(false)
  const [status, setStatus]     = useState('')

  useEffect(() => {
    fetch('/api/settings').then(r => r.json()).then(setSettings).catch(() => {})
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
      setStatus('Connected! Refreshing traces…')
      setTimeout(() => { onSaved(); onClose() }, 1000)
    } catch {
      setStatus('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 bg-black/60 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-[#0f172a] border border-[#334155] rounded-xl p-6 w-[440px] shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="text-[16px] font-semibold text-[#f1f5f9] mb-5">Phoenix Connection</div>

        <div className="mb-4">
          <label className="block text-[11px] font-semibold text-[#94a3b8] uppercase tracking-wider mb-2">
            Phoenix URL
          </label>
          <input
            value={settings.phoenix_url}
            onChange={e => setSettings(s => ({ ...s, phoenix_url: e.target.value }))}
            placeholder="http://localhost:6006"
            className="w-full bg-[#1e293b] border border-[#334155] text-[#f1f5f9] rounded-lg px-3.5 py-2.5 text-[14px] placeholder-[#475569] outline-none focus:border-[#3b82f6] transition-colors"
          />
        </div>

        <div className="mb-6">
          <label className="block text-[11px] font-semibold text-[#94a3b8] uppercase tracking-wider mb-2">
            Project
          </label>
          <input
            value={settings.phoenix_project}
            onChange={e => setSettings(s => ({ ...s, phoenix_project: e.target.value }))}
            placeholder="default"
            className="w-full bg-[#1e293b] border border-[#334155] text-[#f1f5f9] rounded-lg px-3.5 py-2.5 text-[14px] placeholder-[#475569] outline-none focus:border-[#3b82f6] transition-colors"
          />
        </div>

        {status && (
          <div className="text-[#4ade80] text-[13px] mb-4">{status}</div>
        )}

        <div className="flex gap-2 justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-[14px] font-medium text-[#94a3b8] bg-transparent border border-[#334155] rounded-lg hover:text-[#e2e8f0] hover:border-[#475569] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={save}
            disabled={saving}
            className="px-4 py-2 text-[14px] font-medium text-white bg-[#3b82f6] rounded-lg hover:bg-[#2563eb] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {saving ? 'Saving…' : 'Connect'}
          </button>
        </div>
      </div>
    </div>
  )
}
