import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useDomains } from '@/api/domains'
import { useTargets, useCreateTarget } from '@/api/targets'
import type { Alert } from '@/api/alerts'
import { useOpenAlerts, useResolvedAlerts, useResolveAlert, useApproveAlert } from '@/api/alerts'
import { UrlAccordion } from '@/components/UrlAccordion'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'

function AlertRow({ alert, onResolve, onApprove }: {
  alert: Alert
  onResolve: () => void
  onApprove: () => void
}) {
  const isInline = alert.javascript.includes('#inline-')
  return (
    <tr className="border-t border-slate-800/60 hover:bg-[#161625]">
      <td className="px-3 py-2.5">
        {alert.alert_type === 'checksum' ? (
          <Badge className="bg-red-950 text-red-300 text-[10px]">Content changed</Badge>
        ) : (
          <Badge className="bg-blue-950 text-blue-200 text-[10px]">New script</Badge>
        )}
      </td>
      <td className="px-3 py-2.5 font-mono text-[11px] max-w-xs truncate">
        <span className={isInline ? 'text-amber-300' : 'text-violet-300'} title={alert.javascript}>
          {alert.javascript}
        </span>
      </td>
      <td className="px-3 py-2.5 text-slate-500 text-xs">{alert.date.replace('_', ' ')}</td>
      <td className="px-3 py-2.5">
        {alert.resolved ? (
          <Badge className="bg-slate-800 text-slate-400 text-[10px]">Resolved</Badge>
        ) : (
          <Badge className="bg-emerald-950 text-emerald-400 text-[10px]">Open</Badge>
        )}
      </td>
      <td className="px-3 py-2.5">
        {!alert.resolved && (
          <div className="flex gap-1.5">
            <button
              onClick={onApprove}
              className="text-[11px] px-2 py-0.5 border border-slate-700 rounded text-slate-400 hover:border-indigo-500 hover:text-indigo-300 hover:bg-indigo-950 transition-colors"
            >
              Dismiss &amp; Approve
            </button>
            <button
              onClick={onResolve}
              className="text-[11px] px-2 py-0.5 border border-slate-700 rounded text-slate-400 hover:border-emerald-600 hover:text-emerald-400 hover:bg-emerald-950 transition-colors"
            >
              Resolve
            </button>
          </div>
        )}
      </td>
    </tr>
  )
}

