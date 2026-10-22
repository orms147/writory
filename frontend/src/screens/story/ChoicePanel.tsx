import { useId, useState } from 'react';
import { api } from '../../api/client';
import { asApiError, type ApiError } from '../../api/errors';
import type { ChapterEstimateOut, ChoiceKind, PlayerChoice } from '../../api/types';
import { ErrorBlock, FieldError } from '../../components/ErrorBlock';
import { RadioGroup } from '../../components/RadioGroup';
import { Arrow, CharCount, IconPen, cx } from '../../components/ui';
import { usePublicConfig } from '../../config/PublicConfig';
import { errorGroup } from '../../lib/errorGroups';
import { formatUsd, numberWords, roman } from '../../lib/format';
import { useResource } from '../../lib/useResource';

function KindIcon({ kind }: { kind: ChoiceKind }) {
  const common = { width: 13, height: 13, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, 'aria-hidden': true };
  if (kind === 'action') return <svg {...common}><path d="M5 12h14M13 6l6 6-6 6" /></svg>;
  if (kind === 'dialogue') return <svg {...common}><path d="M7 7c-2 2-2 5 0 6M13 7c-2 2-2 5 0 6" /></svg>;
  return <svg {...common}><circle cx="12" cy="12" r="7" /><circle cx="12" cy="12" r="2" /></svg>;
}

/** Nhãn lựa chọn theo máy chủ: "Lời thoại · nói dối" (D-65: sắc thái cố định, không bộ chọn). */
export function choiceLabel(c: PlayerChoice): string {
  return c.tone_label ? `${c.kind_label} · ${c.tone_label}` : c.kind_label;
}

/** Chi phí chương tới, số của máy chủ (D-87): trung vị các chương đã viết của truyện, hoặc số mặc định.
 *  Không có số (null, hoặc API lỗi) thì ghi "chưa có ước tính", không tự đặt số. */
export function EstimateText({ estimate, loading }: { estimate: ChapterEstimateOut | null; loading: boolean }) {
  if (loading) return <span className="italic text-ink-200">đang ước tính…</span>;
  if (!estimate || estimate.usd === null) return <span className="italic text-ink-50">chưa có ước tính</span>;
  const basis = estimate.source === 'story_median' ? `theo ${estimate.chapters_used} chương đã viết` : 'số mặc định';
  return (
    <span className="text-ink-50">
      khoảng {formatUsd(estimate.usd)} mỗi chương <span className="text-ink-300">({basis})</span>
    </span>
  );
}

/** Lựa chọn cuối chương (D-/M-LuaChon). Không chọn sẵn; ba lựa chọn cùng kiểu dáng; ô tự viết đếm
 *  ký tự theo `limits.input.custom_action_max_chars` từ máy chủ. */
