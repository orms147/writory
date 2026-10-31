import { useEffect, useState, type ReactNode } from 'react';
import { Link } from 'react-router';
import type { ApiError } from '../../api/errors';
import type { StageEvent } from '../../api/types';
import { ErrorBlock, type ErrorHandlers } from '../../components/ErrorBlock';
import { Button, Dots, Kicker, cx } from '../../components/ui';
import { numberWords } from '../../lib/format';

/** Bước của màn chờ: mỗi nhãn máy chủ gửi là một vạch, theo thứ tự tới. Không vẽ bước chưa tới,
 *  không phần trăm (README bàn giao mục 4–5). */
export function stageSteps(stages: StageEvent[]): { key: string; label: string; scene: number | null }[] {
  const out: { key: string; label: string; scene: number | null }[] = [];
  for (const s of stages) {
    const key = `${s.stage}:${s.scene ?? ''}`;
    if (out.some((x) => x.key === key)) continue;
    out.push({ key, label: s.label, scene: s.scene });
  }
  return out;
}

function Elapsed({ since }: { since: number }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(t);
  }, []);
  const seconds = Math.max(0, Math.floor((now - since) / 1000));
  return (
    <span>
      Đã {seconds} giây · ngòi bút vẫn đang viết
    </span>
  );
}

/** Màn chờ cảnh đầu kiểu "Mục lục" (D-/M-Cho). `idle`: truyện mở lại ở chương chưa viết, chờ
 *  người chơi bấm viết (không tự gọi model khi chỉ mở trang). */
export function Waiting({
  title,
  chapter,
  stages,
  startedAt,
  chosen,
  error,
  idle,
  onStart,
  handlers,
  extra,
}: {
  title: string;
  chapter: number;
  stages: StageEvent[];
  startedAt: number | null;
  chosen: string | null;
  error: ApiError | null;
  idle: boolean;
  onStart?: () => void;
  handlers: ErrorHandlers;
  /** Hàng phụ dưới thanh trên (nút tải kịch bản của truyện audio). */
  extra?: ReactNode;
}) {
  const steps = stageSteps(stages);
  const word = numberWords(chapter);
  return (
    <main className="wt relative flex min-h-screen flex-col overflow-hidden px-4 pb-10 pt-5 md:px-[124px] md:pt-7">
      <header className="flex items-center justify-between gap-4 text-[13px] text-ink-200">
        <Link to="/" className="wt-link inline-flex min-h-tap items-center gap-1">
          <span aria-hidden="true">←</span> Mục lục
        </Link>
        <span className="truncate text-right">{title}</span>
      </header>
      {extra && <div className="mt-3 flex justify-end">{extra}</div>}

      <div className="mt-10 grid flex-1 content-center gap-10 md:mt-0 md:grid-cols-[1fr_440px] md:items-end md:gap-16">
        <h1 className="font-display font-medium leading-[0.85] text-ink-50">
          <span className="block text-[88px] md:text-[clamp(120px,14vw,200px)]">Chương</span>
          <span className="block text-[88px] italic text-cinnabar-400 md:text-[clamp(120px,14vw,200px)]">{word}</span>
        </h1>
        {chosen && (
          <div className="md:pb-6">
            <Kicker>Bạn đã chọn</Kicker>
            <p className="mt-3 font-reading text-[18px] italic leading-[1.7] text-ink-100 md:text-[20px]">{chosen}</p>
          </div>
        )}
      </div>

      <section aria-label="Tiến trình viết" className="mt-10">
        {error ? (
          <div className="max-w-[560px]">
            <ErrorBlock error={error} sheetOnMobile {...handlers} />
          </div>
        ) : idle ? (
          <div className="flex flex-wrap items-center gap-4 border-t border-ink-750 pt-6">
            <Button onClick={onStart} arrow>
              Viết chương {word}
            </Button>
            <span className="text-[13px] text-ink-400">Ngòi bút bắt đầu khi bạn bấm.</span>
          </div>
        ) : (
          <>
            <ol role="status" aria-live="polite" className="grid gap-4 sm:grid-cols-2 md:grid-cols-4">
              {steps.map((s, i) => {
                const active = i === steps.length - 1;
                return (
                  <li key={s.key} aria-current={active ? 'step' : undefined} className="min-w-0">
                    <span className="block h-[2px] w-full overflow-hidden rounded bg-ink-700">
                      <span className={cx('block h-full', active ? 'wt-flow w-full' : 'w-full bg-cinnabar-400')} />
                    </span>
                    <span className={cx('mt-3 flex items-center gap-2 text-[12px] uppercase tracking-[.14em]', active ? 'text-ink-50' : 'text-ink-400')}>
                      {s.scene !== null ? `Cảnh ${s.scene} · ` : ''}
                      {s.label}
                      {active && <Dots className="text-cinnabar-400" />}
                    </span>
                  </li>
                );
              })}
              {steps.length === 0 && (
                <li className="text-[13px] text-ink-400">
                  <Dots className="mr-2 text-cinnabar-400" />
                  Đang mở trang
                </li>
              )}
            </ol>
            <div className="mt-8 flex flex-col gap-2 border-t border-ink-750 pt-5 text-[14px] text-ink-200 md:flex-row md:justify-between">
              {startedAt !== null && <Elapsed since={startedAt} />}
              <span>Bạn có thể về mục lục trong lúc chờ; đóng thẻ thì ngòi bút dừng lại.</span>
            </div>
          </>
        )}
      </section>
    </main>
  );
}
