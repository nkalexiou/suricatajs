import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { usePatchMe } from '@/api/auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export function Profile() {
  const { user } = useAuth()
  const patchMe = usePatchMe()
  const [name, setName] = useState(user?.name ?? '')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setSuccess('')
    if (password && password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }
    try {
      await patchMe.mutateAsync({
        name: name !== user?.name ? name : undefined,
        password: password || undefined,
      })
      setSuccess('Profile updated')
      setPassword('')
      setConfirmPassword('')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Update failed')
    }
  }

  return (
    <div>
      <h1 className="text-xl font-bold text-slate-100 mb-5">Profile</h1>
      <div className="max-w-md bg-[#161625] border border-slate-700 rounded-lg p-5">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="name" className="text-slate-400 text-xs uppercase tracking-wider">Name</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="bg-[#0f0f1a] border-slate-700 text-slate-200"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label className="text-slate-400 text-xs uppercase tracking-wider">Email</Label>
            <Input value={user?.email ?? ''} disabled className="bg-[#0f0f1a] border-slate-700 text-slate-500" />
          </div>
          <div className="border-t border-slate-700 my-1" />
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="password" className="text-slate-400 text-xs uppercase tracking-wider">New password</Label>
            <Input
              id="password"
              type="password"
              placeholder="Leave blank to keep current"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="bg-[#0f0f1a] border-slate-700 text-slate-200"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="confirm" className="text-slate-400 text-xs uppercase tracking-wider">Confirm password</Label>
            <Input
              id="confirm"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="bg-[#0f0f1a] border-slate-700 text-slate-200"
            />
          </div>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          {success && <p className="text-emerald-400 text-sm">{success}</p>}
          <Button type="submit" disabled={patchMe.isPending} className="bg-indigo-600 hover:bg-indigo-700">
            {patchMe.isPending ? 'Saving…' : 'Save changes'}
          </Button>
        </form>
      </div>
    </div>
  )
}
