import { Link } from 'react-router';
import { IconBack, IconBook, IconChat, cx } from '../../components/ui';
import { formatUsd } from '../../lib/format';

export type ReadingSize = 'sm' | 'md' | 'lg';
export const READING_SIZES: ReadingSize[] = ['sm', 'md', 'lg'];
export const READING_CLASS: Record<ReadingSize, string> = {
  sm: 'text-[17px] leading-[1.75]',
  md: 'text-[18px] leading-[1.75] md:text-[19px] md:leading-[1.8]',
  lg: 'text-[20px] leading-[1.8] md:text-[21px]',
};

/** Thanh trên của trang đọc (D-Doc) và thanh dưới trên điện thoại (M-Doc). Tiến độ chỉ là
 *  "Chương N" kèm khoảng chương cố định của mức độ dài (README bàn giao mục 4). */
export function ReaderHeader({
  title,
  chapter,
  sub,
  spentUsd,
  onNotebook,
  onNarrator,
  onCycleSize,
  narratorOpen,
}: {
  title: string;
  chapter: number;
  sub: string;
  spentUsd: number | null;
  onNotebook: () => void;
  onNarrator: () => void;
  onCycleSize: () => void;
  narratorOpen: boolean;
}) {
  return (
    <header className="sticky top-0 z-30 border-b border-[#26231F] bg-ink-950">
      <div className="flex items-center gap-3 px-3 py-2 md:gap-6 md:px-5 md:py-3">
        <Link to="/" aria-label="Về tủ truyện" className="wt-icon-btn grid min-h-tap min-w-tap place-items-center rounded-[10px] text-ink-200">
          <IconBack />
        </Link>
        <div className="min-w-0 flex-1 leading-tight lg:flex-none lg:basis-[260px]">
          <p className="truncate font-display text-[20px] font-semibold md:text-[22px]">{title}</p>
          <p className="truncate text-[12px] text-ink-400 lg:hidden">
            Chương {chapter} · {sub}
          </p>
        </div>
        <p className="hidden flex-1 items-baseline justify-center gap-3 whitespace-nowrap lg:flex">
          <span className="font-display text-[21px] font-semibold">Chương {chapter}</span>
          <span className="text-[12px] text-ink-400">{sub}</span>
        </p>
        <div className="flex items-center gap-1.5">
          {spentUsd !== null && (
            <span
              title="Chi phí đã dùng cho truyện này"
              className="hidden h-[34px] items-center whitespace-nowrap rounded-full border border-ink-700 px-3 text-[13px] tabular-nums text-ink-100 md:inline-flex"
            >
              Đã dùng {formatUsd(spentUsd)}
            </span>
          )}
          <button
            type="button"
            onClick={onCycleSize}
            aria-label="Đổi cỡ chữ trang đọc"
            className="wt-icon-btn grid min-h-tap min-w-tap place-items-center rounded-[10px] font-display text-[20px] font-semibold text-ink-100"
          >
            Aa
          </button>
          <button
            type="button"
            onClick={onNarrator}
            aria-label="Hỏi người kể"
            aria-pressed={narratorOpen}
            className={cx('wt-icon-btn hidden min-h-tap min-w-tap place-items-center rounded-[10px] text-ink-100 md:grid', narratorOpen && 'bg-ink-800')}
          >
            <IconChat />
          </button>
          <button
            type="button"
            onClick={onNotebook}
            className="wt-btn wt-btn-ghost hidden min-h-tap items-center gap-2 whitespace-nowrap rounded-[10px] border border-ink-600 px-4 text-[14px] font-medium md:inline-flex"
          >
            <IconBook />
            Sổ tay
          </button>
        </div>
      </div>
    </header>
  );
}

export function MobileReaderBar({
  spentUsd,
  onNotebook,
  onNarrator,
}: {
  spentUsd: number | null;
  onNotebook: () => void;
  onNarrator: () => void;
}) {
  return (
    <nav
      aria-label="Công cụ đọc"
      className="fixed inset-x-4 bottom-4 z-30 flex items-center rounded-[18px] bg-ink-900 text-ink-50 shadow-[0_20px_50px_-10px_rgba(0,0,0,.7)] md:hidden"
    >
      <button type="button" onClick={onNotebook} className="flex min-h-[56px] flex-1 items-center justify-center gap-2 text-[14px] font-semibold">
        <IconBook /> Sổ tay
      </button>
      <span aria-hidden="true" className="h-6 w-px bg-ink-700" />
      <button type="button" onClick={onNarrator} className="flex min-h-[56px] flex-1 items-center justify-center gap-2 text-[14px] font-semibold">
        <IconChat /> Hỏi người kể
      </button>
      {spentUsd !== null && (
        <>
          <span aria-hidden="true" className="h-6 w-px bg-ink-700" />
          <span className="px-4 text-[13px] tabular-nums text-ink-200" title="Chi phí đã dùng cho truyện này">
            {formatUsd(spentUsd)}
          </span>
        </>
      )}
    </nav>
  );
}
