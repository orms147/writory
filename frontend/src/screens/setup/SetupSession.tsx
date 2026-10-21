import { useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { api } from '../../api/client';
import { asApiError, type ApiError } from '../../api/errors';
import type { CharacterOption, SetupOut } from '../../api/types';
import { ErrorBlock, FieldError } from '../../components/ErrorBlock';
import { RadioGroup } from '../../components/RadioGroup';
import { Button, CharCount, Dots, IconCheck, Skeleton, cx } from '../../components/ui';
import { lengthText, usePublicConfig, useStoryLength } from '../../config/PublicConfig';
import { once } from '../../lib/inflight';
import { roman } from '../../lib/format';
import { useResource } from '../../lib/useResource';
import { SetupHeader } from './SetupHeader';
import mountains from '../../styles/mountains.svg';

// Khởi tạo · bối cảnh, hướng truyện, nhân vật (D-KhoiTao-BoiCanh, M-KhoiTao, M-HuongTruyen,
// D-KhoiTao-NhanVat, M-NhanVat). Máy chủ giữ ba lựa chọn mỗi bước; giao diện chỉ gửi số thứ tự
// (`api/setup.py`). POST một bước chỉ gọi model khi chưa có lựa chọn; chọn ô chỉ đổi tại chỗ, gửi
// khi bấm nút đi tiếp.

const TINTS = ['', 'hue-rotate-[100deg] saturate-50', 'hue-rotate-[200deg] saturate-50'];

function OptionSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-3" aria-hidden="true">
      {[0, 1, 2].map((i) => (
        <div key={i} className="flex min-h-[220px] flex-col gap-3 rounded-[16px] border border-ink-750 p-6">
          <Skeleton className="h-6 w-2/3" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      ))}
    </div>
  );
}

function Seal({ children }: { children: ReactNode }) {
  return (
    <span aria-hidden="true" className="wt-seal absolute right-5 top-5 grid h-11 w-11 place-items-center rounded-[8px] border-2 border-cinnabar-400 font-display text-[15px] italic text-cinnabar-400">
      {children}
    </span>
  );
}

