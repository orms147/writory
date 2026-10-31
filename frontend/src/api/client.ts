// Client API. Mọi lời gọi qua `request`/`streamChapter`; `fetch` thay được (lớp mock, test).
// Đường dẫn khớp router máy chủ (`backend/src/writory/api/`), đặt sau tiền tố `/api` của proxy Vite.

import { ApiError, asApiError, clientError, errorFromResponse, isAbortError } from './errors';
import { readChapterEvents } from './sse';
import type {
  ActionOut,
  AuthSession,
  ChapterEstimateOut,
  ChapterEvent,
  ChapterOut,
  CharacterChoiceIn,
  ChoicesOut,
  NarratorAnswerOut,
  NarratorQuotaOut,
  NotebookOut,
  PlayerCosts,
  PlayerKeyOut,
  PublicConfig,
  SetupOut,
  SetupStartIn,
  StoriesOut,
  StoryOut,
} from './types';

type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

const API_BASE: string = import.meta.env.VITE_API_BASE ?? '/api';
let fetchImpl: FetchLike = (input, init) => fetch(input, init);

/** Thay `fetch` (lớp mock khi `VITE_MOCK`, hoặc test). */
export function setFetch(fn: FetchLike): void {
  fetchImpl = fn;
}

async function send(method: string, path: string, body?: unknown, signal?: AbortSignal, accept = 'application/json'): Promise<Response> {
  const init: RequestInit = { method, headers: { accept } };
  // Mọi yêu cầu ghi gửi `content-type: application/json`, kể cả khi không có thân: máy chủ dùng nó
  // để chống CSRF ở mọi chế độ (D-89, `deps.api_guard`). Cookie phiên đi kèm vì cùng
  // origin (`credentials` mặc định `same-origin`).
  if (method !== 'GET') init.headers = { ...init.headers, 'content-type': 'application/json' };
  if (body !== undefined) init.body = JSON.stringify(body);
  if (signal) init.signal = signal;
  try {
    return await fetchImpl(`${API_BASE}${path}`, init);
  } catch (err) {
    if (isAbortError(err)) throw err;
    throw asApiError(err);
  }
}

export async function request<T>(method: string, path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await send(method, path, body, signal);
  if (!response.ok) throw await errorFromResponse(response);
  try {
    return (await response.json()) as T;
  } catch (err) {
    if (isAbortError(err)) throw err;
    throw clientError('CLIENT_BAD_RESPONSE');
  }
}

/** GET một tệp chữ (`text/plain`). Lỗi vẫn là JSON G12 như mọi route. */
export async function requestText(path: string, signal?: AbortSignal): Promise<string> {
  const response = await send('GET', path, undefined, signal, 'text/plain');
  if (!response.ok) throw await errorFromResponse(response);
  try {
    return await response.text();
  } catch (err) {
    if (isAbortError(err)) throw err;
    throw clientError('CLIENT_BAD_RESPONSE');
  }
}

const enc = encodeURIComponent;

/** Viết chương tiếp theo qua SSE. Lỗi kiểm được trước khi viết (key, trần, chương dở…) là JSON có
 *  status, nên ném ApiError trước khi có sự kiện nào (`api/play.py`).
 *  `auto` ("Tự viết đến hết"): không cần hành động đã lưu, máy chủ không tạo lựa chọn, luồng kết
 *  thúc sau `chapter_committed` (chương cuối: sau `story_finished`). */
export async function* streamChapter(storyId: string, signal?: AbortSignal, auto = false): AsyncGenerator<ChapterEvent> {
  const query = auto ? '?auto=true' : '';
  const response = await send('POST', `/stories/${enc(storyId)}/chapters/next${query}`, undefined, signal);
  if (!response.ok) throw await errorFromResponse(response);
  if (!response.body) throw clientError('CLIENT_BAD_RESPONSE');
  try {
    yield* readChapterEvents(response.body);
  } catch (err) {
    if (isAbortError(err) || err instanceof ApiError) throw err;
    throw clientError('CLIENT_STREAM_CUT');
  }
}

export const api = {
  publicConfig: () => request<PublicConfig>('GET', '/config/public'),

  session: () => request<AuthSession>('GET', '/auth/session'),
  /** Mã mời chỉ sống trong thân yêu cầu này; không lưu ở trình duyệt, không log (D-89). */
  login: (code: string) => request<AuthSession>('POST', '/auth/login', { code }),
  logout: () => request<AuthSession>('POST', '/auth/logout'),

  stories: () => request<StoriesOut>('GET', '/stories'),
  story: (id: string) => request<StoryOut>('GET', `/stories/${enc(id)}`),
  chapter: (id: string, n: number) => request<ChapterOut>('GET', `/stories/${enc(id)}/chapters/${n}`),
  choices: (id: string) => request<ChoicesOut>('POST', `/stories/${enc(id)}/choices`),
  pickChoice: (id: string, choiceId: string) =>
    request<ActionOut>('POST', `/stories/${enc(id)}/choice`, { choice_id: choiceId }),
  customAction: (id: string, text: string) => request<ActionOut>('POST', `/stories/${enc(id)}/action`, { text }),

  /** Kịch bản audio: văn mọi chương đã ghi, theo thứ tự; rỗng khi chưa có chương nào. */
  script: (id: string) => requestText(`/stories/${enc(id)}/script.txt`),
  chapterEstimate: (id: string) => request<ChapterEstimateOut>('GET', `/stories/${enc(id)}/estimate`),
  notebook: (id: string) => request<NotebookOut>('GET', `/stories/${enc(id)}/notebook`),
  narratorQuota: (id: string) => request<NarratorQuotaOut>('GET', `/stories/${enc(id)}/narrator`),
  askNarrator: (id: string, question: string) =>
    request<NarratorAnswerOut>('POST', `/stories/${enc(id)}/narrator`, { question }),

  playerKey: () => request<PlayerKeyOut>('GET', '/player/key'),
  /** Key chỉ sống trong thân yêu cầu này; không lưu ở trình duyệt, không log (G7). */
  putPlayerKey: (apiKey: string) => request<PlayerKeyOut>('PUT', '/player/key', { api_key: apiKey }),
  deletePlayerKey: () => request<PlayerKeyOut>('DELETE', '/player/key'),
  costs: () => request<PlayerCosts>('GET', '/player/costs'),

  startSetup: (body: SetupStartIn) => request<SetupOut>('POST', '/setup', body),
  setup: (sid: string) => request<SetupOut>('GET', `/setup/${enc(sid)}`),
  proposeSettings: (sid: string) => request<SetupOut>('POST', `/setup/${enc(sid)}/settings`),
  chooseSetting: (sid: string, index: number) => request<SetupOut>('PUT', `/setup/${enc(sid)}/settings`, { index }),
  proposePlots: (sid: string) => request<SetupOut>('POST', `/setup/${enc(sid)}/plots`),
  choosePlot: (sid: string, index: number) => request<SetupOut>('PUT', `/setup/${enc(sid)}/plots`, { index }),
  proposeCharacters: (sid: string) => request<SetupOut>('POST', `/setup/${enc(sid)}/characters`),
  chooseCharacter: (sid: string, body: CharacterChoiceIn) =>
    request<SetupOut>('PUT', `/setup/${enc(sid)}/characters`, body),
  finalize: (sid: string) => request<SetupOut>('POST', `/setup/${enc(sid)}/finalize`),
};
