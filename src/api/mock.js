// ข้อมูลจำลองแบบ "ระบบจริงย่อส่วน": user / project / request เชื่อมกันด้วย id
// รูปแบบข้อมูลที่ส่งออกตรงกับที่ backend ต้องส่ง (ดู README) จึงสลับไปใช้ API จริงได้โดยไม่ต้องแก้หน้าจอ
const wait = (ms = 250) => new Promise((r) => setTimeout(r, ms));
const clone = (x) => JSON.parse(JSON.stringify(x));
const now = Date.now();
const ago = (min) => new Date(now - min * 60000).toISOString();
const ME = 1;
let seq = 1000;

// ---------------- users ----------------
const users = [
  { id: 1, name: 'John Carter', email: '6600123456@student.uni.ac.th', student_id: '6600123456', major: 'Digital Engineering', year: 3, role: 'admin', status: 'active',
    bio: 'UI/UX-focused developer who loves turning messy requirements into clean interfaces.', portfolio: 'github.com/johncarter', open_to_projects: true,
    skills: [{ name: 'React', level: 'Advanced' }, { name: 'UI/UX Design', level: 'Advanced' }, { name: 'Figma', level: 'Advanced' }, { name: 'JavaScript', level: 'Intermediate' }, { name: 'Python', level: 'Intermediate' }, { name: 'SQL', level: 'Beginner' }],
    interests: ['Web Development', 'Sustainability', 'EdTech'],
    notify: { invitations: true, requests: true, team: false, digest: true } },
  { id: 2, name: 'Emma Wilson', major: 'Computer Engineering', year: 3, skills: ['FastAPI', 'PostgreSQL', 'Python'] },
  { id: 3, name: 'Lucas Brown', major: 'Digital Engineering', year: 2, skills: ['SQL', 'Pytest', 'Python'] },
  { id: 4, name: 'Daniel Ortiz', major: 'Computer Engineering', year: 4, skills: ['AWS', 'Docker', 'Linux'] },
  { id: 5, name: 'Oliver Smith', major: 'Computer Engineering', year: 3, skills: ['React', 'JavaScript', 'Figma'] },
  { id: 6, name: 'Sophia Martinez', major: 'Digital Engineering', year: 3, skills: ['Figma', 'UI/UX Design', 'React'] },
  { id: 7, name: 'Ethan Johnson', major: 'Information Technology', year: 2, skills: ['React', 'Node.js', 'SQL'] },
  { id: 8, name: 'Liam Garcia', major: 'Computer Engineering', year: 4, skills: ['UI/UX Design', 'Flutter', 'Python'] },
  { id: 9, name: 'Ava Thompson', major: 'Digital Engineering', year: 2, skills: ['JavaScript', 'Vue.js', 'CSS'] },
  { id: 10, name: 'Noah Davis', major: 'Industrial Engineering', year: 3, skills: ['UI/UX Design', 'Research'] },
  { id: 11, name: 'Grace Hall', major: 'Data Science', year: 3, skills: ['Python', 'Pandas', 'D3.js'] },
  { id: 12, name: 'Ryan King', major: 'Computer Engineering', year: 2, skills: ['JavaScript', 'React'] },
  { id: 13, name: 'Henry Moore', major: 'Business Technology', year: 4, skills: ['Figma', 'Product'] },
  { id: 14, name: 'Chloe Kim', major: 'Computer Engineering', year: 3, skills: ['Flutter', 'Firebase'] },
  { id: 15, name: 'Mia Turner', major: 'Mechanical Engineering', year: 4, skills: ['C++', 'Arduino', 'CAD'] },
  { id: 16, name: 'Leo Adams', major: 'Electrical Engineering', year: 3, skills: ['Arduino', 'C++'] },
  { id: 17, name: 'Zoe Baker', major: 'Computer Engineering', year: 3, skills: ['Python', 'C++'] },
  { id: 18, name: 'Jack Scott', major: 'Information Technology', year: 2, skills: ['Node.js', 'Firebase'], status: 'suspended' },
].map((u) => ({ status: 'active', role: 'student', email: `${6600000000 + u.id * 111}@student.uni.ac.th`, student_id: String(6600000000 + u.id * 111), ...u,
  skills: u.skills.map((s) => (typeof s === 'string' ? { name: s, level: 'Intermediate' } : s)) }));
const user = (id) => users.find((u) => u.id === id);
const mySkills = () => user(ME).skills.map((s) => s.name.toLowerCase());

