// แปลงเวลาเป็นข้อความอ่านง่าย เช่น "12 min ago", "Yesterday", "Oct 3"
export function timeAgo(iso) {
  const d = new Date(iso); const diff = (Date.now() - d.getTime()) / 60000;
  if (diff < 1) return 'Just now';
  if (diff < 60) return `${Math.round(diff)} min ago`;
  if (diff < 60 * 24) { const h = Math.round(diff / 60); return `${h} hour${h > 1 ? 's' : ''} ago`; }
  if (diff < 60 * 48) return 'Yesterday';
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}
export const fmtDate = (iso) => (iso ? new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—');
export const isToday = (iso) => new Date(iso).toDateString() === new Date().toDateString();

// ความแข็งแรงรหัสผ่าน 0-4
export function passwordScore(pw = '') {
  let s = 0;
  if (pw.length >= 8) s++;
  if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) s++;
  if (/\d/.test(pw)) s++;
  if (/[^A-Za-z0-9]/.test(pw)) s++;
  return s;
}
