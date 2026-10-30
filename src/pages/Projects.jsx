import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../api/endpoints';
import { useAsync } from '../utils/useAsync';
import { uploadImage } from '../utils/upload';
import { fmtDate } from '../utils/format';
import { useAuth } from '../auth/AuthContext';
import { AsyncView, Avatar, Button, Chip, Empty, Match, Modal, PageHeader, Section, Segmented, Status, Toggle } from '../components/ui';
import ProjectCard from '../components/ProjectCard';
import { categoryArt, ill } from '../components/art';
import Icon from '../components/Icon';

const CATEGORIES = ['Course Project', 'Competition', 'Senior Project', 'Startup Idea', 'Research'];
const SORTS = [['match', 'Best match'], ['newest', 'Newest'], ['spots', 'Most spots']];
const REPORT_REASONS = ['Spam / scam', 'Academic dishonesty', 'Misleading info', 'Inappropriate content', 'Invalid / empty'];

/* ======================= 04 · Explore projects ======================= */
export function Explore() {
  const [sp, setSp] = useSearchParams();
  const get = (k) => sp.get(k) || '';
  const filters = { q: get('q'), categories: get('categories'), skills: get('skills'), role: get('role'), recruiting: get('recruiting'), spots: get('spots'), sort: get('sort') || 'match' };
  const st = useAsync(() => api.listProjects(filters), [sp.toString()]);
  const opts = useAsync(() => api.listFilterOptions());
  const [skillInput, setSkillInput] = useState('');
  const [qInput, setQInput] = useState(filters.q);
  useEffect(() => setQInput(filters.q), [filters.q]);

  const update = (k, v) => { const n = new URLSearchParams(sp); v ? n.set(k, v) : n.delete(k); setSp(n, { replace: true }); };
  const listOf = (k) => (filters[k] ? filters[k].split(',') : []);
  const toggleIn = (k, v) => { const l = listOf(k); update(k, (l.includes(v) ? l.filter((x) => x !== v) : [...l, v]).join(',')); };
  const active = ['q', 'categories', 'skills', 'role', 'recruiting', 'spots'].some((k) => filters[k]);

  return (
    <>
      <PageHeader eyebrow="Discover" title="Explore projects" subtitle="Find a team that needs exactly what you’re good at — sorted by how well each project matches your skills." art="explore" tone="indigo" />
      <form className="row" onSubmit={(e) => { e.preventDefault(); update('q', qInput.trim()); }}>
        <label className="input row" style={{ flex: 1, height: 46, gap: 8 }}><Icon name="search" size={18} style={{ color: 'var(--faint)' }} />
          <input style={{ border: 0, outline: 0, flex: 1, background: 'none' }} placeholder="Search by title, description or skill…" value={qInput} onChange={(e) => setQInput(e.target.value)} /></label>
        <Button style={{ height: 46 }}>Search</Button>
      </form>
      <div className="row" style={{ alignItems: 'flex-start', gap: 22 }}>
        <aside className="filters card" style={{ gap: 18 }}>
          <div className="row between"><div className="h3">Filters</div>{active && <button className="link-btn" onClick={() => setSp({ sort: filters.sort })}>Reset</button>}</div>
          <div className="col"><div className="lbl">Category</div>
            {(opts.data?.categories || CATEGORIES.map((name) => ({ name }))).map((c) => (
              <label key={c.name} className="cbx"><input type="checkbox" checked={listOf('categories').includes(c.name)} onChange={() => toggleIn('categories', c.name)} />{c.name}{c.count != null && <span className="xs muted" style={{ marginLeft: 'auto' }}>{c.count}</span>}</label>
            ))}</div>
          <div className="divider" />
          <div className="col"><div className="lbl">Skills</div>
            <input className="input" style={{ height: 38 }} placeholder="Add a skill + Enter" value={skillInput} onChange={(e) => setSkillInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && skillInput.trim()) { e.preventDefault(); toggleIn('skills', skillInput.trim()); setSkillInput(''); } }} />
            <div className="chips">{listOf('skills').map((s) => <button key={s} className="chip brand" onClick={() => toggleIn('skills', s)}>{s} <Icon name="x" size={12} /></button>)}</div></div>
          <div className="divider" />
          <div className="col"><div className="lbl">Open role</div>
            <select className="select" style={{ height: 38 }} value={filters.role} onChange={(e) => update('role', e.target.value)}>
              <option value="">Any role</option>{(opts.data?.roles || []).map((r) => <option key={r}>{r}</option>)}</select></div>
          <div className="divider" />
          <div className="col"><div className="lbl">Team status</div>
            <label className="cbx"><input type="checkbox" checked={filters.recruiting === 'true'} onChange={(e) => update('recruiting', e.target.checked ? 'true' : '')} />Recruiting only</label>
            <label className="cbx"><input type="checkbox" checked={filters.spots === 'true'} onChange={(e) => update('spots', e.target.checked ? 'true' : '')} />Has 2+ open spots</label></div>
        </aside>
        <div className="col" style={{ flex: 1, gap: 16, minWidth: 0 }}>
          <div className="row between wrap">
            <div className="small muted">{st.data ? `${st.data.length} project${st.data.length === 1 ? '' : 's'}` : ' '}</div>
            <Segmented options={SORTS} value={filters.sort} onChange={(v) => update('sort', v === 'match' ? '' : v)} />
          </div>
          <AsyncView state={st}>{(list) => list.length === 0
            ? <Empty title="No projects found">Try another keyword or remove some filters.</Empty>
            : <div className="grid g2x">{list.map((p) => <ProjectCard key={p.id} p={p} />)}</div>}
          </AsyncView>
        </div>
      </div>
    </>
  );
}

