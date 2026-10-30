import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api/endpoints';
import { useAsync } from '../utils/useAsync';
import { timeAgo, isToday, fmtDate } from '../utils/format';
import { useAuth } from '../auth/AuthContext';
import { AsyncView, Avatar, Button, Chip, Empty, PageHeader, Section, Segmented, Status, Toggle } from '../components/ui';
import Icon from '../components/Icon';
import { MAJORS } from './Auth';

const LEVELS = ['Beginner', 'Intermediate', 'Advanced'];
const POPULAR = ['AWS', 'FastAPI', 'Docker', 'Node.js', 'Flutter', 'TypeScript', 'Machine Learning'];
const NOTIFY = [['invitations', 'Email for invitations'], ['requests', 'Email for request updates'], ['team', 'Email for team updates'], ['digest', 'Weekly project digest']];

/* ======================= 10 · My profile ======================= */
export function Profile() {
  const st = useAsync(() => api.getMe());
  return <AsyncView state={st}>{(me) => <ProfileForm me={me} />}</AsyncView>;
}

function ProfileForm({ me }) {
  const { refreshProfile } = useAuth();
  const [f, setF] = useState(me);
  const [skill, setSkill] = useState('');
  const [interest, setInterest] = useState('');
  const [state, setState] = useState('idle'); // idle | dirty | saving | saved
  const set = (k, v) => { setState('dirty'); setF((x) => ({ ...x, [k]: v })); };
  const addSkill = (name) => { const n = name.trim(); if (n && !f.skills.some((s) => s.name.toLowerCase() === n.toLowerCase())) set('skills', [...f.skills, { name: n, level: 'Beginner' }]); setSkill(''); };
  const addInterest = () => { const n = interest.trim(); if (n && !f.interests.includes(n)) set('interests', [...f.interests, n]); setInterest(''); };
  const [err, setErr] = useState('');
  async function save() {
    setState('saving'); setErr('');
    try {
    const { name, major, year, bio, portfolio, skills, interests, notify, open_to_projects } = f;
    await api.updateMe({ name, major, year: Number(year), bio, portfolio, skills, interests, notify, open_to_projects });
    await refreshProfile(); setState('saved');
    } catch (e) { setErr(e.message); setState('dirty'); }
  }

  return (
    <>
      <PageHeader eyebrow="Account" art="profile" tone="violet" title="My profile" subtitle="Your skills and interests power your project matches."
        actions={<><Link className="btn secondary" to={`/students/${f.id}`}><Icon name="user" size={16} />View public profile</Link>
          <Button disabled={state === 'saving' || state === 'idle' || state === 'saved'} onClick={save}>{state === 'saving' ? 'Saving…' : state === 'saved' ? <><Icon name="check" size={16} /> Saved</> : 'Save changes'}</Button></>} />
      {err && <div className="err">{err}</div>}
      {state === 'dirty' && <div className="alert"><Icon name="alert" size={18} />You have unsaved changes.</div>}
      <div className="row" style={{ alignItems: 'flex-start', gap: 22 }}>
        <div className="col" style={{ width: 320, flexShrink: 0, gap: 22 }}>
          <div className="card" style={{ alignItems: 'center', textAlign: 'center' }}>
            <Avatar name={f.name} size={104} />
            <div><div className="h2">{f.name}</div><div className="small muted">{f.major} · Year {f.year}</div><div className="xs muted">{f.student_id} · {f.email}</div></div>
            <button type="button" onClick={() => set('open_to_projects', !f.open_to_projects)}><Status value={f.open_to_projects ? 'accepted' : 'closed'} label={f.open_to_projects ? 'Open to projects' : 'Not looking'} /></button>
            <div className="xs muted">{f.open_to_projects ? 'Open to projects — owners can invite you' : 'Not looking — hidden from recommendations'}</div>
            <div className="divider" style={{ width: '100%' }} />
            <div className="row" style={{ width: '100%', justifyContent: 'space-around' }}>
              {[['Teams', me.stats?.teams], ['Projects', me.stats?.projects], ['Skills', f.skills.length]].map(([l, v]) => <div key={l} className="col" style={{ gap: 0, alignItems: 'center' }}><b style={{ fontSize: 18 }}>{v ?? 0}</b><span className="xs muted">{l}</span></div>)}
            </div>
          </div>
          <Section title="Notification preferences" style={{ gap: 12 }}>
            {NOTIFY.map(([k, label]) => (
              <div key={k} className="row between small"><span>{label}</span><Toggle checked={!!f.notify?.[k]} onChange={(v) => set('notify', { ...f.notify, [k]: v })} label={label} /></div>))}
            <div className="xs muted">Emails are sent through AWS SES. In-app notifications are always on.</div>
          </Section>
        </div>
        <div className="col" style={{ flex: 1, gap: 22, minWidth: 0 }}>
          <Section title="Basic information">
            <div className="grid g3" style={{ gap: 14 }}>
              <div className="field"><label className="lbl">Display name</label><input className="input" value={f.name} onChange={(e) => set('name', e.target.value)} /></div>
              <div className="field"><label className="lbl">Major</label><select className="select" value={f.major} onChange={(e) => set('major', e.target.value)}>{[...new Set([f.major, ...MAJORS])].map((m) => <option key={m}>{m}</option>)}</select></div>
              <div className="field"><label className="lbl">Year</label><select className="select" value={f.year} onChange={(e) => set('year', e.target.value)}>{[1, 2, 3, 4, 5, 6].map((y) => <option key={y}>{y}</option>)}</select></div>
            </div>
            <div className="field"><label className="lbl">Bio</label><textarea className="textarea" style={{ minHeight: 90 }} maxLength={400} value={f.bio || ''} onChange={(e) => set('bio', e.target.value)} placeholder="What do you like to build?" /><span className="hint">{(f.bio || '').length} / 400</span></div>
            <div className="field"><label className="lbl">Portfolio / GitHub</label><input className="input" value={f.portfolio || ''} onChange={(e) => set('portfolio', e.target.value)} placeholder="github.com/yourname" /></div>
          </Section>
          <Section title="Skills" right={<span className="xs muted">Used for matching · {f.skills.length} skills</span>}>
            <div className="row"><input className="input" placeholder="Add a skill, e.g. Docker" value={skill} onChange={(e) => setSkill(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addSkill(skill); } }} />
              <Button variant="ghost" onClick={() => addSkill(skill)}>Add</Button></div>
            {f.skills.length === 0 && <div className="small muted">No skills yet — add a few so we can match you with projects.</div>}
            {f.skills.map((s, i) => (
              <div key={s.name} className="row wrap">
                <span style={{ width: 150, fontWeight: 500 }}>{s.name}</span>
                <Segmented small options={LEVELS.map((l) => [l, l])} value={s.level} onChange={(lv) => set('skills', f.skills.map((x, j) => (j === i ? { ...x, level: lv } : x)))} />
                <button type="button" className="muted" style={{ marginLeft: 'auto' }} aria-label={`Remove ${s.name}`} onClick={() => set('skills', f.skills.filter((_, j) => j !== i))}><Icon name="x" size={18} /></button>
              </div>))}
            <div className="col"><div className="xs muted">Popular skills in open projects</div>
              <div className="chips">{POPULAR.filter((p) => !f.skills.some((s) => s.name === p)).map((p) => <button type="button" key={p} className="chip out" onClick={() => addSkill(p)}>+ {p}</button>)}</div></div>
          </Section>
          <Section title="Interests">
            <div className="chips">
              {f.interests.map((t) => <button type="button" key={t} className="chip brand" onClick={() => set('interests', f.interests.filter((x) => x !== t))}>{t} <Icon name="x" size={12} /></button>)}
              <input className="input" style={{ height: 28, width: 160, fontSize: 12 }} placeholder="+ Add interest" value={interest} onChange={(e) => setInterest(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addInterest(); } }} onBlur={addInterest} />
            </div>
          </Section>
        </div>
      </div>
    </>
  );
}