export function DomainDetail() {
  const { id } = useParams<{ id: string }>()
  const domainId = Number(id)
  const { data: domains = [] } = useDomains()
  const domain = domains.find((d) => d.id === domainId)
  const { data: targets = [], refetch: refetchTargets } = useTargets(domainId)
  const { data: openAlerts = [] } = useOpenAlerts()
  const { data: resolvedAlerts = [] } = useResolvedAlerts()
  const createTarget = useCreateTarget()
  const resolveAlert = useResolveAlert()
  const approveAlert = useApproveAlert()
  const [showAddUrl, setShowAddUrl] = useState(false)
  const [newUrl, setNewUrl] = useState('')
  const [urlError, setUrlError] = useState('')
  const [filter, setFilter] = useState<'open' | 'resolved' | 'all'>('open')
  const [search, setSearch] = useState('')

  const domainAlerts = [...openAlerts, ...resolvedAlerts].filter((a) => {
    try {
      return targets.some((t) =>
        new URL(t.url).host === new URL(a.javascript).host || a.javascript.startsWith(t.url)
      )
    } catch { return false }
  })

  const visibleAlerts = domainAlerts
    .filter((a) => filter === 'all' ? true : filter === 'open' ? !a.resolved : a.resolved)
    .filter((a) => !search || a.javascript.includes(search) || a.date.includes(search))

  const openDomainCount = domainAlerts.filter((a) => !a.resolved).length

  async function handleAddUrl(e: React.FormEvent) {
    e.preventDefault()
    setUrlError('')
    try {
      await createTarget.mutateAsync({ url: newUrl.trim(), domain_id: domainId })
      setNewUrl('')
      setShowAddUrl(false)
      refetchTargets()
    } catch (err: unknown) {
      setUrlError(err instanceof Error ? err.message : 'Failed to add URL')
    }
  }

  return (
    <div>
      <div className="text-xs text-slate-500 mb-3">
        <Link to="/" className="text-indigo-400 hover:underline">Domains</Link>
        {' / '}
        <span>{domain?.domain ?? '…'}</span>
      </div>

      <h1 className="text-xl font-bold text-slate-100 mb-1">{domain?.domain ?? '…'}</h1>
      <div className="flex gap-4 text-xs text-slate-500 mb-5">
        <span><span className="font-semibold text-slate-300">{targets.length}</span> URLs monitored</span>
        <span className="text-amber-400 font-semibold">{openDomainCount} open alerts</span>
      </div>

      <Tabs defaultValue="urls">
        <TabsList className="bg-slate-800 mb-4">
          <TabsTrigger value="urls">Target URLs &amp; Scripts</TabsTrigger>
          <TabsTrigger value="log">Detection Log</TabsTrigger>
        </TabsList>

        <TabsContent value="urls">
          <div className="flex justify-end mb-3">
            <Button size="sm" onClick={() => setShowAddUrl(true)} className="bg-indigo-600 hover:bg-indigo-700">
              + Add URL
            </Button>
          </div>
          {targets.length === 0 && (
            <div className="text-slate-500 text-sm py-8 text-center">No URLs yet. Add one to start monitoring.</div>
          )}
          {targets.map((target) => (
            <UrlAccordion
              key={target.id}
              target={target}
              alerts={[...openAlerts, ...resolvedAlerts]}
              onDeleted={() => refetchTargets()}
            />
          ))}
        </TabsContent>

        <TabsContent value="log">
          <div className="flex gap-2 mb-3 flex-wrap items-center">
            <Input
              placeholder="Search script, date…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-56 h-8 bg-[#161625] border-slate-700 text-slate-200 text-sm"
            />
            {(['open', 'resolved', 'all'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1 rounded-full text-xs border transition-colors ${
                  filter === f
                    ? 'bg-indigo-900 border-indigo-500 text-indigo-300'
                    : 'bg-transparent border-slate-700 text-slate-500 hover:text-slate-300'
                }`}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
          <table className="w-full text-xs border-collapse">
            <thead>
              <tr>
                {['Detection', 'Script', 'Date', 'Status', ''].map((h) => (
                  <th key={h} className="text-left px-3 py-2 text-slate-500 uppercase tracking-wider font-medium text-[10px] border-b border-slate-700">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visibleAlerts.map((alert) => (
                <AlertRow
                  key={alert.id}
                  alert={alert}
                  onResolve={() => resolveAlert.mutate(alert.id)}
                  onApprove={() => approveAlert.mutate(alert.id)}
                />
              ))}
              {visibleAlerts.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-3 py-6 text-center text-slate-500">No alerts match the current filter.</td>
                </tr>
              )}
            </tbody>
          </table>
          <p className="text-[10px] text-slate-600 italic mt-2">
            Dismiss &amp; Approve — expected change, updates baseline. | Resolve — incident handled, baseline unchanged.
          </p>
        </TabsContent>
      </Tabs>

      <Dialog open={showAddUrl} onOpenChange={setShowAddUrl}>
        <DialogContent className="bg-[#161625] border-slate-700">
          <DialogHeader>
            <DialogTitle className="text-slate-100">Add URL</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleAddUrl} className="flex flex-col gap-4">
            <Input
              placeholder="https://example.com/checkout"
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
              required
              className="bg-[#0f0f1a] border-slate-700 text-slate-200"
            />
            {urlError && <p className="text-red-400 text-sm">{urlError}</p>}
            <DialogFooter>
              <Button variant="ghost" type="button" onClick={() => setShowAddUrl(false)}>Cancel</Button>
              <Button type="submit" disabled={createTarget.isPending} className="bg-indigo-600 hover:bg-indigo-700">Add</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
