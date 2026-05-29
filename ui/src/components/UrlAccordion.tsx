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

export function UrlAccordion({ target, alerts, onDeleted }: Props) {
  const [open, setOpen] = useState(false)
  const deleteTarget = useDeleteTarget()
  const openAlerts = alerts.filter((a) => !a.resolved)

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
        <span className="font-mono text-sm text-slate-300 flex-1 truncate">{target.url}</span>
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
