import { XCircle, AlertTriangle, Info } from 'lucide-react'
import type { Issue } from '../api/client'
import { cn } from '../lib/utils'
import { CATEGORY_PILL } from '../lib/tokens'

function SevIcon({ severity }: { severity: Issue['severity'] }) {
  const base = 'w-10 h-10 rounded-[9px] flex-shrink-0 flex items-center justify-center'
  if (severity === 'error') return (
    <div className={cn(base, 'bg-red-500/13 border border-red-500/25')}>
      <XCircle size={17} className="text-[#f87171]" />
    </div>
  )
  if (severity === 'warning') return (
    <div className={cn(base, 'bg-amber-500/11 border border-amber-500/25')}>
      <AlertTriangle size={17} className="text-[#fbbf24]" />
    </div>
  )
  return (
    <div className={cn(base, 'bg-blue-500/10 border border-blue-500/22')}>
      <Info size={17} className="text-[#60a5fa]" />
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
        <p className="text-[#94a3b8] text-sm">{summary}</p>
      </div>
    )
  }

  return (
    <div className="p-7 space-y-6">

      {/* Root cause card */}
      <div className="bg-gradient-to-br from-red-500/6 to-red-500/2 border border-red-500/20 rounded-[10px] p-5">
        <div className="flex items-center gap-1.5 mb-2">
          <div className="w-[5px] h-[5px] rounded-full bg-[#ef4444] flex-shrink-0" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-[#f87171]">Root Cause Identified</span>
        </div>
        <div className="text-[14px] font-semibold text-[#fca5a5] mb-2">{rootCause}</div>
        <div className="text-[13px] text-[#94a3b8] leading-relaxed">{summary}</div>
      </div>

      {/* Diagnostics section */}
      <div>
        <div className="flex items-center justify-between mb-3.5">
          <span className="text-[11px] font-bold text-[#475569] uppercase tracking-widest">Diagnostics</span>
          <span className="text-[11px] text-[#334155]">{issues.length} issue{issues.length !== 1 ? 's' : ''} found</span>
        </div>

        <div className="space-y-3">
          {issues.map(issue => (
            <div key={issue.id} className="bg-[#0c1220] border border-[#1e293b] rounded-[11px] p-[18px] flex gap-4 items-start hover:border-[#334155] transition-colors">
              <SevIcon severity={issue.severity} />
              <div className="flex-1 min-w-0">
                <div className="mb-2">
                  <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                    <span className={cn('text-[11px] font-bold px-2.5 py-0.5 rounded-full flex-shrink-0', CATEGORY_PILL[issue.category])}>
                      {issue.category.charAt(0).toUpperCase() + issue.category.slice(1)}
                    </span>
                    <span className="text-[11px] text-[#475569] font-mono bg-[#0f172a] border border-[#1e293b] rounded px-2 py-0.5 whitespace-nowrap">
                      {issue.span_name}
                    </span>
                  </div>
                  <div className="text-[14px] font-semibold text-[#f1f5f9] leading-snug">{issue.explanation.split('.')[0]}</div>
                </div>
                <div className="text-[13px] text-[#64748b] leading-[1.65]">{issue.explanation}</div>
                {issue.suggestion && (
                  <div className="mt-3 p-3 bg-blue-500/4 border border-blue-500/14 rounded-lg">
                    <div className="flex items-center gap-1.5 mb-1.5 text-[10px] font-extrabold uppercase tracking-widest text-[#3b82f6]">
                      <Info size={9} />
                      Recommended Fix
                    </div>
                    <div className="text-[13px] text-[#7dd3fc] leading-[1.65]">{issue.suggestion}</div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
