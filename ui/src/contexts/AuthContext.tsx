import { createContext, useContext } from 'react'
import type { User } from '@/api/auth'

interface AuthContextValue {
  user: User | null | undefined
  isAdmin: boolean
}

export const AuthContext = createContext<AuthContextValue>({
  user: undefined,
  isAdmin: false,
})

export function useAuth() {
  return useContext(AuthContext)
}
