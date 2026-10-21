import { Link } from 'react-router';
import { IconBack, IconCheck, IconClose, cx } from '../../components/ui';

const STEPS = ['Khuôn truyện', 'Bối cảnh', 'Hướng truyện', 'Nhân vật'];

/** Thanh trên của khởi tạo: bốn bước cố định của luồng (không phải tiến độ truyện). */
export function SetupHeader({ step, back }: { step: number; back?: { to: string; label: string } | { onClick: () => void; label: string } }) {
  return (
    <header className="relative z-[2] border-b border-ink-750">
      <div className="mx-auto flex max-w-[1440px] items-center gap-4 px-4 py-3 md:px-[100px] md:py-4">
        {back && 'to' in back ? (
          <Link to={back.to} aria-label={back.label} className="wt-icon-btn grid min-h-tap min-w-tap place-items-center rounded-[10px] text-ink-200">
            {step === 1 ? <IconClose /> : <IconBack />}
          </Link>
        ) : back ? (
          <button type="button" onClick={back.onClick} aria-label={back.label} className="wt-icon-btn grid min-h-tap min-w-tap place-items-center rounded-[10px] text-ink-200">
            <IconBack />
          </button>
        ) : null}
        <p className="font-display text-[24px] font-medium max-md:hidden">Truyện mới</p>
        <p className="text-[14px] text-ink-200 md:hidden">
          Bước {step} / {STEPS.length} · {STEPS[step - 1]}
        </p>
        <ol className="ml-auto hidden items-center gap-5 md:flex" aria-label="Các bước tạo truyện">
          {STEPS.map((label, i) => {
            const n = i + 1;
            const done = n < step;
            const current = n === step;
            return (
              <li key={label} aria-current={current ? 'step' : undefined} className={cx('flex items-center gap-2 text-[14px]', current ? 'font-semibold text-ink-50' : 'text-ink-200')}>
                <span
                  aria-hidden="true"
                  className={cx(
                    'grid h-[26px] w-[26px] place-items-center rounded-full border text-[12px]',
                    current ? 'border-cinnabar-600 bg-cinnabar-600 text-on-cinnabar' : done ? 'border-ink-700 bg-ink-800 text-ink-100' : 'border-ink-600 text-ink-200',
                  )}
                >
                  {done ? <IconCheck /> : n}
                </span>
                {label}
                {done && <span className="sr-only"> (đã xong)</span>}
              </li>
            );
          })}
        </ol>
      </div>
      <span aria-hidden="true" className="absolute bottom-[-1px] left-0 h-[2px] bg-cinnabar-400" style={{ width: `${((step - 1) / (STEPS.length - 1)) * 100 || 6}%` }} />
    </header>
  );
}
