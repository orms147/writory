// Một lần viết chương qua SSE (D-46, D-69). Giữ ngoài React: rời trang đọc sang trang khác trong
// app thì luồng vẫn chạy và chương vẫn được ghi; StrictMode hay mount lại không mở luồng thứ hai
// (máy chủ sẽ trả STORY_BUSY, G8). Đóng thẻ thì trình duyệt ngắt kết nối và máy chủ huỷ lần viết.

import { useCallback, useSyncExternalStore } from 'react';
import { streamChapter } from '../api/client';
import { ApiError, asApiError, clientError, isAbortError } from '../api/errors';
import { isTerminal } from '../api/sse';
import type { ChapterEvent, PlayerChoice, SceneBlockedEvent, StageEvent } from '../api/types';

export interface ChapterRunState {
  storyId: string;
  /** Chương đang viết (chương đã ghi + 1). */
  chapter: number;
  status: 'running' | 'done' | 'failed';
  stages: StageEvent[];
  scenes: { scene: number; text: string }[];
  committed: boolean;
  choices: PlayerChoice[] | null;
  finished: boolean;
  blocked: SceneBlockedEvent | null;
  error: ApiError | null;
  /** Chữ người chơi đã chọn dẫn tới chương này (hiện ở màn chờ), nếu có. */
  chosen: string | null;
  startedAt: number;
}

type Listener = () => void;

const runs = new Map<string, ChapterRunState>();
const listeners = new Map<string, Set<Listener>>();
const controllers = new Map<string, AbortController>();
let version = 0;

function emit(storyId: string) {
  version += 1;
  for (const fn of listeners.get(storyId) ?? []) fn();
  for (const fn of listeners.get('*') ?? []) fn();
}

function update(storyId: string, patch: (s: ChapterRunState) => ChapterRunState) {
  const cur = runs.get(storyId);
  if (!cur) return;
  runs.set(storyId, patch(cur));
  emit(storyId);
}

/** Áp một sự kiện vào trạng thái (thuần, test được). */
export function applyEvent(s: ChapterRunState, e: ChapterEvent): ChapterRunState {
  switch (e.type) {
    case 'stage':
      return { ...s, stages: [...s.stages, e] };
    case 'scene_ready':
      return { ...s, scenes: [...s.scenes.filter((x) => x.scene !== e.scene), { scene: e.scene, text: e.text }] };
    case 'scene_blocked':
      return { ...s, blocked: e, status: 'failed' };
    case 'chapter_committed':
      return { ...s, committed: true, chapter: e.chapter };
    case 'choices_ready':
      return { ...s, choices: e.choices, status: 'done' };
    case 'story_finished':
      return { ...s, finished: true, status: 'done' };
    case 'error':
      return { ...s, error: new ApiError({ code: e.code, message: e.message }), status: 'failed' };
  }
}

export function getRun(storyId: string): ChapterRunState | null {
  return runs.get(storyId) ?? null;
}

export function isRunning(storyId: string): boolean {
  return runs.get(storyId)?.status === 'running';
}

/** Bắt đầu viết chương `chapter`. Đang có lần viết chạy cho truyện này thì trả lại lần đó. */
export function startRun(storyId: string, chapter: number, chosen: string | null = null): ChapterRunState {
  const existing = runs.get(storyId);
  if (existing?.status === 'running') return existing;
  const state: ChapterRunState = {
    storyId, chapter, status: 'running', stages: [], scenes: [], committed: false, choices: null,
    finished: false, blocked: null, error: null, chosen, startedAt: Date.now(),
  };
  runs.set(storyId, state);
  const controller = new AbortController();
  controllers.set(storyId, controller);
  emit(storyId);
  void consume(storyId, controller.signal);
  return state;
}

async function consume(storyId: string, signal: AbortSignal) {
  let terminal = false;
  try {
    for await (const event of streamChapter(storyId, signal)) {
      update(storyId, (s) => applyEvent(s, event));
      if (isTerminal(event)) terminal = true;
    }
    if (!terminal) throw clientError('CLIENT_STREAM_CUT');
  } catch (err) {
    if (isAbortError(err)) return;
    const error = asApiError(err);
    update(storyId, (s) => (s.status === 'running' ? { ...s, status: 'failed', error } : s));
  } finally {
    if (controllers.get(storyId)?.signal === signal) controllers.delete(storyId);
  }
}

/** Bỏ trạng thái của lần viết (đã xong hoặc lỗi) để trang đọc lấy lại trạng thái từ máy chủ. */
export function clearRun(storyId: string) {
  controllers.get(storyId)?.abort();
  controllers.delete(storyId);
  runs.delete(storyId);
  emit(storyId);
}

export function subscribeRun(storyId: string, fn: Listener): () => void {
  let set = listeners.get(storyId);
  if (!set) {
    set = new Set();
    listeners.set(storyId, set);
  }
  set.add(fn);
  return () => {
    set.delete(fn);
  };
}

export function useChapterRun(storyId: string): ChapterRunState | null {
  const subscribe = useCallback((fn: Listener) => subscribeRun(storyId, fn), [storyId]);
  return useSyncExternalStore(subscribe, () => getRun(storyId), () => null);
}

const subscribeAll = (fn: Listener) => subscribeRun('*', fn);

/** Theo dõi mọi lần viết (tủ truyện hiện "đang viết"); trả số phiên bản để render lại. */
export function useAnyRun(): number {
  return useSyncExternalStore(subscribeAll, () => version, () => 0);
}

/** Chỉ cho test. */
export function resetRuns() {
  for (const c of controllers.values()) c.abort();
  controllers.clear();
  runs.clear();
}
