import { useQuery } from '@tanstack/react-query'

export interface Metrics {
  alerts_total: number
  alerts_open: number
  scripts_total: number
  targets_total: number
  last_scan_timestamp: number | null
}

export function useMetrics() {
  return useQuery<Metrics>({
    queryKey: ['metrics'],
    queryFn: async () => {
      const text: string = await fetch('/metrics').then((r) => r.text())
      const parse = (key: string): number | null => {
        const match = text.match(new RegExp(`^${key}\\s+([\\d.]+)`, 'm'))
        return match ? parseFloat(match[1]) : null
      }
      return {
        alerts_total: parse('suricatajs_alerts_total') ?? 0,
        alerts_open: parse('suricatajs_alerts_open') ?? 0,
        scripts_total: parse('suricatajs_scripts_total') ?? 0,
        targets_total: parse('suricatajs_targets_total') ?? 0,
        last_scan_timestamp: parse('suricatajs_last_scan_timestamp_seconds'),
      }
    },
    refetchInterval: 60_000,
  })
}
