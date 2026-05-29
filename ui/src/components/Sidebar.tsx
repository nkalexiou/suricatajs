import { NavLink } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { useOpenAlerts } from '@/api/alerts'
import { Badge } from '@/components/ui/badge'

interface NavItemProps {
  to: string
  label: string
}

function NavItem({ to, label }: NavItemProps) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        `flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
          isActive
            ? 'bg-indigo-900/60 text-indigo-300 font-medium'
            : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
        }`
      }
    >
      {label}
    </NavLink>
  )
}

export function Sidebar() {
  const { isAdmin } = useAuth()
  const { data: openAlerts } = useOpenAlerts()
  const openCount = openAlerts?.length ?? 0

  return (
    <aside className="w-52 shrink-0 bg-[#161625] border-r border-slate-800 flex flex-col p-3 gap-0.5">
      <div className="px-3 py-3 mb-1 text-xs font-bold tracking-widest uppercase text-indigo-500 border-b border-slate-800">
        suricatajs
      </div>
      <NavItem to="/" label="Domains" />
      <NavLink
        to="/alerts"
        className={({ isActive }) =>
          `flex items-center justify-between gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
            isActive
              ? 'bg-indigo-900/60 text-indigo-300 font-medium'
              : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
          }`
        }
      >
        <span>Alerts</span>
        {openCount > 0 && (
          <Badge variant="destructive" className="text-xs px-1.5 py-0">
            {openCount}
          </Badge>
        )}
      </NavLink>
      <NavItem to="/metrics" label="Metrics" />
      <div className="border-t border-slate-800 my-1" />
      <NavItem to="/profile" label="Profile" />
      {isAdmin && <NavItem to="/admin/users" label="Users" />}
    </aside>
  )
}
