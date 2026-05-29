import { useState } from 'react'
import type { Target } from '@/api/targets'
import { useDeleteTarget } from '@/api/targets'
import type { Alert } from '@/api/alerts'
import { ScriptsTable } from './ScriptsTable'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

interface Props {
  target: Target
  alerts: Alert[]
  onDeleted: () => void
}

function formatScanTime(raw: string | null): string {
  if (!raw) return 'No scan yet'
  // raw format: "20250529_161234" → parse as local time
  const m = raw.match(/^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})$/)
  if (!m) return raw
  const d = new Date(
    parseInt(m[1]), parseInt(m[2]) - 1, parseInt(m[3]),
    parseInt(m[4]), parseInt(m[5]), parseInt(m[6])
  )
  return d.toLocaleString(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  })
}

export function UrlAccordion({ target, alerts, onDeleted }: Props) {
  const [open, setOpen] = useState(false)
  const deleteTarget = useDeleteTarget()
  const openAlerts = alerts.filter((a) => {
    if (a.resolved) return false
    if (a.source_page) return a.source_page === target.url
    try {
      return new URL(a.javascript).hostname === new URL(target.url).hostname
    } catch {
      return a.javascript.startsWith(target.url)
    }
  })
  const scanned = formatScanTime(target.last_scanned_at)
  const neverScanned = !target.last_scanned_at

  async function handleDelete() {
    if (!confirm(`Remove ${target.url}?`)) return
    await deleteTarget.mutateAsync(target.id)
    onDeleted()
  }

  return (
    <div className="bg-[#161625] border border-slate-700 rounded-lg overflow-hidden mb-2">
      <div
        className="flex items-center gap-2 px-4 py-3 cursor-pointer hover:bg-[#1a1a2e] select-none"
        onClick={() => setOpen((o) => !o)}
      >
        <span className="text-slate-500 text-xs w-3">{open ? '▼' : '▶'}</span>
        <div className="flex-1 min-w-0">
          <div className="font-mono text-sm text-slate-300 truncate">{target.url}</div>
          <div className={`text-[10px] mt-0.5 ${neverScanned ? 'text-slate-600 italic' : 'text-slate-500'}`}>
            Last scan: {scanned}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Badge className="bg-slate-800 text-slate-400 text-[10px]">
            {target.use_playwright ? 'Browser' : 'Standard'}
          </Badge>
          {openAlerts.length > 0 ? (
            <Badge className="bg-red-950 text-red-300 text-[10px]">{openAlerts.length} alerts</Badge>
          ) : (
            <Badge className="bg-emerald-950 text-emerald-300 text-[10px]">No alerts</Badge>
          )}
        </div>
        <div className="flex gap-1 ml-2" onClick={(e) => e.stopPropagation()}>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs text-slate-500 hover:text-red-400 hover:bg-red-950"
            onClick={handleDelete}
            disabled={deleteTarget.isPending}
          >
            Remove
          </Button>
        </div>
      </div>
      {open && (
        <div className="border-t border-slate-800">
          <ScriptsTable alerts={alerts} targetUrl={target.url} />
        </div>
      )}
    </div>
  )
}