// ---------------- projects ----------------
// roles: ตำแหน่งในทีม user_id = null คือยังว่าง | members: ใครอยู่ในทีมบ้าง
const projects = [
  { id: 1, title: 'Campus Food Waste Tracker', category: 'Course Project', course: 'DES424 Cloud-based App Dev', owner_id: ME, max_size: 5, accepting: true,
    description: 'Canteens on campus throw away a surprising amount of food every day, but nobody measures it. We’re building a web app where canteen staff log leftovers in under 30 seconds and everyone sees weekly dashboards. Goal: cut food waste by 20% this semester.',
    skills: ['React', 'FastAPI', 'PostgreSQL', 'AWS'], duration: 'Aug – Dec 2026', meeting: 'On campus, 2× / week', deadline: '2026-11-30', created_at: ago(60 * 24 * 26),
    roles: [{ name: 'UI/UX Designer', user_id: ME }, { name: 'Backend Developer', user_id: 2 }, { name: 'Data & QA', user_id: 3 }, { name: 'Cloud Engineer', user_id: 4 }, { name: 'Frontend Developer', user_id: null }] },
  { id: 2, title: 'AI Study Buddy Chatbot', category: 'Competition', course: 'National AI Hackathon', owner_id: 5, max_size: 4, accepting: true,
    description: 'An LLM-powered chatbot that turns lecture slides into quizzes and flashcards for exam revision.',
    skills: ['Python', 'NLP', 'React', 'UI/UX Design'], duration: 'Oct – Nov 2026', meeting: 'Online, weekends', deadline: '2026-11-10', created_at: ago(60 * 24 * 9),
    roles: [{ name: 'ML Engineer', user_id: 5 }, { name: 'Backend Developer', user_id: 6 }, { name: 'UI/UX Designer', user_id: ME }, { name: 'Frontend Developer', user_id: null }] },
  { id: 3, title: 'Smart Parking IoT System', category: 'Senior Project', owner_id: 7, max_size: 5, accepting: true,
    description: 'Sensor network that shows free parking spots around campus in real time via a mobile web app.',
    skills: ['Python', 'IoT', 'AWS', 'SQL'], duration: 'Full academic year', meeting: 'Lab, Tue & Thu', deadline: '2026-12-15', created_at: ago(60 * 24 * 14),
    roles: [{ name: 'IoT Engineer', user_id: 7 }, { name: 'Backend Developer', user_id: 8 }, { name: 'Data Analyst', user_id: 9 }, { name: 'Hardware', user_id: 10 }, { name: 'Cloud Engineer', user_id: null }] },
  { id: 4, title: 'City Air Quality Viz', category: 'Research', owner_id: 11, max_size: 3, accepting: true,
    description: 'Interactive map visualizing PM2.5 history and forecasts for city districts using open data.',
    skills: ['Python', 'Pandas', 'D3.js', 'JavaScript'], duration: '8 weeks', meeting: 'Online, flexible', deadline: '2026-11-20', created_at: ago(60 * 24 * 3),
    roles: [{ name: 'Data Scientist', user_id: 11 }, { name: 'Frontend Developer', user_id: 12 }, { name: 'Data Analyst', user_id: null }] },
  { id: 5, title: 'Mobile Health Reminder', category: 'Startup Idea', owner_id: 13, max_size: 4, accepting: true,
    description: 'Medication and appointment reminder app for elderly users with caregiver notifications.',
    skills: ['Flutter', 'Figma', 'UI/UX Design', 'Firebase'], duration: 'Ongoing', meeting: 'Co-working space, Fridays', deadline: '2026-12-01', created_at: ago(60 * 5),
    roles: [{ name: 'Product Lead', user_id: 13 }, { name: 'Mobile Developer', user_id: 14 }, { name: 'UI/UX Designer', user_id: null }, { name: 'Backend Developer', user_id: null }] },
  { id: 6, title: 'Robotics Challenge Team', category: 'Competition', owner_id: 15, max_size: 3, accepting: false,
    description: 'Build an autonomous line-following robot for the national university robotics challenge.',
    skills: ['C++', 'Arduino', 'CAD', 'Python'], duration: 'Sep – Dec 2026', meeting: 'Workshop, daily', deadline: '2026-10-01', created_at: ago(60 * 24 * 40),
    roles: [{ name: 'Team Lead', user_id: 15 }, { name: 'Hardware', user_id: 16 }, { name: 'Software', user_id: 17 }] },
];
const project = (id) => projects.find((p) => p.id === Number(id));
const memberIds = (p) => p.roles.filter((r) => r.user_id).map((r) => r.user_id);
const isFull = (p) => memberIds(p).length >= p.max_size;
const statusOf = (p) => (isFull(p) ? 'full' : p.accepting ? 'recruiting' : 'closed');
const matchOf = (skills, have = mySkills()) => (skills.length ? Math.round((100 * skills.filter((s) => have.includes(s.toLowerCase())).length) / skills.length) : 0);