/* ======================= 05 · Project detail ======================= */
export function ProjectDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const { profile, refreshProfile } = useAuth();
  const st = useAsync(() => api.getProject(id), [id]);
  const [form, setForm] = useState({ role: '', message: '' });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [report, setReport] = useState(null); // null | { reason } | 'sent'
  const [saved, setSaved] = useState(null);

  return (
    <AsyncView state={st}>{(p) => {
      const isSaved = saved?.id === p.id ? saved.value : p.saved;
      const open = p.max_size - p.members.length;
      const have = p.skills.filter(([, h]) => h).length;
      const sendRequest = async (e) => {
        e.preventDefault(); setErr(''); setBusy(true);
        try { await api.requestToJoin(p.id, form); st.reload(); } catch (e2) { setErr(e2.message); } finally { setBusy(false); }
      };
      return (
        <>
          {err && <div className="err">{err}</div>}
          <div className="row small muted" style={{ gap: 8 }}><Link to="/projects" className="row" style={{ gap: 6 }}><Icon name="search" size={15} />Explore projects</Link>/<span style={{ color: 'var(--text)', fontWeight: 500 }}>{p.title}</span></div>
          <div className="card" style={{ padding: 0, overflow: 'hidden', gap: 0 }}>
            <div className="detail-cover" style={{ background: p.cover_url ? `center/cover url(${p.cover_url})` : categoryArt(p.category).bg }}>
              {!p.cover_url && <img src={ill(categoryArt(p.category).art)} alt="" />}
            </div>
            <div className="row between wrap" style={{ padding: 24, alignItems: 'flex-start' }}>
              <div className="col" style={{ gap: 10 }}>
                <div className="row wrap" style={{ gap: 8 }}><Chip kind="brand">{p.category}</Chip>{p.course && <Chip>{p.course}</Chip>}</div>
                <div className="h1">{p.title}</div>
                <div className="row wrap small muted" style={{ gap: 18 }}>
                  <Link to={`/students/${p.owner.id}`} className="row" style={{ gap: 6 }}><Avatar name={p.owner.name} size={22} />Owned by {p.owner.name}</Link>
                  <span className="row" style={{ gap: 6 }}><Icon name="folder" size={15} />Posted {fmtDate(p.created_at)}</span>
                  <span className="row" style={{ gap: 6 }}><Icon name="users" size={15} />{p.members.length} / {p.max_size} members</span>
                  <Status value={p.status} />
                </div>
              </div>
              <div className="row">
                {p.my_role !== 'owner' && <Button variant="secondary" size="sm" onClick={() => setReport({ reason: REPORT_REASONS[0] })}><Icon name="alert" size={15} />Report</Button>}
                <Button variant="secondary" size="sm" onClick={async () => { setErr(''); try { setSaved({ id: p.id, value: (await api.toggleSave(p.id)).saved }); } catch (e) { setErr(e.message); } }}><Icon name="sparkle" size={15} />{isSaved ? 'Saved' : 'Save'}</Button>
              </div>
            </div>
          </div>

          <div className="row" style={{ alignItems: 'flex-start', gap: 22 }}>
            <div className="col" style={{ flex: 1, gap: 22, minWidth: 0 }}>
              <Section title="About this project"><p className="small" style={{ lineHeight: 1.75, color: 'var(--text-2)', whiteSpace: 'pre-line' }}>{p.description}</p></Section>
              <Section title="Roles" right={<span className="xs muted">{p.open_roles.length} of {p.roles.length} roles open</span>} style={{ gap: 4 }}>
                {p.roles.map((r, i) => (
                  <div key={i} className="row between" style={{ padding: '12px 0', borderTop: '1px solid var(--line)' }}>
                    <div className="h3">{r.name}</div>
                    {r.user ? <Link to={`/students/${r.user.id}`} className="row small" style={{ gap: 8 }}><Avatar name={r.user.name} size={26} /><span className="muted">Filled · {r.user.name}</span></Link>
                      : <span className="status rec">Open spot</span>}
                  </div>
                ))}
              </Section>
              <Section title="Current team">
                {p.members.map((m) => (
                  <Link key={m.id} to={`/students/${m.id}`} className="row"><Avatar name={m.name} size={40} />
                    <div><div className="h3 row" style={{ gap: 8 }}>{m.name}{m.owner && <Chip kind="brand">Owner</Chip>}</div><div className="xs muted">{m.role}</div></div></Link>
                ))}
              </Section>
            </div>

            <div className="col" style={{ width: 360, flexShrink: 0, gap: 22 }}>
              <div className="card" id="join" style={{ border: '1.5px solid var(--brand-200)' }}>
                <div className="row between"><div className="h2">Your match</div><Match value={p.match} /></div>
                <div className="row" style={{ gap: 18 }}>
                  <div className="ring" style={{ background: `conic-gradient(var(--brand-600) ${p.match * 3.6}deg, var(--brand-100) 0)` }}><div>{p.match}</div></div>
                  <div className="col small" style={{ gap: 6 }}>
                    <span className="row" style={{ gap: 6 }}><Icon name="check" size={15} style={{ color: 'var(--ok)' }} />{have} of {p.skills.length} required skills</span>
                    <span className="row" style={{ gap: 6 }}><Icon name="check" size={15} style={{ color: 'var(--ok)' }} />{p.open_roles.length} open role{p.open_roles.length === 1 ? '' : 's'}</span>
                    <span className="row" style={{ gap: 6 }}><Icon name="users" size={15} />{open} spot{open === 1 ? '' : 's'} left</span>
                  </div>
                </div>
                <div className="col"><div className="lbl">Required skills</div>
                  <div className="chips">{p.skills.map(([s, h]) => <Chip key={s} kind={h ? 'have' : 'miss'}>{h ? <Icon name="check" size={12} stroke={2.4} /> : null}{s}{!h && ' · missing'}</Chip>)}</div></div>
                <div className="divider" />
                <JoinPanel p={p} meId={profile?.id} form={form} setForm={setForm} busy={busy} err={err} onSubmit={sendRequest}
                  onCancel={async () => { setErr(''); try { await api.cancelRequest(p.my_request.id); st.reload(); } catch (e) { setErr(e.message); } }}
                  onLeave={async () => { setErr(''); try { if (window.confirm(`Leave ${p.title}?`)) { await api.leaveTeam(p.id); await refreshProfile(); nav('/teams'); } } catch (e) { setErr(e.message); } }} />
              </div>
              <Section title="Project details" style={{ gap: 6 }}>
                {[['Category', p.category], ['Max team size', `${p.max_size} members`], ['Open spots', open], ['Duration', p.duration], ['Meeting', p.meeting], ['Apply by', fmtDate(p.deadline)]].map(([k, v]) => (
                  <div key={k} className="kv"><span>{k}</span><span>{v || '—'}</span></div>))}
              </Section>
            </div>
          </div>

          {report && (
            <Modal title="Report this project" onClose={() => setReport(null)}>
              {err && <div className="err">{err}</div>}
              {report === 'sent'
                ? <><div className="alert"><Icon name="checkCircle" size={18} />Thanks — an administrator will review this project.</div><Button onClick={() => setReport(null)}>Close</Button></>
                : <>
                  <div className="small muted">Tell us what’s wrong. Reports are anonymous.</div>
                  {REPORT_REASONS.map((r) => <label key={r} className="cbx"><input type="radio" name="reason" checked={report.reason === r} onChange={() => setReport({ reason: r })} />{r}</label>)}
                  <div className="row" style={{ justifyContent: 'flex-end' }}><Button variant="secondary" onClick={() => setReport(null)}>Cancel</Button>
                    <Button variant="danger" onClick={async () => { setErr(''); try { await api.reportProject(p.id, report.reason); setReport('sent'); } catch (e) { setErr(e.message); } }}>Send report</Button></div>
                </>}
            </Modal>
          )}
        </>
      );
    }}</AsyncView>
  );
}

