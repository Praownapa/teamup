import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import * as cognito from '../auth/cognito';
import { api } from '../api/endpoints';
import { Button } from '../components/ui';
import Icon from '../components/Icon';
import { ill } from '../components/art';
import { validPassword } from '../utils/password';
import { passwordScore } from '../utils/format';

export const MAJORS = ['Digital Engineering', 'Computer Engineering', 'Information Technology', 'Data Science', 'Industrial Engineering', 'Electrical Engineering', 'Mechanical Engineering', 'Business Technology', 'Other'];
const SKILL_SUGGESTIONS = ['React', 'JavaScript', 'Python', 'FastAPI', 'SQL', 'AWS', 'Docker', 'Figma', 'UI/UX Design', 'Flutter', 'Data Analysis', 'Machine Learning'];
const INTEREST_SUGGESTIONS = ['Web Development', 'Mobile Apps', 'AI / ML', 'Data Science', 'Sustainability', 'EdTech', 'HealthTech', 'IoT', 'Product Design', 'Startups'];

function Shell({ title, art = 'login', children }) {
  return (
    <div className="auth">
      <div className="auth-hero">
        <div className="logo" style={{ padding: 0 }}><div className="logo-mark"><Icon name="graduation" size={38} /></div>TeamUp</div>
        <div className="col" style={{ gap: 16 }}>
          <h1>{title}</h1>
          <p style={{ fontSize: 16, lineHeight: 1.6, color: '#e0f2fe', maxWidth: 460 }}>
            Find projects that fit your skills and teammates who fill the gaps — for course projects, competitions and beyond.
          </p>
          <div className="col" style={{ gap: 10, color: '#fff', fontSize: 14 }}>
            {[['sparkle', 'Skill-based project & teammate matching'], ['inbox', 'Join requests and invitations in one place'], ['bell', 'In-app and email notifications']].map(([i, t]) => (
              <div key={t} className="row" style={{ gap: 10 }}><span className="auth-bullet"><Icon name={i} size={15} /></span>{t}</div>
            ))}
          </div>
        </div>
        <img className="auth-art" src={ill(art)} alt="" />
      </div>
      <div className="auth-form">{children}</div>
    </div>
  );
}

const linkStyle = { color: 'var(--brand-600)', fontWeight: 600 };
const field = (label, input, hint) => <div className="field"><label className="lbl">{label}</label>{input}{hint}</div>;

