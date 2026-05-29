import { describe, it, expect, vi, afterEach } from 'vitest'
import { apiFetch, ApiError } from './client'

afterEach(() => vi.restoreAllMocks())

describe('apiFetch', () => {
  it('returns parsed JSON on success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: 1 }),
    }))
    const result = await apiFetch('/test')
    expect(result).toEqual({ id: 1 })
  })

  it('throws ApiError on non-ok response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      json: async () => ({ detail: 'Not authenticated' }),
    }))
    await expect(apiFetch('/test')).rejects.toThrow(ApiError)
  })

  it('includes credentials: include on every request', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({}),
    })
    vi.stubGlobal('fetch', mockFetch)
    await apiFetch('/test')
    expect(mockFetch.mock.calls[0][1]).toMatchObject({ credentials: 'include' })
  })

  it('returns undefined for 204 No Content', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 204 }))
    const result = await apiFetch('/test')
    expect(result).toBeUndefined()
  })
})
