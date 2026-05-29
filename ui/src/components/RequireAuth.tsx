import { Navigate, Outlet } from 'react-router-dom'
import { useMe } from '@/api/auth'
import { AuthContext } from '@/contexts/AuthContext'

export function RequireAuth() {
  const { data: user, isLoading, isError } = useMe()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen text-slate-400">
        Loading…
      </div>
    )
  }

  if (isError || !user) {
    return <Navigate to="/login" replace />
  }

  return (
    <AuthContext.Provider value={{ user, isAdmin: user.role === 'admin' }}>
      <Outlet />
    </AuthContext.Provider>
  )
}