export function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [form, setForm] = useState({ email: loc.state?.email || '', password: '', remember: true });
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault(); setErr(''); setBusy(true);
    try {
      const r = await login(form.email, form.password, form.remember);
      if (r.done) nav(loc.state?.from || '/', { replace: true });
      else if (r.nextStep === 'CONFIRM_SIGN_UP') nav('/confirm', { state: { email: form.email } });
      else setErr(`Additional sign-in step required (${r.nextStep || 'unknown'}). Contact your administrator.`);
    } catch (e2) { setErr(e2.message); } finally { setBusy(false); }
  }

  return (
    <Shell title={<>Build better teams,<br />faster.</>}>
      <form onSubmit={submit}>
        <div><div className="h1">Welcome back</div><div className="sub">Log in with your university account to continue.</div></div>
        {loc.state?.notice && <div className="alert"><Icon name="checkCircle" size={18} />{loc.state.notice}</div>}
        {err && <div className="err">{err}</div>}
        {field('University email', <input className="input" type="email" required autoComplete="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="you@student.uni.ac.th" />)}
        <div className="field">
          <div className="row between"><label className="lbl">Password</label><Link to="/forgot" className="small" style={linkStyle}>Forgot password?</Link></div>
          <input className="input" type="password" required autoComplete="current-password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        </div>
        <label className="cbx"><input type="checkbox" checked={form.remember} onChange={(e) => setForm({ ...form, remember: e.target.checked })} />Keep me signed in</label>
        <Button block disabled={busy}>{busy ? 'Logging in…' : 'Log in'}</Button>
        <div className="xs muted" style={{ textAlign: 'center' }}>Secured by AWS Cognito</div>
        <div className="small muted" style={{ textAlign: 'center' }}>Don’t have an account? <Link to="/register" style={linkStyle}>Create one</Link></div>
      </form>
    </Shell>
  );
}

export function Register() {
  const nav = useNavigate();
  const [f, setF] = useState({ first: '', last: '', studentId: '', major: MAJORS[0], email: '', password: '', terms: false });
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });
  const score = passwordScore(f.password);
  const strength = ['Too weak', 'Weak', 'Fair', 'Good', 'Strong'][score];
  const strengthColor = ['#e2e8f0', '#ef4444', '#f59e0b', '#3b82f6', '#16a34a'][score];

  async function submit(e) {
    e.preventDefault(); setErr('');
    if (!validPassword(f.password)) return setErr('Use at least 8 characters with upper & lower case letters and a number.');
    if (!f.terms) return setErr('Please accept the Terms and Privacy Policy.');
    setBusy(true);
    try {
      const result = await cognito.signUp({ email: f.email, password: f.password, name: `${f.first} ${f.last}`.trim(), studentId: f.studentId, major: f.major });
      nav(result.needsConfirm ? '/confirm' : '/login', { state: { email: f.email, from: '/welcome' } });
    } catch (e2) { setErr(e2.message); } finally { setBusy(false); }
  }

  return (
    <Shell art="register" title={<>Your next team<br />starts here.</>}>
      <form onSubmit={submit}>
        <div className="steps"><b>Step 1 of 2</b>Account details → Skills & interests</div>
        <div><div className="h1">Create your account</div><div className="sub">Use your university email so teammates can trust who you are.</div></div>
        {err && <div className="err">{err}</div>}
        <div className="grid g2" style={{ gap: 14 }}>
          {field('First name', <input className="input" required value={f.first} onChange={set('first')} autoComplete="given-name" />)}
          {field('Last name', <input className="input" required value={f.last} onChange={set('last')} autoComplete="family-name" />)}
          {field('Student ID', <input className="input" required inputMode="numeric" pattern="\d{10}" title="10-digit student ID" value={f.studentId} onChange={set('studentId')} placeholder="6600123456" />)}
          {field('Major', <select className="select" value={f.major} onChange={set('major')}>{MAJORS.map((m) => <option key={m}>{m}</option>)}</select>)}
        </div>
        {field('University email', <input className="input" type="email" required value={f.email} onChange={set('email')} autoComplete="email" />)}
        {field('Password', <input className="input" type="password" required value={f.password} onChange={set('password')} autoComplete="new-password" />,
          f.password && <div className="strength">{[1, 2, 3, 4].map((i) => <i key={i} style={{ background: i <= score ? strengthColor : undefined }} />)}<span className="xs" style={{ color: strengthColor, fontWeight: 600, minWidth: 56, textAlign: 'right' }}>{strength}</span></div>)}
        <label className="cbx"><input type="checkbox" checked={f.terms} onChange={set('terms')} />I agree to the&nbsp;<a href="#terms" style={linkStyle}>Terms</a>&nbsp;and&nbsp;<a href="#privacy" style={linkStyle}>Privacy Policy</a></label>
        <Button block disabled={busy}>{busy ? 'Creating…' : <>Continue <Icon name="send" size={16} /></>}</Button>
        <div className="alert"><Icon name="mail" size={18} />We’ll send a 6-digit verification code to your email to confirm your account.</div>
        <div className="small muted" style={{ textAlign: 'center' }}>Already have an account? <Link to="/login" style={linkStyle}>Log in</Link></div>
      </form>
    </Shell>
  );
}

export function Confirm() {
  const loc = useLocation();
  const nav = useNavigate();
  const [code, setCode] = useState('');
  const [err, setErr] = useState('');
  const [info, setInfo] = useState('');
  const email = loc.state?.email || '';
  async function submit(e) {
    e.preventDefault(); setErr('');
    try {
      await cognito.confirmSignUp(email, code);
      // ยืนยันแล้ว -> login แล้วไปขั้นที่ 2 (ทักษะและความสนใจ)
      nav('/login', { state: { email, from: '/welcome', notice: 'Email verified! Log in to finish setting up your profile.' } });
    } catch (e2) { setErr(e2.message); }
  }
  return (
    <Shell title={<>Almost<br />there.</>}>
      <form onSubmit={submit}>
        <div><div className="h1">Verify your email</div><div className="sub">We sent a 6-digit code to {email || 'your email'}.</div></div>
        {err && <div className="err">{err}</div>}
        {info && <div className="alert">{info}</div>}
        <input className="input" inputMode="numeric" maxLength={6} required value={code} onChange={(e) => setCode(e.target.value)} placeholder="123456" style={{ letterSpacing: 8, fontSize: 20, textAlign: 'center' }} />
        <Button block>Verify</Button>
        <button type="button" className="small" style={linkStyle} onClick={async () => { setErr(''); try { await cognito.resendCode(email); setInfo('A new code has been sent.'); } catch (e) { setErr(e.message); } }}>Resend code</button>
      </form>
    </Shell>
  );
}

