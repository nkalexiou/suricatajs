import { useState } from 'react'
import { useUsers, useCreateUser, useDeleteUser } from '@/api/users'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'

export function Users() {
  const { user: me } = useAuth()
  const { data: users = [], isLoading } = useUsers()
  const createUser = useCreateUser()
  const deleteUser = useDeleteUser()
  const [showDialog, setShowDialog] = useState(false)
  const [form, setForm] = useState({ email: '', name: '', password: '', role: 'operator' })
  const [error, setError] = useState('')

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await createUser.mutateAsync(form)
      setForm({ email: '', name: '', password: '', role: 'operator' })
      setShowDialog(false)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create user')
    }
  }

  async function handleDelete(id: number) {
    if (!confirm('Remove this user?')) return
    await deleteUser.mutateAsync(id)
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-xl font-bold text-slate-100">User management</h1>
        <Button size="sm" onClick={() => setShowDialog(true)} className="bg-indigo-600 hover:bg-indigo-700">
          + Invite user
        </Button>
      </div>

      {isLoading ? (
        <div className="text-slate-500 text-sm">Loading…</div>
      ) : (
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr>
              {['Name', 'Email', 'Role', 'Created', ''].map((h) => (
                <th key={h} className="text-left px-3 py-2 text-slate-500 text-[10px] uppercase tracking-wider font-medium border-b border-slate-700">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-t border-slate-800/50 hover:bg-[#161625]">
                <td className="px-3 py-2.5 text-slate-200">{u.name}</td>
                <td className="px-3 py-2.5 text-slate-400 text-xs">{u.email}</td>
                <td className="px-3 py-2.5">
                  {u.role === 'admin' ? (
                    <Badge className="bg-indigo-950 text-indigo-300 text-[10px]">Admin</Badge>
                  ) : (
                    <Badge className="bg-slate-800 text-slate-400 text-[10px]">Operator</Badge>
                  )}
                </td>
                <td className="px-3 py-2.5 text-slate-500 text-xs">{u.created_at}</td>
                <td className="px-3 py-2.5">
                  {u.id !== me?.id && (
                    <button
                      onClick={() => handleDelete(u.id)}
                      className="text-[11px] px-2 py-0.5 border border-slate-700 rounded text-slate-500 hover:border-red-800 hover:text-red-400 hover:bg-red-950 transition-colors"
                    >
                      Remove
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="bg-[#161625] border-slate-700">
          <DialogHeader>
            <DialogTitle className="text-slate-100">Invite user</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate} className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <Label className="text-slate-400 text-xs uppercase tracking-wider">Name</Label>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required className="bg-[#0f0f1a] border-slate-700 text-slate-200" />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label className="text-slate-400 text-xs uppercase tracking-wider">Email</Label>
              <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required className="bg-[#0f0f1a] border-slate-700 text-slate-200" />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label className="text-slate-400 text-xs uppercase tracking-wider">Password</Label>
              <Input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required className="bg-[#0f0f1a] border-slate-700 text-slate-200" />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label className="text-slate-400 text-xs uppercase tracking-wider">Role</Label>
              <select
                value={form.role}
                onChange={(e) => setForm({ ...form, role: e.target.value })}
                className="bg-[#0f0f1a] border border-slate-700 text-slate-200 rounded-md px-3 py-2 text-sm"
              >
                <option value="operator">Operator</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <DialogFooter>
              <Button variant="ghost" type="button" onClick={() => setShowDialog(false)}>Cancel</Button>
              <Button type="submit" disabled={createUser.isPending} className="bg-indigo-600 hover:bg-indigo-700">Create</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
