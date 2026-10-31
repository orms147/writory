import { Link } from 'react-router';
import { api } from '../api/client';
import type { StorySummary } from '../api/types';
import { ErrorBlock } from '../components/ErrorBlock';
import { TopNav } from '../components/TopNav';
import { Kicker, Skeleton, cx } from '../components/ui';
import { lengthText, usePublicConfig } from '../config/PublicConfig';
import { capitalize, formatUsd, numberWords, relativeTime, roman } from '../lib/format';
import { useResource } from '../lib/useResource';
import { isRunning, useAnyRun } from '../state/chapterRun';
import { maskedKey, usePlayerKey } from '../state/PlayerKey';
import { AudioBadge } from './story/AudioScript';

// Tủ truyện kiểu "Mục lục" (D-/M-ThuVien, D-ThuVienRong, M-Rong): chữ lớn, số La Mã, không thẻ.

function storyStatus(s: StorySummary, first: boolean, now: Date): { text: string; tone: string } {
  if (s.finished) return { text: `Đã khép · ${s.chapter} chương`, tone: 'text-ink-200' };
  if (isRunning(s.story_id)) return { text: `Đang viết chương ${numberWords(s.chapter + 1)}`, tone: 'text-cinnabar-200' };
  if (s.chapter === 0) return { text: 'Chưa viết trang nào', tone: 'text-cinnabar-200' };
  if (first) return { text: `Chương ${s.chapter} · đọc tiếp`, tone: 'text-cinnabar-200' };
  const when = relativeTime(s.updated_at, now);
  return { text: when ? `Chương ${s.chapter} · ${when}` : `Chương ${s.chapter}`, tone: 'text-ink-200' };
}

function summaryLine(stories: StorySummary[]): string {
  const done = stories.filter((s) => s.finished).length;
  const open = stories.length - done;
  const parts = [`${capitalize(numberWords(stories.length))} cuốn.`];
  if (done && open) parts.push(`${capitalize(numberWords(done))} cuốn đã khép, ${numberWords(open)} cuốn còn viết dở.`);
  else if (done) parts.push('Cuốn nào cũng đã khép.');
  else parts.push('Cuốn nào cũng còn viết dở.');
  return parts.join(' ');
}

function Numeral({ n, accent }: { n: number; accent?: boolean }) {
  return (
    <span aria-hidden="true" className={cx('font-display text-[24px] italic md:text-[28px]', accent ? 'text-cinnabar-400' : 'text-ink-500')}>
      {roman(n)}.
    </span>
  );
}