// กล่องด้านขวาเปลี่ยนตามสถานะของเรากับโปรเจกต์นี้
function JoinPanel({ p, meId, form, setForm, busy, err, onSubmit, onCancel, onLeave }) {
  if (p.my_role === 'owner') {
    return (<div className="col"><div className="alert"><Icon name="user" size={18} />You own this project.</div>
      <Link className="btn primary block" to={`/teams/${p.id}`}>Manage team</Link>
      <Link className="btn secondary" to={`/teammates?project=${p.id}`}>Find teammates</Link></div>);
  }
  if (p.my_role === 'member') {
    const mine = p.members.find((m) => m.id === meId)?.role;
    return (<div className="col"><div className="alert"><Icon name="checkCircle" size={18} />You’re a member of this team{mine ? ` as ${mine}` : ''}.</div>
      <Link className="btn primary block" to={`/teams/${p.id}`}>Open team page</Link>
      <Button variant="danger" onClick={onLeave}>Leave team</Button></div>);
  }
  if (p.my_request) {
    return (<div className="col"><div className="alert" style={{ background: 'var(--warn-bg)', color: 'var(--warn)' }}><Icon name="inbox" size={18} />Request sent for <b>&nbsp;{p.my_request.role}</b>. Waiting for the owner to respond.</div>
      <Button variant="secondary" onClick={onCancel}>Cancel request</Button></div>);
  }
  if (p.status !== 'recruiting') {
    return <div className="alert"><Icon name="alert" size={18} />{p.status === 'full' ? 'This team is complete.' : 'The owner has paused recruitment.'} It no longer accepts requests.</div>;
  }
  return (
    <form className="col" style={{ gap: 14 }} onSubmit={onSubmit}>
      {err && <div className="err">{err}</div>}
      <div className="field"><label className="lbl">Role you’re applying for</label>
        <select className="select" required value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
          <option value="">Choose a role</option>{[...new Set(p.open_roles)].map((r) => <option key={r}>{r}</option>)}</select></div>
      <div className="field"><label className="lbl">Message to owner <span className="muted" style={{ fontWeight: 400 }}>(optional)</span></label>
        <textarea className="textarea" style={{ minHeight: 90 }} maxLength={500} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} placeholder="Why are you a good fit?" /></div>
      <Button block disabled={busy}>{busy ? 'Sending…' : 'Request to Join'}</Button>
      <div className="xs muted" style={{ textAlign: 'center' }}>The owner will be notified in-app and by email.</div>
    </form>
  );
}

