import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { Link } from 'react-router';

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(' ');
}

export function Logo({ className }: { className?: string }) {
  return (
    <Link to="/" aria-label="WriTory, về tủ truyện" className={cx('inline-flex min-h-tap items-center', className)}>
      <span className="font-display text-[22px] font-semibold leading-none text-ink-50">Wri</span>
      <span className="font-display text-[22px] font-medium italic leading-none text-cinnabar-400">Tory</span>
    </Link>
  );
}

export function Kicker({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span className={cx('text-[12px] font-medium uppercase tracking-[.2em] text-ink-400', className)}>{children}</span>
  );
}

type Variant = 'primary' | 'ghost' | 'paper' | 'danger-ghost';

const VARIANT: Record<Variant, string> = {
  primary: 'wt-btn wt-btn-primary bg-cinnabar-600 text-on-cinnabar border border-cinnabar-600',
  ghost: 'wt-btn wt-btn-ghost border border-ink-600 text-ink-50 bg-transparent',
  paper: 'wt-btn wt-btn-paper border border-paper-400 text-paper-950 bg-transparent',
  'danger-ghost': 'wt-btn wt-btn-ghost border border-ink-600 text-cinnabar-200 bg-transparent',
};

const BASE =
  'inline-flex min-h-tap items-center justify-center gap-2 rounded-[12px] px-5 text-[15px] font-semibold disabled:cursor-not-allowed disabled:opacity-60';

export function Button({
  variant = 'primary',
  className,
  children,
  arrow,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; arrow?: boolean }) {
  return (
    <button type="button" {...rest} className={cx(BASE, VARIANT[variant], className)}>
      {children}
      {arrow && <Arrow />}
    </button>
  );
}

export function LinkButton({
  to,
  variant = 'primary',
  className,
  children,
  arrow,
}: {
  to: string;
  variant?: Variant;
  className?: string;
  children: ReactNode;
  arrow?: boolean;
}) {
  return (
    <Link to={to} className={cx(BASE, VARIANT[variant], className)}>
      {children}
      {arrow && <Arrow />}
    </Link>
  );
}

export function Arrow({ dir = 'right' }: { dir?: 'right' | 'left' | 'down' }) {
  const ch = dir === 'right' ? '→' : dir === 'left' ? '←' : '↓';
  return (
    <span className="wt-arrow" aria-hidden="true">
      {ch}
    </span>
  );
}

export function Dots({ className }: { className?: string }) {
  return (
    <span className={cx('inline-flex gap-[3px]', className)} aria-hidden="true">
      <span className="wt-dot" />
      <span className="wt-dot" />
      <span className="wt-dot" />
    </span>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <span aria-hidden="true" className={cx('wt-skeleton block', className)} />;
}

/** Đếm ký tự "12 / 200". `max` luôn từ `/config/public`; chưa đặt thì chỉ hiện số đã gõ. */
export function CharCount({ value, max, id, tone = 'dark' }: { value: string; max: number | null; id?: string; tone?: 'dark' | 'paper' }) {
  const over = max !== null && value.length > max;
  const muted = tone === 'paper' ? 'text-paper-700' : 'text-ink-400';
  return (
    <span id={id} className={cx('text-[12px] tabular-nums', over ? 'text-cinnabar-600' : muted)}>
      {max === null ? value.length : `${value.length} / ${max}`}
    </span>
  );
}

export function IconBook() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z" />
      <path d="M5 17a3 3 0 0 1 3-3h11" />
    </svg>
  );
}

export function IconChat() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 5h16v11H9l-5 4z" />
      <path d="M9 10h.01M12 10h.01M15 10h.01" />
    </svg>
  );
}

export function IconBack() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M15 6l-6 6 6 6" />
    </svg>
  );
}

export function IconClose() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}

export function IconCheck({ size = 12 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 12l5 5 9-10" />
    </svg>
  );
}

export function IconSend() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}

export function IconPen() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 20l4-1L19 8l-3-3L5 16z" />
    </svg>
  );
}
