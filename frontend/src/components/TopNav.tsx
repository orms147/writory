import { NavLink, useNavigate } from 'react-router';
import { api } from '../api/client';
import { LOGIN_PATH, useAuth } from '../state/Auth';
import { maskedKey, usePlayerKey } from '../state/PlayerKey';
import { Logo, cx } from './ui';

const item = ({ isActive }: { isActive: boolean }) =>
  cx('wt-link inline-flex min-h-tap items-center text-[14px]', isActive ? 'text-ink-50' : 'text-ink-200');

/** Thanh trên của khung tối. Chế độ `invite`: tên người được mời và nút đăng xuất (D-89); chế độ
 *  `dev`: mọi người là người chơi dev (D-44). */
export function TopNav({ keyLabel = 'Khoá' }: { keyLabel?: string }) {
  const key = usePlayerKey();
  const auth = useAuth();
  const navigate = useNavigate();
  const hasKey = key.data?.has_key ?? false;
  const invite = auth.data?.mode === 'invite' && auth.data.logged_in;
  const logout = async () => {
    try {
      auth.set(await api.logout());
    } catch {
      auth.reload(); // máy chủ lỗi: đọc lại phiên thay vì đoán
    }
    navigate(LOGIN_PATH, { replace: true });
  };
  return (
    <header className="relative z-[2] mx-auto flex w-full max-w-[1440px] items-center justify-between gap-4 px-4 pt-5 md:px-[100px] md:pt-6">
      <Logo />
      <nav aria-label="Chính" className="flex items-center gap-5 md:gap-7">
        <NavLink to="/" end className={(s) => cx(item(s), 'max-md:hidden')}>
          Tủ truyện
        </NavLink>
        <NavLink to="/khoa" className={(s) => cx(item(s), !hasKey && key.data && 'text-cinnabar-200')}>
          {key.data === null ? keyLabel : hasKey ? `${keyLabel} ${maskedKey(key.data.last4, '••')}` : 'Chưa có khoá'}
        </NavLink>
        {invite ? (
          <>
            <span className="text-[14px] text-ink-200 max-md:hidden">{auth.data?.name}</span>
            <button type="button" onClick={logout} className="wt-link inline-flex min-h-tap items-center text-[14px] text-ink-200">
              Đăng xuất
            </button>
          </>
        ) : (
          <NavLink to={LOGIN_PATH} className={item} title="Máy chủ ở chế độ dev: bạn đang là người chơi dev">
            dev
          </NavLink>
        )}
      </nav>
    </header>
  );
}