export function Library() {
  const config = usePublicConfig();
  const key = usePlayerKey();
  const stories = useResource(() => api.stories(), 'stories');
  const costs = useResource(() => api.costs(), 'costs');
  useAnyRun();
  const now = new Date();

  const list = stories.data?.stories ?? null;
  const hasKey = key.data?.has_key ?? false;
  const level = (k: string) => config.story_lengths.find((l) => l.key === k) ?? null;
  const firstOpen = list?.findIndex((s) => !s.finished && s.chapter > 0) ?? -1;

  return (
    <main className="wt relative min-h-screen overflow-hidden pb-16">
      <TopNav />
      <div className="mx-auto w-full max-w-[1440px] px-4 md:px-[100px]">
        <section className="mt-10 flex flex-col gap-6 border-b border-ink-750 pb-6 md:mt-12 md:flex-row md:items-end md:justify-between md:pb-0">
          <h1 className="font-display font-medium leading-[0.85] text-ink-50">
            <span className="text-[84px] md:text-[150px]">Mục </span>
            <span className="text-[84px] italic text-cinnabar-400 max-md:block md:text-[150px]">lục</span>
          </h1>
          <div className="max-w-[340px] md:pb-12">
            <Kicker>Tủ truyện của bạn</Kicker>
            <p className="mt-2 text-[15px] leading-relaxed text-ink-200">
              {list === null ? '' : list.length === 0 ? 'Tủ còn trống. Trang đầu tiên của một đời khác đang chờ bạn.' : summaryLine(list)}
            </p>
          </div>
        </section>

        {stories.error && <ErrorBlock className="mt-8" error={stories.error} onRetry={stories.reload} />}

        {list === null && !stories.error && (
          <div className="mt-8 flex flex-col gap-6" aria-busy="true">
            <Skeleton className="h-12 w-2/3" />
            <Skeleton className="h-12 w-1/2" />
          </div>
        )}

        {list !== null && (
          <ol className="border-ink-750">
            {list.length === 0 && (
              <li className="border-b border-ink-750">
                <Link to="/khoa" className="wt-row grid min-h-[120px] grid-cols-[48px_1fr] items-center gap-x-4 py-6 md:grid-cols-[100px_1fr_auto] md:py-8">
                  <Numeral n={1} accent={!hasKey} />
                  <span>
                    <span className="block font-display text-[32px] font-medium leading-tight md:text-[52px]">
                      {hasKey ? 'Khoá OpenRouter đã sẵn' : 'Dán khoá OpenRouter'}
                    </span>
                    <span className="mt-1 block text-[14px] text-ink-200">
                      Bạn trả phí gọi model qua tài khoản OpenRouter của mình. Khoá được mã hoá khi lưu.
                    </span>
                  </span>
                  <span className={cx('col-start-2 mt-2 text-[14px] md:col-start-auto md:mt-0', hasKey ? 'text-jade-200' : 'text-cinnabar-200')}>
                    {hasKey ? `đã có khoá ${maskedKey(key.data?.last4 ?? null, '••')}` : 'chưa có khoá'}
                  </span>
                </Link>
              </li>
            )}
            {list.map((s, i) => {
              const status = storyStatus(s, i === firstOpen, now);
              const showExcerpt = !s.finished && s.last_excerpt && i === firstOpen;
              return (
                <li key={s.story_id} className="border-b border-ink-750">
                  <Link
                    to={`/truyen/${encodeURIComponent(s.story_id)}`}
                    className="wt-row group grid grid-cols-[48px_1fr] items-start gap-x-4 md:items-center py-6 md:grid-cols-[88px_1fr_210px_170px_32px] md:py-8"
                  >
                    <Numeral n={i + 1} accent={i === firstOpen} />
                    <span className="min-w-0">
                      <span className="block font-display text-[32px] font-medium leading-[1.05] md:text-[52px]">{s.title}</span>
                      {showExcerpt && (
                        <span className="mt-2 block font-reading text-[15px] italic text-ink-100">“{s.last_excerpt}”</span>
                      )}
                    </span>
                    <span className="col-start-2 mt-2 text-[13px] text-ink-200 md:col-start-auto md:mt-0">
                      {lengthText(level(s.length_level), s.length_label)}
                      {s.style === 'audio' && <AudioBadge label="Audio" className="ml-2 align-middle" />}
                    </span>
                    <span className={cx('col-start-2 text-[14px] md:col-start-auto', status.tone)}>{status.text}</span>
                    <span aria-hidden="true" className="hidden text-ink-500 transition-transform group-hover:translate-x-1 md:block">
                      →
                    </span>
                  </Link>
                </li>
              );
            })}
            <li className="border-b border-ink-750">
              {list.length === 0 && !hasKey ? (
                <div aria-disabled="true" className="grid min-h-[120px] grid-cols-[48px_1fr] items-center gap-x-4 py-6 md:grid-cols-[100px_1fr_auto] md:py-8">
                  <Numeral n={2} />
                  <span>
                    <span className="block font-display text-[30px] italic text-ink-200 md:text-[48px]">Mở một trang chưa viết</span>
                    <span className="mt-1 block text-[14px] text-ink-200">Chọn thể loại, độ dài và nhân vật cho truyện đầu tiên.</span>
                  </span>
                  <span className="col-start-2 mt-2 text-[13px] text-ink-400 md:col-start-auto md:mt-0">sau khi có khoá</span>
                </div>
              ) : (
                <Link to="/moi" className="wt-row grid min-h-[96px] grid-cols-[48px_1fr_auto] items-center gap-x-4 py-6 md:grid-cols-[100px_1fr_40px] md:py-8">
                  <Numeral n={list.length + (list.length === 0 ? 2 : 1)} />
                  <span className="font-display text-[30px] italic text-ink-200 md:text-[40px]">Mở một trang chưa viết</span>
                  <span aria-hidden="true" className="text-cinnabar-400">
                    +
                  </span>
                </Link>
              )}
            </li>
          </ol>
        )}

        {costs.data && (
          <p className="mt-6 text-right text-[13px] text-ink-400">Tháng này đã dùng {formatUsd(costs.data.this_month_usd)}</p>
        )}
      </div>
    </main>
  );
}