// ---------------- requests & invitations ----------------
// type: request = นักศึกษาขอเข้าทีม | invitation = เจ้าของทีมเชิญนักศึกษา
let requests = [
  { id: 1, type: 'request', project_id: 1, user_id: 5, role: 'Frontend Developer', message: 'I’ve built two React dashboards for my internship and would love to help with the charts.', created_at: ago(12), status: 'pending' },
  { id: 2, type: 'request', project_id: 1, user_id: 7, role: 'Frontend Developer', message: 'I want to improve my React skills on a real project.', created_at: ago(180), status: 'pending' },
  { id: 3, type: 'invitation', project_id: 5, user_id: ME, by_id: 13, role: 'UI/UX Designer', message: 'Your Figma portfolio is great — we need someone to design our reminder screens!', created_at: ago(60), status: 'pending' },
  { id: 4, type: 'request', project_id: 6, user_id: ME, role: 'Software', message: 'I can help with the dashboard for sensor data.', created_at: ago(60 * 24 * 26), status: 'rejected' },
  { id: 5, type: 'request', project_id: 1, user_id: 3, role: 'Data & QA', message: 'Happy to own testing.', created_at: ago(60 * 24 * 21), status: 'accepted' },
  { id: 6, type: 'invitation', project_id: 1, user_id: 6, by_id: ME, role: 'Frontend Developer', message: 'Would love your help on the dashboard UI.', created_at: ago(60 * 24), status: 'pending' },
];

// ---------------- notifications ----------------
let notifications = [
  { id: 1, kind: 'request', request_id: 1, text: 'Oliver Smith requested to join Campus Food Waste Tracker as Frontend Developer.', created_at: ago(12), unread: true },
  { id: 2, kind: 'invite', request_id: 3, text: 'Henry Moore invited you to join Mobile Health Reminder as UI/UX Designer.', created_at: ago(60), unread: true },
  { id: 3, kind: 'request', request_id: 2, text: 'Ethan Johnson requested to join Campus Food Waste Tracker as Frontend Developer.', created_at: ago(180), unread: true },
  { id: 4, kind: 'accepted', text: 'Your request to join AI Study Buddy Chatbot was accepted. Say hi to your new team!', created_at: ago(60 * 26), unread: false },
  { id: 5, kind: 'team', text: 'Lucas Brown joined Campus Food Waste Tracker as Data & QA.', created_at: ago(60 * 24 * 2), unread: false },
  { id: 6, kind: 'declined', text: 'Your request to join Robotics Challenge Team was declined. The team is now complete.', created_at: ago(60 * 24 * 26), unread: false },
  { id: 7, kind: 'match', text: '3 new projects match your skills: React, UI/UX Design, Figma.', created_at: ago(60 * 24 * 27), unread: false },
];
const notify = (kind, text, extra = {}) => notifications.unshift({ id: ++seq, kind, text, created_at: new Date().toISOString(), unread: true, ...extra });

// ---------------- admin data ----------------
let categories = ['Course Project', 'Competition', 'Senior Project', 'Startup Idea', 'Research'];
let reports = [
  { id: 1, project: 'Easy A — We Do Your Assignment', owner: 'user_4412', reason: 'Academic dishonesty', reporters: 3, created_at: ago(60 * 20), status: 'open' },
  { id: 2, project: 'CRYPTO PUMP GROUP', owner: 'newuser_99', reason: 'Spam / scam', reporters: 5, created_at: ago(60 * 40), status: 'open' },
  { id: 3, project: 'test test test', owner: 'Chloe Kim', reason: 'Invalid / empty', reporters: 1, created_at: ago(60 * 24 * 3), status: 'open' },
  { id: 4, project: 'Hackathon team – need 10 people', owner: 'Jack Scott', reason: 'Misleading info', reporters: 2, created_at: ago(60 * 24 * 4), status: 'open' },
];
const saved = new Set([2]);

