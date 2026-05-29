import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from './client'

export interface User {
  id: number
  email: string
  name: string
  role: 'admin' | 'operator'
  created_at: string
}

export const authKeys = {
  me: ['auth', 'me'] as const,
}

export function useMe() {
  return useQuery<User>({
    queryKey: authKeys.me,
    queryFn: () => apiFetch('/auth/me'),
    retry: false,
    staleTime: 5 * 60 * 1000,
  })
}

export function useLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { email: string; password: string }) =>
      apiFetch<User>('/auth/login', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: (user) => qc.setQueryData(authKeys.me, user),
  })
}

export function useLogout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => apiFetch('/auth/logout', { method: 'POST' }),
    onSuccess: () => qc.setQueryData(authKeys.me, null),
  })
}

export function usePatchMe() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { name?: string; password?: string }) =>
      apiFetch<User>('/auth/me', { method: 'PATCH', body: JSON.stringify(body) }),
    onSuccess: (user) => qc.setQueryData(authKeys.me, user),
  })
}
