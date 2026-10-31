// "Tự viết đến hết": vòng viết từng chương bằng `chapters/next?auto=true`, không lựa chọn cuối chương.
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router';
import { afterEach, describe, expect, it } from 'vitest';
import { setFetch } from '../api/client';
import { StoryScreen } from '../screens/story/StoryScreen';
import { resetAutos } from '../state/autoWrite';
import { resetRuns } from '../state/chapterRun';
import type { MockOptions } from '../mock/server';
import { renderApp, withMock } from './render';

afterEach(() => {
  resetAutos();
  resetRuns();
});

/** Máy chủ giả, ghi lại đường dẫn mọi lời gọi viết chương; `hold()` giữ lời gọi viết chương kế tiếp
 *  tới khi `release()`, để test bấm nút trong lúc chương đang viết mà không phụ thuộc thời gian.
 *  `beforeNext(n)`: chạy trước lời gọi viết chương thứ n (đếm từ 1). */
function autoMock(options: MockOptions = {}, beforeNext: (n: number) => void = () => {}) {
  const server = withMock(options);
  const next: string[] = [];
  let gate: Promise<void> | null = null;
  let open: () => void = () => {};
  setFetch(async (url, init) => {
    if (url.includes('/chapters/next')) {
      next.push(url);
      beforeNext(next.length);
      if (gate) await gate;
    }
    return server.fetch(url, init);
  });
  return {
    server,
    next,
    hold: () => {
      gate = new Promise((resolve) => {
        open = resolve;
      });
    },
    release: () => {
      gate = null;
      open();
    },
  };
}

function renderStory(id: string) {
  return renderApp(
    <Routes>
      <Route path="/truyen/:id" element={<StoryScreen />} />
    </Routes>,
    { route: `/truyen/${id}` },
  );
}

describe('máy chủ giả: chế độ auto', () => {
  it('không cần hành động đã lưu, không gửi choices_ready; chế độ thường vẫn đòi chọn', async () => {
    const server = withMock();
    const post = (query: string) =>
      server.fetch(`/api/stories/s-chuong/chapters/next${query}`, { method: 'POST', headers: { 'content-type': 'application/json' } });
    const manual = await post('');
    expect(manual.status).toBe(409);
    expect((await manual.json()).code).toBe('CHOICE_REQUIRED');
    const events = [...(await (await post('?auto=true')).text()).matchAll(/^event: (\w+)$/gm)].map((m) => m[1]);
    expect(events).toContain('chapter_committed');
    expect(events).not.toContain('choices_ready');
    expect(events[events.length - 1]).toBe('chapter_committed');
  });
});

describe('tự viết đến hết', () => {
  it('có nút kèm câu giải thích ở truyện chữ và truyện audio chưa kết; truyện đã kết thì không', async () => {
    withMock();
    const first = renderStory('s-chuong');
    const button = await screen.findByRole('button', { name: 'Tự viết đến hết' });
    expect(button).toHaveAccessibleDescription(/Không cần chọn: truyện tự đi theo kế hoạch tới chương cuối/);
    first.unmount();
    const audio = renderStory('s-dai');
    expect(await screen.findByRole('button', { name: 'Tự viết đến hết' })).toBeInTheDocument();
    audio.unmount();
    renderStory('s-ngo');
    expect(await screen.findByRole('link', { name: 'Đọc lại từ trang đầu' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Tự viết đến hết' })).toBeNull();
  });

  it('bấm nút: gọi chapters/next?auto=true từng chương, không cần chọn, tới story_finished thì hiện màn kết', async () => {
    const { server, next } = autoMock();
    renderStory('s-chuong'); // đã ghi chương 2, bản kế hoạch giả có 4 chương, chưa chọn hướng
    await userEvent.click(await screen.findByRole('button', { name: 'Tự viết đến hết' }));
    expect(await screen.findByRole('link', { name: 'Đọc lại từ trang đầu' }, { timeout: 3000 })).toBeInTheDocument();
    expect(next).toEqual(['/api/stories/s-chuong/chapters/next?auto=true', '/api/stories/s-chuong/chapters/next?auto=true']);
    const story = await (await server.fetch('/api/stories/s-chuong')).json();
    expect(story).toMatchObject({ chapter: 4, finished: true });
    expect(screen.queryByRole('button', { name: /Dừng sau chương này/ })).toBeNull();
  });

  it('"Dừng sau chương này": chương đang viết vẫn viết xong và được ghi, rồi vòng dừng', async () => {
    const { server, next, hold, release } = autoMock();
    renderStory('s-haidang'); // chưa có chương nào
    hold();
    await userEvent.click(await screen.findByRole('button', { name: 'Tự viết đến hết' }));
    expect(await screen.findByText('Đang tự viết chương một…')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Dừng sau chương này' }));
    expect(screen.getByRole('button', { name: 'Sẽ dừng sau chương này' })).toBeDisabled();
    release();
    // Chương một đã ghi, hiện như chương đã xong; chưa có lựa chọn vì viết ở chế độ tự viết.
    expect(await screen.findByText('Chương này chưa có lựa chọn.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Tự viết đến hết' })).toBeInTheDocument();
    expect(next).toEqual(['/api/stories/s-haidang/chapters/next?auto=true']);
    const story = await (await server.fetch('/api/stories/s-haidang')).json();
    expect(story).toMatchObject({ chapter: 1, finished: false, choices: [] });
  });

  it('lỗi ở một chương: vòng dừng, lỗi hiện bằng giao diện lỗi sẵn có', async () => {
    let fault: string | null = null;
    // Chương thứ hai của vòng chạm trần chi phí (lỗi trước khi mở luồng).
    const { next } = autoMock({ fault: () => fault }, (n) => {
      if (n === 2) fault = 'COST_LIMIT_STORY';
    });
    renderStory('s-chuong');
    await userEvent.click(await screen.findByRole('button', { name: 'Tự viết đến hết' }));
    expect(await screen.findByText(/đã dùng hết trần chi phí cho một truyện/, {}, { timeout: 3000 })).toBeInTheDocument();
    expect(next).toHaveLength(2);
    expect(screen.queryByRole('button', { name: /Dừng sau chương này/ })).toBeNull();
    expect(screen.queryByText(/Đang tự viết/)).toBeNull();
    // "Thử lại" chạy tiếp vòng tự viết (vẫn auto=true) từ chương chưa viết được.
    fault = null;
    await userEvent.click(screen.getByRole('button', { name: 'Thử lại' }));
    expect(await screen.findByRole('link', { name: 'Đọc lại từ trang đầu' }, { timeout: 3000 })).toBeInTheDocument();
    expect(next).toHaveLength(3);
    expect(next.every((url) => url.endsWith('/chapters/next?auto=true'))).toBe(true);
  });
});
