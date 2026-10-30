// Máy chủ giả trong trình duyệt (D-69): thay `fetch` khi chạy `npm run dev:mock` (VITE_MOCK=1)
// và trong test. Trả `Response` thật, kể cả luồng SSE bằng ReadableStream, nên giao diện đi qua
// đúng client, bộ đọc SSE và bộ đọc lỗi như với máy chủ thật.
//
// Kịch bản lỗi: thêm `?loi=<MÃ>` vào URL trang (ví dụ `/truyen/s-chuong?loi=COST_LIMIT_CHAPTER`).
// Tủ trống, chưa có khoá: `?mock=rong`.

import type {
  ChapterEvent,
  PlayerChoice,
  StageEvent,
  SetupOut,
  SetupStartIn,
  StorySummary,
} from '../api/types';
import {
  CHARACTERS,
  END_SCENE,
  FINISHED_SCENES,
  MOCK_CONFIG,
  MOCK_LENGTH_LEVELS,
  PLOTS,
  SCENES,
  SETTINGS,
  makeChoices,
  notebookFor,
} from './data';
import { MOCK_ERRORS } from './messages';

interface MockStory {
  id: string;
  title: string;
  length_level: string;
  total: number; // số chương của bản kế hoạch giả: ẩn với giao diện như ở máy chủ thật
  chapter: number;
  scenes: Record<number, string[]>;
  choices: Record<number, PlayerChoice[]>;
  action: { for_chapter: number; source: 'choice' | 'custom'; text: string } | null;
  spent: number;
  updated_at: string;
  narratorUsed: Record<number, number>;
  busy: boolean;
}

interface MockSetup {
  out: SetupOut;
}

export interface MockOptions {
  /** Nhân thời gian chờ của luồng SSE và các bước gọi model; 0 trong test. */
  delayScale?: number;
  /** `rong`: chưa có khoá, chưa có truyện. */
  scenario?: string | null;
  /** Mã lỗi giả lập (như `?loi=`); hàm thì đọc lại ở mỗi lời gọi. */
  fault?: string | null | (() => string | null);
  now?: () => Date;
  /** Chế độ đăng nhập của máy chủ giả (D-89). `invite`: phải đăng nhập bằng `MOCK_INVITE_CODE`;
   *  mặc định `dev`. Ở mọi chế độ, route ghi phải gửi `content-type: application/json` như máy chủ
   *  thật (chống CSRF). */
  auth?: 'dev' | 'invite';
}

/** Mã mời của máy chủ giả (không phải mã thật; máy chủ thật tạo mã bằng `writory.db.invites`). */
export const MOCK_INVITE_CODE = 'wt-mock-mock-mock-mock-mock-mock-mock-mock';
const MOCK_INVITE_NAME = 'Bạn thử';

const KEY_PREFIX = 'sk-or-';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });
}

function errorResponse(code: string, fields?: string[]): Response {
  const known = MOCK_ERRORS[code] ?? MOCK_ERRORS.INTERNAL_ERROR ?? { message: '', status: 500 };
  return jsonResponse({ code, message: known.message, ...(fields ? { fields } : {}) }, known.status);
}

function errorPayload(code: string): { code: string; message: string } {
  return { code, message: (MOCK_ERRORS[code] ?? MOCK_ERRORS.INTERNAL_ERROR)?.message ?? '' };
}

const STAGE_LABELS: Record<string, string> = {
  context: 'Đang dựng bối cảnh',
  outline: 'Đang lên dàn ý',
  write: 'Đang viết',
  review: 'Đang soát',
  commit: 'Đang lưu chương',
  choices: 'Đang nghĩ lựa chọn',
};

function stage(name: StageEvent['stage'], scene: number | null = null): ChapterEvent {
  return { type: 'stage', stage: name, scene, attempt: scene === null ? null : 1, label: STAGE_LABELS[name] ?? name };
}