// ---------------- views (รูปแบบที่ส่งให้หน้าจอ) ----------------
const brief = (u) => ({ id: u.id, name: u.name, major: u.major, year: u.year });
function projectView(p) {
  const myReq = requests.find((r) => r.project_id === p.id && r.user_id === ME && r.type === 'request' && r.status === 'pending');
  const have = mySkills();
  return {
    id: p.id, title: p.title, category: p.category, course: p.course, description: p.description, cover_url: p.cover_url || '',
    owner: brief(user(p.owner_id)), max_size: p.max_size, accepting: p.accepting, status: statusOf(p), created_at: p.created_at,
    duration: p.duration, meeting: p.meeting, deadline: p.deadline, saved: saved.has(p.id),
    skills: p.skills.map((s) => [s, have.includes(s.toLowerCase())]), match: matchOf(p.skills),
    roles: p.roles.map((r) => ({ name: r.name, user: r.user_id ? brief(user(r.user_id)) : null })),
    members: p.roles.filter((r) => r.user_id).map((r) => ({ ...brief(user(r.user_id)), role: r.name, owner: r.user_id === p.owner_id, skills: user(r.user_id).skills.map((s) => s.name) })),
    open_roles: p.roles.filter((r) => !r.user_id).map((r) => r.name),
    my_role: p.owner_id === ME ? 'owner' : memberIds(p).includes(ME) ? 'member' : null,
    my_request: myReq ? { id: myReq.id, role: myReq.role, status: myReq.status } : null,
    pending_requests: requests.filter((r) => r.project_id === p.id && r.type === 'request' && r.status === 'pending').length,
    pending_invitations: requests.filter((r) => r.project_id === p.id && r.type === 'invitation' && r.status === 'pending').length,
  };
}
function requestView(r) {
  const p = project(r.project_id); const u = user(r.user_id);
  const type = r.type === 'invitation' ? (r.user_id === ME ? 'invitation' : 'sent') : (r.user_id === ME ? 'sent' : 'received');
  return {
    id: r.id, type, kind: r.type, status: r.status, role: r.role, message: r.message, created_at: r.created_at,
    project: { id: p.id, title: p.title, open_spots: p.max_size - memberIds(p).length },
    student: brief(u), by: r.by_id ? brief(user(r.by_id)) : null,
    match: matchOf(p.skills, u.skills.map((s) => s.name.toLowerCase())),
  };
}
function meView() {
  const u = user(ME);
  return { ...clone(u), teams: projects.filter((p) => memberIds(p).includes(ME)).map((p) => ({ id: p.id, title: p.title, is_owner: p.owner_id === ME, status: statusOf(p) })),
    stats: { teams: projects.filter((p) => memberIds(p).includes(ME)).length, projects: projects.filter((p) => p.owner_id === ME).length, skills: u.skills.length } };
}

