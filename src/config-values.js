// Explicit runtime value > Vite build value > development default.
export function resolveConfig(rt = {}, env = {}) {
  const mockValue = String(rt.USE_MOCK ?? env.VITE_USE_MOCK ?? 'true').trim().toLowerCase();
  if (!['true', 'false'].includes(mockValue)) throw new Error('USE_MOCK must be true or false.');
  // cognito = real sign-in; local = real backend without Cognito (backend AUTH_MODE=dev; development only).
  const authValue = String(rt.AUTH_MODE ?? env.VITE_AUTH_MODE ?? 'cognito').trim().toLowerCase();
  if (!['cognito', 'local'].includes(authValue)) throw new Error('AUTH_MODE must be cognito or local.');
  return {
    apiBaseUrl: (rt.API_BASE_URL || env.VITE_API_BASE_URL || '/api').replace(/\/+$/, ''),
    useMock: mockValue === 'true',
    authMode: authValue,
    cognito: {
      userPoolId: rt.COGNITO_USER_POOL_ID || env.VITE_COGNITO_USER_POOL_ID || '',
      userPoolClientId: rt.COGNITO_CLIENT_ID || env.VITE_COGNITO_CLIENT_ID || '',
    },
  };
}
