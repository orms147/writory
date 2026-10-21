import { Link } from 'react-router';
import type { ApiError } from '../api/errors';
import {
  ACTION_LABEL,
  GROUP_ACTIONS,
  GROUP_KICKER,
  OPENROUTER_CREDITS_URL,
  errorGroup,
  type ErrorAction,
} from '../lib/errorGroups';
import { cx } from './ui';

export interface ErrorHandlers {
  onRetry?: () => void;
  onReload?: () => void;
  onBackToChoices?: () => void;
  onBackToReading?: () => void;
}

type Tone = 'dark' | 'paper';

const BTN =
  'wt-btn inline-flex min-h-tap items-center justify-center rounded-[10px] px-4 text-[14px] font-semibold';

function btnClass(primary: boolean, tone: Tone): string {
  if (primary) return cx(BTN, 'wt-btn-primary bg-cinnabar-600 text-on-cinnabar');
  return tone === 'paper'
    ? cx(BTN, 'wt-btn-paper border border-paper-400 text-paper-950')
    : cx(BTN, 'wt-btn-ghost border border-ink-600 text-ink-50');
}

function ActionButton({ action, primary, tone, handlers }: { action: ErrorAction; primary: boolean; tone: Tone; handlers: ErrorHandlers }) {
  const label = ACTION_LABEL[action];
  const cls = btnClass(primary, tone);
  switch (action) {
    case 'paste_key':
      return <Link className={cls} to="/khoa">{label}</Link>;
    case 'home':
      return <Link className={cls} to="/">{label}</Link>;
    case 'new_story':
      return <Link className={cls} to="/moi">{label}</Link>;
    case 'open_openrouter':
      return (
        <a className={cls} href={OPENROUTER_CREDITS_URL} target="_blank" rel="noreferrer noopener">
          {label} <span aria-hidden="true">↗</span>
          <span className="sr-only">(mở thẻ mới)</span>
        </a>
      );
    case 'retry':
      if (!handlers.onRetry) return null;
      return <button type="button" className={cls} onClick={handlers.onRetry}>{label}</button>;
    case 'reload':
      return (
        <button type="button" className={cls} onClick={handlers.onReload ?? (() => window.location.reload())}>
          {label}
        </button>
      );
    case 'back_to_choices': {
      const fn = handlers.onBackToChoices ?? handlers.onReload;
      if (!fn) return null;
      return <button type="button" className={cls} onClick={fn}>{label}</button>;
    }
    case 'back_to_reading':
      if (!handlers.onBackToReading) return null;
      return <button type="button" className={cls} onClick={handlers.onBackToReading}>{label}</button>;
  }
}

/** Khối lỗi: nhãn nhóm, nguyên văn `message` của máy chủ, nút theo `code`. Không hiện mã lỗi. */
export function ErrorBlock({
  error,
  tone = 'dark',
  className,
  sheetOnMobile = false,
  ...handlers
}: ErrorHandlers & { error: ApiError; tone?: Tone; className?: string; sheetOnMobile?: boolean }) {
  const group = errorGroup(error.code);
  const actions = GROUP_ACTIONS[group];
  const mobileSheet = sheetOnMobile && group === 'key';
  return (
    <section
      role="alert"
      data-error-group={group}
      className={cx(
        'rounded-[16px] border p-5 text-left',
        tone === 'paper' ? 'border-paper-400 bg-paper-100 text-paper-950' : 'border-ink-750 bg-ink-900 text-ink-50',
        mobileSheet &&
          'max-md:fixed max-md:inset-x-0 max-md:bottom-0 max-md:z-50 max-md:rounded-b-none max-md:rounded-t-[24px] max-md:border-ink-750 max-md:bg-ink-850 max-md:pb-8 max-md:text-ink-50 max-md:shadow-[0_-24px_60px_-20px_rgba(0,0,0,.8)]',
        className,
      )}
    >
      {mobileSheet && <span aria-hidden="true" className="mx-auto mb-4 block h-1 w-10 rounded-full bg-ink-600 md:hidden" />}
      <p className={cx('flex items-center gap-2 text-[12px]', tone === 'paper' ? 'text-paper-700' : 'text-ink-400')}>
        <span aria-hidden="true" className="h-[7px] w-[7px] rounded-full bg-cinnabar-400" />
        {GROUP_KICKER[group]}
      </p>
      <p className="mt-2 text-[15px] leading-relaxed">{error.message}</p>
      {actions.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {actions.map((a, i) => (
            <ActionButton key={a} action={a} primary={i === 0} tone={mobileSheet ? 'dark' : tone} handlers={handlers} />
          ))}
        </div>
      )}
    </section>
  );
}

/** Lỗi ngay dưới ô nhập (ô tự viết, ô hỏi người kể, sửa nhân vật): không mở hộp thoại. */
export function FieldError({ id, message, tone = 'dark' }: { id: string; message: string; tone?: Tone }) {
  return (
    <p id={id} role="alert" className={cx('mt-2 flex gap-2 text-[13px] leading-snug', tone === 'paper' ? 'text-cinnabar-700' : 'text-cinnabar-200')}>
      <span aria-hidden="true">!</span>
      <span>{message}</span>
    </p>
  );
}