/* ======================= 11 · Notifications ======================= */
const NFILTERS = [['all', 'All'], ['unread', 'Unread'], ['request', 'Requests'], ['invite', 'Invitations'], ['team', 'Team updates']];
const NICON = { request: 'inbox', invite: 'mail', accepted: 'checkCircle', declined: 'xCircle', team: 'users', match: 'sparkle' };
export function Notifications() {
  const st = useAsync(() => api.listNotifications());
  const { refreshCounts, refreshProfile } = useAuth();
  const nav = useNavigate();
  const [filter, setFilter] = useState('all');
  const [handled, setHandled] = useState({});
  const [err, setErr] = useState('');
  const after = async () => { await st.reload(); refreshCounts(); };

  return (
    <>
      <PageHeader eyebrow="Updates" art="notifications" tone="rose" title="Notifications" subtitle="Important updates are also sent to your email."
        actions={<Button variant="secondary" onClick={async () => { setErr(''); try { await api.markAllRead(); await after(); } catch (e) { setErr(e.message); } }}><Icon name="check" size={16} /> Mark all as read</Button>} />
      {err && <div className="err">{err}</div>}
      <div className="row" style={{ alignItems: 'flex-start', gap: 22 }}>
        <div className="col" style={{ flex: 1, gap: 14, minWidth: 0 }}>
          <AsyncView state={st}>{(all) => {
            const unread = all.filter((n) => n.unread).length;
            const list = all.filter((n) => filter === 'all' || (filter === 'unread' ? n.unread : filter === 'team' ? ['team', 'accepted', 'declined'].includes(n.kind) : n.kind === filter));
            const groups = [['TODAY', list.filter((n) => isToday(n.created_at))], ['EARLIER', list.filter((n) => !isToday(n.created_at))]].filter(([, l]) => l.length);
            return (
              <>
                <Segmented options={NFILTERS.map(([k, l]) => [k, k === 'unread' ? `Unread · ${unread}` : l])} value={filter} onChange={setFilter} />
                {list.length === 0 ? <Empty title="You’re all caught up">No notifications here.</Empty> : (
                  <div className="card" style={{ padding: 0, gap: 0, overflow: 'hidden' }}>
                    {groups.map(([label, items]) => (
                      <div key={label}>
                        <div className="xs muted" style={{ padding: '10px 20px', background: '#f8fafc', fontWeight: 600, letterSpacing: '.6px' }}>{label}</div>
                        {items.map((n) => {
                          const done = handled[n.id];
                          const act = async (accept) => {
                            setErr('');
                            try { await api.respondRequest(n.request_id, accept); setHandled({ ...handled, [n.id]: accept ? 'Accepted' : 'Declined' }); if (accept) refreshProfile(); after(); }
                            catch (e) { setErr(e.message); }
                          };
                          return (
                            <div key={n.id} className="row" style={{ padding: '16px 20px', borderTop: '1px solid var(--line)', background: n.unread ? 'var(--brand-50)' : '#fff', alignItems: 'flex-start', cursor: 'pointer' }}
                              onClick={async () => { if (n.unread) { try { await api.markRead(n.id); await after(); } catch (e) { setErr(e.message); } } }}>
                              <div className={`n-ic ${n.kind}`}><Icon name={NICON[n.kind] || 'bell'} size={19} /></div>
                              <div className="col" style={{ flex: 1, gap: 4 }}>
                                <div className="small" style={{ lineHeight: 1.5 }}>{n.text}</div>
                                <div className="xs muted">{timeAgo(n.created_at)}</div>
                                {n.request_id && (done ? <span className="xs" style={{ fontWeight: 600, color: done === 'Accepted' ? 'var(--ok)' : 'var(--bad)' }}>{done}</span>
                                  : n.unread && <div className="row" style={{ marginTop: 6 }} onClick={(e) => e.stopPropagation()}>
                                    <Button variant="secondary" size="sm" onClick={() => act(false)}>Decline</Button>
                                    <Button size="sm" onClick={() => act(true)}>{n.kind === 'invite' ? 'Accept invite' : 'Accept'}</Button>
                                    <Button variant="ghost" size="sm" onClick={() => nav(n.kind === 'invite' ? '/requests?tab=invitation' : '/requests')}>Details</Button></div>)}
                              </div>
                              {n.unread && <span className="udot" title="Unread" />}
                            </div>);
                        })}
                      </div>))}
                  </div>)}
              </>
            );
          }}</AsyncView>
        </div>
        <div className="card" style={{ width: 300, flexShrink: 0 }}>
          <div className="row"><div className="stat-ic" style={{ background: 'var(--brand-50)', color: 'var(--brand-600)' }}><Icon name="mail" /></div><div className="h3">Email notifications</div></div>
          <div className="small muted" style={{ lineHeight: 1.5 }}>We email you for invitations, join request updates and team changes.</div>
          <Link className="btn secondary sm" to="/profile">Manage preferences</Link>
        </div>
      </div>
    </>
  );
}