// ---------------- API ----------------
export async function getMe() { await wait(); return meView(); }
export async function updateMe(data) { await wait(); Object.assign(user(ME), clone(data)); return meView(); }
export async function getUser(id) {
  await wait(); const u = user(Number(id)); if (!u) throw new Error('Student not found');
  return { ...brief(u), bio: u.bio || '', skills: u.skills, interests: u.interests || [], teams: projects.filter((p) => memberIds(p).includes(u.id)).map((p) => ({ id: p.id, title: p.title })) };
}
export async function getCounts() {
  await wait(120);
  return { pending_requests: requests.filter((r) => r.status === 'pending' && ((r.type === 'request' && project(r.project_id).owner_id === ME) || (r.type === 'invitation' && r.user_id === ME))).length,
    unread_notifications: notifications.filter((n) => n.unread).length };
}
export async function getDashboard() {
  await wait();
  const mine = projects.filter((p) => memberIds(p).includes(ME));
  const others = projects.filter((p) => !memberIds(p).includes(ME) && statusOf(p) === 'recruiting');
  const c = await getCounts();
  return {
    stats: { teams: mine.length, pending: requests.filter((r) => r.status === 'pending' && r.type === 'request' && project(r.project_id).owner_id === ME).length,
      invitations: requests.filter((r) => r.status === 'pending' && r.type === 'invitation' && r.user_id === ME).length,
      matches: others.filter((p) => matchOf(p.skills) >= 50).length, unread: c.unread_notifications },
    recommended: others.map(projectView).sort((a, b) => b.match - a.match).slice(0, 2),
    my_teams: mine.map(projectView), activity: clone(notifications.slice(0, 4)),
  };
}
export async function listProjects({ q = '', categories: cats = '', skills = '', role = '', recruiting = '', spots = '', sort = 'match' } = {}) {
  await wait();
  const cs = cats ? cats.split(',') : []; const ks = skills ? skills.toLowerCase().split(',') : [];
  let list = projects.map(projectView).filter((p) =>
    (!q || `${p.title} ${p.description} ${p.skills.map((s) => s[0]).join(' ')}`.toLowerCase().includes(q.toLowerCase()))
    && (!cs.length || cs.includes(p.category))
    && (!ks.length || ks.every((k) => p.skills.some(([s]) => s.toLowerCase().includes(k))))
    && (!role || p.open_roles.some((r) => r === role))
    && (recruiting !== 'true' || p.status === 'recruiting')
    && (spots !== 'true' || p.max_size - p.members.length >= 2));
  const by = { match: (a, b) => b.match - a.match, newest: (a, b) => b.created_at.localeCompare(a.created_at), spots: (a, b) => (b.max_size - b.members.length) - (a.max_size - a.members.length) };
  return list.sort(by[sort] || by.match);
}
export async function listFilterOptions() {
  await wait(100);
  return { categories: categories.map((c) => ({ name: c, count: projects.filter((p) => p.category === c).length })),
    roles: [...new Set(projects.flatMap((p) => p.roles.filter((r) => !r.user_id).map((r) => r.name)))].sort() };
}
export async function getProject(id) { await wait(); const p = project(id); if (!p) throw new Error('Project not found'); return projectView(p); }
export async function createProject(data) {
  await wait(400);
  const roles = [{ name: data.owner_role || 'Project Owner', user_id: ME }];
  (data.roles || []).forEach((r) => { for (let i = 0; i < (r.spots || 1); i++) roles.push({ name: r.name, user_id: null }); });
  const p = { id: ++seq, owner_id: ME, accepting: data.accepting !== false, created_at: new Date().toISOString(), duration: data.duration || '—', meeting: data.meeting || '—',
    title: data.title, category: data.category, course: data.course, description: data.description, cover_url: data.cover_url, max_size: Math.max(data.max_size, roles.length), deadline: data.deadline, skills: data.skills, roles };
  projects.unshift(p); return projectView(p);
}
export async function updateProject(id, data) { await wait(); Object.assign(project(id), data); return projectView(project(id)); }
export async function toggleSave(id) { await wait(150); saved.has(Number(id)) ? saved.delete(Number(id)) : saved.add(Number(id)); return { saved: saved.has(Number(id)) }; }
export async function reportProject(id, reason) { await wait(); reports.unshift({ id: ++seq, project: project(id).title, owner: user(project(id).owner_id).name, reason, reporters: 1, created_at: new Date().toISOString(), status: 'open' }); return { ok: true }; }
export async function requestToJoin(id, { role, message }) {
  await wait(400); const p = project(id);
  if (statusOf(p) !== 'recruiting') throw new Error('This team is no longer accepting requests.');
  if (requests.some((r) => r.project_id === p.id && r.user_id === ME && r.status === 'pending')) throw new Error('You already have a pending request for this project.');
  requests.unshift({ id: ++seq, type: 'request', project_id: p.id, user_id: ME, role, message, created_at: new Date().toISOString(), status: 'pending' });
  return projectView(p);
}
export async function cancelRequest(id) { await wait(); requests = requests.filter((r) => r.id !== Number(id)); return null; }
export async function getRecommendedStudents(projectId) {
  await wait(); const p = project(projectId);
  const inTeam = memberIds(p); const open = p.roles.filter((r) => !r.user_id).map((r) => r.name);
  return users.filter((u) => !inTeam.includes(u.id) && u.status === 'active').map((u) => {
    const have = u.skills.map((s) => s.name.toLowerCase());
    const fits = open.find((r) => (/front/i.test(r) && have.some((s) => /react|javascript|vue/.test(s))) || (/ui/i.test(r) && have.some((s) => /figma|ui/.test(s))) || (/cloud/i.test(r) && have.includes('aws'))) || open[0] || '—';
    const invited = requests.some((r) => r.project_id === p.id && r.user_id === u.id && r.type === 'invitation' && r.status === 'pending');
    return { ...brief(u), match: matchOf(p.skills, have), fits, invited, skills: u.skills.map((s) => [s.name, p.skills.map((x) => x.toLowerCase()).includes(s.name.toLowerCase())]) };
  }).filter((s) => s.match > 0 || s.fits !== '—').sort((a, b) => b.match - a.match);
}
export async function inviteStudent(projectId, userId, role) {
  await wait(300);
  requests.unshift({ id: ++seq, type: 'invitation', project_id: Number(projectId), user_id: userId, by_id: ME, role, message: '', created_at: new Date().toISOString(), status: 'pending' });
  return { ok: true };
}
export async function getTeam(id) { return getProject(id); }
export async function changeMemberRole(projectId, userId, role) {
  await wait(); const p = project(projectId);
  const cur = p.roles.find((r) => r.user_id === userId); const target = p.roles.find((r) => r.name === role && !r.user_id);
  if (target) { target.user_id = userId; cur.user_id = null; } else cur.name = role;
  return projectView(p);
}
export async function removeMember(projectId, userId) {
  await wait(); const p = project(projectId); const r = p.roles.find((x) => x.user_id === userId);
  if (r) r.user_id = null; notify('team', `${user(userId).name} was removed from ${p.title}.`); return projectView(p);
}
export async function leaveTeam(projectId) {
  await wait(); const p = project(projectId); const r = p.roles.find((x) => x.user_id === ME); if (r) r.user_id = null; return null;
}
export async function listRequests() {
  await wait();
  return requests.filter((r) => r.user_id === ME || project(r.project_id).owner_id === ME || r.by_id === ME).map(requestView);
}
export async function respondRequest(id, accept) {
  await wait(300); const r = requests.find((x) => x.id === Number(id)); const p = project(r.project_id);
  if (accept && isFull(p)) throw new Error('The team is already full.');
  r.status = accept ? 'accepted' : 'rejected';
  if (accept) {
    const slot = p.roles.find((x) => !x.user_id && x.name === r.role) || p.roles.find((x) => !x.user_id);
    if (slot) slot.user_id = r.user_id; else p.roles.push({ name: r.role, user_id: r.user_id });
    // ทีมเต็มแล้ว: ปฏิเสธคำขอที่เหลือให้อัตโนมัติ
    if (isFull(p)) requests.filter((x) => x.project_id === p.id && x.status === 'pending').forEach((x) => { x.status = 'rejected'; });
  }
  notifications.forEach((n) => { if (n.request_id === r.id) n.unread = false; });
  return requestView(r);
}
export async function listNotifications() { await wait(); return clone(notifications); }
export async function markRead(id) { await wait(80); const n = notifications.find((x) => x.id === Number(id)); if (n) n.unread = false; return null; }
export async function markAllRead() { await wait(150); notifications = notifications.map((n) => ({ ...n, unread: false })); return null; }
export async function getUploadUrl() { await wait(); return { upload_url: null, file_url: '' }; }

