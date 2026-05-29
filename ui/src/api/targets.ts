import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from './client'

export interface Target {
  id: number
  url: string
  name: string | null
  domain_id: number | null
  scan_interval_minutes: number | null
  crawl_depth: number
  use_playwright: boolean
  created_at: string
  approved_checksum: string | null
  approved_at: string | null
}

export interface TargetCreate {
  url: string
  name?: string
  domain_id?: number
  scan_interval_minutes?: number
  crawl_depth?: number
  use_playwright?: boolean
}

export const targetKeys = {
  all: ['targets'] as const,
  byDomain: (domainId: number) => ['targets', 'domain', domainId] as const,
}

export function useTargets(domainId?: number) {
  return useQuery<Target[]>({
    queryKey: domainId !== undefined ? targetKeys.byDomain(domainId) : targetKeys.all,
    queryFn: () =>
      apiFetch(`/targets${domainId !== undefined ? `?domain_id=${domainId}` : ''}`),
  })
}

export function useCreateTarget() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: TargetCreate) =>
      apiFetch<Target>('/targets', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: targetKeys.all }),
  })
}

export function useDeleteTarget() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiFetch(`/targets/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: targetKeys.all }),
  })
}
