import { describe, it, expect } from 'vitest';
import { resolveConfig } from '../src/config-values';
import { validPassword } from '../src/utils/password';
import { errorMessage } from '../src/api/error-message';

describe('configuration precedence', () => {
  it('defaults to mock with /api', () => expect(resolveConfig()).toMatchObject({ useMock: true, apiBaseUrl: '/api' }));
  it('allows local env to turn mock off', () => expect(resolveConfig({}, { VITE_USE_MOCK: 'false' }).useMock).toBe(false));
  it('explicit runtime false overrides env true', () => expect(resolveConfig({ USE_MOCK: false }, { VITE_USE_MOCK: 'true' }).useMock).toBe(false));
  it('explicit runtime true overrides env false', () => expect(resolveConfig({ USE_MOCK: 'true' }, { VITE_USE_MOCK: 'false' }).useMock).toBe(true));
  it('normalizes and rejects invalid booleans', () => {
    expect(resolveConfig({ USE_MOCK: ' FALSE ' }).useMock).toBe(false);
    expect(() => resolveConfig({ USE_MOCK: 'flase' })).toThrow();
  });
  it('uses runtime URL and IDs, removes trailing slash', () => expect(resolveConfig({ API_BASE_URL: 'https://example.test/api/', COGNITO_USER_POOL_ID: 'runtime', COGNITO_CLIENT_ID: 'client' }, { VITE_API_BASE_URL: '/env' })).toMatchObject({ apiBaseUrl: 'https://example.test/api', cognito: { userPoolId: 'runtime', userPoolClientId: 'client' } }));
});
describe('error display', () => {
  it.each([
    [{ message: 'Message', detail: 'Detail' }, 'Message'],
    [{ detail: 'Detail' }, 'Detail'],
    [{ detail: [{ loc: ['body', 'name'], msg: 'Required' }] }, 'body.name: Required'],
    [{ detail: { arbitrary: true } }, 'Fallback'],
    [null, 'Fallback'],
  ])('returns readable strings', (data, expected) => expect(errorMessage(data, 'Fallback')).toBe(expected));
});
describe('password requirements', () => {
  it.each(['Aa1!', 'abcdefgh1', 'ABCDEFGH1', 'Abcdefgh!'])('rejects %s', (pw) => expect(validPassword(pw)).toBe(false));
  it('accepts the documented minimum', () => expect(validPassword('Abcdefg1')).toBe(true));
});
