import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { InkText } from '../../components/InkText';
import { Button, Dots, cx } from '../../components/ui';
import { capitalize, numberWords } from '../../lib/format';
import { usePrefersReducedMotion } from '../../lib/media';

// Trang giấy của một chương (D-/M-Doc, D-/M-DuoiKip). Cảnh hiện lần lượt: cảnh sau chỉ bắt đầu
// chạy chữ khi cảnh trước đã hiện hết. Chạm vào trang thì hiện hết ngay.

/** Số cảnh đã hiện hết của mỗi chương, giữ khi rời trang đọc rồi quay lại trong cùng phiên. */
const revealedByChapter = new Map<string, number>();

export interface Writing {
  scene: number | null;
  label: string;
}

export function writingText(w: Writing): string {
  return w.scene !== null ? `Cảnh ${w.scene} đang được viết` : w.label;
}

export function ChapterPage({
  revealKey,
  chapter,
  scenes,
  live,
  writing,
  sizeClass,
  footer,
  onNotebook,
  onNarrator,
}: {
  revealKey: string;
  chapter: number;
  scenes: string[];
  live: boolean;
  writing: Writing | null;
  sizeClass: string;
  footer?: ReactNode;
  onNotebook: () => void;
  onNarrator: () => void;
}) {
  const reduced = usePrefersReducedMotion();
  const animate = live && !reduced;
  const [revealed, setRevealed] = useState(() => (animate ? (revealedByChapter.get(revealKey) ?? 0) : scenes.length));
  const [fullUpTo, setFullUpTo] = useState(0);
  const [atEnd, setAtEnd] = useState(false);
  const sentinel = useRef<HTMLDivElement>(null);

  const shownRevealed = animate ? revealed : scenes.length;
  const allRevealed = shownRevealed >= scenes.length;

  const onSceneDone = useCallback(
    (i: number) => {
      setRevealed((r) => {
        const next = Math.max(r, i + 1);
        revealedByChapter.set(revealKey, next);
        return next;
      });
    },
    [revealKey],
  );

  useEffect(() => {
    const el = sentinel.current;
    if (!el) return;
    if (typeof IntersectionObserver === 'undefined') {
      setAtEnd(true);
      return;
    }
    const io = new IntersectionObserver((entries) => setAtEnd(entries.some((e) => e.isIntersecting)), { rootMargin: '0px 0px 80px 0px' });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  const revealAll = () => {
    if (!allRevealed) setFullUpTo(scenes.length);
  };

  const sceneMarks = scenes.map((_, i) => i + 1);
  const behind = live && allRevealed && writing !== null;

  return (
    <article
      data-paper="1"
      className="wt-grain wt-grain-paper relative mx-auto w-full max-w-reading rounded-t-[6px] bg-paper-50 px-6 pb-16 pt-8 text-paper-950 shadow-[0_0_0_1px_#2A2724,0_40px_80px_-40px_rgba(0,0,0,.9)] md:px-[clamp(24px,7vw,88px)] md:pt-[clamp(32px,6vw,72px)]"
    >
      <div className="mb-8 flex flex-col items-center gap-1.5 text-center md:mb-9">
        <h1 className="font-display text-[34px] font-semibold leading-[1.05] md:text-[46px]">{capitalize(`chương ${numberWords(chapter)}`)}</h1>
        <div className="mt-2 flex flex-wrap items-center justify-center gap-2.5 text-[12px] text-paper-700">
          <span aria-hidden="true" className="h-px w-7 bg-paper-400" />
          {sceneMarks.map((n) => (
            <span key={n} className="inline-flex items-center gap-1.5">
              <span aria-hidden="true" className="h-[7px] w-[7px] rounded-full bg-cinnabar-600" />
              Cảnh {n}
            </span>
          ))}
          {live && writing?.scene != null && writing.scene > scenes.length && (
            <span className="inline-flex items-center gap-1.5 text-paper-500">
              <span aria-hidden="true" className="wt-breathe h-[7px] w-[7px] rounded-full border border-cinnabar-600" />
              Cảnh {writing.scene} · đang viết
              {allRevealed && scenes.length > 0 && ` · bạn đã đọc hết cảnh ${scenes.length}`}
            </span>
          )}
          <span aria-hidden="true" className="h-px w-7 bg-paper-400" />
        </div>
      </div>

      <div
        className={cx('wt-reading font-reading [hyphens:auto]', sizeClass)}
        onClick={revealAll}
      >
        {scenes.slice(0, Math.min(scenes.length, shownRevealed + 1)).map((text, i) => (
          <div key={i} className={cx(i > 0 && 'mt-[0.9em]')}>
            <InkText
              text={text}
              animate={animate && i >= shownRevealed}
              revealAll={i < fullUpTo}
              onDone={() => onSceneDone(i)}
              dropCap={i === 0}
            />
          </div>
        ))}
      </div>
      {!allRevealed && (
        <div className="mt-6 flex justify-center">
          <button type="button" onClick={revealAll} className="wt-link min-h-tap text-[13px] text-paper-700">
            Hiện hết cảnh
          </button>
        </div>
      )}

      <div ref={sentinel} aria-hidden="true" />

      {live && writing && !behind && (
        <WritingLine writing={writing} />
      )}
      {behind && (atEnd ? <BehindPen writing={writing} onNotebook={onNotebook} onNarrator={onNarrator} /> : <WritingLine writing={writing} />)}

      {allRevealed && footer}
    </article>
  );
}

function WritingLine({ writing }: { writing: Writing }) {
  return (
    <div role="status" className="mt-12 flex flex-col items-center gap-3 border-t border-paper-400 pt-7 text-center">
      <svg width="40" height="12" viewBox="0 0 40 12" aria-hidden="true">
        <path d="M2 6 C10 1 14 11 20 6 C26 1 30 11 38 6" stroke="#B8432B" strokeWidth="1.6" fill="none" strokeLinecap="round" />
      </svg>
      <span className="flex items-center gap-2.5 text-[14px] text-paper-800">
        <Dots className="text-cinnabar-600" />
        {writingText(writing)}
      </span>
      <span aria-hidden="true" className="h-[2px] w-[220px] overflow-hidden rounded bg-paper-200">
        <span className="wt-flow block h-full w-full" />
      </span>
      {writing.scene !== null && (
        <span className="text-[13px] text-paper-700">Cảnh {writing.scene} sẽ hiện ngay dưới đây khi viết xong. Bạn cứ đọc thong thả.</span>
      )}
    </div>
  );
}

function BehindPen({ writing, onNotebook, onNarrator }: { writing: Writing; onNotebook: () => void; onNarrator: () => void }) {
  return (
    <div role="status" className="mt-10 rounded-[18px] bg-paper-200 px-6 py-8 text-center">
      <svg width="180" height="16" viewBox="0 0 180 16" aria-hidden="true" className="mx-auto">
        <path className="wt-draw" d="M2 9 C30 2 50 15 80 8 C110 2 130 14 178 6" stroke="#B8432B" strokeWidth="2" fill="none" strokeLinecap="round" />
      </svg>
      <h2 className="mt-4 font-display text-[30px] font-medium">Bạn đọc nhanh hơn ngòi bút</h2>
      <p className="mx-auto mt-2 max-w-[440px] text-[14px] text-paper-800">
        {writing.scene !== null ? `Cảnh ${writing.scene} đang được viết.` : `${writing.label}.`} Trang sẽ tự nối tiếp ngay dưới đây khi xong, bạn không cần làm gì.
      </p>
      <div className="mt-5 flex flex-wrap justify-center gap-2">
        <Button variant="paper" onClick={onNotebook}>
          Mở sổ tay trong lúc chờ
        </Button>
        <Button variant="paper" onClick={onNarrator}>
          Hỏi người kể
        </Button>
      </div>
    </div>
  );
}