export function ForgotPassword() {
  const nav = useNavigate();
  const [step, setStep] = useState(1);
  const [f, setF] = useState({ email: '', code: '', password: '' });
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  async function submit(e) {
    e.preventDefault(); setErr(''); setBusy(true);
    try {
      if (step === 1) { await cognito.forgotPassword(f.email); setStep(2); }
      else {
        if (!validPassword(f.password)) throw new Error('Use at least 8 characters with upper & lower case letters and a number.');
        await cognito.confirmForgotPassword(f.email, f.code, f.password);
        nav('/login', { state: { email: f.email, notice: 'Password updated. Log in with your new password.' } });
      }
    } catch (e2) { setErr(e2.message); } finally { setBusy(false); }
  }
  return (
    <Shell title={<>Reset your<br />password.</>}>
      <form onSubmit={submit}>
        <div><div className="h1">Forgot password</div><div className="sub">{step === 1 ? 'Enter your university email and we’ll send you a reset code.' : `Enter the code sent to ${f.email} and choose a new password.`}</div></div>
        {err && <div className="err">{err}</div>}
        {step === 1
          ? field('University email', <input className="input" type="email" required value={f.email} onChange={set('email')} />)
          : <>
            {field('Reset code', <input className="input" inputMode="numeric" maxLength={6} required value={f.code} onChange={set('code')} />)}
            {field('New password', <input className="input" type="password" required value={f.password} onChange={set('password')} autoComplete="new-password" />)}
          </>}
        <Button block disabled={busy}>{busy ? 'Please wait…' : step === 1 ? 'Send reset code' : 'Update password'}</Button>
        <div className="small muted" style={{ textAlign: 'center' }}><Link to="/login" style={linkStyle}>Back to log in</Link></div>
      </form>
    </Shell>
  );
}

// สมัครขั้นที่ 2: เลือกทักษะและความสนใจ (ใช้คำนวณ match)
export function Welcome() {
  const nav = useNavigate();
  const { profile, refreshProfile } = useAuth();
  const [skills, setSkills] = useState([]);
  const [interests, setInterests] = useState([]);
  // โปรไฟล์โหลดเสร็จทีหลัง: เติมทักษะ/ความสนใจเดิมให้ครั้งเดียว
  const [loaded, setLoaded] = useState(false);
  useEffect(() => {
    if (profile && !loaded) { setSkills(profile.skills.map((s) => s.name)); setInterests(profile.interests || []); setLoaded(true); }
  }, [profile, loaded]);
  const [custom, setCustom] = useState('');
  const [busy, setBusy] = useState(false);
  const toggle = (list, setList, v) => setList(list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);
  const allSkills = [...new Set([...SKILL_SUGGESTIONS, ...skills])];

  const [err, setErr] = useState('');
  async function finish() {
    setBusy(true); setErr('');
    try {
    const old = Object.fromEntries((profile?.skills || []).map((s) => [s.name, s.level]));
    await api.updateMe({ skills: skills.map((name) => ({ name, level: old[name] || 'Beginner' })), interests });
    await refreshProfile(); nav('/');
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  }

  return (
    <Shell art="register" title={<>Tell us what<br />you’re good at.</>}>
      <div className="col" style={{ width: 460, maxWidth: '100%', gap: 20 }}>
        {err && <div className="err">{err}</div>}
        <div className="steps"><b>Step 2 of 2</b>Account details → Skills & interests</div>
        <div><div className="h1">Skills & interests</div><div className="sub">We use these to match you with projects and teammates. You can change them later in My Profile.</div></div>
        <div className="col"><div className="lbl">Your skills ({skills.length})</div>
          <div className="chips">{allSkills.map((s) => <button type="button" key={s} className={`chip ${skills.includes(s) ? 'brand' : 'out'}`} onClick={() => toggle(skills, setSkills, s)}>{skills.includes(s) && <Icon name="check" size={13} stroke={2.4} />}{s}</button>)}</div>
          <div className="row"><input className="input" style={{ height: 38 }} placeholder="Add another skill" value={custom} onChange={(e) => setCustom(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && custom.trim()) { e.preventDefault(); setSkills([...new Set([...skills, custom.trim()])]); setCustom(''); } }} />
            <Button type="button" variant="ghost" size="sm" onClick={() => { if (custom.trim()) { setSkills([...new Set([...skills, custom.trim()])]); setCustom(''); } }}>Add</Button></div>
        </div>
        <div className="col"><div className="lbl">Interests</div>
          <div className="chips">{INTEREST_SUGGESTIONS.map((s) => <button type="button" key={s} className={`chip ${interests.includes(s) ? 'brand' : 'out'}`} onClick={() => toggle(interests, setInterests, s)}>{s}</button>)}</div>
        </div>
        <Button block disabled={busy || skills.length === 0} onClick={finish}>{busy ? 'Saving…' : 'Finish & go to dashboard'}</Button>
        {skills.length === 0 && <div className="hint" style={{ textAlign: 'center' }}>Pick at least one skill.</div>}
        <button type="button" className="small muted" onClick={() => nav('/')}>Skip for now</button>
      </div>
    </Shell>
  );
}
