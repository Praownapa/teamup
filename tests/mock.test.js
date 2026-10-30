import { it, expect, vi, afterEach } from 'vitest';
import * as api from '../src/api/mock';
afterEach(() => vi.useRealTimers());
it('creates a project, edits recruitment and returns matching shapes', async () => {
  vi.useFakeTimers();
  const pending = api.createProject({ title: 'Regression', category: 'Research', description: 'Test', max_size: 2, skills: ['React'], owner_role: 'Lead', roles: [{ name: 'Developer', spots: 1 }] });
  await vi.runAllTimersAsync(); const project = await pending;
  expect(project).toMatchObject({ title: 'Regression', my_role: 'owner', open_roles: ['Developer'], skills: [['React', true]] });
  const update = api.updateProject(project.id, { accepting: false }); await vi.runAllTimersAsync(); expect((await update).status).toBe('closed');
});
it('accepting the last slot rejects remaining pending requests', async () => {
  vi.useFakeTimers();
  const response = api.respondRequest(1, true); await vi.runAllTimersAsync(); expect((await response).status).toBe('accepted');
  const pending = api.listRequests(); await vi.runAllTimersAsync(); const list = await pending;
  expect(list.find((r) => r.id === 2).status).toBe('rejected');
});
