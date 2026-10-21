import { afterEach, describe, expect, it } from 'vitest';
import { withMock } from '../test/render';
import { getRun, resetRuns, startRun, subscribeRun } from './chapterRun';

function until(storyId: string, done: () => boolean): Promise<void> {
  return new Promise((resolve) => {
    if (done()) return resolve();
    const off = subscribeRun(storyId, () => {
      if (done()) {
        off();
        resolve();
      }
    });
  });
}

afterEach(() => resetRuns());

describe('lần viết chương qua SSE (máy chủ giả)', () => {
  it('đủ sự kiện: các bước, hai cảnh, ghi chương, lựa chọn', async () => {
    withMock();
    // Chương 2 đã có lựa chọn; chọn một rồi viết chương 3.
    const { api } = await import('../api/client');
    const story = await api.story('s-chuong');
    await api.pickChoice('s-chuong', story.choices[0]!.id);
    startRun('s-chuong', 3, 'chữ đã chọn');
    await until('s-chuong', () => getRun('s-chuong')?.status !== 'running');
    const run = getRun('s-chuong')!;
    expect(run.status).toBe('done');
    expect(run.stages.map((s) => s.stage)).toContain('write');
    expect(run.scenes.map((s) => s.scene)).toEqual([1, 2]);
    expect(run.committed).toBe(true);
    expect(run.choices).toHaveLength(3);
    expect(run.chosen).toBe('chữ đã chọn');
  });

  it('cảnh bị chặn: dừng ở scene_blocked, giữ cảnh đã hiện, chưa ghi chương', async () => {
    withMock({ fault: 'SCENE_LEAK_BLOCKED' });
    startRun('s-haidang', 1);
    await until('s-haidang', () => getRun('s-haidang')?.status !== 'running');
    const run = getRun('s-haidang')!;
    expect(run.blocked?.code).toBe('SCENE_LEAK_BLOCKED');
    expect(run.scenes).toHaveLength(1);
    expect(run.committed).toBe(false);
  });

  it('lỗi trước khi mở luồng (JSON có status) thành lỗi của lần viết', async () => {
    withMock({ fault: 'COST_LIMIT_STORY' });
    startRun('s-haidang', 1);
    await until('s-haidang', () => getRun('s-haidang')?.status !== 'running');
    expect(getRun('s-haidang')?.error?.code).toBe('COST_LIMIT_STORY');
  });

  it('gọi lại khi đang chạy không mở luồng thứ hai', () => {
    withMock();
    const a = startRun('s-haidang', 1);
    const b = startRun('s-haidang', 1);
    expect(b).toBe(a);
  });
});
