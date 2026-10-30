import { Link } from 'react-router-dom';
import { api } from '../api/endpoints';
import { useAsync } from '../utils/useAsync';
import { timeAgo } from '../utils/format';
import { useAuth, displayName } from '../auth/AuthContext';
import { ill, categoryArt } from '../components/art';
import { AsyncView, Avatar, Status } from '../components/ui';
import Icon from '../components/Icon';

// [ค่าใน stats, ชื่อ, ไอคอน, ลิงก์เมื่อกด]
const STATS = [
  ['teams', 'Active teams', 'folder', '/teams'],
  ['pending', 'Requests to review', 'inbox', '/requests'],
  ['invitations', 'New invitations', 'mail', '/requests?tab=invitation'],
  ['matches', 'Matching projects', 'sparkle', '/projects?recruiting=true'],
];
const DOT = { request: '#3b82f6', invite: '#8b5cf6', accepted: '#10b981', team: '#0ea5e9', declined: '#f43f5e', match: '#f59e0b' };

export default function Dashboard() {
  const st = useAsync(() => api.getDashboard());
  const { profile, user } = useAuth();
  const firstName = displayName(profile, user).split(' ')[0];
  const today = new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  return (
    <AsyncView state={st}>{(d) => {
      // เพื่อนร่วมทีมจากทุกทีม (ไม่ซ้ำ ไม่รวมตัวเอง)
      const mates = [...new Map(d.my_teams.flatMap((p) => p.members).filter((m) => m.id !== profile?.id).map((m) => [m.id, m])).values()];
      const strength = Math.min(100, 20 + Math.min(profile?.skills?.length || 0, 6) * 8 + (profile?.bio ? 15 : 0) + ((profile?.interests?.length || 0) >= 2 ? 10 : 0) + (profile?.portfolio ? 7 : 0));
      return (
      <>
        <section className="hero">
          <div className="date">{today}</div>
          <h1>Welcome back{firstName ? `, ${firstName}` : ''}!</h1>
          <p>Find your next project and the teammates who fill your skill gaps.</p>
          <div className="row" style={{ marginTop: 8 }}>
            <Link to="/projects" className="btn cta sm">Explore projects</Link>
          </div>
          <img className="art" src={ill('teams')} alt="" />
        </section>

        <div className="row" style={{ alignItems: 'stretch', gap: 24 }}>
          <div className="col" style={{ flex: 1, gap: 22, minWidth: 0 }}>
            <div className="section-t"><div className="h2">Overview</div></div>
            <div className="grid g4">
              {STATS.map(([k, label, icon, to]) => (
                <Link key={k} to={to} className={`stat-big ${k === 'pending' && d.stats[k] > 0 ? 'sel' : ''}`}>
                  <div className="ico"><Icon name={icon} size={30} /></div>
                  <div className="stat-v">{d.stats[k]}</div>
                  <div className="small muted">{label}</div>
                </Link>
              ))}
            </div>

            <div className="section-t"><div className="h2">Recommended projects</div><Link className="link" to="/projects">See all</Link></div>
            {d.recommended.length === 0 && <div className="card small muted">No open projects match you yet — add more skills in My Profile.</div>}
            <div className="grid g2">
              {d.recommended.map((p, i) => (
                <div key={p.id} className={`course ${i === 0 ? 'sel' : ''}`}>
                  <div className="col" style={{ gap: 10 }}>
                    <div className="t">{p.title}</div>
                    <div className="xs muted">{p.category} · {p.match}% match</div>
                    <Link to={`/projects/${p.id}`} className="btn primary sm" style={{ alignSelf: 'flex-start' }}>View</Link>
                  </div>
                  <div className="course-art" style={{ background: categoryArt(p.category).bg }}><img src={ill(categoryArt(p.category).art)} alt="" /></div>
                </div>
              ))}
            </div>

            <div className="section-t"><div className="h2">My teams</div><Link className="link" to="/teams">Manage</Link></div>
            <div className="card" style={{ padding: '6px 18px' }}>
              {d.my_teams.length === 0 && <div className="small muted" style={{ padding: 12 }}>You’re not in a team yet. <Link className="link" to="/projects">Find one</Link> or <Link className="link" to="/projects/new">create a project</Link>.</div>}
              {d.my_teams.map((p, i) => (
                <Link key={p.id} to={`/teams/${p.id}`} className="row between wrap" style={{ padding: '12px 0', borderTop: i ? '1px solid var(--line)' : 0 }}>
                  <div className="row"><div className="course-art" style={{ width: 52, height: 44, background: categoryArt(p.category).bg }}><img src={ill(categoryArt(p.category).art)} alt="" style={{ height: 38 }} /></div>
                    <div><div className="h3">{p.title}</div><div className="xs muted">{p.my_role === 'owner' ? 'Owner' : p.members.find((m) => m.id === profile?.id)?.role || 'Member'} · {p.members.length}/{p.max_size} members</div></div></div>
                  <div className="row"><div className="avs">{p.members.slice(0, 4).map((m) => <Avatar key={m.id} name={m.name} size={28} />)}</div><Status value={p.status} /></div>
                </Link>
              ))}
            </div>
          </div>

          <div className="col" style={{ width: 320, flexShrink: 0, gap: 22 }}>
            <div className="h2">Your teammates</div>
            {mates.length
              ? <div className="people">{mates.slice(0, 4).map((m) => <Link key={m.id} to={`/students/${m.id}`} title={`${m.name} · ${m.role}`}><Avatar name={m.name} size={64} /></Link>)}{mates.length > 4 && <Link to="/teams" className="more-mates">+{mates.length - 4}</Link>}</div>
              : <div className="small muted">Join or create a team to see your teammates here.</div>}
            <div className="card" style={{ gap: 10 }}>
              <div className="row between"><div className="h3">Profile strength</div><b style={{ color: 'var(--brand-700)' }}>{strength}%</b></div>
              <div className="bar"><div style={{ width: `${strength}%` }} /></div>
              <div className="xs muted">{strength < 100 ? 'Add more skills, a bio and interests to get better project matches.' : 'Your profile is complete — nice!'}</div>
              <div className="chips">{(profile?.skills || []).slice(0, 4).map((s) => <span key={s.name} className="chip have">{s.name}</span>)}<Link to="/profile" className="chip out">+ Edit profile</Link></div>
            </div>
            <div className="section-t"><div className="h2">Daily notice</div><Link className="link" to="/notifications">See all</Link></div>
            <div className="card" style={{ gap: 0, flex: 1 }}>
              {d.activity.map((n) => (
                <div key={n.id} className="notice">
                  <span className="dot" style={{ background: DOT[n.kind] || '#94a3b8' }} />
                  <div className="col" style={{ gap: 3 }}>
                    <div className="small" style={{ fontWeight: 500 }}>{n.text}</div>
                    <div className="xs muted">{timeAgo(n.created_at)}</div>
                  </div>
                </div>
              ))}
              <Link className="link small" to="/notifications">See more</Link>
            </div>
          </div>
        </div>
      </>
      );
    }}</AsyncView>
  );
}