export function SetupSession() {
  const { session = '' } = useParams();
  const navigate = useNavigate();
  const res = useResource(() => api.setup(session), `setup:${session}`);
  const [view, setView] = useState<'world' | 'characters' | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<{ at: string; err: ApiError } | null>(null);
  const leaving = useRef(false);
  const setup = res.data;

  const run = async (at: string, fn: () => Promise<SetupOut>) => {
    setBusy(at);
    setError(null);
    try {
      const out = await once(`${session}:${at}`, fn);
      if (at === 'finalize') leaving.current = true; // CharactersStep tự chuyển trang, kèm lệnh viết
      res.set(out);
      return out;
    } catch (err) {
      setError({ at, err: asApiError(err) });
      return null;
    } finally {
      setBusy(null);
    }
  };

  // Bước bối cảnh chưa có lựa chọn: tạo ngay (đây là mục đích của trang).
  const needSettings = setup !== null && setup.step === 'settings' && setup.settings === null;
  useEffect(() => {
    if (needSettings && !error) void run('settings', () => api.proposeSettings(session));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [needSettings]);

  // Mở lại phiên đã chốt: sang trang truyện (không tự viết). Vừa chốt xong thì `onDone` đã chuyển trang.
  useEffect(() => {
    if (leaving.current) return;
    if (setup?.step === 'done' && setup.story_id) navigate(`/truyen/${encodeURIComponent(setup.story_id)}`, { replace: true });
  }, [setup, navigate]);

  if (res.error) {
    return (
      <main className="wt relative min-h-screen">
        <SetupHeader step={2} back={{ to: '/moi', label: 'Về khuôn truyện' }} />
        <div className="mx-auto max-w-[560px] px-4 py-12">
          <ErrorBlock error={res.error} onRetry={res.reload} />
        </div>
      </main>
    );
  }
  if (!setup) {
    return (
      <main className="wt relative min-h-screen" aria-busy="true">
        <SetupHeader step={2} />
        <div className="mx-auto max-w-[1440px] px-4 py-12 md:px-[100px]">
          <OptionSkeleton />
        </div>
      </main>
    );
  }

  const atCharacters = setup.step === 'characters' || setup.step === 'finalize' || setup.step === 'done';
  const current = view ?? (atCharacters ? 'characters' : 'world');

  if (current === 'characters' && setup.characters) {
    return (
      <CharactersStep
        setup={setup}
        busy={busy}
        error={error}
        onBack={() => setView('world')}
        run={run}
        onDone={(out, chosen) => {
          leaving.current = true;
          navigate(`/truyen/${encodeURIComponent(out.story_id ?? '')}`, { state: { autostart: true, chosen } });
        }}
      />
    );
  }
  return (
    <WorldStep
      setup={setup}
      busy={busy}
      error={error}
      run={run}
      onCharacters={() => setView('characters')}
      onRetrySettings={() => void run('settings', () => api.proposeSettings(session))}
    />
  );
}

type Run = (at: string, fn: () => Promise<SetupOut>) => Promise<SetupOut | null>;

function tagLine(setup: SetupOut, lengthLabel: string): string {
  return [setup.tags.genre, setup.tags.voice, lengthLabel].filter(Boolean).join(' · ');
}

function WorldStep({
  setup,
  busy,
  error,
  run,
  onCharacters,
  onRetrySettings,
}: {
  setup: SetupOut;
  busy: string | null;
  error: { at: string; err: ApiError } | null;
  run: Run;
  onCharacters: () => void;
  onRetrySettings: () => void;
}) {
  const level = useStoryLength(setup.length_level);
  const [setting, setSetting] = useState<number | null>(setup.setting_index);
  const [plot, setPlot] = useState<number | null>(setup.plot_index);
  const settingsId = useId();
  const plotsId = useId();
  const sid = setup.session_id;
  const chosenSetting = setup.setting_index !== null ? setup.settings?.[setup.setting_index] : null;
  const settingChanged = setting !== setup.setting_index;
  const plotsShown = !settingChanged && setup.plots !== null;

  const showPlots = async () => {
    if (setting === null) return;
    let out: SetupOut | null = setup;
    if (settingChanged) out = await run('choose-setting', () => api.chooseSetting(sid, setting));
    if (out && out.plots === null) await run('plots', () => api.proposePlots(sid));
    setPlot(null);
  };

  const toCharacters = async () => {
    if (plot === null) return;
    let out: SetupOut | null = setup;
    if (plot !== setup.plot_index) out = await run('choose-plot', () => api.choosePlot(sid, plot));
    if (out && out.characters === null) out = await run('characters', () => api.proposeCharacters(sid));
    if (out?.characters) onCharacters();
  };

  const err = (at: string[]) => (error && at.includes(error.at) ? error.err : null);

  return (
    <main className="wt relative min-h-screen overflow-hidden pb-28">
      <SetupHeader step={plotsShown ? 3 : 2} back={{ to: '/moi', label: 'Đổi khuôn truyện' }} />
      <div className="mx-auto w-full max-w-[1440px] px-4 md:px-[100px]">
        <section aria-labelledby={settingsId}>
          <div className="mt-8 flex flex-wrap items-end justify-between gap-4 md:mt-11">
            <div>
              <h1 id={settingsId} className="font-display text-[34px] font-medium leading-tight md:text-[46px]">
                Ba nơi để bắt đầu
              </h1>
              <p className="mt-1 text-[14px] text-ink-200">{tagLine(setup, level?.label ?? setup.length_level)}</p>
            </div>
          </div>
          <div className="mt-6">
            {setup.settings === null ? (
              err(['settings']) ? (
                <ErrorBlock error={err(['settings'])!} onRetry={onRetrySettings} />
              ) : (
                <div role="status" aria-live="polite">
                  <span className="sr-only">Ngòi bút đang nghĩ ba bối cảnh</span>
                  <OptionSkeleton />
                </div>
              )
            ) : (
              <RadioGroup
                labelledBy={settingsId}
                options={setup.settings.map((o, i) => ({ key: String(i), o, i }))}
                value={setting === null ? null : String(setting)}
                onChange={(k) => setSetting(k === null ? null : Number(k))}
                className="grid gap-4 md:grid-cols-3"
                optionClassName={(_, c) => cx('wt-card relative overflow-hidden rounded-[16px] border bg-ink-900', c ? 'border-cinnabar-400' : 'border-ink-750')}
                render={({ o, i }) => (
                  <>
                    <span aria-hidden="true" className={cx('block h-[130px] bg-cover bg-bottom opacity-80', TINTS[i % TINTS.length])} style={{ backgroundImage: `url(${mountains})` }} />
                    <span aria-hidden="true" className="absolute left-6 top-4 font-display text-[36px] italic text-ink-50">
                      {roman(i + 1)}
                    </span>
                    <Seal>Chọn</Seal>
                    <span className="block px-6 pb-6 pt-2">
                      <span className="block font-display text-[26px] font-medium leading-tight">{o.title}</span>
                      <span className="mt-3 block font-reading text-[15px] leading-relaxed text-ink-100">{o.intro}</span>
                    </span>
                  </>
                )}
              />
            )}
          </div>
          {setup.settings && !plotsShown && (
            <div className="mt-6 flex flex-wrap items-center justify-end gap-3">
              {err(['choose-setting', 'plots']) && (
                <ErrorBlock className="w-full" error={err(['choose-setting', 'plots'])!} onRetry={() => void showPlots()} />
              )}
              <Button onClick={() => void showPlots()} disabled={setting === null || busy !== null} arrow={setting !== null && busy === null}>
                {busy === 'plots' || busy === 'choose-setting' ? 'Ngòi bút đang nghĩ…' : 'Xem ba hướng truyện'}
              </Button>
            </div>
          )}
          {(busy === 'plots' || busy === 'choose-setting') && (
            <div role="status" className="mt-8">
              <span className="sr-only">Ngòi bút đang nghĩ ba hướng truyện</span>
              <OptionSkeleton />
            </div>
          )}
        </section>

        {plotsShown && setup.plots && (
          <section aria-labelledby={plotsId} className="mt-12 border-t border-ink-750 pt-10">
            <h2 id={plotsId} className="font-display text-[30px] font-medium leading-tight md:text-[40px]">
              Chuyện gì sẽ xảy ra ở {chosenSetting?.title}?
            </h2>
            <p className="mt-1 text-[14px] text-ink-200">Chọn một hướng. Ngòi bút sẽ giữ phần còn lại cho đến lúc nó tự lộ ra trên trang.</p>
            <RadioGroup
              labelledBy={plotsId}
              options={setup.plots.map((o, i) => ({ key: String(i), o }))}
              value={plot === null ? null : String(plot)}
              onChange={(k) => setPlot(k === null ? null : Number(k))}
              className="mt-6 grid gap-4 md:grid-cols-3"
              optionClassName={(_, c) => cx('wt-card relative rounded-[16px] border bg-ink-900 p-6', c ? 'border-cinnabar-400 bg-ink-800' : 'border-ink-750')}
              render={({ o }) => (
                <>
                  <Seal>
                    <IconCheck size={14} />
                  </Seal>
                  <span className="block pr-12 font-display text-[26px] font-medium leading-tight">{o.title}</span>
                  <span className="mt-3 block font-reading text-[15px] leading-relaxed text-ink-100">{o.summary}</span>
                </>
              )}
            />
          </section>
        )}

        <div className="mt-10 flex flex-wrap items-center justify-between gap-4 border-t border-ink-750 pt-6">
          <Link to="/moi" className="wt-link inline-flex min-h-tap items-center text-[14px] text-ink-200">
            ← Đổi khuôn truyện
          </Link>
          {plotsShown && (
            <Button onClick={() => void toCharacters()} disabled={plot === null || busy !== null} arrow={plot !== null && busy === null}>
              {busy === 'characters' || busy === 'choose-plot' ? 'Ngòi bút đang nghĩ…' : 'Gặp ba nhân vật'}
            </Button>
          )}
        </div>
        {err(['choose-plot', 'characters']) && (
          <ErrorBlock className="mt-4" error={err(['choose-plot', 'characters'])!} onRetry={() => void toCharacters()} />
        )}
      </div>
    </main>
  );
}

type Field = 'name' | 'personality' | 'backstory';

function CharactersStep({
  setup,
  busy,
  error,
  run,
  onBack,
  onDone,
}: {
  setup: SetupOut;
  busy: string | null;
  error: { at: string; err: ApiError } | null;
  run: Run;
  onBack: () => void;
  onDone: (out: SetupOut, chosen: string | null) => void;
}) {
  const config = usePublicConfig();
  const level = useStoryLength(setup.length_level);
  const options = setup.characters ?? [];
  const sid = setup.session_id;
  const [index, setIndex] = useState<number | null>(setup.character_index);
  const base: CharacterOption | null =
    index === null ? null : index === setup.character_index && setup.protagonist ? setup.protagonist : (options[index] ?? null);
  const [edits, setEdits] = useState<Record<Field, string> | null>(base ? { ...base } : null);
  const listId = useId();
  const ids = { name: useId(), personality: useId(), backstory: useId(), err: useId() };
  const limits: Record<Field, number | null> = {
    name: config.input.character_name_max_chars,
    personality: config.input.personality_max_chars,
    backstory: config.input.backstory_max_chars,
  };

  const pick = (k: string | null) => {
    const i = k === null ? null : Number(k);
    setIndex(i);
    const b = i === null ? null : i === setup.character_index && setup.protagonist ? setup.protagonist : (options[i] ?? null);
    setEdits(b ? { ...b } : null);
  };

  const err = error && ['choose-character', 'finalize'].includes(error.at) ? error.err : null;
  const badFields = new Set(err?.fields ?? []);
  const finalizing = busy === 'finalize';

  const start = async () => {
    if (index === null || !edits) return;
    const original = options[index];
    if (!original) return;
    const body = {
      index,
      name: edits.name !== original.name ? edits.name : null,
      personality: edits.personality !== original.personality ? edits.personality : null,
      backstory: edits.backstory !== original.backstory ? edits.backstory : null,
    };
    const chosen = await run('choose-character', () => api.chooseCharacter(sid, body));
    if (!chosen) return;
    const done = await run('finalize', () => api.finalize(sid));
    if (done?.story_id) {
      const setting = done.setting_index !== null ? done.settings?.[done.setting_index] : null;
      const plot = done.plot_index !== null ? done.plots?.[done.plot_index] : null;
      onDone(done, [setting?.title, plot?.summary].filter(Boolean).join('. ') || null);
    }
  };

  const plotTitle = setup.plot_index !== null ? setup.plots?.[setup.plot_index]?.title : null;
  const settingTitle = setup.setting_index !== null ? setup.settings?.[setup.setting_index]?.title : null;

  const field = (f: Field, label: string, multiline: boolean) => (
    <div className="mt-5 first:mt-0">
      <div className="flex items-center justify-between gap-3">
        <label htmlFor={ids[f]} className="text-[14px] font-semibold">
          {label}
        </label>
        {edits && <CharCount id={`${ids[f]}-count`} value={edits[f]} max={limits[f]} />}
      </div>
      {multiline ? (
        <textarea
          id={ids[f]}
          value={edits?.[f] ?? ''}
          disabled={!edits || finalizing}
          onChange={(e) => setEdits((x) => (x ? { ...x, [f]: e.target.value } : x))}
          rows={f === 'backstory' ? 4 : 2}
          aria-invalid={badFields.has(f) || undefined}
          aria-describedby={cx(`${ids[f]}-count`, badFields.has(f) && ids.err) || undefined}
          className={cx(
            'wt-input mt-2 block w-full resize-y rounded-[12px] border bg-ink-900 px-4 py-3 font-reading text-[16px] text-ink-50',
            badFields.has(f) ? 'border-cinnabar-400' : 'border-ink-700',
          )}
        />
      ) : (
        <input
          id={ids[f]}
          value={edits?.[f] ?? ''}
          disabled={!edits || finalizing}
          onChange={(e) => setEdits((x) => (x ? { ...x, [f]: e.target.value } : x))}
          aria-invalid={badFields.has(f) || undefined}
          aria-describedby={cx(`${ids[f]}-count`, badFields.has(f) && ids.err) || undefined}
          className={cx(
            'wt-input mt-2 block min-h-[52px] w-full rounded-[12px] border bg-ink-900 px-4 font-display text-[24px] text-ink-50',
            badFields.has(f) ? 'border-cinnabar-400' : 'border-ink-700',
          )}
        />
      )}
    </div>
  );

  return (
    <main className="wt relative min-h-screen overflow-hidden pb-16">
      <SetupHeader step={4} back={{ onClick: onBack, label: 'Về bối cảnh và hướng truyện' }} />
      <div className="mx-auto w-full max-w-[1440px] px-4 md:px-[100px]">
        <h1 id={listId} className="mt-8 font-display text-[34px] font-medium leading-tight md:mt-11 md:text-[46px]">
          Bạn sẽ là ai{settingTitle ? ` ở ${settingTitle}` : ''}?
        </h1>
        <p className="mt-1 text-[14px] text-ink-200">{[plotTitle, 'chọn một người, rồi sửa tuỳ ý.'].filter(Boolean).join(' · ')}</p>

        <div className="mt-7 grid gap-6 md:grid-cols-[340px_1fr]">
          <div>
            <RadioGroup
              labelledBy={listId}
              options={options.map((o, i) => ({ key: String(i), o }))}
              value={index === null ? null : String(index)}
              onChange={pick}
              className="flex flex-col gap-3"
              optionClassName={(_, c) => cx('wt-card flex w-full items-center gap-4 rounded-[16px] border p-4', c ? 'border-cinnabar-400 bg-ink-800' : 'border-ink-750 bg-ink-900')}
              render={({ o }, c) => (
                <>
                  <span aria-hidden="true" className={cx('relative grid h-14 w-14 flex-none place-items-center rounded-full font-display text-[28px]', c ? 'bg-cinnabar-600 text-on-cinnabar' : 'bg-ink-700 text-ink-50')}>
                    {o.name.trim().split(/\s+/).pop()?.charAt(0) ?? ''}
                  </span>
                  <span className="min-w-0">
                    <span className="block font-display text-[24px] font-medium leading-tight">{o.name}</span>
                    <span className="mt-0.5 line-clamp-2 block text-[13px] text-ink-200">{o.personality}</span>
                  </span>
                </>
              )}
            />
            <p className="mt-3 text-[13px] text-ink-400">Ba người này đều có lý do để có mặt ở nơi bạn chọn.</p>
          </div>

          <section aria-label="Sửa nhân vật chính" className="rounded-[20px] border border-ink-750 bg-ink-900/60 p-5 md:p-7">
            {!edits ? (
              <p className="text-[14px] text-ink-200">Chọn một nhân vật ở bên để xem và sửa.</p>
            ) : (
              <>
                {field('name', 'Tên', false)}
                {field('personality', 'Tính cách', true)}
                {field('backstory', 'Quá khứ', true)}
                <p className="mt-2 text-[12px] text-ink-400">Ngòi bút coi đây là sự thật về nhân vật của bạn, nhưng không coi là mệnh lệnh cho câu chuyện.</p>
              </>
            )}
            {err && (err.fields.length > 0 ? <FieldError id={ids.err} message={err.message} /> : <ErrorBlock className="mt-4" error={err} onRetry={() => void start()} />)}
            <div className="mt-6 flex flex-wrap items-center justify-between gap-4 border-t border-ink-750 pt-5">
              <p className="text-[13px] leading-relaxed text-ink-200">
                Chương 1 · {lengthText(level, setup.length_level)}
                <br />
                Ước tính: <span className="italic">chưa có ước tính</span>
              </p>
              <Button onClick={() => void start()} disabled={!edits || busy !== null} arrow={!!edits && busy === null}>
                {finalizing ? 'Đang dựng thế giới…' : busy === 'choose-character' ? 'Đang lưu nhân vật…' : 'Bắt đầu chương 1'}
              </Button>
            </div>
            {finalizing && (
              <p role="status" className="mt-4 flex items-center gap-2 text-[13px] text-ink-200">
                <Dots className="text-cinnabar-400" /> Ngòi bút đang dựng thế giới trước trang đầu. Việc này lâu hơn một bước thường.
              </p>
            )}
          </section>
        </div>

        <div className="mt-8">
          <button type="button" onClick={onBack} className="wt-link inline-flex min-h-tap items-center text-[14px] text-ink-200">
            ← Đổi bối cảnh hoặc hướng truyện
          </button>
        </div>
      </div>
    </main>
  );
}
