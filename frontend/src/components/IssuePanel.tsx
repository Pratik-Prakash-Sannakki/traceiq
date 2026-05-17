import { useState } from 'react'
import { ChevronDown, ChevronUp, Lightbulb, AlertCircle } from 'lucide-react'
import type { Issue } from '../api/client'
import { cn } from '../lib/utils'
import { CATEGORY_PILL } from '../lib/tokens'

const CATEGORY_COLOR: Record<string, string> = {
  failure: '#ef4444',
  latency: '#f59e0b',
  quality: '#8b5cf6',
  logic:   '#3b82f6',
}

function IssueCard({ issue }: { issue: Issue }) {
  const [open, setOpen] = useState(false)
  const color = CATEGORY_COLOR[issue.category] ?? '#64748b'

  return (
    <div
      className="bg-[#0c1220] border border-[#1e293b] rounded-lg overflow-hidden"
      style={{ borderLeft: `3px solid ${color}` }}
    >
      {/* Clickable header */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-[#0f1828] transition-colors"
      >
        <span className={cn('text-[10px] font-bold px-2 py-0.5 rounded-full flex-shrink-0', CATEGORY_PILL[issue.category])}>
          {issue.category.charAt(0).toUpperCase() + issue.category.slice(1)}
        </span>
        <span className="text-[11px] text-[#475569] font-mono bg-[#0f172a] border border-[#1e293b] rounded px-1.5 py-0.5 whitespace-nowrap flex-shrink-0">
          {issue.span_name}
        </span>
        <span className="flex-1 text-[12px] text-[#94a3b8] truncate text-left">
          {issue.explanation.split('.')[0]}.
        </span>
        <span className="flex-shrink-0 text-[#475569]">
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </span>
      </button>

      {/* Expanded body */}
      {open && (
        <div className="px-4 pb-4 border-t border-[#1e293b]">
          <p className="text-[12px] text-[#94a3b8] leading-[1.7] pt-3">
            {issue.explanation}
          </p>
          {issue.suggestion && (
            <div className="mt-3 px-3 py-2.5 bg-[#0a1628] border border-blue-500/15 rounded-md">
              <div className="flex items-center gap-1.5 mb-1.5">
                <Lightbulb size={9} className="text-[#3b82f6] flex-shrink-0" />
                <span className="text-[9px] font-extrabold uppercase tracking-widest text-[#3b82f6]">Recommended Fix</span>
              </div>
              <p className="text-[12px] text-[#60a5fa] leading-[1.7]">{issue.suggestion}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function IssuePanel({ issues, rootCause, summary }: {
  issues: Issue[]
  rootCause: string
  summary: string
}) {
  const [rcaOpen, setRcaOpen] = useState(false)

  if (issues.length === 0) {
    return (
      <div className="p-6 max-w-3xl">
        <div className="flex items-center gap-2 text-[#4ade80] font-semibold mb-2">
          <span>✓</span> No issues found
        </div>
        <p className="text-[#64748b] text-[13px] leading-relaxed">{summary}</p>
      </div>
    )
  }

  return (
    <div className="p-5 space-y-4 max-w-3xl">

      {/* Root cause — compact with expand */}
      <div
        className="border border-red-500/25 rounded-lg overflow-hidden"
        style={{ borderLeft: '3px solid #ef4444' }}
      >
        <button
          onClick={() => setRcaOpen(o => !o)}
          className="w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-red-500/3 transition-colors"
        >
          <AlertCircle size={14} className="text-[#f87171] flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <div className="text-[9px] font-bold uppercase tracking-widest text-[#f87171] mb-1">Root Cause</div>
            <p className={cn(
              'text-[12px] text-[#fca5a5] font-medium leading-snug',
              !rcaOpen && 'line-clamp-2'
            )}>
              {rootCause}
            </p>
            {rcaOpen && (
              <p className="text-[12px] text-[#94a3b8] leading-[1.7] mt-2">{summary}</p>
            )}
          </div>
          <span className="text-[#f87171] flex-shrink-0 mt-0.5">
            {rcaOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </span>
        </button>
      </div>

      {/* Diagnostics header */}
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold text-[#475569] uppercase tracking-widest">Diagnostics</span>
        <span className="text-[10px] text-[#334155]">{issues.length} issue{issues.length !== 1 ? 's' : ''} found</span>
      </div>

      {/* Issue cards — collapsed by default */}
      <div className="space-y-2">
        {issues.map(issue => (
          <IssueCard key={issue.id} issue={issue} />
        ))}
      </div>
    </div>
  )
}
