import type { Alert } from '@/api/alerts'
import { Badge } from '@/components/ui/badge'

interface ScriptRow {
  uri: string
  alertType: 'changed' | 'new'
  isInline: boolean
}

function deriveScripts(alerts: Alert[], targetUrl: string): ScriptRow[] {
  const rows: ScriptRow[] = []
  for (const alert of alerts) {
    const isInline = alert.javascript.includes('#inline-')
    const relatedToUrl = alert.source_page
      ? alert.source_page === targetUrl
      : (() => {
          try {
            return new URL(alert.javascript).hostname === new URL(targetUrl).hostname
          } catch {
            return alert.javascript.startsWith(targetUrl)
          }
        })()
    if (!relatedToUrl) continue
    rows.push({
      uri: alert.javascript,
      alertType: alert.alert_type === 'checksum' ? 'changed' : 'new',
      isInline,
    })
  }
  return rows
}

export function ScriptsTable({ alerts, targetUrl }: { alerts: Alert[]; targetUrl: string }) {
  const scripts = deriveScripts(alerts, targetUrl)

  if (scripts.length === 0) {
    return <div className="px-4 py-3 text-xs text-slate-500 italic">No active alerts for this URL.</div>
  }

  return (
    <table className="w-full text-xs border-collapse">
      <thead>
        <tr className="bg-[#12121f]">
          <th className="text-left px-4 py-2 text-slate-500 uppercase tracking-wider font-medium">Script URI</th>
          <th className="text-left px-4 py-2 text-slate-500 uppercase tracking-wider font-medium">Type</th>
          <th className="text-left px-4 py-2 text-slate-500 uppercase tracking-wider font-medium">Status</th>
        </tr>
      </thead>
      <tbody>
        {scripts.map((s) => (
          <tr key={s.uri} className="border-t border-[#12121f] hover:bg-[#1a1a2e]">
            <td className="px-4 py-2.5 font-mono text-[11px] text-violet-300 max-w-xs truncate" title={s.uri}>
              {s.uri}
            </td>
            <td className="px-4 py-2.5">
              {s.isInline ? (
                <Badge className="bg-amber-950 text-amber-300 text-[10px]">Inline</Badge>
              ) : (
                <Badge className="bg-blue-950 text-blue-300 text-[10px]">External</Badge>
              )}
            </td>
            <td className="px-4 py-2.5">
              {s.alertType === 'changed' && (
                <Badge className="bg-red-950 text-red-300 text-[10px]">Changed</Badge>
              )}
              {s.alertType === 'new' && (
                <Badge className="bg-blue-950 text-blue-200 text-[10px]">New</Badge>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
