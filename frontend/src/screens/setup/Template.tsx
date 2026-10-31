import { useId, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router';
import { api } from '../../api/client';
import { asApiError, type ApiError } from '../../api/errors';
import type { NamesStyle, PlacesStyle, SetupStartIn, StoryStyle } from '../../api/types';
import { ErrorBlock } from '../../components/ErrorBlock';
import { RadioGroup } from '../../components/RadioGroup';
import { Button, Kicker, cx } from '../../components/ui';
import { usePublicConfig } from '../../config/PublicConfig';
import { once } from '../../lib/inflight';
import { SetupHeader } from './SetupHeader';

// Khởi tạo · khuôn truyện (D-KhoiTao-Khuon, M-Khuon). Thể loại và giọng văn là nhãn giao diện
// (gửi nguyên chữ làm tag, chữ người chơi chọn: G4). Độ dài và mức u tối lấy từ `/config/public`.
// Quy ước tên: mặc định để máy chủ đặt theo thể loại (`naming: null`, D-32).

export const GENRES = ['Kỳ ảo · tu tiên', 'Cổ trang', 'Lịch sử', 'Trinh thám', 'Đô thị', 'Hiện đại', 'Tương lai giả tưởng'];
export const VOICES = ['Trầm, lạnh', 'Trữ tình', 'Gai góc', 'Hóm hỉnh'];

const NAMES: { key: NamesStyle; label: string; example: string }[] = [
  { key: 'han_viet', label: 'Kiểu Hán Việt', example: 'Kha Diệp, Lương Phục, Đỗ Khiêm' },
  { key: 'viet', label: 'Kiểu Việt', example: 'Nguyễn Thị Hạnh, Trần Văn Lục, bà Tư' },
];
const PLACES: { key: PlacesStyle; label: string; example: string }[] = [
  { key: 'hu_cau', label: 'Hư cấu', example: 'đèo Lạc Nhạn, bến Vạn Thuỷ' },
  { key: 'that', label: 'Có thật', example: 'phố Hàng Bạc, chợ Bến Thành' },
];

/** Kiểu truyện: văn xuôi (mặc định) hay kịch bản để đọc thành tiếng bằng TTS một giọng. */
const STYLES: { key: StoryStyle; label: string; hint: string }[] = [
  { key: 'prose', label: 'Truyện chữ', hint: 'Văn xuôi để đọc trên trang.' },
  {
    key: 'audio',
    label: 'Kịch bản audio',
    hint: 'Viết để đọc thành tiếng bằng TTS: người kể xưng tôi, câu ngắn, lời thoại có câu dẫn. Tải kịch bản .txt ở màn truyện.',
  },
];

const chip = (checked: boolean) =>
  cx(
    'wt-chip inline-flex min-h-tap items-center rounded-full border px-4 text-[15px] font-medium',
    checked ? 'border-cinnabar-400 bg-cinnabar-400/15 text-cinnabar-100' : 'border-ink-700 text-ink-100',
  );

const segment = (checked: boolean) =>
  cx('flex min-h-tap flex-1 items-center justify-center rounded-[10px] px-3 text-[14px] font-medium', checked ? 'bg-ink-50 text-ink-950' : 'text-ink-200');

function Section({ id, title, aside, children }: { id: string; title: string; aside?: ReactNode; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="mt-9">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id={id}>
          <Kicker>{title}</Kicker>
        </h2>
        {aside}
      </div>
      <div className="mt-3">{children}</div>
    </section>
  );
}

export function Template() {
  const config = usePublicConfig();
  const navigate = useNavigate();
  const ids = { genre: useId(), naming: useId(), names: useId(), places: useId(), voice: useId(), dark: useId(), style: useId(), length: useId(), pov: useId() };
  const [genre, setGenre] = useState<string | null>(null);
  const [voice, setVoice] = useState<string | null>(null);
  const [darkness, setDarkness] = useState<string | null>(config.default_darkness_level);
  const [style, setStyle] = useState<StoryStyle>('prose');
  const [length, setLength] = useState<string | null>(null);
  const [names, setNames] = useState<NamesStyle | null>(null);
  const [places, setPlaces] = useState<PlacesStyle | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [sending, setSending] = useState(false);

  const custom = names !== null || places !== null;
  const level = config.story_lengths.find((l) => l.key === length) ?? null;
  const darkLabel = config.darkness_levels.find((d) => d.key === darkness)?.label ?? null;
  const ready = genre !== null && level !== null && !sending;

  const pickNames = (k: NamesStyle | null) => {
    setNames(k);
    if (k !== null && places === null) setPlaces(PLACES[0]?.key ?? 'hu_cau');
  };
  const pickPlaces = (k: PlacesStyle | null) => {
    setPlaces(k);
    if (k !== null && names === null) setNames(NAMES[0]?.key ?? 'han_viet');
  };

  const summary = [
    genre ?? 'chưa chọn thể loại',
    voice?.toLocaleLowerCase('vi'),
    darkLabel && `u tối ${darkLabel.toLocaleLowerCase('vi')}`,
    style === 'audio' && 'kịch bản audio',
    custom
      ? `${NAMES.find((n) => n.key === names)?.label.toLocaleLowerCase('vi')}, địa danh ${PLACES.find((p) => p.key === places)?.label.toLocaleLowerCase('vi')}`
      : 'tên theo thể loại',
    level ? `${level.label.toLocaleLowerCase('vi')}, ${level.chapters_min}–${level.chapters_max} chương` : 'chưa chọn độ dài',
  ]
    .filter(Boolean)
    .join(' · ');

  const submit = async () => {
    if (!ready || !genre || !level) return;
    setSending(true);
    setError(null);
    const body: SetupStartIn = {
      tags: { genre, voice },
      length_level: level.key,
      naming: custom && names && places ? { names, places } : null,
      ...(darkness ? { darkness_level: darkness } : {}),
      // Truyện chữ là mặc định của máy chủ: chỉ gửi khi chọn kiểu khác.
      ...(style !== 'prose' ? { style } : {}),
    };
    try {
      const out = await once('setup:start', () => api.startSetup(body));
      navigate(`/moi/${encodeURIComponent(out.session_id)}`);
    } catch (err) {
      setError(asApiError(err));
      setSending(false);
    }
  };

  return (
    <main className="wt relative min-h-screen overflow-hidden pb-32 md:pb-16">
      <SetupHeader step={1} back={{ to: '/', label: 'Đóng, về tủ truyện' }} />
      <div className="mx-auto grid w-full max-w-[1440px] gap-10 px-4 md:grid-cols-[1fr_300px] md:px-[100px] lg:gap-16">
        <div className="min-w-0">
          <h1 className="mt-8 font-display text-[34px] font-medium leading-tight md:mt-11 md:text-[50px]">Bạn muốn sống trong loại truyện nào?</h1>
          <p className="mt-2 text-[15px] text-ink-200">Chọn một thể loại chính. Phần còn lại để ngòi bút đề xuất.</p>

          <Section id={ids.genre} title="A · Thể loại chính — chọn một">
            <RadioGroup
              labelledBy={ids.genre}
              options={GENRES.map((g) => ({ key: g }))}
              value={genre}
              onChange={setGenre}
              className="flex flex-wrap gap-2.5"
              optionClassName={(_, c) => chip(c)}
              render={(o) => o.key}
            />
          </Section>

          <Section
            id={ids.naming}
            title="B · Tên người & địa danh"
            aside={
              custom ? (
                <button
                  type="button"
                  onClick={() => {
                    setNames(null);
                    setPlaces(null);
                  }}
                  className="wt-link min-h-tap text-[13px] text-cinnabar-200"
                >
                  đã đổi · dùng lại mặc định
                </button>
              ) : (
                <span className="text-[13px] text-ink-400">theo thể loại</span>
              )
            }
          >
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <p id={ids.names} className="mb-2 text-[15px] font-semibold">
                  Tên nhân vật
                </p>
                <RadioGroup
                  labelledBy={ids.names}
                  options={NAMES}
                  value={names}
                  onChange={pickNames}
                  className="flex gap-1 rounded-[14px] border border-ink-700 bg-ink-900 p-1"
                  optionClassName={(_, c) => segment(c)}
                  render={(o) => o.label}
                />
                {names && <p className="mt-2 font-reading text-[14px] italic text-ink-200">Ví dụ: {NAMES.find((n) => n.key === names)?.example}</p>}
              </div>
              <div>
                <p id={ids.places} className="mb-2 text-[15px] font-semibold">
                  Địa danh
                </p>
                <RadioGroup
                  labelledBy={ids.places}
                  options={PLACES}
                  value={places}
                  onChange={pickPlaces}
                  className="flex gap-1 rounded-[14px] border border-ink-700 bg-ink-900 p-1"
                  optionClassName={(_, c) => segment(c)}
                  render={(o) => o.label}
                />
                {places && <p className="mt-2 font-reading text-[14px] italic text-ink-200">Ví dụ: {PLACES.find((p) => p.key === places)?.example}</p>}
              </div>
            </div>
            {!custom && <p className="mt-2 text-[13px] text-ink-400">Máy chủ đặt quy ước tên theo thể loại bạn chọn; bấm một ô để tự chọn.</p>}
          </Section>

          <Section id={ids.voice} title="C · Giọng văn & độ u tối">
            <RadioGroup
              labelledBy={ids.voice}
              options={VOICES.map((v) => ({ key: v }))}
              value={voice}
              onChange={setVoice}
              allowDeselect
              className="flex flex-wrap gap-2.5"
              optionClassName={(_, c) => chip(c)}
              render={(o) => o.key}
            />
            {config.darkness_levels.length > 0 && (
              <>
                <p id={ids.dark} className="sr-only">
                  Độ u tối
                </p>
                <RadioGroup
                  labelledBy={ids.dark}
                  options={config.darkness_levels}
                  value={darkness}
                  onChange={setDarkness}
                  className="mt-4 grid grid-cols-3 gap-3 md:max-w-[640px]"
                  optionClassName={(_, c) =>
                    cx('wt-card min-h-[64px] rounded-[12px] border px-4 py-3', c ? 'border-cinnabar-400 bg-cinnabar-400/10' : 'border-ink-700')
                  }
                  render={(o) => <span className="text-[15px] font-semibold">{o.label}</span>}
                />
              </>
            )}
            <p id={ids.style} className="mb-2 mt-6 text-[15px] font-semibold">
              Kiểu truyện
            </p>
            <RadioGroup
              labelledBy={ids.style}
              options={STYLES}
              value={style}
              onChange={(k) => setStyle(k ?? 'prose')}
              className="grid gap-3 md:max-w-[640px] md:grid-cols-2"
              optionClassName={(_, c) =>
                cx('wt-card rounded-[12px] border px-4 py-3', c ? 'border-cinnabar-400 bg-cinnabar-400/10' : 'border-ink-700')
              }
              render={(o) => (
                <>
                  <span className="block text-[15px] font-semibold">{o.label}</span>
                  <span className="mt-1 block text-[13px] text-ink-200">{o.hint}</span>
                </>
              )}
            />
          </Section>

          <Section id={ids.length} title="D · Độ dài">
            <RadioGroup
              labelledBy={ids.length}
              options={config.story_lengths}
              value={length}
              onChange={setLength}
              className={cx('grid gap-3 sm:grid-cols-2', config.story_lengths.length > 2 && 'lg:grid-cols-4')}
              optionClassName={(_, c) =>
                cx('wt-card flex min-h-[120px] flex-col justify-end rounded-[16px] border p-5', c ? 'border-cinnabar-400 bg-[#201D1A]' : 'border-ink-750 bg-[#181715]')
              }
              render={(o, c) => {
                const i = config.story_lengths.indexOf(o);
                return (
                  <>
                    <span aria-hidden="true" className="mb-4 flex items-end gap-1">
                      {Array.from({ length: i + 1 }, (_, k) => (
                        <span
                          key={k}
                          className={cx('block rounded-[2px]', c ? (k % 2 ? 'bg-cinnabar-600' : 'bg-cinnabar-400') : k % 2 ? 'bg-ink-700' : 'bg-ink-600')}
                          style={{ width: `${8 + k * 4}px`, height: `${30 + k * 8}px` }}
                        />
                      ))}
                    </span>
                    <span className="block font-display text-[26px] font-medium leading-tight">{o.label}</span>
                    <span className="mt-1 block text-[13px] text-ink-200">
                      {o.chapters_min}–{o.chapters_max} chương
                    </span>
                  </>
                );
              }}
            />
          </Section>

          <Section id={ids.pov} title="E · Góc nhìn">
            <div className="grid gap-3 md:grid-cols-2">
              <div role="radiogroup" aria-labelledby={ids.pov} className="contents">
                <span role="radio" aria-checked="true" tabIndex={0} className="wt-card rounded-[16px] border border-cinnabar-400 bg-ink-800/60 p-5">
                  <span className="block text-[16px] font-semibold">Chỉ nhân vật chính</span>
                  <span className="mt-1 block text-[14px] text-ink-200">Bạn chỉ thấy những gì nhân vật của bạn thấy, nghe, đoán.</span>
                </span>
                <span role="radio" aria-checked="false" aria-disabled="true" className="rounded-[16px] border border-ink-750 p-5 text-ink-200">
                  <span className="flex items-center gap-2 text-[16px] font-semibold">
                    Nhiều nhân vật <span className="rounded-full bg-ink-800 px-2 py-0.5 text-[11px] font-medium text-ink-100">sắp có</span>
                  </span>
                  <span className="mt-1 block text-[14px]">Có chương kể qua mắt người khác.</span>
                </span>
              </div>
            </div>
          </Section>
        </div>

        <aside className="md:pt-11">
          <div className="border-t border-ink-750 pt-6 md:sticky md:top-6">
            <Kicker>Khuôn của bạn</Kicker>
            <p className="mt-3 font-display text-[24px] leading-snug text-ink-50 md:text-[28px]">{summary}.</p>
            <div className="mt-5 flex justify-between gap-4 border-t border-ink-750 pt-4 text-[14px]">
              <span className="text-ink-200">Ước tính cả truyện</span>
              <span className="italic text-ink-200">chưa có ước tính</span>
            </div>
            <div className="max-md:fixed max-md:inset-x-0 max-md:bottom-0 max-md:z-20 max-md:border-t max-md:border-ink-750 max-md:bg-ink-950 max-md:px-4 max-md:py-3">
              <Button className="mt-5 w-full max-md:mt-0" onClick={submit} disabled={!ready} arrow={ready}>
                {sending ? 'Đang mở phiên…' : 'Gợi ý bối cảnh'}
              </Button>
              <p className="mt-2 text-center text-[12px] text-ink-400">
                {genre && level ? 'Ngòi bút sẽ đưa ra ba bối cảnh để bạn chọn.' : 'Chọn thể loại chính và độ dài trước.'}
              </p>
            </div>
            {error && <ErrorBlock className="mt-4" error={error} onRetry={submit} />}
          </div>
        </aside>
      </div>
    </main>
  );
}
