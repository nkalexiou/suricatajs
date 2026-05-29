import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDomains, useCreateDomain } from '@/api/domains'
import { useOpenAlerts } from '@/api/alerts'
import { useTargets } from '@/api/targets'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'

function DomainCard({ domain, alertCount, urlCount, onClick }: {
  domain: { id: number; domain: string }
  alertCount: number
  urlCount: number
  onClick: () => void
}) {
  return (
    <div
      onClick={onClick}
      className="bg-[#161625] border border-slate-700 rounded-lg p-4 cursor-pointer hover:border-indigo-500 transition-colors"
    >
      <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Domain</div>
      <div className="text-base font-semibold text-slate-100 mb-2">{domain.domain}</div>
      <div className="flex gap-3 text-xs">
        <span className="text-slate-500">{urlCount} URLs</span>
        <span className={alertCount > 0 ? 'text-amber-400 font-semibold' : 'text-emerald-400 font-semibold'}>
          {alertCount} open {alertCount === 1 ? 'alert' : 'alerts'}
        </span>
      </div>
    </div>
  )
}

export function Domains() {
  const { data: domains = [], isLoading } = useDomains()
  const { data: alerts = [] } = useOpenAlerts()
  const { data: targets = [] } = useTargets()
  const createDomain = useCreateDomain()
  const navigate = useNavigate()
  const [showDialog, setShowDialog] = useState(false)
  const [newDomain, setNewDomain] = useState('')
  const [error, setError] = useState('')

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await createDomain.mutateAsync({ domain: newDomain.trim() })
      setNewDomain('')
      setShowDialog(false)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create domain')
    }
  }

  function alertCountForDomain(domainId: number): number {
    const domainTargets = targets.filter((t) => t.domain_id === domainId)
    return alerts.filter((a) => {
      try {
        const host = new URL(a.javascript).host
        return domainTargets.some((t) => new URL(t.url).host === host)
      } catch {
        return false
      }
    }).length
  }

  function urlCountForDomain(domainId: number): number {
    return targets.filter((t) => t.domain_id === domainId).length
  }

  if (isLoading) return <div className="text-slate-500">Loading…</div>

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-xl font-bold text-slate-100">Domains</h1>
        <Button onClick={() => setShowDialog(true)} size="sm" className="bg-indigo-600 hover:bg-indigo-700">
          + Add domain
        </Button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {domains.map((d) => (
          <DomainCard
            key={d.id}
            domain={d}
            alertCount={alertCountForDomain(d.id)}
            urlCount={urlCountForDomain(d.id)}
            onClick={() => navigate(`/domains/${d.id}`)}
          />
        ))}
        {domains.length === 0 && (
          <div className="col-span-3 text-slate-500 text-sm py-8 text-center">
            No domains yet. Add one to start monitoring.
          </div>
        )}
      </div>

      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="bg-[#161625] border-slate-700">
          <DialogHeader>
            <DialogTitle className="text-slate-100">Add domain</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate} className="flex flex-col gap-4">
            <Input
              placeholder="example.com"
              value={newDomain}
              onChange={(e) => setNewDomain(e.target.value)}
              required
              className="bg-[#0f0f1a] border-slate-700 text-slate-200"
            />
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <DialogFooter>
              <Button variant="ghost" type="button" onClick={() => setShowDialog(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createDomain.isPending} className="bg-indigo-600 hover:bg-indigo-700">
                Add
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
