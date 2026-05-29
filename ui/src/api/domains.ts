import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from './client'

export interface Domain {
  id: number
  domain: string
  created_at: string
}

export const domainKeys = {
  all: ['domains'] as const,
}

export function useDomains() {
  return useQuery<Domain[]>({
    queryKey: domainKeys.all,
    queryFn: () => apiFetch('/domains'),
  })
}

export function useCreateDomain() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { domain: string }) =>
      apiFetch<Domain>('/domains', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: domainKeys.all }),
  })
}

export function useDeleteDomain() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiFetch(`/domains/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: domainKeys.all }),
  })
}
