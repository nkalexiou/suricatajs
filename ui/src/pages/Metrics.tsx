import { useMetrics } from '@/api/metrics'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

function StatCard({ label, value }: { label: string; value: number | string }) {
  return (
    <Card className="bg-[#161625] border-slate-700">
      <CardHeader className="pb-1 pt-4 px-4">
        <CardTitle className="text-[10px] text-slate-500 uppercase tracking-wider font-medium">{label}</CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4">
        <div className="text-3xl font-bold text-slate-100">{value}</div>
      </CardContent>
    </Card>
  )
}

export function Metrics() {
  const { data, isLoading } = useMetrics()

  const lastScan = data?.last_scan_timestamp
    ? new Date(data.last_scan_timestamp * 1000).toLocaleString()
    : 'Never'

  return (
    <div>
      <h1 className="text-xl font-bold text-slate-100 mb-4">Metrics / Status</h1>
      {isLoading ? (
        <div className="text-slate-500 text-sm">Loading…</div>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            <StatCard label="Total alerts" value={data?.alerts_total ?? 0} />
            <StatCard label="Open alerts" value={data?.alerts_open ?? 0} />
            <StatCard label="Scripts tracked" value={data?.scripts_total ?? 0} />
            <StatCard label="Targets" value={data?.targets_total ?? 0} />
          </div>
          <div className="text-xs text-slate-500">Last scan: {lastScan}</div>
        </>
      )}
    </div>
  )
}
