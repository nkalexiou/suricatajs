import { useState, useMemo } from 'react'
import { useOpenAlerts, useResolvedAlerts, useResolveAlert, useApproveAlert } from '@/api/alerts'
import type { Alert } from '@/api/alerts'
import { useDomains } from '@/api/domains'
import { useTargets } from '@/api/targets'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'

function domainForAlert(
  alert: Alert,
  targets: { url: string; domain_id: number | null }[],
  domains: { id: number; domain: string }[]
) {
  try {
    const alertHost = new URL(alert.javascript).host
    const target = targets.find((t) => {
      try { return new URL(t.url).host === alertHost } catch { return false }
    })
    if (!target?.domain_id) return null
    return domains.find((d) => d.id === target.domain_id)?.domain ?? null
  } catch {
    return null
  }
}

export function Alerts() {
  const { data: openAlerts = [] } = useOpenAlerts()
  const { data: resolvedAlerts = [] } = useResolvedAlerts()
  const { data: domains = [] } = useDomains()
  const { data: targets = [] } = useTargets()
  const resolveAlert = useResolveAlert()
  const approveAlert = useApproveAlert()
  const [statusFilter, setStatusFilter] = useState<'open' | 'resolved' | 'all'>('open')
  const [domainFilter, setDomainFilter] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  const allAlerts = useMemo(() => {
    if (statusFilter === 'open') return openAlerts
    if (statusFilter === 'resolved') return resolvedAlerts
    return [...openAlerts, ...resolvedAlerts]
  }, [statusFilter, openAlerts, resolvedAlerts])

  const visible = allAlerts.filter((a) => {
    if (domainFilter) {
      const d = domainForAlert(a, targets, domains)
      if (d !== domainFilter) return false
    }
    if (search) {
      const q = search.toLowerCase()
      return (
        a.javascript.toLowerCase().includes(q) ||
        a.date.includes(q) ||
        (domainForAlert(a, targets, domains) ?? '').toLowerCase().includes(q)
      )
    }
    return true
  })

  const isInline = (uri: string) => uri.includes('#inline-')

  return (
    <div>
      <h1 className="text-xl font-bold text-slate-100 mb-2">Alerts</h1>
      <div className="flex gap-4 text-xs text-slate-500 mb-4">
        <span><span className="font-semibold text-amber-400">{openAlerts.length}</span> open</span>
        <span><span className="font-semibold text-slate-300">{resolvedAlerts.length}</span> resolved</span>
      </div>

      <div className="flex flex-wrap gap-2 mb-4 items-center">
        <Input
          placeholder="Search script, domain, date…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-60 h-8 bg-[#161625] border-slate-700 text-slate-200 text-sm"
        />
        <div className="flex gap-1.5 items-center">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider mr-1">Status</span>
          {(['open', 'resolved', 'all'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setStatusFilter(f)}
              className={`px-2.5 py-1 rounded-full text-[11px] border transition-colors ${
                statusFilter === f
                  ? 'bg-indigo-900 border-indigo-500 text-indigo-300'
                  : 'bg-transparent border-slate-700 text-slate-500 hover:text-slate-300'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
        <div className="flex gap-1.5 items-center">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider mr-1">Domain</span>
          <button
            onClick={() => setDomainFilter(null)}
            className={`px-2.5 py-1 rounded-full text-[11px] border transition-colors ${
              !domainFilter ? 'bg-indigo-900 border-indigo-500 text-indigo-300' : 'bg-transparent border-slate-700 text-slate-500 hover:text-slate-300'
            }`}
          >
            All
          </button>
          {domains.map((d) => (
            <button
              key={d.id}
              onClick={() => setDomainFilter(d.domain)}
              className={`px-2.5 py-1 rounded-full text-[11px] border transition-colors ${
                domainFilter === d.domain ? 'bg-indigo-900 border-indigo-500 text-indigo-300' : 'bg-transparent border-slate-700 text-slate-500 hover:text-slate-300'
              }`}
            >
              {d.domain}
            </button>
          ))}
        </div>
      </div>

      <table className="w-full border-collapse text-xs">
        <thead>
          <tr>
            {['Detection', 'Script', 'Domain', 'Date', 'Status', ''].map((h) => (
              <th key={h} className="text-left px-3 py-2 text-slate-500 text-[10px] uppercase tracking-wider font-medium border-b border-slate-700">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {visible.map((a) => {
            const domain = domainForAlert(a, targets, domains)
            return (
              <tr key={a.id} className={`border-t border-slate-800/50 hover:bg-[#161625] ${a.resolved ? 'opacity-50' : ''}`}>
                <td className="px-3 py-2.5">
                  {a.alert_type === 'checksum' ? (
                    <Badge className="bg-red-950 text-red-300 text-[10px]">Content changed</Badge>
                  ) : (
                    <Badge className="bg-blue-950 text-blue-200 text-[10px]">New script</Badge>
                  )}
                </td>
                <td className="px-3 py-2.5 max-w-[220px] truncate">
                  <span className={`font-mono text-[11px] ${isInline(a.javascript) ? 'text-amber-300' : 'text-violet-300'}`} title={a.javascript}>
                    {a.javascript}
                  </span>
                </td>
                <td className="px-3 py-2.5">
                  {domain ? (
                    <span className="px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-300 text-[10px] font-medium">
                      {domain}
                    </span>
                  ) : <span className="text-slate-600">—</span>}
                </td>
                <td className="px-3 py-2.5 text-slate-500">{a.date.replace('_', ' ')}</td>
                <td className="px-3 py-2.5">
                  {a.resolved ? (
                    <Badge className="bg-slate-800 text-slate-400 text-[10px]">Resolved</Badge>
                  ) : (
                    <Badge className="bg-emerald-950 text-emerald-400 text-[10px]">Open</Badge>
                  )}
                </td>
                <td className="px-3 py-2.5">
                  {!a.resolved && (
                    <div className="flex gap-1.5">
                      <button
                        onClick={() => approveAlert.mutate(a.id)}
                        className="text-[10px] px-2 py-0.5 border border-slate-700 rounded text-slate-400 hover:border-indigo-500 hover:text-indigo-300 hover:bg-indigo-950 transition-colors"
                      >
                        Dismiss &amp; Approve
                      </button>
                      <button
                        onClick={() => resolveAlert.mutate(a.id)}
                        className="text-[10px] px-2 py-0.5 border border-slate-700 rounded text-slate-400 hover:border-emerald-600 hover:text-emerald-400 hover:bg-emerald-950 transition-colors"
                      >
                        Resolve
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            )
          })}
          {visible.length === 0 && (
            <tr>
              <td colSpan={6} className="px-3 py-8 text-center text-slate-500">No alerts match current filters.</td>
            </tr>
          )}
        </tbody>
      </table>
      <p className="text-[10px] text-slate-600 italic mt-2">
        Dismiss &amp; Approve — expected change, updates baseline. | Resolve — incident handled, baseline unchanged.
      </p>
    </div>
  )
}
