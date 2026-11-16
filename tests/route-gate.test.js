import { describe, it, expect } from 'vitest';
import { routeGate } from '../src/auth/route-gate';

const user = { email: 'a@x.test', groups: [] };
const profile = { id: 1, name: 'A' };

describe('protected route gate', () => {
  it('waits while the session is being checked', () => expect(routeGate({ user: undefined })).toBe('loading'));
  it('sends signed-out visitors to login', () => expect(routeGate({ user: null })).toBe('login'));
  it('waits for the first profile load', () => expect(routeGate({ user, profile: null, profileLoading: true })).toBe('loading'));
  it('shows the error when the profile cannot load', () => expect(routeGate({ user, profile: null, profileError: new Error('x') })).toBe('error'));
  // A background refresh (after saving the profile, accepting an invitation...) must not unmount the page.
  it('keeps the page during a background profile refresh', () => expect(routeGate({ user, profile, profileLoading: true })).toBe('ok'));
  it('sends non-admins away from admin pages', () => {
    expect(routeGate({ user, profile, adminOnly: true, isAdmin: false })).toBe('home');
    expect(routeGate({ user, profile, adminOnly: true, isAdmin: true })).toBe('ok');
  });
});
