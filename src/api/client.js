import { errorMessage } from './error-message';
import { config } from '../config';
import { getAccessToken } from '../auth/cognito';

export class ApiError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

// fetch wrapper: แนบ Authorization: Bearer <JWT> ทุกครั้ง (backend จะ "Validate token" กับ Cognito)
export async function request(path, { method = 'GET', body, headers = {} } = {}) {
  const token = await getAccessToken();
  const res = await fetch(`${config.apiBaseUrl}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401) {
    window.location.href = '/login'; // token หมดอายุหรือไม่ถูกต้อง
    throw new ApiError(401, 'Unauthorized');
  }
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = errorMessage(await res.json(), msg); } catch { /* non-JSON error */ }
    msg ||= `Request failed (${res.status}).`;
    throw new ApiError(res.status, msg);
  }
  return res.status === 204 ? null : res.json();
}
