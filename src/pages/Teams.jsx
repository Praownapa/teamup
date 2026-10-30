import { useState } from 'react';
import { Link, Navigate, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../api/endpoints';
import { useAsync } from '../utils/useAsync';
import { timeAgo, fmtDate } from '../utils/format';
import { useAuth } from '../auth/AuthContext';
import { AsyncView, Avatar, Bar, Button, Chip, Empty, Loading, Match, PageHeader, Section, Segmented, Status, Toggle } from '../components/ui';
import { categoryArt, ill } from '../components/art';
import Icon from '../components/Icon';

/* ======================= 07 · Find teammates ======================= */
export function FindTeammates() {
  const { profile } = useAuth();
  const [sp, setSp] = useSearchParams();
  const owned = (profile?.teams || []).filter((t) => t.is_owner);
  const projectId = Number(sp.get('project')) || owned[0]?.id;
  const proj = useAsync(() => (projectId ? api.getProject(projectId) : Promise.resolve(null)), [projectId]);
  const st = useAsync(() => (projectId ? api.getRecommendedStudents(projectId) : Promise.resolve([])), [projectId]);
  const [invited, setInvited] = useState({});
  const [err, setErr] = useState('');
  const [q, setQ] = useState('');
  const [role, setRole] = useState('all');

  if (!profile) return <Loading />;
  if (!owned.length) return (
    <>
      <PageHeader eyebrow="Recruit" art="teammates" tone="teal" title="Find teammates" subtitle="Recommendations appear once you own a project." />
      <Empty title="You don’t own a project yet">Create a project first, then we’ll recommend students who fit your required skills.</Empty>
      <Link className="btn primary" style={{ alignSelf: 'center' }} to="/projects/new"><Icon name="plus" size={16} />Create a project</Link>
    </>
  );
  const p = proj.data;
  return (
    <>
      <PageHeader eyebrow="Recruit" art="teammates" tone="teal" title="Find teammates" subtitle={`Students recommended for ${p?.title || 'your project'} based on its required skills.`} />
      {err && <div className="err">{err}</div>}
      <div className="card row wrap" style={{ gap: 18, padding: 16 }}>
        <div className="course-art" style={{ width: 64, height: 52, background: categoryArt(p?.category).bg }}><img src={ill(categoryArt(p?.category).art)} alt="" style={{ height: 46 }} /></div>
        <div className="col" style={{ gap: 2, flex: 1, minWidth: 200 }}><span className="xs muted">Recommending for</span>
          <select className="select" style={{ height: 36, maxWidth: 340, fontWeight: 600 }} value={projectId} onChange={(e) => { setSp({ project: e.target.value }); setInvited({}); setRole('all'); }}>
            {owned.map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}</select></div>
        <div className="col" style={{ gap: 6 }}><span className="xs muted">Open roles</span>
          <div className="chips">{p?.open_roles.length ? [...new Set(p.open_roles)].map((r) => <Chip key={r} kind="brand">{r}</Chip>) : <span className="small muted">None — team is complete</span>}</div></div>
        <div className="col" style={{ gap: 2, alignItems: 'flex-end' }}><span className="xs muted">Team</span><b>{p ? `${p.members.length} / ${p.max_size}` : '–'}</b></div>
      </div>
      <div className="row between wrap">
        <label className="input row" style={{ width: 320, height: 40, gap: 8 }}><Icon name="search" size={16} style={{ color: 'var(--faint)' }} />
          <input style={{ border: 0, outline: 0, flex: 1, background: 'none' }} placeholder="Search by name or skill" value={q} onChange={(e) => setQ(e.target.value)} /></label>
        {p && <Segmented small options={[['all', 'All roles'], ...[...new Set(p.open_roles)].map((r) => [r, r])]} value={role} onChange={setRole} />}
      </div>
      <AsyncView state={st}>{(all) => {
        const list = all.filter((s) => (role === 'all' || s.fits === role) && (!q || `${s.name} ${s.skills.map((x) => x[0]).join(' ')}`.toLowerCase().includes(q.toLowerCase())));
        if (!list.length) return <Empty title="No matching students">Try another role or keyword.</Empty>;
        const full = p && p.members.length >= p.max_size;
        return list.map((s) => {
          const done = invited[s.id] || s.invited;
          return (
            <div key={s.id} className="card row wrap" style={{ padding: 18, gap: 18 }}>
              <Avatar name={s.name} size={56} />
              <div className="col" style={{ flex: 1, gap: 6, minWidth: 220 }}>
                <div className="row"><div className="h3">{s.name}</div><Match value={s.match} /></div>
                <div className="xs muted">{s.major} · Year {s.year} · Fits: <b style={{ color: 'var(--text-2)' }}>{s.fits}</b></div>
                <div className="chips">{s.skills.map(([k, h]) => <Chip key={k} kind={h ? 'have' : ''}>{k}</Chip>)}</div>
              </div>
              <div className="row">
                <Link className="btn secondary sm" to={`/students/${s.id}`}>View profile</Link>
                <Button size="sm" disabled={done || full || s.fits === '—'} onClick={async () => { setErr(''); try { await api.inviteStudent(projectId, s.id, s.fits); setInvited({ ...invited, [s.id]: true }); } catch (e) { setErr(e.message); } }}>
                  {done ? <><Icon name="check" size={15} /> Invitation sent</> : <><Icon name="send" size={15} /> Invite to team</>}</Button>
              </div>
            </div>
          );
        });
      }}</AsyncView>
    </>
  );
}

/* ======================= 08 · Requests & invitations ======================= */
const TABS = [['received', 'Join requests received'], ['invitation', 'Invitations for me'], ['sent', 'Sent by me']];
export function Requests() {
  const st = useAsync(() => api.listRequests());
  const { refreshCounts, refreshProfile } = useAuth();
  const [sp, setSp] = useSearchParams();
  const tab = sp.get('tab') || 'received';
  const [busyId, setBusyId] = useState(null);
  const [err, setErr] = useState('');

  async function respond(r, accept) {
    setErr(''); setBusyId(r.id);
    try { await api.respondRequest(r.id, accept); await st.reload(); refreshCounts(); if (accept) refreshProfile(); }
    catch (e) { setErr(e.message); } finally { setBusyId(null); }
  }

  return (
    <>
      <PageHeader eyebrow="Inbox" art="requests" tone="amber" title="Requests & invitations" subtitle="Review who wants to join your projects and respond to invitations." />
      <AsyncView state={st}>{(all) => {
        const pending = (t) => all.filter((r) => r.type === t && r.status === 'pending');
        const list = tab === 'sent' ? all.filter((r) => r.type === 'sent') : pending(tab);
        const history = all.filter((r) => r.status !== 'pending');
        const lowSpots = tab === 'received' ? [...new Map(pending('received').map((r) => [r.project.id, r.project])).values()].filter((p) => p.open_spots <= 2) : [];
        return (
          <>
            <div className="tabs">{TABS.map(([k, l]) => (
              <button key={k} className={`tab ${tab === k ? 'on' : ''}`} onClick={() => setSp(k === 'received' ? {} : { tab: k })}>
                {l} <span className="chip" style={{ height: 20, marginLeft: 6 }}>{k === 'sent' ? all.filter((r) => r.type === 'sent').length : pending(k).length}</span></button>))}</div>
            {err && <div className="err">{err}</div>}
            {lowSpots.map((p) => (
              <div key={p.id} className="alert" style={{ background: 'var(--warn-bg)', color: '#92400e' }}><Icon name="users" size={18} />
                <span><b>{p.title}</b> has {p.open_spots} open spot{p.open_spots === 1 ? '' : 's'} left. The team closes automatically when it’s full and remaining requests are declined.</span></div>))}
            {list.length === 0
              ? <Empty title="Nothing here yet">{tab === 'received' ? 'New join requests for your projects will show up here.' : tab === 'invitation' ? 'When a project owner invites you, it appears here.' : 'Requests you send and invitations you make appear here.'}</Empty>
              : <div className="card" style={{ padding: 0, gap: 0 }}>{list.map((r) => {
                const other = r.type === 'invitation' ? r.by : r.student;
                return (
                  <div key={r.id} className="row wrap" style={{ padding: 20, borderBottom: '1px solid var(--line)', alignItems: 'flex-start' }}>
                    <Link to={`/students/${other.id}`}><Avatar name={other.name} size={44} /></Link>
                    <div className="col" style={{ flex: 1, minWidth: 240 }}>
                      <div className="row wrap" style={{ gap: 8 }}><Link to={`/students/${other.id}`} className="h3">{other.name}</Link>
                        <span className="xs muted">{r.type === 'received' ? `${r.match}% match · ${other.major}` : r.type === 'invitation' ? 'Project owner' : r.kind === 'invitation' ? `You invited ${r.student.name}` : 'Your request'}</span></div>
                      <div className="small">{r.type === 'invitation' ? 'invited you to' : r.type === 'received' ? 'wants to join' : r.kind === 'invitation' ? 'invited to' : 'requested to join'} <Link to={`/projects/${r.project.id}`}><b>{r.project.title}</b></Link> as <Chip kind="brand">{r.role}</Chip></div>
                      {r.message && <div className="small muted" style={{ background: '#f8fafc', padding: '10px 12px', borderRadius: 10 }}>“{r.message}”</div>}
                      <div className="xs muted">{timeAgo(r.created_at)}</div>
                    </div>
                    {r.status === 'pending' && r.type !== 'sent'
                      ? <div className="row"><Button variant="danger" size="sm" disabled={busyId === r.id} onClick={() => respond(r, false)}><Icon name="x" size={15} />Decline</Button>
                        <Button variant={r.type === 'invitation' ? 'primary' : 'success'} size="sm" disabled={busyId === r.id} onClick={() => respond(r, true)}><Icon name="check" size={15} />{r.type === 'invitation' ? 'Accept invite' : 'Accept'}</Button></div>
                      : <div className="row">{r.status === 'pending' && r.kind === 'request' && <Button variant="secondary" size="sm" onClick={async () => { setErr(''); try { await api.cancelRequest(r.id); st.reload(); } catch (e) { setErr(e.message); } }}>Cancel</Button>}<Status value={r.status} /></div>}
                  </div>);
              })}</div>}
            <Section title="Recently handled" style={{ padding: 0, gap: 0 }}>
              {history.length === 0 ? <div className="empty-row">No handled requests yet.</div> : (
                <div className="table-wrap"><table><thead><tr><th>STUDENT / PROJECT</th><th>TYPE</th><th>ROLE</th><th>DATE</th><th>STATUS</th></tr></thead><tbody>
                  {history.map((r) => (
                    <tr key={r.id}>
                      <td><div className="row" style={{ gap: 10 }}><Avatar name={r.student.name} size={30} /><div><div style={{ fontWeight: 600 }}>{r.type === 'sent' && r.kind === 'request' ? `You → ${r.project.title}` : r.student.name}</div><div className="xs muted">{r.project.title}</div></div></div></td>
                      <td className="muted">{r.kind === 'invitation' ? (r.type === 'invitation' ? 'Invitation received' : 'Invitation sent') : r.type === 'received' ? 'Request received' : 'Request sent'}</td>
                      <td>{r.role}</td><td className="muted">{fmtDate(r.created_at)}</td><td><Status value={r.status} /></td>
                    </tr>))}
                </tbody></table></div>)}
            </Section>
          </>
        );
      }}</AsyncView>
    </>
  );
}

/* ======================= 09 · Team management (owner) / team page (member) ======================= */
export function TeamManagement() {
  const { id } = useParams();
  const nav = useNavigate();
  const { profile, refreshProfile } = useAuth();
  const st = useAsync(() => api.getTeam(id), [id]);
  const [p2, setP2] = useState(null);
  const [err, setErr] = useState('');

  return (
    <AsyncView state={st}>{(p0) => {
      const p = p2 && p2.id === p0.id ? p2 : p0;
      if (!p.my_role) return <Navigate to={`/projects/${p.id}`} replace />;
      const owner = p.my_role === 'owner';
      const run = async (fn) => { setErr(''); try { setP2(await fn()); } catch (e) { setErr(e.message); } };
      const coverage = p.skills.map(([s]) => [s, p.members.filter((m) => m.skills?.some((x) => x.toLowerCase() === s.toLowerCase())).length]);
      const allRoles = [...new Set(p.roles.map((r) => r.name))];
      return (
        <>
          <PageHeader eyebrow={owner ? 'Your project' : 'Your team'} art="hero" tone="navy" title={owner ? 'Manage team' : p.title} subtitle={owner ? p.title : `Owned by ${p.owner.name} · you’re a member`}
            actions={owner
              ? <><Link className="btn secondary" to={`/projects/${p.id}`}>View project page</Link><Link className="btn primary" to={`/teammates?project=${p.id}`}><Icon name="users" size={16} />Find teammates</Link></>
              : <><Link className="btn secondary" to={`/projects/${p.id}`}>View project page</Link>
                <Button variant="danger" onClick={async () => { setErr(''); try { if (window.confirm(`Leave ${p.title}?`)) { await api.leaveTeam(p.id); await refreshProfile(); nav('/teams'); } } catch (e) { setErr(e.message); } }}><Icon name="logout" size={16} />Leave team</Button></>} />
          {err && <div className="err">{err}</div>}
          <div className="grid g3">
            <div className="stat-big" style={{ alignItems: 'flex-start', textAlign: 'left' }}><div className="small muted">Team size</div><div className="stat-v">{p.members.length} / {p.max_size}</div><div style={{ width: '100%' }}><Bar value={(100 * p.members.length) / p.max_size} /></div></div>
            <div className="stat-big" style={{ alignItems: 'flex-start', textAlign: 'left' }}><div className="small muted">Recruitment status</div><Status value={p.status} />
              <div className="xs muted">{p.status === 'full' ? 'Team is complete.' : `${p.max_size - p.members.length} spot(s) open · closes automatically when full.`}</div></div>
            <div className="stat-big" style={{ alignItems: 'flex-start', textAlign: 'left' }}><div className="small muted">Pending</div><div className="stat-v">{p.pending_requests + p.pending_invitations}</div>
              <div className="xs muted">{p.pending_requests} join request(s) · {p.pending_invitations} invitation(s) sent</div>
              {owner && p.pending_requests > 0 && <Link to="/requests" className="link-btn">Review requests →</Link>}</div>
          </div>

          <Section title="Members" right={owner && <span className="xs muted">Only the project owner can change roles or remove members.</span>} style={{ padding: 0, gap: 0 }}>
            <div className="table-wrap"><table><thead><tr><th>MEMBER</th><th>ROLE</th><th>SKILLS</th><th /></tr></thead><tbody>
              {p.members.map((m) => (
                <tr key={m.id}>
                  <td><Link to={`/students/${m.id}`} className="row" style={{ gap: 12 }}><Avatar name={m.name} size={38} /><div><div style={{ fontWeight: 600 }}>{m.name}{m.id === profile?.id && ' (You)'}</div><div className="xs muted">{m.owner ? 'Owner' : 'Member'} · {m.major}</div></div></Link></td>
                  <td>{owner && !m.owner
                    ? <select className="select" style={{ height: 36, width: 200 }} value={m.role} onChange={(e) => run(() => api.changeMemberRole(p.id, m.id, e.target.value))}>
                      {[...new Set([m.role, ...allRoles])].map((r) => <option key={r}>{r}</option>)}</select>
                    : <span>{m.role}</span>}</td>
                  <td><div className="chips">{(m.skills || []).slice(0, 3).map((s) => <Chip key={s}>{s}</Chip>)}</div></td>
                  <td style={{ textAlign: 'right' }}>{owner && !m.owner && <Button variant="danger" size="sm" onClick={() => window.confirm(`Remove ${m.name} from the team?`) && run(() => api.removeMember(p.id, m.id))}>Remove</Button>}</td>
                </tr>))}
              {p.roles.filter((r) => !r.user).map((r, i) => (
                <tr key={`open${i}`}>
                  <td><div className="row" style={{ gap: 12 }}><div className="open-slot"><Icon name="plus" size={16} /></div><div><div style={{ fontWeight: 600, color: 'var(--brand-700)' }}>Open spot</div><div className="xs muted">{r.name}</div></div></div></td>
                  <td colSpan={2} className="small muted">Waiting for a request or invitation to be accepted.</td>
                  <td style={{ textAlign: 'right' }}>{owner && <Link className="btn ghost sm" to={`/teammates?project=${p.id}`}><Icon name="mail" size={14} />Invite</Link>}</td>
                </tr>))}
            </tbody></table></div>
          </Section>

          <div className="grid g2">
            <Section title="Required skills coverage">
              {coverage.map(([s, n]) => (
                <div key={s} className="row" style={{ gap: 12 }}><span className="small" style={{ width: 110 }}>{s}</span>
                  <div className="bar"><div style={{ width: `${n ? 100 : 12}%`, background: n ? 'var(--ok)' : '#f59e0b' }} /></div>
                  <span className="xs muted" style={{ width: 100, textAlign: 'right' }}>{n ? `${n} member${n > 1 ? 's' : ''}` : 'needs support'}</span></div>))}
            </Section>
            {owner ? (
              <Section title="Recruitment">
                <div className="setting"><div><div className="h3">Accept join requests</div><div className="xs muted">Show this project as recruiting in Explore and allow requests.</div></div>
                  <Toggle checked={p.accepting} onChange={(v) => run(() => api.updateProject(p.id, { accepting: v }))} label="Accept join requests" /></div>
                <div className="setting"><div><div className="h3">Email me about new requests</div><div className="xs muted">Account-wide preference for {profile?.email}; delivery requires backend email setup.</div></div>
                  <Toggle checked={!!profile?.notify?.requests} onChange={async (requests) => { setErr(''); try { await api.updateMe({ notify: { ...profile.notify, requests } }); await refreshProfile(); } catch (e) { setErr(e.message); } }} label="Email me about new requests" /></div>
                <div className="setting danger"><div><div className="h3" style={{ color: 'var(--bad)' }}>Close recruitment</div><div className="xs" style={{ color: 'var(--bad)' }}>Stop accepting requests. You can reopen it any time.</div></div>
                  <Button variant="danger" size="sm" disabled={!p.accepting} onClick={() => run(() => api.updateProject(p.id, { accepting: false }))}>Close</Button></div>
              </Section>
            ) : (
              <Section title="About this project">
                <p className="small" style={{ lineHeight: 1.7, color: 'var(--text-2)' }}>{p.description}</p>
                {[['Duration', p.duration], ['Meeting', p.meeting], ['Owner', p.owner.name]].map(([k, v]) => <div key={k} className="kv"><span>{k}</span><span>{v}</span></div>)}
              </Section>
            )}
          </div>
        </>
      );
    }}</AsyncView>
  );
}

/* ======================= My teams ======================= */
export function MyTeams() {
  const { profile } = useAuth();
  const st = useAsync(() => Promise.all((profile?.teams || []).map((t) => api.getProject(t.id))), [profile?.teams?.map((t) => t.id).join()]);
  if (!profile) return <Loading />;
  return (
    <>
      <PageHeader eyebrow="Teams" art="teams" tone="sky" title="My teams" subtitle="Projects you own or have joined."
        actions={<Link className="btn primary" to="/projects/new"><Icon name="plus" size={16} />New project</Link>} />
      <AsyncView state={st}>{(teams) => teams.length === 0
        ? <Empty title="No teams yet">Join a project from Explore or create your own.</Empty>
        : <div className="grid g2">{teams.map((p) => (
          <Link key={p.id} to={`/teams/${p.id}`} className="card pcard" style={{ padding: 0, gap: 0, overflow: 'hidden' }}>
            <div className="pcover" style={{ height: 110, background: categoryArt(p.category).bg }}><img src={ill(categoryArt(p.category).art)} alt="" style={{ height: 96 }} />
              <span className={`chip ${p.my_role === 'owner' ? 'brand' : ''}`} style={{ position: 'absolute', top: 12, left: 12, background: '#fff' }}>{p.my_role === 'owner' ? 'Owner' : 'Member'}</span></div>
            <div className="col" style={{ padding: 18 }}>
              <div className="row between"><div className="h3" style={{ fontSize: 16 }}>{p.title}</div><Status value={p.status} /></div>
              <div className="row between"><div className="avs">{p.members.slice(0, 5).map((m) => <Avatar key={m.id} name={m.name} size={28} />)}</div>
                <span className="xs muted">{p.members.length}/{p.max_size} members{p.my_role === 'owner' && p.pending_requests ? ` · ${p.pending_requests} pending` : ''}</span></div>
            </div>
          </Link>))}</div>}
      </AsyncView>
    </>
  );
}

/* ======================= Student public profile (View profile) ======================= */
export function StudentProfile() {
  const { id } = useParams();
  const st = useAsync(() => api.getUser(id), [id]);
  return (
    <AsyncView state={st}>{(u) => (
      <>
        <div className="page-hero tone-sky">
          <div className="row" style={{ gap: 20, position: 'relative' }}>
            <Avatar name={u.name} size={96} />
            <div className="page-hero-text"><div className="eyebrow">Student</div><div className="h1">{u.name}</div><div className="sub">{u.major} · Year {u.year}</div></div>
          </div>
        </div>
        <div className="grid g2">
          <Section title="Skills"><div className="col">{u.skills.map((s) => <div key={s.name} className="kv"><span style={{ color: 'var(--text)', fontWeight: 500 }}>{s.name}</span><span className="muted">{s.level}</span></div>)}</div></Section>
          <Section title="About">
            <p className="small muted" style={{ lineHeight: 1.7 }}>{u.bio || 'No bio yet.'}</p>
            {u.interests.length > 0 && <div className="chips">{u.interests.map((t) => <Chip key={t} kind="brand">{t}</Chip>)}</div>}
            <div className="lbl">Teams</div>
            {u.teams.length ? u.teams.map((t) => <Link key={t.id} to={`/projects/${t.id}`} className="link-btn">{t.title}</Link>) : <span className="small muted">Not in a team yet.</span>}
          </Section>
        </div>
      </>
    )}</AsyncView>
  );
}
