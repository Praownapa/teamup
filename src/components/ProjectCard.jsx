import { Link } from 'react-router-dom';
import { Avatar, Chip, Match, Status } from './ui';
import Icon from './Icon';
import { categoryArt, ill } from './art';

export default function ProjectCard({ p }) {
  const have = p.skills.filter(([, h]) => h).length;
  const cover = categoryArt(p.category);
  return (
    <div className="card pcard" style={{ gap: 14, padding: 0, overflow: 'hidden' }}>
      <div className="pcover" style={{ background: p.cover_url ? `center/cover url(${p.cover_url})` : cover.bg }}>
        {!p.cover_url && <img src={ill(cover.art)} alt="" />}
        <Match value={p.match} />
      </div>
      <div className="col" style={{ gap: 14, padding: '0 20px 20px' }}>
      <div className="row between">
        <span className="xs muted" style={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.6px' }}>{p.category}</span>
      </div>
      <div className="col" style={{ gap: 6 }}>
        <div className="h3" style={{ fontSize: 17 }}>{p.title}</div>
        <div className="small muted" style={{ lineHeight: 1.5 }}>{p.description}</div>
      </div>
      <div className="chips">{p.skills.map(([s, h]) => <Chip key={s} kind={h ? 'have' : 'miss'}>{s}</Chip>)}</div>
      <div className="small muted row" style={{ gap: 6 }}><Icon name="checkCircle" size={16} style={{ color: "var(--ok)" }} />You have {have} of {p.skills.length} required skills</div>
      <div className="divider" />
      <div className="row between">
        <div className="row" style={{ gap: 10 }}>
          <div className="avs">{p.members.slice(0, 4).map((m) => <Avatar key={m.id} name={m.name} size={28} />)}</div>
          <span className="xs muted">{p.members.length}/{p.max_size} members</span>
        </div>
        <Status value={p.status} />
      </div>
      <div className="row">
        <Link className="btn secondary sm" to={`/projects/${p.id}`}>View details</Link>
        {p.my_role ? <Link className="btn ghost sm" to={`/teams/${p.id}`}>{p.my_role === 'owner' ? 'Manage team' : 'Your team'}</Link>
          : p.my_request ? <span className="status pending">Request sent</span>
          : p.status === 'recruiting'
            ? <Link className="btn primary sm" to={`/projects/${p.id}#join`}>Request to Join</Link>
            : <button className="btn secondary sm" disabled>Closed</button>}
      </div>
      </div>
    </div>
  );
}
