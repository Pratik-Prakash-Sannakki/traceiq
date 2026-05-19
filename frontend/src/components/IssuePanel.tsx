import { XCircle, AlertTriangle, Info, Zap } from 'lucide-react'
import type { Issue } from '../api/client'

const CAT = {
  failure: {
    Icon: XCircle,
    iconColor: '#f87171',
    leftBg: '#1d0909',
    rightBg: '#0d1525',
    border: 'rgba(239,68,68,0.3)',
    pillBg: 'rgba(239,68,68,0.15)',
    pillColor: '#f87171',
    pillLabel: 'Failure',
  },
  latency: {
    Icon: AlertTriangle,
    iconColor: '#fbbf24',
    leftBg: '#1d1508',
    rightBg: '#0d1525',
    border: 'rgba(245,158,11,0.3)',
    pillBg: 'rgba(245,158,11,0.15)',
    pillColor: '#fbbf24',
    pillLabel: 'Latency',
  },
  logic: {
    Icon: Info,
    iconColor: '#60a5fa',
    leftBg: '#07111e',
    rightBg: '#0d1525',
    border: 'rgba(59,130,246,0.3)',
    pillBg: 'rgba(59,130,246,0.15)',
    pillColor: '#60a5fa',
    pillLabel: 'Logic',
  },
  quality: {
    Icon: Zap,
    iconColor: '#a78bfa',
    leftBg: '#0e0818',
    rightBg: '#0d1525',
    border: 'rgba(139,92,246,0.3)',
    pillBg: 'rgba(139,92,246,0.15)',
    pillColor: '#a78bfa',
    pillLabel: 'Quality',
  },
} as const

function IssueCard({ issue }: { issue: Issue }) {
  const c    = CAT[issue.category as keyof typeof CAT] ?? CAT.logic
  const Icon = c.Icon

  const dot   = issue.explanation.indexOf('. ')
  const title = dot > 0 ? issue.explanation.slice(0, dot + 1) : issue.explanation
  const body  = dot > 0 ? issue.explanation.slice(dot + 2) : ''

  return (
    <div style={{ display: 'flex', borderRadius: 10, overflow: 'hidden', border: `1px solid ${c.border}` }}>

      {/* Left: icon only, no label */}
      <div style={{
        width: 52, flexShrink: 0,
        background: c.leftBg,
        borderRight: `1px solid ${c.border}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <Icon size={17} strokeWidth={1.75} style={{ color: c.iconColor }} />
      </div>

      {/* Right content */}
      <div style={{ flex: 1, minWidth: 0, background: c.rightBg, padding: '14px 18px' }}>
        {/* Pill + span tag row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, flexWrap: 'wrap' }}>
          <span style={{
            fontSize: 10, fontWeight: 700,
            padding: '2px 8px', borderRadius: 20,
            background: c.pillBg, color: c.pillColor,
            border: `1px solid ${c.border}`,
          }}>
            {c.pillLabel}
          </span>
          <span style={{
            fontSize: 11, fontFamily: 'var(--mono)',
            background: '#060e1a', border: '1px solid var(--line)',
            borderRadius: 5, padding: '1px 7px', color: 'var(--t3)',
            whiteSpace: 'nowrap',
          }}>
            {issue.span_name}
          </span>
        </div>

        {/* Title */}
        <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--t1)', lineHeight: 1.5, marginBottom: body ? 8 : 0 }}>
          {title}
        </p>

        {/* Body */}
        {body && (
          <p style={{ fontSize: 12, color: 'var(--t2)', lineHeight: 1.7, marginBottom: issue.suggestion ? 12 : 0 }}>
            {body}
          </p>
        )}

        {/* Recommended fix */}
        {issue.suggestion && (
          <div style={{ paddingTop: 10, borderTop: '1px solid var(--line)' }}>
            <p style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: '#3b82f6', marginBottom: 6 }}>
              ◎ Recommended Fix
            </p>
            <p style={{ fontSize: 12, color: '#93c5fd', lineHeight: 1.7 }}>{issue.suggestion}</p>
          </div>
        )}
      </div>
    </div>
  )
}

export function IssuePanel({ issues, rootCause, summary }: {
  issues:    Issue[]
  rootCause: string
  summary:   string
}) {
  if (issues.length === 0) {
    return (
      <div style={{ padding: '36px 40px' }}>
        <div style={{ background: '#071a0e', border: '1px solid #1a4a28', borderRadius: 12, padding: '20px 24px' }}>
          <p style={{ fontSize: 14, fontWeight: 600, color: '#4ade80', marginBottom: 8 }}>✓ No issues found</p>
          <p style={{ fontSize: 13, color: 'var(--t2)', lineHeight: 1.75 }}>{summary}</p>
        </div>
      </div>
    )
  }

  const m        = rootCause.match(/^(.+?[.!?])\s+(.+)$/s)
  const headline = m ? m[1] : rootCause
  const detail   = m ? m[2] : ''

  return (
    <div style={{ padding: '36px 40px 60px' }}>

      {/* Root cause — distinct card, full width */}
      <div style={{
        background: '#0c0e1f',
        border: '1px solid #3b3f8c',
        borderRadius: 12,
        padding: '24px 28px',
        marginBottom: 32,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
          <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#818cf8', flexShrink: 0 }} />
          <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.12em', color: '#818cf8' }}>
            Root Cause Identified
          </span>
        </div>
        {/* Full-width headline */}
        <p style={{ fontSize: 16, fontWeight: 700, color: 'var(--t1)', lineHeight: 1.5, marginBottom: 14 }}>
          {headline}
        </p>
        {/* Full-width detail */}
        {(detail || summary) && (
          <p style={{ fontSize: 14, color: 'var(--t2)', lineHeight: 1.8 }}>
            {detail || summary}
          </p>
        )}
      </div>

      {/* Diagnostics header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
        <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--t3)' }}>
          Diagnostics
        </span>
        <span style={{ fontSize: 11, color: 'var(--t3)' }}>{issues.length} issues found</span>
      </div>

      {/* Diagnostic cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {issues.map(issue => <IssueCard key={issue.id} issue={issue} />)}
      </div>

    </div>
  )
}
