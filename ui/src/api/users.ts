import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from './client'
import type { User } from './auth'

export const userKeys = {
  all: ['users'] as const,
}

export function useUsers() {
  return useQuery<User[]>({
    queryKey: userKeys.all,
    queryFn: () => apiFetch('/users'),
  })
}

export function useCreateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { email: string; name: string; password: string; role: string }) =>
      apiFetch<User>('/users', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: userKeys.all }),
  })
}

export function useDeleteUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => apiFetch(`/users/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: userKeys.all }),
  })
}
