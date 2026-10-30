import Icon from './Icon';
import { useEffect, useState } from 'react';
import { avatarUri, cachedAvatar, ill } from './art';
// ชิ้นส่วน UI ที่ใช้ซ้ำทุกหน้า (ตรงกับ component ใน Figma)

export const initials = (name = '') => name.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase();

export function Avatar({ name = '', size = 36 }) {
  const [src, setSrc] = useState(() => cachedAvatar(name));
  useEffect(() => { let on = true; avatarUri(name).then((u) => on && setSrc(u)); return () => { on = false; }; }, [name]);
  const style = { width: size, height: size };
  // ระหว่างโหลดภาพ แสดงวงกลมตัวย่อชื่อไปก่อน
  if (!src) return <div className="av av-ph" style={{ ...style, fontSize: size * 0.36 }} title={name}>{initials(name)}</div>;
  return <img className="av" src={src} alt={name} title={name} width={size} height={size} style={style} />;
}

export function Button({ variant = 'primary', size, block, children, ...rest }) {
  return <button className={['btn', variant, size, block && 'block'].filter(Boolean).join(' ')} {...rest}>{children}</button>;
}

export const Chip = ({ kind = '', children }) => <span className={`chip ${kind}`}>{children}</span>;

const STATUS_LABEL = { recruiting: 'Recruiting', full: 'Team complete', closed: 'Not recruiting', open: 'Open', pending: 'Pending', accepted: 'Accepted', rejected: 'Rejected' };
export const Status = ({ value, label }) => <span className={`status ${value === 'recruiting' ? 'rec' : value}`}>{label || STATUS_LABEL[value] || value}</span>;

export function Match({ value }) {
  const k = value >= 80 ? 'hi' : value >= 60 ? 'mid' : 'lo';
  return <span className={`match ${k}`}><Icon name="sparkle" size={13} stroke={2.2} /> {value}% match</span>;
}

export const Bar = ({ value }) => <div className="bar"><div style={{ width: `${value}%` }} /></div>;

export function Loading({ label = 'Loading…' }) {
  return <div className="state"><div className="spinner" /><span>{label}</span></div>;
}

export function Empty({ title, children }) {
  return <div className="state"><img className="state-art" src={ill('empty')} alt="" /><div className="h3" style={{ color: 'var(--text)' }}>{title}</div><div>{children}</div></div>;
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="state">
      <img className="state-art" src={ill('error')} alt="" />
      <div className="h3" style={{ color: 'var(--text)' }}>Something went wrong</div>
      <div>{error?.message || 'Please try again.'}</div>
      {onRetry && <Button variant="secondary" size="sm" onClick={onRetry}>Try again</Button>}
    </div>
  );
}

// แสดง loading / error ให้อัตโนมัติ แล้วค่อยเรียก children(data)
export function AsyncView({ state, children }) {
  if (state.loading) return <Loading />;
  if (state.error) return <ErrorState error={state.error} onRetry={state.reload} />;
  return children(state.data);
}

// หัวหน้าแบบธรรมดา หรือแบบ banner มีภาพประกอบ (ใส่ art) และสีประจำหน้า (tone)
export function PageHeader({ title, subtitle, actions, art, tone = 'navy', eyebrow }) {
  if (!art) {
    return (
      <div className="ph">
        <div><div className="h1">{title}</div>{subtitle && <div className="sub">{subtitle}</div>}</div>
        {actions && <div className="row">{actions}</div>}
      </div>
    );
  }
  return (
    <section className={`page-hero tone-${tone}`}>
      <div className="page-hero-text">
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <div className="h1">{title}</div>
        {subtitle && <div className="sub">{subtitle}</div>}
        {actions && <div className="row wrap" style={{ marginTop: 14 }}>{actions}</div>}
      </div>
      <img className="page-hero-art" src={ill(art)} alt="" />
    </section>
  );
}

// สวิตช์เปิด/ปิด (ตาม Figma: Open for join requests, Email notifications)
export function Toggle({ checked, onChange, label }) {
  return (
    <button type="button" role="switch" aria-checked={checked} aria-label={label}
      className={`toggle ${checked ? '' : 'off'}`} onClick={() => onChange(!checked)}><span className="knob" /></button>
  );
}

// ปุ่มเลือกแบบกลุ่ม (Best match / Newest / Most spots ...)
export function Segmented({ options, value, onChange, small }) {
  return (
    <div className={`seg ${small ? 'sm' : ''}`}>
      {options.map(([v, label]) => (
        <button type="button" key={v} className={v === value ? 'on' : ''} onClick={() => onChange(v)}>{label}</button>
      ))}
    </div>
  );
}

// กล่องข้อความลอย (ใช้กับ Report project, ยืนยันการลบ)
export function Modal({ title, children, onClose }) {
  return (
    <div className="modal-bg" onClick={onClose}>
      <div className="modal card" onClick={(e) => e.stopPropagation()} role="dialog" aria-label={title}>
        <div className="row between"><div className="h2">{title}</div><button type="button" className="muted" onClick={onClose} aria-label="Close"><Icon name="x" size={18} /></button></div>
        {children}
      </div>
    </div>
  );
}

// การ์ดหัวข้อพร้อมลิงก์ด้านขวา
export function Section({ title, right, children, style }) {
  return (
    <div className="card" style={style}>
      <div className="row between"><div className="h2">{title}</div>{right}</div>
      {children}
    </div>
  );
}
