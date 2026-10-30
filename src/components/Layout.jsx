import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth, displayName } from '../auth/AuthContext';
import { Avatar } from './ui';
import Icon from './Icon';

// [path, label, icon, ชื่อตัวเลขใน counts]
const MENU = [
  ['/', 'Dashboard', 'dashboard'],
  ['/projects', 'Explore Projects', 'compass'],
  ['/teammates', 'Find Teammates', 'users'],
  ['/requests', 'Requests', 'inbox', 'pending_requests'],
  ['/teams', 'My Teams', 'folder'],
  ['/notifications', 'Notifications', 'bell', 'unread_notifications'],
  ['/profile', 'My Profile', 'user'],
];

export default function Layout() {
  const { user, profile, counts, isAdmin, logout } = useAuth();
  const nav = useNavigate();
  const name = displayName(profile, user);
  const subtitle = isAdmin ? 'Administrator' : profile ? [profile.major, profile.year && `Year ${profile.year}`].filter(Boolean).join(' · ') : '';
  return (
    <div className="app">
      <aside className="side">
        <div className="logo"><div className="logo-mark"><Icon name="graduation" size={38} /></div>TeamUp</div>
        <nav className="nav">
          {MENU.map(([to, label, icon, countKey]) => (
            <NavLink key={to} to={to} end={to === '/' || to === '/projects'}>
              <Icon name={icon} />{label}{countKey && counts[countKey] > 0 && <span className="cnt">{counts[countKey]}</span>}
            </NavLink>
          ))}
          {isAdmin && <NavLink to="/admin"><Icon name="shield" />Admin Panel</NavLink>}
        </nav>
        <NavLink to="/projects/new" className="btn cta"><Icon name="plus" size={18} /> New Project</NavLink>
        <div className="me" style={{ marginTop: 0 }}>
          <Icon name="logout" />
          <button style={{ color: '#fff', fontWeight: 500 }} onClick={async () => { await logout(); nav('/login'); }}>Logout</button>
        </div>
      </aside>
      <div className="main">
        <header className="top">
          <label className="search"><Icon name="search" size={18} /><input placeholder="Search projects, skills or students..." onKeyDown={(e) => e.key === 'Enter' && nav(`/projects?q=${encodeURIComponent(e.currentTarget.value)}`)} /></label>
          <div className="top-r">
            <NavLink to="/notifications" className="btn secondary sm"><Icon name="bell" size={18} /></NavLink>
            <div className="who">
              <Avatar name={name} size={42} i={0} />
              <div><b>{name}</b><small>{subtitle}</small></div>
            </div>
          </div>
        </header>
        <main className="content"><Outlet /></main>
      </div>
    </div>
  );
}
