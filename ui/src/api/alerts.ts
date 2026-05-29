import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from './client'

export interface Alert {
  id: number
  javascript: string
  stored_checksum: string | null
  new_checksum: string | null
  date: string
  alert_msg: string
  alert_type: 'new_script' | 'checksum'
  diff: string | null
  sri: string | null
  resolved: boolean
  resolved_at: string | null
  resolved_by: number | null
  source_page: string | null
}

export const alertKeys = {
  open: ['alerts', 'open'] as const,
  resolved: ['alerts', 'resolved'] as const,
  all: ['alerts', 'all'] as const,
}

export function useOpenAlerts() {
  return useQuery<Alert[]>({
    queryKey: alertKeys.open,
    queryFn: () => apiFetch('/alerts'),
    refetchInterval: 30_000,
  })
}

export function useResolvedAlerts() {
  return useQuery<Alert[]>({
    queryKey: alertKeys.resolved,
    queryFn: () => apiFetch('/alerts?resolved=1'),
  })
}

export function useResolveAlert() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiFetch<Alert>(`/alerts/${id}/resolve`, { method: 'PATCH' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: alertKeys.open })
      qc.invalidateQueries({ queryKey: alertKeys.resolved })
    },
  })
}

export function useApproveAlert() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiFetch<Alert>(`/alerts/${id}/approve`, { method: 'PATCH' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: alertKeys.open })
      qc.invalidateQueries({ queryKey: alertKeys.resolved })
    },
  })
}
