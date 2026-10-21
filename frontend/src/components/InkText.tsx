import { useEffect, useMemo, useRef, useState } from 'react';
import { paragraphs } from '../lib/format';
import { cx } from './ui';

// Chữ chạy dần phía client (README bàn giao mục 5): máy chủ gửi trọn chữ của cảnh; ở đây hiện từng
// từ, cụm mới mờ → nét. `animate=false` (đọc lại, giảm chuyển động) hoặc `revealAll` thì hiện đủ
// ngay. Chữ hiện đúng nguyên văn, kể cả dấu thoại "- " (D-31): chỉ tách đoạn, không đổi ký tự.

const STEP_MS = 38; // nhịp chữ chạy (hoạt cảnh, không phải số liệu nghiệp vụ)
const FRESH = 6; // số từ cuối còn đang "ngấm mực"

interface Props {
  text: string;
  animate: boolean;
  revealAll: boolean;
  onDone?: () => void;
  dropCap?: boolean;
}

export function InkText({ text, animate, revealAll, onDone, dropCap = false }: Props) {
  const paras = useMemo(() => paragraphs(text).map((p) => p.match(/\S+\s*/g) ?? []), [text]);
  const total = useMemo(() => paras.reduce((n, p) => n + p.length, 0), [paras]);
  const full = !animate || revealAll;
  const [shown, setShown] = useState(full ? total : 0);
  const doneRef = useRef(false);
  const onDoneRef = useRef(onDone);
  onDoneRef.current = onDone;

  const visible = full ? total : shown;
  const done = visible >= total;

  useEffect(() => {
    if (full || done) return;
    const t = window.setInterval(() => setShown((n) => Math.min(total, n + 1)), STEP_MS);
    return () => window.clearInterval(t);
  }, [full, done, total]);

  useEffect(() => {
    if (done && !doneRef.current) {
      doneRef.current = true;
      onDoneRef.current?.();
    }
  }, [done]);

  if (done) {
    return (
      <>
        {paras.map((words, i) => (
          <p key={i} className={cx(dropCap && i === 0 && 'wt-dropcap')}>
            {words.join('').trimEnd()}
          </p>
        ))}
      </>
    );
  }

  let offset = 0;
  return (
    <>
      <div className="sr-only">
        {paras.map((words, i) => (
          <p key={i}>{words.join('').trimEnd()}</p>
        ))}
      </div>
      <div aria-hidden="true">
        {paras.map((words, i) => {
          const start = offset;
          offset += words.length;
          if (start >= visible) return null;
          const count = Math.min(words.length, visible - start);
          const freshFrom = Math.max(0, visible - FRESH - start);
          const settled = words.slice(0, Math.min(count, freshFrom)).join('');
          const fresh = words.slice(Math.min(count, freshFrom), count);
          const isCurrent = start + count === visible;
          return (
            <p key={i} className={cx(dropCap && i === 0 && 'wt-dropcap')}>
              {settled}
              {fresh.map((w, j) => (
                <span key={start + freshFrom + j} className="wt-ink-word">
                  {w}
                </span>
              ))}
              {isCurrent && <span className="wt-caret" />}
            </p>
          );
        })}
      </div>
    </>
  );
}