// ---------------- admin ----------------
export async function adminOverview(period = '30d') {
  await wait();
  const f = { '7d': 0.3, '30d': 1, semester: 3.2 }[period] || 1;
  return {
    stats: { students: users.length + 1230, projects: 382, teams: 214, reports: reports.filter((r) => r.status === 'open').length,
      deltas: { students: Math.round(86 * f), projects: Math.round(41 * f), teams: Math.round(29 * f) } },
    activity: [40, 55, 48, 70, 62, 85, 78, 92, 66, 74, 88, 96].map((v, i) => ({ week: `W${i + 1}`, requests: Math.round(v * f), projects: Math.round(v * 0.5 * f) })),
    categories: categories.map((c) => ({ name: c, count: projects.filter((p) => p.category === c).length * 27 + 12 })),
    reports: clone(reports.filter((r) => r.status === 'open')),
    users: users.map((u) => ({ ...brief(u), email: u.email, student_id: u.student_id, role: u.role, status: u.status, projects: projects.filter((p) => memberIds(p).includes(u.id)).length })),
  };
}
export async function adminResolveReport(id, action) { await wait(); const r = reports.find((x) => x.id === id); r.status = action; return null; }
export async function adminSetUserStatus(id, status) { await wait(); user(id).status = status; return null; }
export async function adminAddCategory(name) { await wait(); if (!categories.includes(name)) categories.push(name); return null; }
export async function adminDeleteCategory(name) { await wait(); categories = categories.filter((c) => c !== name); return null; }
