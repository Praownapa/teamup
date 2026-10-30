import { beforeEach, afterEach, it, expect, vi } from 'vitest';
vi.mock('../src/config', () => ({ config: { apiBaseUrl: '/api', useMock: false } }));
vi.mock('../src/auth/cognito', () => ({ getAccessToken: vi.fn(async () => 'test-token') }));
import { request, ApiError } from '../src/api/client';
import { api } from '../src/api/endpoints';
import * as mock from '../src/api/mock';
beforeEach(() => { vi.stubGlobal('window', { location: { href: '/' } }); vi.stubGlobal('fetch', vi.fn()); });
afterEach(() => vi.unstubAllGlobals());
it('keeps real and mock method names aligned', () => expect(Object.keys(api).sort()).toEqual(Object.keys(mock).sort()));
it('preserves authorization and JSON body', async () => {
  fetch.mockResolvedValue(new Response('{"ok":true}'));
  await request('/projects', { method: 'POST', body: { title: 'A' } });
  expect(fetch).toHaveBeenCalledWith('/api/projects', expect.objectContaining({ method: 'POST', body: '{"title":"A"}', headers: expect.objectContaining({ Authorization: 'Bearer test-token' }) }));
});
it('uses overview, not the obsolete stats URL', async () => {
  fetch.mockResolvedValue(new Response('{}'));
  await api.adminOverview('30d');
  expect(fetch.mock.calls[0][0]).toBe('/api/admin/overview?period=30d');
});
it('preserves member DELETE response', async () => {
  fetch.mockResolvedValue(new Response('{"id":1,"members":[]}'));
  expect(await api.removeMember(1, 2)).toEqual({ id: 1, members: [] });
  expect(fetch.mock.calls[0][0]).toBe('/api/projects/1/members/2');
  expect(fetch.mock.calls[0][1].method).toBe('DELETE');
});
it('returns null for 204', async () => { fetch.mockResolvedValue(new Response(null, { status: 204 })); expect(await request('/x')).toBeNull(); });
it.each([{ message: 'Denied' }, { detail: 'Denied' }])('shows backend errors', async (body) => {
  fetch.mockResolvedValue(new Response(JSON.stringify(body), { status: 403 }));
  await expect(request('/x')).rejects.toMatchObject({ status: 403, message: 'Denied' });
});
it('handles non-JSON failure', async () => { fetch.mockResolvedValue(new Response('proxy error', { status: 502 })); await expect(request('/x')).rejects.toBeInstanceOf(ApiError); });
it('redirects unauthorized requests', async () => { fetch.mockResolvedValue(new Response(null, { status: 401 })); await expect(request('/x')).rejects.toMatchObject({ status: 401 }); expect(window.location.href).toBe('/login'); });
it('propagates network failures', async () => { fetch.mockRejectedValue(new TypeError('Failed to fetch')); await expect(request('/x')).rejects.toThrow('Failed to fetch'); });
