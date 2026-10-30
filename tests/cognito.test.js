import { it, expect, vi } from 'vitest';
vi.mock('../src/config', () => ({ config: { useMock: false, cognito: { userPoolId: 'ap-southeast-1_Test', userPoolClientId: 'testclient' } } }));
vi.mock('aws-amplify', () => ({ Amplify: { configure: vi.fn() } }));
vi.mock('aws-amplify/auth', () => ({ signUp: vi.fn(async () => ({ nextStep: { signUpStep: 'CONFIRM_SIGN_UP' } })), signIn: vi.fn(), confirmSignUp: vi.fn(), signOut: vi.fn(), fetchAuthSession: vi.fn(), getCurrentUser: vi.fn(), resetPassword: vi.fn(), confirmResetPassword: vi.fn(), resendSignUpCode: vi.fn() }));
import { signUp as awsSignUp } from 'aws-amplify/auth';
import { signUp } from '../src/auth/cognito';
it('sends both Cognito custom attributes unchanged', async () => {
  expect(await signUp({ email: 'test@example.test', password: 'Abcdefg1', name: 'Test', studentId: '0123456789', major: 'Computing' })).toEqual({ needsConfirm: true });
  expect(awsSignUp).toHaveBeenLastCalledWith(expect.objectContaining({ options: { userAttributes: { email: 'test@example.test', name: 'Test', 'custom:student_id': '0123456789', 'custom:major': 'Computing' } } }));
});
it('omits optional major when absent', async () => { await signUp({ email: 'test@example.test', studentId: '0123456789' }); expect(awsSignUp.mock.lastCall[0].options.userAttributes).not.toHaveProperty('custom:major'); });
