import { it, expect, vi, beforeEach } from 'vitest';

vi.mock('../src/config', () => ({ config: { useMock: false, authMode: 'local', cognito: { userPoolId: '', userPoolClientId: '' } } }));
vi.mock('aws-amplify', () => ({ Amplify: { configure: vi.fn() } }));
vi.mock('aws-amplify/auth', () => ({ signUp: vi.fn(), signIn: vi.fn(), confirmSignUp: vi.fn(), signOut: vi.fn(), fetchAuthSession: vi.fn(), getCurrentUser: vi.fn(), resetPassword: vi.fn(), confirmResetPassword: vi.fn(), resendSignUpCode: vi.fn() }));

import { Amplify } from 'aws-amplify';
import { signIn as awsSignIn, signUp as awsSignUp } from 'aws-amplify/auth';
import { buildDevToken, signUp, signIn, signOut, currentUser, getAccessToken, confirmSignUp } from '../src/auth/cognito';

beforeEach(() => {
  const store = new Map();
  vi.stubGlobal('localStorage', { getItem: (k) => store.get(k) ?? null, setItem: (k, v) => store.set(k, String(v)), removeItem: (k) => store.delete(k) });
});

it('encodes a dev token', () => {
  expect(buildDevToken({ email: 'a@x.test', name: 'A B', studentId: '0012345678', major: '' })).toBe('dev:email=a%40x.test&name=A+B&student_id=0012345678');
});

it('registers and signs in without Cognito', async () => {
  expect(await signUp({ email: 'New@Example.test', password: 'x', name: 'New Person', studentId: '0012345678', major: 'Data Science' })).toEqual({ needsConfirm: false });
  expect(await confirmSignUp('new@example.test', '000000')).toBe(true);
  expect(await signIn('new@example.test', 'anything')).toEqual({ done: true });
  expect(await getAccessToken()).toBe('dev:email=new%40example.test&name=New+Person&student_id=0012345678&major=Data+Science');
  expect(await currentUser()).toEqual({ email: 'new@example.test', name: 'New Person', groups: [] });
  expect(awsSignIn).not.toHaveBeenCalled();
  expect(awsSignUp).not.toHaveBeenCalled();
  expect(Amplify.configure).not.toHaveBeenCalled();
});

it('signs in a demo student who never registered here', async () => {
  await signIn(' John.Carter@student.uni.ac.th ', 'anything');
  expect(await getAccessToken()).toBe('dev:email=john.carter%40student.uni.ac.th');
});

it('signs out locally', async () => {
  await signIn('a@x.test', 'p');
  await signOut();
  expect(await currentUser()).toBeNull();
  expect(await getAccessToken()).toBeNull();
});