export function ChoicePanel({
  storyId,
  chapter,
  choices,
  spentUsd,
  chosenBefore,
  onChosen,
}: {
  storyId: string;
  chapter: number;
  choices: PlayerChoice[];
  spentUsd: number | null;
  chosenBefore: string | null;
  onChosen: (text: string) => void;
}) {
  const config = usePublicConfig();
  const max = config.input.custom_action_max_chars;
  const [picked, setPicked] = useState<string | null>(null);
  const [custom, setCustom] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const headingId = useId();
  const customId = useId();
  const countId = useId();
  const errId = useId();

  const usingCustom = custom.trim().length > 0;
  // Đã chọn từ trước (mở lại trang): viết tiếp được với hành động đó, không chọn sẵn ô nào.
  const keepBefore = !usingCustom && picked === null && chosenBefore !== null;
  const canSend = !sending && (usingCustom || picked !== null || keepBefore);
  const next = chapter + 1;
  const estimate = useResource(() => api.chapterEstimate(storyId), `estimate:${storyId}:${chapter}`);
  const fieldError = error && errorGroup(error.code) === 'action_input' ? error : null;
  const blockError = error && !fieldError ? error : null;

  const submit = async () => {
    if (!canSend) return;
    if (keepBefore && chosenBefore !== null) {
      onChosen(chosenBefore);
      return;
    }
    setSending(true);
    setError(null);
    try {
      const out = usingCustom ? await api.customAction(storyId, custom) : await api.pickChoice(storyId, picked ?? '');
      onChosen(out.text);
    } catch (err) {
      setError(asApiError(err));
      setSending(false);
    }
  };

  return (
    <section aria-labelledby={headingId} className="mt-10">
      <div className="flex items-center gap-4" aria-hidden="true">
        <span className="h-px flex-1 bg-paper-400" />
        <span className="grid h-10 w-10 -rotate-6 place-items-center rounded-[8px] border-2 border-cinnabar-600 font-display text-[15px] font-semibold text-cinnabar-600">
          {roman(chapter)}
        </span>
        <span className="text-[12px] uppercase tracking-[.2em] text-paper-700">Hết chương {numberWords(chapter)}</span>
        <span className="h-px flex-1 bg-paper-400" />
      </div>
      <h2 id={headingId} className="mt-8 font-display text-[34px] font-medium md:text-[38px]">
        Bạn sẽ…
      </h2>
      {chosenBefore && (
        <p className="mt-2 text-[14px] text-paper-700">
          Bạn đã chọn cho chương {numberWords(next)}: <span className="font-reading italic text-paper-800">{chosenBefore}</span>. Chọn lại được tới khi bấm viết.
        </p>
      )}

      <RadioGroup
        labelledBy={headingId}
        options={choices.map((c) => ({ key: c.id, choice: c }))}
        value={usingCustom ? null : picked}
        onChange={(k) => {
          setPicked(k);
          setCustom('');
          setError(null);
        }}
        className="mt-5 flex flex-col gap-3"
        optionClassName={(_, checked) =>
          cx(
            'wt-choice group flex w-full min-h-tap items-start gap-4 rounded-[14px] border p-4 md:p-5',
            checked ? 'border-cinnabar-600 bg-[#FFF9EF]' : 'border-paper-400 bg-paper-100',
          )
        }
        render={(o, checked) => (
          <>
            <span
              aria-hidden="true"
              className={cx('mt-1 grid h-6 w-6 flex-none place-items-center rounded-full border-2', checked ? 'border-cinnabar-600' : 'border-paper-500')}
            >
              {checked && <span className="h-2.5 w-2.5 rounded-full bg-cinnabar-600" />}
            </span>
            <span className="min-w-0 flex-1">
              <span className="flex items-center gap-2 text-[12px] font-semibold uppercase tracking-[.12em] text-cinnabar-700">
                <KindIcon kind={o.choice.kind} />
                {choiceLabel(o.choice)}
              </span>
              <span className="mt-1.5 block font-reading text-[17px] leading-[1.6] text-paper-950 md:text-[18px]">{o.choice.text}</span>
            </span>
            <span aria-hidden="true" className="wt-go hidden text-paper-500 md:inline">
              →
            </span>
          </>
        )}
      />

      <div className="mt-6">
        <div className="flex items-center justify-between gap-3">
          <label htmlFor={customId} className="flex items-center gap-2 text-[14px] font-semibold text-paper-950">
            <IconPen />
            Hoặc tự viết hành động của bạn
          </label>
          <CharCount id={countId} value={custom} max={max} tone="paper" />
        </div>
        <textarea
          id={customId}
          value={custom}
          onChange={(e) => {
            setCustom(e.target.value);
            setError(null);
          }}
          rows={3}
          aria-describedby={cx(countId, fieldError && errId) || undefined}
          aria-invalid={fieldError ? true : undefined}
          placeholder="Ví dụ: Lẳng lặng theo dấu chân trên tuyết, không báo ai."
          className={cx(
            'wt-input wt-input-paper mt-2 block w-full resize-y rounded-[12px] border bg-paper-100 px-4 py-3 font-reading text-[16px] text-paper-950',
            fieldError ? 'border-cinnabar-600' : usingCustom ? 'border-cinnabar-600' : 'border-paper-400',
          )}
        />
        {fieldError ? (
          <FieldError id={errId} message={fieldError.message} tone="paper" />
        ) : (
          <p className="mt-2 text-[12px] text-paper-700">
            Việc vượt sức nhân vật vẫn được viết thành truyện, nhưng có thể thất bại hoặc phải trả giá.
          </p>
        )}
      </div>

      {blockError && <ErrorBlock error={blockError} tone="paper" className="mt-5" onRetry={submit} />}

      <div className="sticky bottom-3 z-10 mt-6 flex flex-wrap items-center justify-between gap-3 rounded-[16px] bg-ink-950 px-5 py-4 text-ink-200 shadow-[0_20px_40px_-20px_rgba(0,0,0,.6)]">
        <p className="text-[13px] leading-snug">
          Chương {next} · ước tính: <EstimateText estimate={estimate.data} loading={estimate.loading} />
          {spentUsd !== null && (
            <>
              <br />
              Truyện đã dùng {formatUsd(spentUsd)}
            </>
          )}
        </p>
        <button
          type="button"
          onClick={submit}
          disabled={!canSend}
          className={cx(
            'wt-btn inline-flex min-h-[48px] items-center gap-2 rounded-[12px] px-5 text-[15px] font-semibold',
            canSend ? 'wt-btn-primary bg-cinnabar-600 text-on-cinnabar' : 'bg-ink-600 text-ink-200',
          )}
        >
          {sending
            ? 'Đang gửi…'
            : usingCustom
              ? `Viết chương ${next} theo ý tôi`
              : picked || keepBefore
                ? `Viết chương ${next}`
                : 'Chọn một hướng trước'}
          {canSend && <Arrow />}
        </button>
      </div>
    </section>
  );
}
