// ห่อ AWS Amplify Auth ไว้ที่นี่ ถ้าเปลี่ยน library ภายหลังก็แก้แค่ไฟล์นี้
import { Amplify } from 'aws-amplify';
import {
  signIn as aSignIn, signUp as aSignUp, confirmSignUp as aConfirm,
  signOut as aSignOut, fetchAuthSession, getCurrentUser,
  resetPassword as aReset, confirmResetPassword as aConfirmReset, resendSignUpCode as aResend,
} from 'aws-amplify/auth';
import { config } from '../config';

const MOCK_KEY = 'teamup_mock_user';

if (!config.useMock) {
  Amplify.configure({ Auth: { Cognito: {
    userPoolId: config.cognito.userPoolId,
    userPoolClientId: config.cognito.userPoolClientId,
    loginWith: { email: true },
  } } });
}

export async function signIn(email, password) {
  if (config.useMock) { localStorage.setItem(MOCK_KEY, email); return { done: true }; }
  const { isSignedIn, nextStep } = await aSignIn({ username: email, password });
  return { done: isSignedIn, nextStep: nextStep?.signInStep };
}

// ลงทะเบียน: Cognito ส่งรหัส 6 หลักไปที่อีเมล
export async function signUp({ email, password, name, studentId, major }) {
  if (config.useMock) return { needsConfirm: true };
  const { nextStep } = await aSignUp({
    username: email, password,
    options: { userAttributes: { email, name, 'custom:student_id': studentId, ...(major ? { 'custom:major': major } : {}) } },
  });
  return { needsConfirm: nextStep.signUpStep === 'CONFIRM_SIGN_UP' };
}

export async function confirmSignUp(email, code) {
  if (config.useMock) return true;
  await aConfirm({ username: email, confirmationCode: code });
  return true;
}

export async function signOut() {
  if (config.useMock) { localStorage.removeItem(MOCK_KEY); return; }
  await aSignOut();
}

export async function currentUser() {
  if (config.useMock) { const e = localStorage.getItem(MOCK_KEY); return e ? { email: e, groups: ['admin'] } : null; }
  try {
    await getCurrentUser();
    const { tokens } = await fetchAuthSession();
    const p = tokens?.idToken?.payload || {};
    return { email: p.email, name: p.name, groups: p['cognito:groups'] || [] };
  } catch { return null; }
}

// JWT ที่จะแนบไปกับทุก request ถึง FastAPI (Amplify refresh token ให้เองเมื่อหมดอายุ)
export async function getAccessToken() {
  if (config.useMock) return 'mock-token';
  try { const { tokens } = await fetchAuthSession(); return tokens?.accessToken?.toString() || null; }
  catch { return null; }
}

export async function resendCode(email) {
  if (config.useMock) return true;
  await aResend({ username: email });
  return true;
}

// ลืมรหัสผ่าน: Cognito ส่งรหัสไปที่อีเมล แล้วตั้งรหัสใหม่ด้วยรหัสนั้น
export async function forgotPassword(email) {
  if (config.useMock) return true;
  await aReset({ username: email });
  return true;
}
export async function confirmForgotPassword(email, code, newPassword) {
  if (config.useMock) return true;
  await aConfirmReset({ username: email, confirmationCode: code, newPassword });
  return true;
}

// "Keep me signed in": ถ้าไม่ติ๊ก จะ sign out เมื่อปิดเบราว์เซอร์
const REMEMBER = 'teamup_remember';
const SESSION = 'teamup_session_alive';
export function setRemember(remember) {
  try { localStorage.setItem(REMEMBER, remember ? '1' : '0'); sessionStorage.setItem(SESSION, '1'); } catch { /* ignore */ }
}
export async function enforceRemember() {
  try {
    if (localStorage.getItem(REMEMBER) === '0' && !sessionStorage.getItem(SESSION)) await signOut();
    sessionStorage.setItem(SESSION, '1');
  } catch { /* ignore */ }
}
