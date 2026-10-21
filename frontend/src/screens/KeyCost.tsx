import { useId, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import { api } from '../api/client';
import { asApiError, type ApiError } from '../api/errors';
import { ErrorBlock, FieldError } from '../components/ErrorBlock';
import { TopNav } from '../components/TopNav';
import { Button, IconBack, Kicker, LinkButton, cx } from '../components/ui';
import { usePublicConfig } from '../config/PublicConfig';
import { OPENROUTER_KEYS_URL } from '../lib/errorGroups';
import { formatCap, formatUsd } from '../lib/format';
import { useResource } from '../lib/useResource';
import { maskedKey, usePlayerKey } from '../state/PlayerKey';

// Khoá & chi phí (D-/M-KetNoiKhoa). Key chỉ đi trong thân PUT; ô nhập không điều khiển bằng state
// React và được xoá ngay sau khi gửi; không lưu ở trình duyệt, không log (G7). Chỉ hiện `last4`.

function KeyForm({ changing, onCancel, onSaved }: { changing: boolean; onCancel: () => void; onSaved: () => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [saving, setSaving] = useState(false);
  const inputId = useId();
  const errId = useId();
  const key = usePlayerKey();

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const input = inputRef.current;
    if (!input || saving) return;
    const value = input.value;
    setSaving(true);
    setError(null);
    try {
      const out = await api.putPlayerKey(value);
      input.value = '';
      key.set(out);
      onSaved();
    } catch (err) {
      input.value = '';
      setError(asApiError(err));
    } finally {
      setSaving(false);
    }
  };

  const fieldError = error && (error.hasField('api_key') || error.code === 'PLAYER_KEY_INVALID') ? error : null;
  const blockError = error && !fieldError ? error : null;

  return (
    <form onSubmit={submit} className="mt-5" autoComplete="off">
      <label htmlFor={inputId} className="block text-[14px] text-ink-100">
        {changing ? 'Dán khoá mới (thay khoá hiện tại)' : 'Dán khoá API của OpenRouter (bắt đầu bằng sk-or-)'}
      </label>
      <input
        ref={inputRef}
        id={inputId}
        type="password"
        name="openrouter-key"
        autoComplete="off"
        spellCheck={false}
        autoCapitalize="off"
        aria-invalid={fieldError ? true : undefined}
        aria-describedby={fieldError ? errId : undefined}
        placeholder="sk-or-…"
        className={cx(
          'wt-input mt-2 block min-h-[48px] w-full rounded-[12px] border bg-ink-900 px-4 font-mono text-[15px] text-ink-50',
          fieldError ? 'border-cinnabar-400' : 'border-ink-700',
        )}
      />
      {fieldError && <FieldError id={errId} message={fieldError.message} />}
      <p className="mt-2 text-[12px] text-ink-400">
        Lấy khoá ở{' '}
        <a className="wt-link text-ink-200" href={OPENROUTER_KEYS_URL} target="_blank" rel="noreferrer noopener">
          openrouter.ai/keys<span className="sr-only"> (mở thẻ mới)</span>
        </a>
        . WriTory mã hoá khoá khi lưu và không bao giờ hiện lại đầy đủ.
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button type="submit" disabled={saving}>
          {saving ? 'Đang lưu…' : 'Lưu khoá'}
        </Button>
        {changing && (
          <Button variant="ghost" onClick={onCancel}>
            Huỷ
          </Button>
        )}
      </div>
      {blockError && <ErrorBlock className="mt-4" error={blockError} />}
    </form>
  );
}

function KeySection() {
  const key = usePlayerKey();
  const [changing, setChanging] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [removeError, setRemoveError] = useState<ApiError | null>(null);
  const connected = key.data?.has_key ?? false;

  const remove = async () => {
    setRemoveError(null);
    try {
      key.set(await api.deletePlayerKey());
      setConfirm(false);
    } catch (err) {
      setRemoveError(asApiError(err));
    }
  };

  return (
    <section aria-labelledby="key-heading" className="border-t border-ink-700 pt-6">
      <div className="flex items-center justify-between gap-4">
        <h2 id="key-heading">
          <Kicker>Khoá OpenRouter</Kicker>
        </h2>
        {key.data && (
          <span className={cx('inline-flex items-center gap-2 text-[13px] font-medium', connected ? 'text-jade-200' : 'text-cinnabar-200')}>
            <span aria-hidden="true" className={cx('h-[7px] w-[7px] rounded-full', connected ? 'bg-jade-400' : 'bg-cinnabar-400')} />
            {connected ? 'Đã có khoá' : 'Chưa có khoá'}
          </span>
        )}
      </div>
      {key.error && <ErrorBlock className="mt-4" error={key.error} onRetry={key.reload} />}
      {key.data && connected && !changing && (
        <>
          <p className="mt-5 flex flex-wrap items-baseline gap-x-4 gap-y-1">
            <span className="font-mono text-[26px] tracking-[.12em] text-ink-50" aria-label={`Khoá kết thúc bằng ${key.data.last4 ?? ''}`}>
              {maskedKey(key.data.last4)}
            </span>
            <span className="text-[13px] text-ink-400">chỉ hiện 4 ký tự cuối</span>
          </p>
          {confirm ? (
            <div role="alertdialog" aria-labelledby="confirm-remove" className="mt-5 rounded-[14px] border border-ink-700 bg-ink-900 p-4">
              <p id="confirm-remove" className="text-[14px] text-ink-100">
                Ngắt khoá này? Truyện của bạn vẫn còn, nhưng ngòi bút sẽ không viết tiếp cho tới khi bạn dán khoá khác.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button onClick={remove}>Ngắt khoá</Button>
                <Button variant="ghost" onClick={() => setConfirm(false)}>
                  Giữ khoá
                </Button>
              </div>
            </div>
          ) : (
            <div className="mt-5 flex flex-wrap gap-2">
              <Button variant="ghost" onClick={() => setChanging(true)}>
                Đổi khoá
              </Button>
              <Button variant="danger-ghost" onClick={() => setConfirm(true)}>
                Ngắt khoá
              </Button>
            </div>
          )}
          {removeError && <ErrorBlock className="mt-4" error={removeError} onRetry={remove} />}
        </>
      )}
      {key.data && (!connected || changing) && (
        <KeyForm changing={changing} onCancel={() => setChanging(false)} onSaved={() => setChanging(false)} />
      )}
      <div className="mt-6 flex flex-wrap items-center gap-3 text-[13px] text-ink-400">
        <button
          type="button"
          disabled
          aria-disabled="true"
          className="inline-flex min-h-tap items-center gap-2 rounded-[10px] border border-dashed border-ink-700 px-4 text-ink-400"
        >
          Kết nối với OpenRouter
          <span className="rounded-full bg-ink-800 px-2 py-0.5 text-[11px] text-ink-200">sắp có</span>
        </button>
        <span>Hiện tại bạn dán khoá tay.</span>
      </div>
    </section>
  );
}

function CostSection() {
  const config = usePublicConfig();
  const costs = useResource(() => api.costs(), 'costs');
  const stories = useResource(() => api.stories(), 'stories');
  const titleOf = (id: string) => stories.data?.stories.find((s) => s.story_id === id)?.title ?? id;
  const rows: [string, string][] = [
    ['Trần mỗi cảnh', formatCap(config.cost_usd.per_scene)],
    ['Trần mỗi chương', formatCap(config.cost_usd.per_chapter)],
    ['Trần mỗi truyện', formatCap(config.cost_usd.per_story)],
  ];
  return (
    <section aria-labelledby="cost-heading" className="border-t border-ink-700 pt-6">
      <h2 id="cost-heading">
        <Kicker>Bút & chi phí</Kicker>
      </h2>
      <div className="mt-5 flex items-baseline justify-between gap-4">
        <p className="font-display text-[30px] font-medium">Bút {config.writer_tier.label}</p>
        <span className="text-[12px] uppercase tracking-[.2em] text-ink-400">Chỉ đọc</span>
      </div>
      <p className="text-[13px] text-ink-400">Bản 1 dùng một bút cho mọi truyện.</p>
      <dl className="mt-4">
        <div className="flex items-center justify-between gap-4 border-t border-ink-750 py-3.5">
          <dt className="text-[15px] text-ink-100">Ước tính chương tiếp theo</dt>
          <dd className="italic text-ink-200">chưa có ước tính</dd>
        </div>
        {rows.map(([label, value]) => (
          <div key={label} className="flex items-center justify-between gap-4 border-t border-ink-750 py-3.5">
            <dt className="text-[15px] text-ink-100">{label}</dt>
            <dd className="tabular-nums text-ink-50">{value}</dd>
          </div>
        ))}
      </dl>
      <p className="border-t border-ink-750 pt-4 text-[13px] leading-relaxed text-ink-400">
        Chạm trần nào thì WriTory dừng viết ở đó và báo cho bạn. Trần do hệ thống đặt, không đổi được ở đây.
      </p>

      <h3 className="mt-7">
        <Kicker>Đã dùng theo truyện</Kicker>
      </h3>
      {costs.error && <ErrorBlock className="mt-3" error={costs.error} onRetry={costs.reload} />}
      {costs.data && (
        <dl className="mt-2">
          {costs.data.stories.map((s) => (
            <div key={s.story_id} className="flex items-baseline justify-between gap-4 border-t border-ink-750 py-3.5">
              <dt className="font-display text-[20px]">{titleOf(s.story_id)}</dt>
              <dd className="tabular-nums text-ink-50">{formatUsd(s.spent_usd)}</dd>
            </div>
          ))}
          <div className="flex items-baseline justify-between gap-4 border-t border-ink-600 py-3.5 font-semibold">
            <dt>Tháng này</dt>
            <dd className="tabular-nums">{formatUsd(costs.data.this_month_usd)}</dd>
          </div>
          <div className="flex items-baseline justify-between gap-4 border-t border-ink-750 py-3.5 text-ink-200">
            <dt>Tổng</dt>
            <dd className="tabular-nums">{formatUsd(costs.data.total_usd)}</dd>
          </div>
        </dl>
      )}
    </section>
  );
}

export function KeyCost() {
  return (
    <main className="wt relative min-h-screen overflow-hidden pb-16">
      <div className="max-md:hidden">
        <TopNav keyLabel="Khoá & chi phí" />
      </div>
      <div className="mx-auto w-full max-w-[1440px] px-4 md:px-[100px]">
        <div className="mt-5 flex items-center gap-2 md:hidden">
          <Link to="/" aria-label="Về tủ truyện" className="wt-icon-btn grid min-h-tap min-w-tap place-items-center rounded-[10px] text-ink-200">
            <IconBack />
          </Link>
        </div>
        <h1 className="mt-4 font-display font-medium leading-none md:mt-10">
          <span className="text-[44px] md:text-[110px]">Khoá & </span>
          <span className="text-[44px] italic text-cinnabar-400 md:text-[110px]">chi phí</span>
        </h1>
        <p className="mt-4 max-w-[680px] text-[15px] leading-relaxed text-ink-200 md:text-[16px]">
          Bạn trả phí gọi model qua tài khoản OpenRouter của mình. WriTory giữ khoá ở dạng mã hoá và không bao giờ hiện lại đầy đủ.
        </p>
        <div className="mt-8 grid gap-10 md:grid-cols-2 md:gap-6">
          <KeySection />
          <CostSection />
        </div>
        <div className="mt-10 flex justify-end">
          <LinkButton to="/moi" arrow className="max-md:w-full">
            Bắt đầu truyện mới
          </LinkButton>
        </div>
      </div>
    </main>
  );
}
