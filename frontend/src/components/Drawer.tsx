import { useEffect, useId, useRef, type ReactNode } from 'react';
import { IconClose, cx } from './ui';

/** Ngăn kéo bên phải (máy tính) / sheet từ dưới (điện thoại). Hộp thoại thật: Esc đóng, focus vào
 *  nút đóng khi mở, trả focus khi đóng. `overlay`: làm mờ trang phía sau (sổ tay). */
export function Drawer({
  open,
  onClose,
  title,
  kicker,
  children,
  footer,
  overlay = true,
  widthClass = 'md:w-[600px]',
  headerExtra,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  kicker?: string;
  children: ReactNode;
  footer?: ReactNode;
  overlay?: boolean;
  widthClass?: string;
  headerExtra?: ReactNode;
}) {
  const titleId = useId();
  const closeRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onCloseRef.current();
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      previous?.focus();
    };
  }, [open]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-40">
      {overlay ? (
        <button
          type="button"
          tabIndex={-1}
          aria-hidden="true"
          className="absolute inset-0 h-full w-full cursor-default bg-ink-950/60 backdrop-blur-[2px]"
          onClick={onClose}
        />
      ) : (
        <button
          type="button"
          tabIndex={-1}
          aria-hidden="true"
          className="absolute inset-0 h-full w-full cursor-default bg-ink-950/40 md:hidden"
          onClick={onClose}
        />
      )}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={cx(
          'wt-rise absolute flex flex-col border-ink-750 bg-ink-850 text-ink-50 shadow-[0_0_80px_-20px_rgba(0,0,0,.9)]',
          'inset-x-0 bottom-0 max-h-[90vh] min-h-[60vh] rounded-t-[24px] border-t',
          'md:inset-y-0 md:left-auto md:right-0 md:max-h-none md:min-h-0 md:rounded-none md:border-l md:border-t-0',
          widthClass,
        )}
      >
        <span aria-hidden="true" className="mx-auto mt-3 block h-1 w-10 rounded-full bg-ink-600 md:hidden" />
        <header className="flex items-start justify-between gap-4 px-5 pb-3 pt-4 md:px-6 md:pt-6">
          <div className="min-w-0">
            {kicker && <p className="text-[12px] font-medium uppercase tracking-[.2em] text-ink-400">{kicker}</p>}
            <h2 id={titleId} className="font-display text-[28px] font-semibold leading-tight md:text-[32px]">
              {title}
            </h2>
            {headerExtra}
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Đóng"
            className="wt-icon-btn grid min-h-tap min-w-tap place-items-center rounded-[10px] text-ink-200"
          >
            <IconClose />
          </button>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
        {footer && <footer className="border-t border-ink-750 px-5 py-4 md:px-6">{footer}</footer>}
      </div>
    </div>
  );
}
