import { XCircle, AlertTriangle, Info, Lightbulb } from 'lucide-react'
import type { Issue } from '../api/client'
import { cn } from '../lib/utils'
import { CATEGORY_PILL } from '../lib/tokens'

const CATEGORY_BORDER: Record<'failure' | 'latency' | 'quality' | 'logic', string> = {
  failure: 'border-l-red-500/60',
  latency: 'border-l-amber-500/60',
  quality: 'border-l-violet-500/60',
  logic:   'border-l-blue-500/60',
}

function SevIcon({ severity }: { severity: Issue['severity'] }) {
  const base = 'w-9 h-9 rounded-lg flex-shrink-0 flex items-center justify-center'
  if (severity === 'error') return (
    <div className={cn(base, 'bg-red-500/12 border border-red-500/25')}>
      <XCircle size={16} className="text-[#f87171]" />
    </div>
  )
  if (severity === 'warning') return (
    <div className={cn(base, 'bg-amber-500/10 border border-amber-500/25')}>
      <AlertTriangle size={16} className="text-[#fbbf24]" />
    </div>
  )
  return (
    <div className={cn(base, 'bg-blue-500/10 border border-blue-500/20')}>
      <Info size={16} className="text-[#60a5fa]" />
    </div>
  )
}

export function IssuePanel({ issues, rootCause, summary }: {
  issues: Issue[]
  rootCause: string
  summary: string
}) {
  if (issues.length === 0) {
    return (
      <div className="p-8">
        <div className="text-[#4ade80] font-semibold mb-2">✓ No issues found</div>
        <p className="text-[#94a3b8] text-sm leading-relaxed">{summary}</p>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-5">

      {/* Root cause card */}
      <div className="bg-red-500/5 border border-red-500/20 border-l-[3px] border-l-red-500 rounded-lg p-4">
        <div className="flex items-center gap-1.5 mb-2">
          <div className="w-[5px] h-[5px] rounded-full bg-[#ef4444] flex-shrink-0" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-[#f87171]">Root Cause Identified</span>
        </div>
        <div className="text-[13px] font-semibold text-[#fca5a5] mb-2 leading-snug">{rootCause}</div>
        <div className="text-[12px] text-[#94a3b8] leading-relaxed">{summary}</div>
      </div>

      {/* Diagnostics section */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <span className="text-[10px] font-bold text-[#475569] uppercase tracking-widest">Diagnostics</span>
          <span className="text-[10px] text-[#334155]">{issues.length} issue{issues.length !== 1 ? 's' : ''} found</span>
        </div>

        <div className="space-y-2.5">
          {issues.map(issue => (
            <div
              key={issue.id}
              className={cn(
                'bg-[#0c1220] border border-[#1e293b] border-l-[3px] rounded-lg overflow-hidden hover:bg-[#0f1828] transition-colors',
                CATEGORY_BORDER[issue.category]
              )}
            >
              {/* Card header */}
              <div className="flex items-center gap-2.5 px-4 pt-4 pb-2.5">
                <SevIcon severity={issue.severity} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className={cn('text-[10px] font-bold px-2 py-0.5 rounded-full flex-shrink-0', CATEGORY_PILL[issue.category])}>
                      {issue.category.charAt(0).toUpperCase() + issue.category.slice(1)}
                    </span>
                    <span className="text-[10px] text-[#475569] font-mono bg-[#0f172a] border border-[#1e293b] rounded px-1.5 py-0.5 whitespace-nowrap">
                      {issue.span_name}
                    </span>
                  </div>
                </div>
              </div>

              {/* Explanation */}
              <div className="px-4 pb-3">
                <p className="text-[12px] text-[#94a3b8] leading-[1.7]">{issue.explanation}</p>
              </div>

              {/* Recommended fix */}
              {issue.suggestion && (
                <div className="mx-4 mb-4 px-3 py-2.5 bg-[#0a1628] border border-blue-500/15 rounded-md">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <Lightbulb size={9} className="text-[#3b82f6] flex-shrink-0" />
                    <span className="text-[9px] font-extrabold uppercase tracking-widest text-[#3b82f6]">Recommended Fix</span>
                  </div>
                  <p className="text-[12px] text-[#60a5fa] leading-[1.7]">{issue.suggestion}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
