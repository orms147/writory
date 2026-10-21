import { NavLink } from 'react-router';
import { maskedKey, usePlayerKey } from '../state/PlayerKey';
import { Logo, cx } from './ui';

const item = ({ isActive }: { isActive: boolean }) =>
  cx('wt-link inline-flex min-h-tap items-center text-[14px]', isActive ? 'text-ink-50' : 'text-ink-200');

/** Thanh trên của khung tối. Chưa có đăng nhập: mọi người là người chơi dev (D-44). */
export function TopNav({ keyLabel = 'Khoá' }: { keyLabel?: string }) {
  const key = usePlayerKey();
  const hasKey = key.data?.has_key ?? false;
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
        <NavLink to="/dang-nhap" className={item} title="Chưa có đăng nhập: bạn đang là người chơi dev">
          dev
        </NavLink>
      </nav>
    </header>
  );
}