const PRE_STREAM = new Set([
  'PLAYER_KEY_MISSING', 'PLAYER_KEY_UNREADABLE', 'COST_LIMIT_STORY', 'STORY_BUSY', 'CHAPTER_PENDING',
  'WRITORY_RATE_LIMITED', 'CHOICE_REQUIRED', 'STORY_COMPLETE', 'CONFIG_LIMIT_NOT_SET',
]);
// Mã của `scene_blocked`: lộ bí mật (G2) và chiều theo hành động vượt luật (G6, D-137).
const LEAK = new Set(['SCENE_LEAK_BLOCKED', 'SCENE_OVERREACH_BLOCKED']);
const ACTION_FAULTS = new Set([
  'ACTION_EMPTY', 'ACTION_TOO_LONG', 'ACTION_OUT_OF_STORY', 'ACTION_UNCLEAR', 'ACTION_FORBIDDEN',
  'LLM_CONTENT_BLOCKED', 'INPUT_BLOCKED',
]);
const NARRATOR_FAULTS = new Set(['NARRATOR_QUESTION_EMPTY', 'NARRATOR_QUESTION_TOO_LONG', 'NARRATOR_LIMIT_REACHED']);

export function createMockServer(options: MockOptions = {}) {
  const scale = options.delayScale ?? 1;
  const now = options.now ?? (() => new Date());
  const fault = () => (typeof options.fault === 'function' ? options.fault() : (options.fault ?? null));
  const empty = options.scenario === 'rong';

  let key: string | null = empty ? null : 'sk-or-v1-mock-0000000000007f3a';
  let monthSpent = empty ? 0 : 0.31;
  const stories = new Map<string, MockStory>();
  const setups = new Map<string, MockSetup>();
  let seq = 0;
  let loggedIn = false;

  const daysAgo = (d: number) => new Date(now().getTime() - d * 86400000).toISOString();

  if (!empty) {
    const a: MockStory = {
      id: 's-chuong', title: 'Chuông Đồng Đèo Gió', length_level: 'short', total: 4, chapter: 2,
      scenes: { 1: [SCENES[0] ?? '', SCENES[1] ?? ''], 2: [SCENES[2] ?? '', SCENES[3] ?? ''] },
      choices: { 2: makeChoices(1) }, action: null, spent: 0.09, updated_at: daysAgo(0.1),
      narratorUsed: {}, busy: false,
    };
    const b: MockStory = {
      id: 's-ngo', title: 'Ngõ Mười Ba Đèn Lồng', length_level: 'short', total: 2, chapter: 2,
      scenes: { 1: [FINISHED_SCENES[0] ?? ''], 2: [FINISHED_SCENES[1] ?? ''] },
      choices: {}, action: null, spent: 0.22, updated_at: daysAgo(3), narratorUsed: {}, busy: false,
    };
    const c: MockStory = {
      id: 's-haidang', title: 'Hải Đăng Không Người Gác', length_level: 'medium', total: 12, chapter: 0,
      scenes: {}, choices: {}, action: null, spent: 0.02, updated_at: daysAgo(9), narratorUsed: {}, busy: false,
    };
    for (const s of [a, b, c]) stories.set(s.id, s);
  }

  const wait = (ms: number, signal?: AbortSignal | null) =>
    new Promise<void>((resolve, reject) => {
      if (signal?.aborted) return reject(new DOMException('aborted', 'AbortError'));
      const t = setTimeout(resolve, ms * scale);
      signal?.addEventListener('abort', () => {
        clearTimeout(t);
        reject(new DOMException('aborted', 'AbortError'));
      });
    });

  function lastExcerpt(s: MockStory): string | null {
    const scenes = s.scenes[s.chapter];
    const last = scenes?.[scenes.length - 1];
    if (!last) return null;
    const paras = last.split('\n').filter(Boolean);
    return paras[paras.length - 1] ?? null;
  }

  function summary(s: MockStory): StorySummary {
    // Như máy chủ thật: nhãn lấy từ mọi mức, kể cả mức đã đóng (truyện cũ vẫn có nhãn, D-88).
    const level = MOCK_LENGTH_LEVELS.find((l) => l.key === s.length_level);
    return {
      story_id: s.id, title: s.title, length_level: s.length_level, length_label: level?.label ?? s.length_level,
      chapter: s.chapter, finished: s.chapter >= s.total, last_excerpt: lastExcerpt(s), updated_at: s.updated_at,
    };
  }

  function storyOut(s: MockStory) {
    const finished = s.chapter >= s.total;
    return {
      story_id: s.id, length_level: s.length_level, chapter: s.chapter, pending: false,
      choices: s.chapter >= 1 ? (s.choices[s.chapter] ?? []) : [],
      action: s.action && s.action.for_chapter === s.chapter + 1 ? s.action : null,
      next_ready: !finished && (s.chapter === 0 || (s.action !== null && s.action.for_chapter === s.chapter + 1)),
      finished,
    };
  }

  function spend(s: MockStory | null, usd: number) {
    monthSpent += usd;
    if (s) s.spent += usd;
  }

  function sseResponse(s: MockStory, signal?: AbortSignal | null): Response {
    const chapter = s.chapter + 1;
    const f = fault();
    const enc = new TextEncoder();
    let cancelled = false;
    const body = new ReadableStream<Uint8Array>({
      async start(controller) {
        const send = (e: ChapterEvent) => {
          const text = `event: ${e.type}\ndata: ${JSON.stringify(e)}\n\n`;
          // Cắt đôi mỗi sự kiện để giao diện luôn đi qua đường ghép chuỗi bị cắt.
          const mid = Math.floor(text.length / 2);
          controller.enqueue(enc.encode(text.slice(0, mid)));
          controller.enqueue(enc.encode(text.slice(mid)));
        };
        const ping = () => controller.enqueue(enc.encode(': ping\n\n'));
        try {
          s.busy = true;
          send(stage('context'));
          await wait(700, signal);
          send(stage('outline'));
          await wait(900, signal);
          const base = ((chapter - 1) * 2) % SCENES.length;
          const texts = [SCENES[base] ?? '', SCENES[(base + 1) % SCENES.length] ?? ''];
          const isLast = chapter >= s.total;
          const finalTexts = isLast ? [texts[0] ?? '', END_SCENE] : texts;
          for (let i = 0; i < finalTexts.length; i++) {
            const n = i + 1;
            send(stage('write', n));
            await wait(i === 0 ? 1800 : 7000, signal);
            ping();
            send(stage('review', n));
            await wait(700, signal);
            if (f && LEAK.has(f) && n === 2) {
              send({ type: 'scene_blocked', scene: n, ...errorPayload(f) });
              return;
            }
            if (f && !PRE_STREAM.has(f) && !LEAK.has(f) && !ACTION_FAULTS.has(f) && !NARRATOR_FAULTS.has(f) && n === 2) {
              send({ type: 'error', ...errorPayload(f) });
              return;
            }
            send({ type: 'scene_ready', scene: n, text: finalTexts[i] ?? '' });
          }
          send(stage('commit'));
          await wait(600, signal);
          s.scenes[chapter] = finalTexts;
          s.chapter = chapter;
          s.action = null;
          s.updated_at = now().toISOString();
          spend(s, 0.04);
          send({ type: 'chapter_committed', chapter });
          if (isLast) {
            send({ type: 'story_finished', chapter });
            return;
          }
          send(stage('choices'));
          await wait(900, signal);
          const choices = makeChoices(chapter);
          s.choices[chapter] = choices;
          send({ type: 'choices_ready', chapter, choices });
        } catch (err) {
          cancelled = true; // người đọc rời trang: không ghi gì thêm, như máy chủ
          try {
            controller.error(err);
          } catch {
            /* luồng đã huỷ */
          }
        } finally {
          s.busy = false;
          if (!cancelled) {
            try {
              controller.close();
            } catch {
              /* đã đóng */
            }
          }
        }
      },
      cancel() {
        cancelled = true;
        s.busy = false;
      },
    });
    return new Response(body, { status: 200, headers: { 'content-type': 'text/event-stream' } });
  }

  function newSetup(body: SetupStartIn): SetupOut {
    seq += 1;
    return {
      session_id: `setup-mock${seq}`, step: 'settings',
      tags: { genre: body.tags.genre, era: null, voice: body.tags.voice ?? null },
      darkness_level: body.darkness_level ?? null,
      length_level: body.length_level,
      naming: body.naming ?? { names: 'han_viet', places: 'hu_cau' },
      settings: null, setting_index: null, plots: null, plot_index: null, characters: null,
      character_index: null, protagonist: null, story_id: null,
    };
  }

  async function readBody(init?: RequestInit): Promise<Record<string, unknown>> {
    if (!init?.body || typeof init.body !== 'string') return {};
    try {
      return JSON.parse(init.body) as Record<string, unknown>;
    } catch {
      return {};
    }
  }

  async function handle(url: string, init?: RequestInit): Promise<Response> {
    const method = (init?.method ?? 'GET').toUpperCase();
    const path = url.replace(/^.*?\/api/, '').split('?')[0] ?? '';
    const signal = init?.signal ?? null;
    const body = await readBody(init);
    const f = fault();
    const parts = path.split('/').filter(Boolean).map(decodeURIComponent);

    if (path === '/config/public' && method === 'GET') return jsonResponse(MOCK_CONFIG);

    // --- đăng nhập (D-89) ---
    const authMode = options.auth ?? 'dev';
    const sessionOut = () =>
      authMode === 'dev'
        ? { mode: 'dev', logged_in: true, name: null }
        : { mode: 'invite', logged_in: loggedIn, name: loggedIn ? MOCK_INVITE_NAME : null };
    if (method !== 'GET') {
      const headers = new Headers(init?.headers);
      if ((headers.get('content-type') ?? '').split(';')[0]?.trim() !== 'application/json') {
        return errorResponse('REQUEST_ORIGIN_INVALID');
      }
    }
    if (path === '/auth/session' && method === 'GET') return jsonResponse(sessionOut());
    if (path === '/auth/login' && method === 'POST') {
      if (authMode === 'invite') {
        const typed = typeof body.code === 'string' ? body.code.trim().toLowerCase() : '';
        if (typed !== MOCK_INVITE_CODE) return errorResponse('INVITE_CODE_INVALID');
        loggedIn = true;
      }
      return jsonResponse(sessionOut());
    }
    if (path === '/auth/logout' && method === 'POST') {
      loggedIn = false;
      return jsonResponse(sessionOut());
    }
    if (authMode === 'invite' && !loggedIn) return errorResponse('AUTH_REQUIRED');

    // --- key, chi phí ---
    if (path === '/player/key') {
      if (method === 'GET') return jsonResponse({ has_key: key !== null, last4: key ? key.slice(-4) : null });
      if (method === 'PUT') {
        const raw = typeof body.api_key === 'string' ? body.api_key.trim() : '';
        if (!raw.startsWith(KEY_PREFIX) || raw.length < KEY_PREFIX.length + 8) {
          return errorResponse('PLAYER_KEY_INVALID', ['api_key']);
        }
        key = raw;
        return jsonResponse({ has_key: true, last4: raw.slice(-4) });
      }
      if (method === 'DELETE') {
        key = null;
        return jsonResponse({ has_key: false, last4: null });
      }
    }
    if (path === '/player/costs' && method === 'GET') {
      const list = [...stories.values()];
      return jsonResponse({
        total_usd: list.reduce((a, s) => a + s.spent, 0),
        this_month_usd: monthSpent,
        stories: list.map((s) => ({ story_id: s.id, spent_usd: s.spent })),
      });
    }

    // --- truyện ---
    if (path === '/stories' && method === 'GET') {
      const list = [...stories.values()].sort((x, y) => y.updated_at.localeCompare(x.updated_at));
      return jsonResponse({ stories: list.map(summary) });
    }
    if (parts[0] === 'stories' && parts[1]) {
      const s = stories.get(parts[1]);
      if (!s) return errorResponse('STORY_NOT_FOUND');
      const rest = parts.slice(2).join('/');
      if (rest === '' && method === 'GET') return jsonResponse(storyOut(s));
      if (rest === 'estimate' && method === 'GET') {
        // Giả: trung bình chi phí đã tiêu trên số chương đã viết; chưa viết chương nào thì số mặc định.
        const measured = s.chapter >= 1;
        return jsonResponse({
          chapter: s.chapter + 1,
          usd: measured ? s.spent / s.chapter : MOCK_CONFIG.chapter_estimate_default_usd,
          source: measured ? 'story_median' : 'default',
          chapters_used: measured ? s.chapter : 0,
        });
      }
      if (rest === 'chapters/next' && method === 'POST') {
        if (!key) return errorResponse('PLAYER_KEY_MISSING');
        if (s.busy) return errorResponse('STORY_BUSY');
        if (s.chapter >= s.total) return errorResponse('STORY_COMPLETE');
        if (s.chapter >= 1 && !(s.action && s.action.for_chapter === s.chapter + 1)) return errorResponse('CHOICE_REQUIRED');
        if (f && PRE_STREAM.has(f)) return errorResponse(f);
        return sseResponse(s, signal);
      }
      if (parts[2] === 'chapters' && parts[3] && method === 'GET') {
        const n = Number(parts[3]);
        const scenes = s.scenes[n];
        if (!scenes) return errorResponse('CHAPTER_NOT_FOUND');
        return jsonResponse({ number: n, scenes });
      }
      if (rest === 'choices' && method === 'POST') {
        if (s.chapter === 0 || s.chapter >= s.total) return jsonResponse({ chapter: s.chapter, choices: [] });
        await wait(1200, signal);
        const choices = s.choices[s.chapter] ?? makeChoices(s.chapter);
        s.choices[s.chapter] = choices;
        return jsonResponse({ chapter: s.chapter, choices });
      }
      if (rest === 'choice' && method === 'POST') {
        if (s.chapter >= s.total) return errorResponse('STORY_COMPLETE');
        const c = (s.choices[s.chapter] ?? []).find((x) => x.id === body.choice_id);
        if (!c) return errorResponse('CHOICE_NOT_FOUND');
        s.action = { for_chapter: s.chapter + 1, source: 'choice', text: c.text };
        return jsonResponse(s.action);
      }
      if (rest === 'action' && method === 'POST') {
        if (s.chapter >= s.total) return errorResponse('STORY_COMPLETE');
        const text = typeof body.text === 'string' ? body.text.trim() : '';
        if (!text) return errorResponse('ACTION_EMPTY');
        const max = MOCK_CONFIG.input.custom_action_max_chars;
        if (max !== null && text.length > max) return errorResponse('ACTION_TOO_LONG');
        await wait(800, signal);
        if (f && ACTION_FAULTS.has(f)) return errorResponse(f);
        s.action = { for_chapter: s.chapter + 1, source: 'custom', text };
        return jsonResponse(s.action);
      }
      if (rest === 'notebook' && method === 'GET') return jsonResponse(notebookFor(s.chapter));
      if (rest === 'narrator') {
        const limit = MOCK_CONFIG.narrator_questions_per_chapter ?? 0;
        const used = s.narratorUsed[s.chapter] ?? 0;
        if (method === 'GET') return jsonResponse({ remaining: Math.max(0, limit - used) });
        if (method === 'POST') {
          const q = typeof body.question === 'string' ? body.question.trim() : '';
          if (!q) return errorResponse('NARRATOR_QUESTION_EMPTY');
          const max = MOCK_CONFIG.input.narrator_question_max_chars;
          if (max !== null && q.length > max) return errorResponse('NARRATOR_QUESTION_TOO_LONG');
          if (f && NARRATOR_FAULTS.has(f)) return errorResponse(f);
          if (used >= limit) return errorResponse('NARRATOR_LIMIT_REACHED');
          await wait(1100, signal);
          s.narratorUsed[s.chapter] = used + 1;
          spend(s, 0.002);
          const book = notebookFor(s.chapter);
          const lower = q.toLocaleLowerCase('vi');
          const hit = book.entries.find((e) =>
            [e.text, ...e.aliases].some((name) => lower.includes(name.toLocaleLowerCase('vi'))),
          );
          return jsonResponse({
            answer: hit?.quote ? `Bạn đã đọc: ${hit.quote}` : 'Bạn chưa biết điều này.',
            remaining: Math.max(0, limit - used - 1),
            source_chapters: hit ? [hit.since_chapter] : [],
          });
        }
      }
    }

    // --- khởi tạo ---
    if (path === '/setup' && method === 'POST') {
      const start = body as unknown as SetupStartIn;
      if (!start.tags?.genre) return errorResponse('REQUEST_INVALID', ['tags.genre']);
      const length = MOCK_LENGTH_LEVELS.find((l) => l.key === start.length_level);
      if (!length) return errorResponse('REQUEST_INVALID', ['length_level']);
      if (!length.player_selectable) return errorResponse('STORY_LENGTH_NOT_OPEN', ['length_level']);
      const out = newSetup(start);
      setups.set(out.session_id, { out });
      return jsonResponse(out);
    }
    if (parts[0] === 'setup' && parts[1]) {
      const rec = setups.get(parts[1]);
      if (!rec) return errorResponse('SETUP_NOT_FOUND');
      const o = rec.out;
      const step = parts[2] ?? '';
      const save = (next: Partial<SetupOut>) => {
        rec.out = { ...rec.out, ...next };
        return jsonResponse(rec.out);
      };
      if (step === '' && method === 'GET') return jsonResponse(o);
      if (method === 'POST' && ['settings', 'plots', 'characters'].includes(step)) {
        if (!key) return errorResponse('PLAYER_KEY_MISSING');
        if (step === 'settings' && o.settings) return jsonResponse(o);
        if (step === 'plots' && o.plots) return jsonResponse(o);
        if (step === 'characters' && o.characters) return jsonResponse(o);
        if ((step === 'plots' && o.setting_index === null) || (step === 'characters' && o.plot_index === null)) {
          return errorResponse('SETUP_STEP_NOT_READY');
        }
        await wait(1600, signal);
        if (f === 'LLM_INSUFFICIENT_CREDITS' || f === 'LLM_AUTH_FAILED') return errorResponse(f);
        if (step === 'settings') return save({ settings: SETTINGS });
        if (step === 'plots') return save({ plots: PLOTS });
        return save({ characters: CHARACTERS });
      }
      if (method === 'PUT' && ['settings', 'plots', 'characters'].includes(step)) {
        const index = typeof body.index === 'number' ? body.index : -1;
        if (index < 0 || index > 2) return errorResponse('REQUEST_INVALID', ['index']);
        if (step === 'settings') {
          if (!o.settings) return errorResponse('SETUP_STEP_NOT_READY');
          if (o.setting_index === index) return jsonResponse(o);
          return save({ setting_index: index, step: 'plots', plots: null, plot_index: null, characters: null, character_index: null, protagonist: null });
        }
        if (step === 'plots') {
          if (!o.plots) return errorResponse('SETUP_STEP_NOT_READY');
          if (o.plot_index === index) return jsonResponse(o);
          return save({ plot_index: index, step: 'characters', characters: null, character_index: null, protagonist: null });
        }
        const option = o.characters?.[index];
        if (!option) return errorResponse('SETUP_STEP_NOT_READY');
        const limits = MOCK_CONFIG.input;
        const pick = (field: 'name' | 'personality' | 'backstory', max: number | null) => {
          const edited = body[field];
          const value = (typeof edited === 'string' ? edited : option[field]).trim();
          const bad = !value || (typeof edited === 'string' && max !== null && value.length > max);
          return { value, bad };
        };
        const name = pick('name', limits.character_name_max_chars);
        const personality = pick('personality', limits.personality_max_chars);
        const backstory = pick('backstory', limits.backstory_max_chars);
        const bad = (['name', 'personality', 'backstory'] as const).filter((_, i) => [name, personality, backstory][i]?.bad);
        if (bad.length) return errorResponse('CHARACTER_EDIT_INVALID', [...bad]);
        return save({
          character_index: index, step: 'finalize',
          protagonist: { name: name.value, personality: personality.value, backstory: backstory.value },
        });
      }
      if (method === 'POST' && step === 'finalize') {
        if (o.story_id) return jsonResponse(o);
        if (!o.protagonist) return errorResponse('SETUP_STEP_NOT_READY');
        if (!key) return errorResponse('PLAYER_KEY_MISSING');
        await wait(2600, signal);
        seq += 1;
        const id = `s-moi${seq}`;
        const setting = o.settings?.[o.setting_index ?? 0];
        stories.set(id, {
          id, title: setting?.title ?? 'Truyện mới', length_level: o.length_level, total: 4, chapter: 0,
          scenes: {}, choices: {}, action: null, spent: 0, updated_at: now().toISOString(), narratorUsed: {}, busy: false,
        });
        spend(stories.get(id) ?? null, 0.03);
        return save({ story_id: id, step: 'done' });
      }
    }

    return errorResponse('ROUTE_NOT_FOUND');
  }

  return {
    fetch: (url: string, init?: RequestInit) => handle(url, init),
  };
}
