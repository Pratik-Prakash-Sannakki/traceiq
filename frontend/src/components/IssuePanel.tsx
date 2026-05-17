import type { Issue } from '../api/client'

const CATEGORY_COLOR: Record<string, string> = {
  failure: '#ef4444',
  latency: '#f59e0b',
  quality: '#8b5cf6',
  logic: '#3b82f6',
}

const SEVERITY_ICON: Record<string, string> = {
  error: '🔴',
  warning: '🟡',
  info: '🔵',
}

export function IssuePanel({ issues, rootCause, summary }: {
  issues: Issue[]
  rootCause: string
  summary: string
}) {
  if (issues.length === 0) {
    return (
      <div style={{ padding: 16 }}>
        <div style={{ color: '#22c55e', fontWeight: 600 }}>✓ No issues found</div>
        <p style={{ color: '#94a3b8', marginTop: 8, fontSize: 14 }}>{summary}</p>
      </div>
    )
  }

  return (
    <div style={{ padding: 16 }}>
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 12, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 4 }}>Root Cause</div>
        <div style={{ color: '#f1f5f9', fontSize: 14 }}>{rootCause}</div>
      </div>
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 12, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 4 }}>Summary</div>
        <div style={{ color: '#94a3b8', fontSize: 13 }}>{summary}</div>
      </div>
      <div style={{ fontSize: 12, color: '#94a3b8', textTransform: 'uppercase', marginBottom: 8 }}>
        Issues ({issues.length})
      </div>
      {issues.map(issue => (
        <div key={issue.id} style={{
          background: '#0f172a',
          border: `1px solid ${CATEGORY_COLOR[issue.category] ?? '#333'}`,
          borderRadius: 8, padding: 12, marginBottom: 8,
        }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
            <span>{SEVERITY_ICON[issue.severity]}</span>
            <span style={{
              background: CATEGORY_COLOR[issue.category],
              color: 'white', borderRadius: 4, padding: '1px 6px', fontSize: 11
            }}>
              {issue.category}
            </span>
            <span style={{ color: '#94a3b8', fontSize: 12 }}>{issue.span_name}</span>
          </div>
          <div style={{ color: '#f1f5f9', fontSize: 13, marginBottom: 6 }}>{issue.explanation}</div>
          <div style={{ color: '#60a5fa', fontSize: 12 }}>💡 {issue.suggestion}</div>
        </div>
      ))}
    </div>
  )
}
