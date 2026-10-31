import type { ReactNode } from 'react';
import { Link } from 'react-router';
import { LinkButton } from '../../components/ui';
import { formatUsd } from '../../lib/format';

/** Truyện đã kết (D-/M-KetTruyen). Truyện đã khép nên số chương đã viết không còn là bí mật. */
export function Finished({
  storyId,
  title,
  meta,
  lastExcerpt,
  chapters,
  spentUsd,
  extra,
}: {
  storyId: string;
  title: string;
  meta: string;
  lastExcerpt: string | null;
  chapters: number;
  spentUsd: number | null;
  /** Hàng phụ dưới các nút (nút tải kịch bản của truyện audio). */
  extra?: ReactNode;
}) {
  return (
    <main className="wt relative min-h-screen overflow-hidden px-4 pb-16 pt-5 md:px-[100px] md:pt-6">
      <header className="flex items-center justify-between gap-4 text-[13px] text-ink-200">
        <Link to="/" className="wt-link inline-flex min-h-tap items-center gap-1">
          <span aria-hidden="true">←</span> Tủ truyện
        </Link>
        <span className="text-right">{meta}</span>
      </header>
      <section className="mx-auto mt-10 flex max-w-[760px] flex-col items-center text-center md:mt-12">
        <span className="wt-rise grid h-[112px] w-[112px] place-items-center rounded-[16px] border-[3px] border-cinnabar-400 font-display text-[36px] font-semibold text-cinnabar-400">
          Hết
        </span>
        <h1 className="wt-rise wt-d1 mt-6 font-display text-[44px] font-medium leading-[1.05] md:text-[60px]">{title}</h1>
        {lastExcerpt && (
          <blockquote className="wt-rise wt-d2 mt-5 max-w-[640px] font-reading text-[18px] italic leading-relaxed text-ink-100 md:text-[20px]">
            “{lastExcerpt}”
          </blockquote>
        )}
        <dl className="wt-rise wt-d3 mt-6 flex flex-wrap justify-center gap-x-7 gap-y-2 border-t border-ink-750 pt-5 text-[14px] text-ink-200">
          <div className="flex gap-1.5">
            <dt className="sr-only">Số chương</dt>
            <dd>
              <strong className="font-semibold text-ink-50">{chapters}</strong> chương
            </dd>
          </div>
          {spentUsd !== null && (
            <div className="flex gap-1.5">
              <dt>tổng chi phí</dt>
              <dd>
                <strong className="font-semibold text-ink-50">{formatUsd(spentUsd)}</strong>
              </dd>
            </div>
          )}
        </dl>
        <div className="wt-rise wt-d4 mt-7 flex flex-wrap justify-center gap-3">
          <LinkButton to={`/truyen/${encodeURIComponent(storyId)}/chuong/1`}>Đọc lại từ trang đầu</LinkButton>
          <LinkButton to="/moi" variant="ghost">
            Bắt đầu một đời mới
          </LinkButton>
        </div>
        {extra && <div className="wt-rise wt-d4 mt-6">{extra}</div>}
      </section>
    </main>
  );
}
