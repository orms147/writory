import { createContext, useContext, type ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router';
import { api } from '../api/client';
import type { AuthSession } from '../api/types';
import { ErrorBlock } from '../components/ErrorBlock';
import { useResource, type Resource } from '../lib/useResource';

// Phiên đăng nhập (D-89). Máy chủ quyết chế độ: `dev` thì không cần đăng nhập; `invite` thì chưa
// đăng nhập là về `/dang-nhap`. Token chỉ nằm trong cookie HttpOnly: trang không đọc, không lưu gì.

const AuthContext = createContext<Resource<AuthSession> | null>(null);

export const LOGIN_PATH = '/dang-nhap';

export function AuthProvider({ children }: { children: ReactNode }) {
  const res = useResource(() => api.session(), 'auth-session');
  return <AuthContext.Provider value={res}>{children}</AuthContext.Provider>;
}

/** Cho test: cấp phiên có sẵn. */
export function AuthValue({ value, children }: { value: AuthSession; children: ReactNode }) {
  const res: Resource<AuthSession> = { data: value, error: null, loading: false, reload: () => {}, set: () => {} };
  return <AuthContext.Provider value={res}>{children}</AuthContext.Provider>;
}

export function useAuth(): Resource<AuthSession> {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth ngoài AuthProvider');
  return value;
}

/** Ở chế độ `invite`, chưa đăng nhập thì chuyển về màn đăng nhập (trừ chính màn đó). */
export function RequireLogin({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const location = useLocation();
  if (auth.error) {
    return (
      <main className="wt relative grid min-h-screen place-items-center px-4">
        <ErrorBlock error={auth.error} onRetry={auth.reload} />
      </main>
    );
  }
  if (!auth.data) {
    return (
      <main className="wt relative min-h-screen" aria-busy="true">
        <span className="sr-only" role="status">
          Đang tải
        </span>
      </main>
    );
  }
  const needsLogin = auth.data.mode === 'invite' && !auth.data.logged_in;
  if (needsLogin && location.pathname !== LOGIN_PATH) return <Navigate to={LOGIN_PATH} replace />;
  return <>{children}</>;
}
