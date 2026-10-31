// "Tự viết đến hết": viết liền từng chương bằng `POST /stories/{id}/chapters/next?auto=true`, không
// chờ người chơi chọn; máy chủ bỏ bước tạo lựa chọn. Giữ ngoài React như `chapterRun`: rời trang đọc
// sang trang khác trong app thì vòng vẫn chạy; đóng thẻ thì lần viết đang chạy bị huỷ (máy chủ không
// ghi chương dở) và vòng dừng.
//
// Dừng: chỉ sau khi chương đang viết xong. Không huỷ giữa chương: chương bị huỷ không được lưu mà
// tiền đã tốn. Lỗi bất kỳ: dừng vòng. Lỗi của lần viết nằm ở `ChapterRunState` (giao diện lỗi của
// lần viết hiện nó); lỗi ngoài lần viết (lấy lại trạng thái truyện) nằm ở `error` dưới đây.

import { useCallback, useSyncExternalStore } from 'react';
import { api } from '../api/client';
import { asApiError, type ApiError } from '../api/errors';
import type { StoryOut } from '../api/types';
import { clearRun, getRun, startRun, subscribeRun, type ChapterRunState } from './chapterRun';

export interface AutoWriteState {
  storyId: string;
  status: 'running' | 'stopped' | 'finished' | 'failed';
  /** Người chơi đã bấm "Dừng sau chương này". */
  stopRequested: boolean;
  /** Trạng thái truyện lấy lại sau mỗi chương, để trang đọc hiện chương vừa ghi. */
  story: StoryOut | null;
  /** Lỗi ngoài lần viết chương. */
  error: ApiError | null;
}

type Listener = () => void;

const autos = new Map<string, AutoWriteState>();
const listeners = new Map<string, Set<Listener>>();
/** Mỗi lần bắt đầu một vòng có số riêng; vòng cũ thấy số đổi thì thôi (reset trong test). */
const tokens = new Map<string, number>();
let seq = 0;

function emit(storyId: string) {
  for (const fn of listeners.get(storyId) ?? []) fn();
}

function patch(storyId: string, fn: (s: AutoWriteState) => AutoWriteState) {
  const cur = autos.get(storyId);
  if (!cur) return;
  autos.set(storyId, fn(cur));
  emit(storyId);
}

export function getAuto(storyId: string): AutoWriteState | null {
  return autos.get(storyId) ?? null;
}

export function isAutoRunning(storyId: string): boolean {
  return autos.get(storyId)?.status === 'running';
}

/** Bắt đầu (hoặc tiếp tục) tự viết. Đang chạy thì không mở vòng thứ hai. */
export function startAuto(storyId: string): void {
  if (isAutoRunning(storyId)) return;
  seq += 1;
  const token = seq;
  tokens.set(storyId, token);
  autos.set(storyId, { storyId, status: 'running', stopRequested: false, story: autos.get(storyId)?.story ?? null, error: null });
  emit(storyId);
  void loop(storyId, token);
}

/** Dừng sau chương đang viết; không ngắt chương giữa chừng. */
export function stopAuto(storyId: string): void {
  patch(storyId, (s) => (s.status === 'running' ? { ...s, stopRequested: true } : s));
}

/** Chờ lần viết đang chạy kết thúc. `null`: lần viết bị bỏ ở nơi khác (`clearRun`). */
function waitRun(storyId: string): Promise<ChapterRunState | null> {
  return new Promise((resolve) => {
    let off: (() => void) | null = null;
    const check = () => {
      const run = getRun(storyId);
      if (run && run.status === 'running') return false;
      off?.();
      resolve(run);
      return true;
    };
    if (check()) return;
    off = subscribeRun(storyId, () => void check());
  });
}

async function loop(storyId: string, token: number) {
  const alive = () => tokens.get(storyId) === token;
  const end = (status: AutoWriteState['status']) => patch(storyId, (s) => ({ ...s, status }));
  try {
    for (;;) {
      const story = await api.story(storyId);
      if (!alive()) return;
      patch(storyId, (s) => ({ ...s, story }));
      // Lần viết trước đã ghi xong: bỏ nó để trang đọc hiện chương vừa ghi từ `story`.
      if (getRun(storyId)?.status === 'done') clearRun(storyId);
      if (story.finished) return end('finished');
      if (getAuto(storyId)?.stopRequested) return end('stopped');
      startRun(storyId, story.chapter + 1, null, { auto: true });
      const run = await waitRun(storyId);
      if (!alive()) return;
      if (!run) return end('stopped');
      if (run.status === 'failed') return end('failed');
    }
  } catch (err) {
    if (!alive()) return;
    patch(storyId, (s) => ({ ...s, status: 'failed', error: asApiError(err) }));
  }
}

export function subscribeAuto(storyId: string, fn: Listener): () => void {
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

export function useAutoWrite(storyId: string): AutoWriteState | null {
  const subscribe = useCallback((fn: Listener) => subscribeAuto(storyId, fn), [storyId]);
  return useSyncExternalStore(subscribe, () => getAuto(storyId), () => null);
}

/** Chỉ cho test. */
export function resetAutos() {
  tokens.clear();
  autos.clear();
}