/* ======================= 12 · Admin panel ======================= */
export function Admin() {
  const [period, setPeriod] = useState('30d');
  const st = useAsync(() => api.adminOverview(period), [period]);
  const [q, setQ] = useState('');
  const [newCat, setNewCat] = useState('');
  const [err, setErr] = useState('');
  const run = async (fn) => { setErr(''); try { await fn(); await st.reload(); } catch (e) { setErr(e.message); } };

  function exportCsv(d) {
    const rows = [['Metric', 'Value'], ['Registered students', d.stats.students], ['Projects created', d.stats.projects], ['Teams formed', d.stats.teams], ['Open reports', d.stats.reports],
      [], ['Week', 'Join requests', 'New projects'], ...d.activity.map((a) => [a.week, a.requests, a.projects])];
    const url = URL.createObjectURL(new Blob([rows.map((r) => r.join(',')).join('\n')], { type: 'text/csv' }));
    const a = document.createElement('a'); a.href = url; a.download = `teamup-report-${period}.csv`; a.click(); URL.revokeObjectURL(url);
  }

  return (
    <AsyncView state={st}>{(d) => {
      const max = Math.max(1, ...d.activity.flatMap((a) => [a.requests, a.projects]));
      const users = d.users.filter((u) => !q || `${u.name} ${u.email} ${u.student_id}`.toLowerCase().includes(q.toLowerCase()));
      return (
        <>
          {err && <div className="err">{err}</div>}
          <PageHeader eyebrow="Administrator" art="admin" tone="slate" title="Admin panel" subtitle="Monitor platform usage, moderate content and manage categories."
            actions={<><Segmented small options={[['7d', '7 days'], ['30d', '30 days'], ['semester', 'Semester']]} value={period} onChange={setPeriod} />
              <Button variant="secondary" size="sm" onClick={() => exportCsv(d)}><Icon name="send" size={14} />Export report</Button></>} />
          <div className="grid g4">
            {[['students', 'Registered students', 'users'], ['projects', 'Projects created', 'folder'], ['teams', 'Teams formed', 'checkCircle'], ['reports', 'Open reports', 'alert']].map(([k, l, i]) => (
              <div key={k} className="stat-big" style={{ alignItems: 'flex-start', textAlign: 'left' }}>
                <div className="row between" style={{ width: '100%' }}><div className="ico" style={{ width: 40, height: 40 }}><Icon name={i} size={20} /></div>
                  {d.stats.deltas[k] != null ? <span className="xs" style={{ color: 'var(--ok)', fontWeight: 600 }}>+{d.stats.deltas[k]}</span> : d.stats.reports > 0 && <Status value="rejected" label="Review" />}</div>
                <div className="stat-v">{d.stats[k].toLocaleString()}</div><div className="small muted">{l}</div></div>))}
          </div>
          <div className="row" style={{ alignItems: 'stretch', gap: 22 }}>
            <Section title="Activity" right={<div className="row xs muted"><span className="legend" style={{ background: 'var(--brand-600)' }} />Join requests<span className="legend" style={{ background: '#a5b4fc' }} />New projects</div>} style={{ flex: 1, minWidth: 0 }}>
              <div className="chart">{d.activity.map((a) => (
                <div key={a.week} className="wk" title={`${a.week}: ${a.requests} requests, ${a.projects} projects`}>
                  <span style={{ height: `${(100 * a.requests) / max}%`, background: 'var(--brand-600)' }} /><span style={{ height: `${(100 * a.projects) / max}%`, background: '#a5b4fc' }} /></div>))}</div>
              <div className="row xs muted" style={{ gap: 12 }}>{d.activity.map((a) => <span key={a.week} style={{ flex: 1, textAlign: 'center' }}>{a.week}</span>)}</div>
            </Section>
            <Section title="Categories" style={{ width: 340, flexShrink: 0 }}>
              <form className="row" onSubmit={(e) => { e.preventDefault(); if (newCat.trim()) run(async () => { await api.adminAddCategory(newCat.trim()); setNewCat(''); }); }}>
                <input className="input" style={{ height: 36 }} placeholder="New category" value={newCat} onChange={(e) => setNewCat(e.target.value)} /><Button size="sm" variant="ghost"><Icon name="plus" size={14} />Add</Button></form>
              {d.categories.map((c) => (
                <div key={c.name} className="row"><div className="stat-ic" style={{ width: 32, height: 32, background: '#f1f5f9' }}><Icon name="folder" size={15} /></div>
                  <span className="small" style={{ flex: 1, fontWeight: 500 }}>{c.name}</span><span className="xs muted">{c.count} projects</span>
                  <button className="muted" aria-label={`Delete ${c.name}`} onClick={() => window.confirm(`Delete category “${c.name}”?`) && run(() => api.adminDeleteCategory(c.name))}><Icon name="x" size={15} /></button></div>))}
            </Section>
          </div>
          <Section title="Reported projects" right={<Status value={d.reports.length ? 'rejected' : 'accepted'} label={`${d.reports.length} open`} />} style={{ padding: 0, gap: 0 }}>
            {d.reports.length === 0 ? <div className="empty-row">No open reports. 🎉</div> : (
              <div className="table-wrap"><table><thead><tr><th>PROJECT</th><th>REASON</th><th>REPORTED BY</th><th>DATE</th><th>ACTIONS</th></tr></thead><tbody>
                {d.reports.map((r) => (
                  <tr key={r.id}><td><div style={{ fontWeight: 600 }}>{r.project}</div><div className="xs muted">by {r.owner}</div></td>
                    <td><Chip kind="miss">{r.reason}</Chip></td><td className="muted">{r.reporters} student{r.reporters > 1 ? 's' : ''}</td><td className="muted">{fmtDate(r.created_at)}</td>
                    <td><div className="row" style={{ gap: 6 }}><Button variant="danger" size="sm" onClick={() => window.confirm(`Remove “${r.project}”?`) && run(() => api.adminResolveReport(r.id, 'removed'))}>Remove</Button>
                      <Button variant="secondary" size="sm" onClick={() => run(() => api.adminResolveReport(r.id, 'dismissed'))}>Dismiss</Button></div></td></tr>))}
              </tbody></table></div>)}
          </Section>
          <Section title="User accounts" right={<label className="input row" style={{ width: 260, height: 36, gap: 6 }}><Icon name="search" size={15} style={{ color: 'var(--faint)' }} /><input style={{ border: 0, outline: 0, flex: 1, background: 'none' }} placeholder="Search users" value={q} onChange={(e) => setQ(e.target.value)} /></label>} style={{ padding: 0, gap: 0 }}>
            <div className="table-wrap"><table><thead><tr><th>USER</th><th>STUDENT ID</th><th>ROLE</th><th>TEAMS</th><th>STATUS</th><th /></tr></thead><tbody>
              {users.map((u) => (
                <tr key={u.id}><td><Link to={`/students/${u.id}`} className="row" style={{ gap: 10 }}><Avatar name={u.name} size={32} /><div><div style={{ fontWeight: 600 }}>{u.name}</div><div className="xs muted">{u.email}</div></div></Link></td>
                  <td className="muted">{u.student_id}</td><td><Chip kind={u.role === 'admin' ? 'brand' : ''}>{u.role === 'admin' ? 'Admin' : 'Student'}</Chip></td><td>{u.projects}</td>
                  <td><Status value={u.status === 'active' ? 'accepted' : 'rejected'} label={u.status === 'active' ? 'Active' : 'Suspended'} /></td>
                  <td style={{ textAlign: 'right' }}>{u.role !== 'admin' && (u.status === 'active'
                    ? <Button variant="danger" size="sm" onClick={() => window.confirm(`Suspend ${u.name}?`) && run(() => api.adminSetUserStatus(u.id, 'suspended'))}>Suspend</Button>
                    : <Button variant="secondary" size="sm" onClick={() => run(() => api.adminSetUserStatus(u.id, 'active'))}>Reactivate</Button>)}</td></tr>))}
              {users.length === 0 && <tr><td colSpan={6} className="empty-row">No users match “{q}”.</td></tr>}
            </tbody></table></div>
          </Section>
        </>
      );
    }}</AsyncView>
  );
}

export function NotFound() {
  return <Empty title="Page not found">This page doesn’t exist. <Link className="link" to="/">Back to dashboard</Link></Empty>;
}