/* ======================= 06 · Create project ======================= */
export function CreateProject() {
  const nav = useNavigate();
  const { profile, refreshProfile } = useAuth();
  const [f, setF] = useState({ title: '', description: '', category: CATEGORIES[0], course: '', cover_url: '', skills: [], owner_role: '', roles: [{ name: '', spots: 1 }], max_size: 5, deadline: '', duration: '', meeting: '', accepting: true });
  const [skill, setSkill] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const set = (k, v) => setF((x) => ({ ...x, [k]: v }));
  const spots = f.roles.filter((r) => r.name.trim()).reduce((a, r) => a + Number(r.spots || 1), 0) + 1;
  const addSkill = () => { const s = skill.trim(); if (s && !f.skills.includes(s)) set('skills', [...f.skills, s]); setSkill(''); };

  async function onFile(e) {
    const file = e.target.files?.[0]; if (!file) return;
    setUploading(true); setErr('');
    try { const url = await uploadImage(file); set('cover_url', url || URL.createObjectURL(file)); } catch (e2) { setErr(e2.message); } finally { setUploading(false); }
  }
  async function submit(e) {
    e.preventDefault(); setErr('');
    if (uploading) return setErr('Wait for the image upload to finish.');
    if (f.skills.length === 0) return setErr('Add at least one required skill.');
    if (!f.roles.some((r) => r.name.trim())) return setErr('Add at least one role you are looking for.');
    if (spots > f.max_size) return setErr(`Your roles need ${spots} people (including you) but the maximum team size is ${f.max_size}.`);
    setBusy(true);
    try {
      const p = await api.createProject({ ...f, roles: f.roles.filter((r) => r.name.trim()) });
      await refreshProfile(); nav(`/projects/${p.id}`);
    } catch (e2) { setErr(e2.message); } finally { setBusy(false); }
  }

  const preview = useMemo(() => ({
    id: 0, title: f.title || 'Your project title', description: f.description || 'Your description will appear here.', category: f.category, cover_url: f.cover_url, match: 100, status: f.accepting ? 'recruiting' : 'closed', max_size: f.max_size,
    skills: f.skills.map((s) => [s, true]), members: [{ id: 1, name: profile?.name || 'You' }],
  }), [f, profile]);

  return (
    <form onSubmit={submit} className="col" style={{ gap: 22 }}>
      <PageHeader eyebrow="New project" art="create" tone="violet" title="Create a new project" subtitle="Describe your project and the skills you need — we’ll recommend students who fit."
        actions={<><Button type="button" variant="secondary" onClick={() => nav(-1)}>Cancel</Button><Button disabled={busy || uploading}>{busy ? 'Publishing…' : <><Icon name="check" size={18} /> Publish project</>}</Button></>} />
      {err && <div className="err">{err}</div>}
      <div className="row" style={{ alignItems: 'flex-start', gap: 22 }}>
        <div className="col" style={{ flex: 1, gap: 22, minWidth: 0 }}>
          <Section title="1 · Basic information">
            <div className="field"><label className="lbl">Project title *</label><input className="input" required maxLength={80} value={f.title} onChange={(e) => set('title', e.target.value)} /><span className="hint">{f.title.length} / 80 characters</span></div>
            <div className="field"><label className="lbl">Description *</label><textarea className="textarea" required maxLength={2000} value={f.description} onChange={(e) => set('description', e.target.value)} placeholder="What are you building, why, and how will the team work?" /></div>
            <div className="grid g2" style={{ gap: 14 }}>
              <div className="field"><label className="lbl">Category *</label><select className="select" value={f.category} onChange={(e) => set('category', e.target.value)}>{CATEGORIES.map((c) => <option key={c}>{c}</option>)}</select></div>
              <div className="field"><label className="lbl">Course / event</label><input className="input" value={f.course} onChange={(e) => set('course', e.target.value)} placeholder="e.g. DES424 Cloud-based App Dev" /></div>
            </div>
            <div className="field"><label className="lbl">Cover image</label>
              <label className="dropzone">
                <input type="file" accept="image/png,image/jpeg,image/webp" onChange={onFile} hidden />
                {f.cover_url ? <img src={f.cover_url} alt="" style={{ maxHeight: 120, borderRadius: 10 }} /> : <Icon name="folder" size={26} />}
                <b>{uploading ? 'Uploading…' : f.cover_url ? 'Change image' : 'Click to upload'}</b>
                <span className="xs muted">PNG, JPG or WebP, up to 5 MB · stored on Amazon S3. Without one we use an illustration for your category.</span>
              </label></div>
          </Section>

          <Section title="2 · Required skills & roles">
            <div className="field"><label className="lbl">Required skills *</label>
              <div className="row"><input className="input" value={skill} placeholder="Type a skill and press Enter" onChange={(e) => setSkill(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addSkill(); } }} />
                <Button type="button" variant="ghost" onClick={addSkill}>Add</Button></div>
              <div className="chips">{f.skills.map((s) => <button type="button" key={s} className="chip brand" onClick={() => set('skills', f.skills.filter((x) => x !== s))}>{s} <Icon name="x" size={12} /></button>)}</div>
              <span className="hint">Used to calculate the match score for students.</span></div>
            <div className="field"><label className="lbl">Your role in the team</label><input className="input" value={f.owner_role} onChange={(e) => set('owner_role', e.target.value)} placeholder="e.g. Project Lead" /></div>
            <div className="lbl">Roles you’re looking for *</div>
            {f.roles.map((r, i) => (
              <div key={i} className="row">
                <input className="input" style={{ flex: 1 }} placeholder="e.g. Frontend Developer" value={r.name} onChange={(e) => set('roles', f.roles.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))} />
                <select className="select" style={{ width: 120 }} value={r.spots} onChange={(e) => set('roles', f.roles.map((x, j) => (j === i ? { ...x, spots: Number(e.target.value) } : x)))}>
                  {[1, 2, 3, 4].map((n) => <option key={n} value={n}>{n} spot{n > 1 ? 's' : ''}</option>)}</select>
                <Button type="button" variant="secondary" size="sm" aria-label="Remove role" disabled={f.roles.length === 1} onClick={() => set('roles', f.roles.filter((_, j) => j !== i))}><Icon name="x" size={15} /></Button>
              </div>
            ))}
            <div><Button type="button" variant="ghost" size="sm" onClick={() => set('roles', [...f.roles, { name: '', spots: 1 }])}><Icon name="plus" size={16} /> Add role</Button></div>
          </Section>

          <Section title="3 · Team settings">
            <div className="grid g2" style={{ gap: 14 }}>
              <div className="field"><label className="lbl">Maximum team size *</label>
                <div className="row" style={{ gap: 0 }}>
                  <button type="button" className="input stepper" onClick={() => set('max_size', Math.max(2, f.max_size - 1))}>−</button>
                  <div className="input stepper-v">{f.max_size}</div>
                  <button type="button" className="input stepper" onClick={() => set('max_size', Math.min(10, f.max_size + 1))}>+</button>
                </div>
                <span className="hint">Including you · roles above need {spots}. New members can’t join once the team is full.</span></div>
              <div className="field"><label className="lbl">Recruitment deadline</label><input className="input" type="date" value={f.deadline} onChange={(e) => set('deadline', e.target.value)} /></div>
              <div className="field"><label className="lbl">Duration</label><input className="input" value={f.duration} onChange={(e) => set('duration', e.target.value)} placeholder="e.g. Aug – Dec 2026" /></div>
              <div className="field"><label className="lbl">Meeting</label><input className="input" value={f.meeting} onChange={(e) => set('meeting', e.target.value)} placeholder="e.g. On campus, 2× / week" /></div>
            </div>
            <div className="setting"><div><div className="h3">Open for join requests</div><div className="xs muted">Students can request to join. Turn off to recruit by invitation only.</div></div>
              <Toggle checked={f.accepting} onChange={(v) => set('accepting', v)} label="Open for join requests" /></div>
          </Section>
        </div>
        <div className="col" style={{ width: 340, flexShrink: 0, gap: 14, position: 'sticky', top: 12 }}>
          <div className="lbl">Preview</div>
          <div style={{ pointerEvents: 'none' }}><ProjectCard p={preview} /></div>
          <div className="alert"><Icon name="sparkle" size={18} />After publishing, go to Find Teammates to invite students who match your required skills.</div>
        </div>
      </div>
    </form>
  );
}

