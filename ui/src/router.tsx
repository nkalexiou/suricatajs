import { createBrowserRouter } from 'react-router-dom'
import { RequireAuth } from '@/components/RequireAuth'
import { Layout } from '@/components/Layout'
import { Login } from '@/pages/Login'
import { Domains } from '@/pages/Domains'
import { DomainDetail } from '@/pages/DomainDetail'
import { Alerts } from '@/pages/Alerts'
import { Metrics } from '@/pages/Metrics'
import { Profile } from '@/pages/Profile'
import { Users } from '@/pages/admin/Users'

export const router = createBrowserRouter([
  { path: '/login', element: <Login /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <Layout />,
        children: [
          { path: '/', element: <Domains /> },
          { path: '/domains/:id', element: <DomainDetail /> },
          { path: '/alerts', element: <Alerts /> },
          { path: '/metrics', element: <Metrics /> },
          { path: '/profile', element: <Profile /> },
          { path: '/admin/users', element: <Users /> },
        ],
      },
    ],
  },
])
