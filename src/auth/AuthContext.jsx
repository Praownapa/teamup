import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import * as cognito from './cognito';
import { routeGate } from './route-gate';
import { api } from '../api/endpoints';
import { ErrorState, Loading } from '../components/ui';

const AuthCtx = createContext(null);
const NO_COUNTS = { pending_requests: 0, unread_notifications: 0 };

export function AuthProvider({ children }) {
  const [user, setUser] = useState(undefined);   // จาก Cognito: undefined = กำลังเช็ก, null = ยังไม่ login
  const [profile, setProfile] = useState(null);   // จาก backend: ชื่อ สาขา ชั้นปี ทีมของฉัน
  const [profileError, setProfileError] = useState(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const activeUser = useRef(user);
  activeUser.current = user;
  const [counts, setCounts] = useState(NO_COUNTS); // ตัวเลขบนเมนู

  useEffect(() => { cognito.enforceRemember().then(() => cognito.currentUser()).then(setUser); }, []);

  const refreshProfile = useCallback(async () => {
    const owner = activeUser.current;
    setProfileLoading(true); setProfileError(null);
    try { const next = await api.getMe(); if (owner === activeUser.current) setProfile(next); }
    catch (error) { if (owner === activeUser.current) { setProfile(null); setProfileError(error); } }
    finally { if (owner === activeUser.current) setProfileLoading(false); }
  }, []);
  const refreshCounts = useCallback(async () => { const owner = activeUser.current; try { const next = await api.getCounts(); if (owner === activeUser.current) setCounts(next); } catch { /* retried on next refresh */ } }, []);

  // login แล้วค่อยโหลดข้อมูลผู้ใช้ และล้างข้อมูลเมื่อ logout
  useEffect(() => {
    if (user) { refreshProfile(); refreshCounts(); }
    else { setProfile(null); setCounts(NO_COUNTS); setProfileError(null); setProfileLoading(false); }
  }, [user, refreshProfile, refreshCounts]);

  const isAdmin = !!user?.groups?.includes('admin') || profile?.role === 'admin';
  const value = {
    user, profile, profileError, profileLoading, counts, isAdmin, refreshProfile, refreshCounts,
    async login(email, password, remember = true) {
      const r = await cognito.signIn(email, password);
      cognito.setRemember(remember);
      if (r.done) setUser(await cognito.currentUser());
      return r;
    },
    async logout() { await cognito.signOut(); setUser(null); },
  };
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);

// ชื่อที่ใช้แสดง: โปรไฟล์จาก backend ก่อน ถ้ายังไม่มีใช้ชื่อหรืออีเมลจาก Cognito
export function displayName(profile, user) {
  return profile?.name || user?.name || user?.email?.split('@')[0] || '';
}

export function ProtectedRoute({ children, adminOnly = false }) {
  const { user, profile, profileError, refreshProfile, isAdmin } = useAuth();
  const loc = useLocation();
  const gate = routeGate({ user, profile, profileError, adminOnly, isAdmin });
  if (gate === 'loading') return <Loading />;
  if (gate === 'login') return <Navigate to="/login" state={{ from: loc.pathname }} replace />;
  if (gate === 'error') return <ErrorState error={profileError} onRetry={refreshProfile} />;
  if (gate === 'home') return <Navigate to="/" replace />;
  return children;
}
