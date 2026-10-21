import { useEffect, useId, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { api } from '../../api/client';
import { asApiError, type ApiError } from '../../api/errors';
import { Drawer } from '../../components/Drawer';
import { ErrorBlock, FieldError } from '../../components/ErrorBlock';
import { CharCount, Dots, IconSend, cx } from '../../components/ui';
import { usePublicConfig } from '../../config/PublicConfig';
import { errorGroup } from '../../lib/errorGroups';
import { useResource } from '../../lib/useResource';

// Hỏi người kể (D-/M-HoiNguoiKe): không câu hỏi gợi ý; câu trả lời hiện nguyên văn; số câu còn lại
// và nguồn do máy chủ trả (D-65).

interface Message {
  id: number;
  who: 'me' | 'narrator';
  text: string;
  sources?: number[];
}

export function sourceText(chapters: number[]): string | null {
  if (chapters.length === 0) return null;
  return `Từ chương ${[...chapters].sort((a, b) => a - b).join(', ')}`;
}

export function NarratorPanel({
  storyId,
  chapter,
  open,
  onClose,
}: {
  storyId: string;
  chapter: number;
  open: boolean;
  onClose: () => void;
}) {
  return (
    <Drawer open={open} onClose={onClose} title="Hỏi người kể" overlay={false} widthClass="md:w-[400px]">
      {open && <NarratorBody storyId={storyId} chapter={chapter} onClose={onClose} />}
    </Drawer>
  );
}

function NarratorBody({ storyId, chapter, onClose }: { storyId: string; chapter: number; onClose: () => void }) {
  const config = usePublicConfig();
  const max = config.input.narrator_question_max_chars;
  const quota = useResource(() => api.narratorQuota(storyId), `${storyId}:${chapter}`);
  const [remaining, setRemaining] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [limitError, setLimitError] = useState<ApiError | null>(null);
  const seq = useRef(0);
  const listEnd = useRef<HTMLDivElement>(null);
  const inputId = useId();
  const countId = useId();
  const errId = useId();

  useEffect(() => {
    if (quota.data) setRemaining(quota.data.remaining);
  }, [quota.data]);

  useEffect(() => {
    listEnd.current?.scrollIntoView({ block: 'end' });
  }, [messages, pending]);

  const left = remaining ?? quota.data?.remaining ?? null;
  const exhausted = limitError !== null || left === 0;
  const fieldError = error && errorGroup(error.code) === 'narrator_input' ? error : null;
  const blockError = error && !fieldError ? error : null;

  const send = async (e?: FormEvent) => {
    e?.preventDefault();
    const q = question;
    if (pending || exhausted) return;
    setError(null);
    seq.current += 1;
    const mine: Message = { id: seq.current, who: 'me', text: q };
    setMessages((m) => [...m, mine]);
    setQuestion('');
    setPending(true);
    try {
      const out = await api.askNarrator(storyId, q);
      seq.current += 1;
      setMessages((m) => [...m, { id: seq.current, who: 'narrator', text: out.answer, sources: out.source_chapters }]);
      setRemaining(out.remaining);
    } catch (err) {
      const apiErr = asApiError(err);
      setMessages((m) => m.filter((x) => x.id !== mine.id));
      setQuestion(q);
      if (errorGroup(apiErr.code) === 'narrator_limit') setLimitError(apiErr);
      else setError(apiErr);
    } finally {
      setPending(false);
    }
  };

  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      void send();
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-ink-750 px-5 pb-4 md:px-6">
        <p className="text-[13px] leading-snug text-ink-200">
          Không tốn lượt chơi. Người kể chỉ đáp từ những gì bạn đã biết.
        </p>
        <p role="status" aria-live="polite" className={cx('mt-1 text-[13px]', exhausted ? 'text-cinnabar-200' : 'text-ink-200')}>
          {left === null ? '' : exhausted ? 'Đã hết lượt hỏi trong chương này' : `Còn ${left} câu hỏi trong chương này`}
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-5 md:px-6" aria-live="polite">
        <ul className="flex flex-col gap-3">
          {messages.map((m) =>
            m.who === 'me' ? (
              <li key={m.id} className="max-w-[85%] self-end rounded-[14px] bg-ink-800 px-4 py-3 text-[14px] text-ink-50">
                <span className="sr-only">Bạn hỏi: </span>
                {m.text}
              </li>
            ) : (
              <li key={m.id} className="max-w-[90%] self-start rounded-[14px] bg-paper-50 px-4 py-3 text-paper-950">
                <span className="sr-only">Người kể: </span>
                <p className="font-reading text-[15px] leading-relaxed">{m.text}</p>
                {m.sources && sourceText(m.sources) && <p className="mt-2 text-[12px] text-paper-700">{sourceText(m.sources)}</p>}
              </li>
            ),
          )}
          {pending && (
            <li className="self-start rounded-[14px] bg-paper-50 px-4 py-3 text-paper-700" role="status">
              <Dots className="text-cinnabar-600" />
              <span className="sr-only">Người kể đang trả lời</span>
            </li>
          )}
        </ul>
        {blockError && <ErrorBlock error={blockError} className="mt-4" onRetry={() => setError(null)} />}
        <div ref={listEnd} />
      </div>

      <div className="border-t border-ink-750 px-5 py-4 md:px-6">
        {exhausted ? (
          <div className="rounded-[14px] border border-ink-750 bg-ink-900 p-4">
            <p className="text-[14px] leading-relaxed text-ink-100">
              {limitError ? limitError.message : 'Đã hết lượt hỏi trong chương này. Lượt mới mở ở chương sau.'}
            </p>
            <button
              type="button"
              onClick={onClose}
              className="wt-btn wt-btn-ghost mt-3 inline-flex min-h-tap items-center rounded-[10px] border border-ink-600 px-4 text-[14px] font-semibold"
            >
              Quay lại trang đọc
            </button>
          </div>
        ) : (
          <form onSubmit={send}>
            <div className="flex items-center justify-between">
              <label htmlFor={inputId} className="text-[13px] text-ink-200">
                Câu hỏi của bạn
              </label>
              <CharCount id={countId} value={question} max={max} />
            </div>
            <div className="mt-2 flex items-end gap-2">
              <textarea
                id={inputId}
                rows={2}
                value={question}
                onChange={(e) => {
                  setQuestion(e.target.value);
                  setError(null);
                }}
                onKeyDown={onKey}
                aria-describedby={cx(countId, fieldError && errId) || undefined}
                aria-invalid={fieldError ? true : undefined}
                placeholder="Hỏi về điều bạn đã thấy, đã nghe…"
                className={cx(
                  'wt-input min-h-tap flex-1 resize-none rounded-[12px] border bg-ink-900 px-4 py-3 text-[14px] text-ink-50',
                  fieldError ? 'border-cinnabar-400' : 'border-ink-700',
                )}
              />
              <button
                type="submit"
                disabled={pending}
                aria-label="Gửi câu hỏi"
                className="wt-btn wt-btn-primary grid h-12 w-12 flex-none place-items-center rounded-[12px] bg-cinnabar-600 text-on-cinnabar disabled:opacity-60"
              >
                <IconSend />
              </button>
            </div>
            {fieldError && <FieldError id={errId} message={fieldError.message} />}
          </form>
        )}
      </div>
    </div>
  );
}
