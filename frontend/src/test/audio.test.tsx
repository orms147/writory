// Kiểu truyện kịch bản audio: chọn lúc khởi tạo, nút tải kịch bản .txt ở màn truyện, nhãn ở tủ truyện.
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Route, Routes } from 'react-router';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import { setFetch } from '../api/client';
import { Library } from '../screens/Library';
import { Template } from '../screens/setup/Template';
import { ScriptDownload } from '../screens/story/AudioScript';
import { StoryScreen } from '../screens/story/StoryScreen';
import { renderApp, withMock } from './render';

// jsdom không có URL.createObjectURL / revokeObjectURL.
beforeAll(() => {
  for (const name of ['createObjectURL', 'revokeObjectURL'] as const) {
    if (!(name in URL)) Object.defineProperty(URL, name, { value: () => 'blob:mock', configurable: true, writable: true });
  }
});

/** Máy chủ giả, ghi lại mọi yêu cầu (đường dẫn, phương thức, thân). */
function recordingMock() {
  const server = withMock();
  const seen: { url: string; method: string; body: Record<string, unknown> | null }[] = [];
  setFetch(async (url, init) => {
    seen.push({ url, method: init?.method ?? 'GET', body: typeof init?.body === 'string' ? JSON.parse(init.body) : null });
    return server.fetch(url, init);
  });
  return { server, seen };
}

async function fillTemplate() {
  await userEvent.click(screen.getByRole('radio', { name: 'Cổ trang' }));
  await userEvent.click(screen.getByRole('radio', { name: /Truyện ngắn/ }));
}

describe('khởi tạo: kiểu truyện', () => {
  it('mặc định là truyện chữ: không gửi style (máy chủ hiểu là prose)', async () => {
    const { seen } = recordingMock();
    renderApp(<Template />);
    expect(screen.getByRole('radio', { name: /^Truyện chữ/ })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByRole('radio', { name: /^Kịch bản audio/ })).toHaveAttribute('aria-checked', 'false');
    await fillTemplate();
    await userEvent.click(screen.getByRole('button', { name: /Gợi ý bối cảnh/ }));
    await waitFor(() => expect(seen.some((r) => r.url.endsWith('/setup') && r.method === 'POST')).toBe(true));
    const start = seen.find((r) => r.url.endsWith('/setup') && r.method === 'POST');
    expect(start?.body).not.toHaveProperty('style');
  });

  it('chọn "Kịch bản audio" thì POST /setup gửi style "audio"; phiên trả về style', async () => {
    const { server, seen } = recordingMock();
    renderApp(<Template />);
    await fillTemplate();
    await userEvent.click(screen.getByRole('radio', { name: /^Kịch bản audio/ }));
    expect(screen.getByText(/Viết để đọc thành tiếng bằng TTS/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /Gợi ý bối cảnh/ }));
    await waitFor(() => expect(seen.some((r) => r.url.endsWith('/setup') && r.method === 'POST')).toBe(true));
    const start = seen.find((r) => r.url.endsWith('/setup') && r.method === 'POST');
    expect(start?.body).toMatchObject({ style: 'audio' });
    const out = await (await server.fetch('/api/setup/setup-mock1')).json();
    expect(out.style).toBe('audio');
  });

  it('độ dài theo kiểu truyện: audio chỉ hiện mức audio và gửi mức audio; đổi lại truyện chữ thì hiện và gửi mức truyện chữ', async () => {
    const { seen } = recordingMock();
    renderApp(<Template />);
    const lengths = () =>
      within(screen.getByRole('radiogroup', { name: 'D · Độ dài' }))
        .getAllByRole('radio')
        .map((r) => r.textContent ?? '');
    const checkedLength = () =>
      within(screen.getByRole('radiogroup', { name: 'D · Độ dài' }))
        .getAllByRole('radio')
        .find((r) => r.getAttribute('aria-checked') === 'true');
    const posts = () => seen.filter((r) => r.url.endsWith('/setup') && r.method === 'POST');

    // Truyện chữ (mặc định): chỉ mức truyện chữ.
    expect(lengths()).toEqual([expect.stringMatching(/^Truyện ngắn/), expect.stringMatching(/^Truyện vừa/)]);
    await userEvent.click(screen.getByRole('radio', { name: 'Cổ trang' }));
    await userEvent.click(screen.getByRole('radio', { name: /Truyện vừa/ }));

    // Đổi sang audio: chỉ mức audio, mức đầu được chọn thay mức truyện chữ, có số phút.
    await userEvent.click(screen.getByRole('radio', { name: /^Kịch bản audio/ }));
    expect(lengths()).toEqual([
      expect.stringMatching(/^Audio ~30 phút/),
      expect.stringMatching(/^Audio ~45 phút/),
      expect.stringMatching(/^Audio ~1 tiếng/),
    ]);
    expect(screen.queryByRole('radio', { name: /Truyện ngắn|Truyện vừa/ })).toBeNull();
    expect(checkedLength()).toHaveTextContent('Audio ~30 phút');
    expect(checkedLength()).toHaveTextContent('khoảng 30 phút nghe · 3–4 chương');
    await userEvent.click(screen.getByRole('radio', { name: /Audio ~45 phút/ }));
    await userEvent.click(screen.getByRole('button', { name: /Gợi ý bối cảnh/ }));
    await waitFor(() => expect(posts()).toHaveLength(1));
    expect(posts()[0]?.body).toMatchObject({ style: 'audio', length_level: 'audio_45' });
  });

  it('đổi lại truyện chữ: hiện mức truyện chữ, chọn mức đầu, gửi mức truyện chữ không kèm style', async () => {
    const { seen } = recordingMock();
    renderApp(<Template />);
    await userEvent.click(screen.getByRole('radio', { name: 'Cổ trang' }));
    await userEvent.click(screen.getByRole('radio', { name: /^Kịch bản audio/ }));
    await userEvent.click(screen.getByRole('radio', { name: /Audio ~1 tiếng/ }));
    await userEvent.click(screen.getByRole('radio', { name: /^Truyện chữ/ }));
    const group = within(screen.getByRole('radiogroup', { name: 'D · Độ dài' }));
    expect(group.getAllByRole('radio').map((r) => r.textContent)).toEqual([
      expect.stringMatching(/^Truyện ngắn/),
      expect.stringMatching(/^Truyện vừa/),
    ]);
    expect(screen.queryByText(/Audio ~/)).toBeNull();
    expect(group.getByRole('radio', { name: /Truyện ngắn/ })).toHaveAttribute('aria-checked', 'true');
    await userEvent.click(screen.getByRole('button', { name: /Gợi ý bối cảnh/ }));
    await waitFor(() => expect(seen.some((r) => r.url.endsWith('/setup') && r.method === 'POST')).toBe(true));
    const start = seen.find((r) => r.url.endsWith('/setup') && r.method === 'POST');
    expect(start?.body).toMatchObject({ length_level: 'short' });
    expect(start?.body).not.toHaveProperty('style');
  });

  it('bấm lại kiểu đang chọn: mức độ dài đã đúng kiểu thì giữ nguyên', async () => {
    recordingMock();
    renderApp(<Template />);
    await userEvent.click(screen.getByRole('radio', { name: /^Kịch bản audio/ }));
    await userEvent.click(screen.getByRole('radio', { name: /Audio ~45 phút/ }));
    await userEvent.click(screen.getByRole('radio', { name: /^Kịch bản audio/ }));
    expect(screen.getByRole('radio', { name: /Audio ~45 phút/ })).toHaveAttribute('aria-checked', 'true');
  });

  it('máy chủ giả: mức độ dài khác kiểu truyện bị /setup từ chối bằng REQUEST_INVALID ở length_level', async () => {
    const server = withMock();
    const post = (body: Record<string, unknown>) =>
      server.fetch('/api/setup', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ tags: { genre: 'Cổ trang' }, naming: null, ...body }),
      });
    for (const body of [{ length_level: 'short', style: 'audio' }, { length_level: 'audio_30' }, { length_level: 'audio_30', style: 'prose' }]) {
      const res = await post(body);
      expect(res.status).toBe(422);
      expect(await res.json()).toMatchObject({ code: 'REQUEST_INVALID', fields: ['length_level'] });
    }
    expect((await post({ length_level: 'audio_60', style: 'audio' })).status).toBe(200);
    expect((await post({ length_level: 'medium' })).status).toBe(200);
  });

  it('máy chủ giả: /config/public có style và minutes cho mỗi mức', async () => {
    const server = withMock();
    const config = await (await server.fetch('/api/config/public')).json();
    expect(config.story_lengths).toEqual([
      expect.objectContaining({ key: 'short', style: 'prose', minutes: null }),
      expect.objectContaining({ key: 'medium', style: 'prose', minutes: null }),
      { key: 'audio_30', label: 'Audio ~30 phút', chapters_min: 3, chapters_max: 4, style: 'audio', minutes: 30 },
      { key: 'audio_45', label: 'Audio ~45 phút', chapters_min: 5, chapters_max: 5, style: 'audio', minutes: 45 },
      { key: 'audio_60', label: 'Audio ~1 tiếng', chapters_min: 6, chapters_max: 7, style: 'audio', minutes: 60 },
    ]);
  });

  it('máy chủ giả từ chối style lạ bằng REQUEST_INVALID', async () => {
    const server = withMock();
    const res = await server.fetch('/api/setup', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ tags: { genre: 'Cổ trang' }, length_level: 'short', naming: null, style: 'video' }),
    });
    expect(res.status).toBe(422);
    expect(await res.json()).toMatchObject({ code: 'REQUEST_INVALID', fields: ['style'] });
  });
});

function renderStory(id: string) {
  return renderApp(
    <Routes>
      <Route path="/truyen/:id" element={<StoryScreen />} />
    </Routes>,
    { route: `/truyen/${id}` },
  );
}

describe('màn truyện: tải kịch bản', () => {
  it('truyện audio: có nhãn và nút; bấm thì gọi /stories/{id}/script.txt qua client, lưu thành <id>.txt', async () => {
    const { seen } = recordingMock();
    const blobs: Blob[] = [];
    vi.spyOn(URL, 'createObjectURL').mockImplementation((b) => {
      blobs.push(b as Blob);
      return 'blob:mock';
    });
    const saved: string[] = [];
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
      saved.push(this.download);
    });
    renderStory('s-dai');
    const button = await screen.findByRole('button', { name: 'Tải kịch bản (.txt)' });
    expect(screen.getByText('Kịch bản audio')).toBeInTheDocument();
    expect(button).toBeEnabled();
    await userEvent.click(button);
    await waitFor(() => expect(saved).toEqual(['s-dai.txt']));
    expect(seen.filter((r) => r.url.endsWith('/stories/s-dai/script.txt')).map((r) => r.method)).toEqual(['GET']);
    expect(blobs).toHaveLength(1);
    expect(blobs[0]?.type).toBe('text/plain;charset=utf-8');
    expect(blobs[0]?.size).toBeGreaterThan(0);
  });

  it('truyện chữ: không có nhãn, không có nút', async () => {
    withMock();
    renderStory('s-chuong');
    expect(await screen.findByText('Chuông Đồng Đèo Gió')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Tải kịch bản/ })).toBeNull();
    expect(screen.queryByText('Kịch bản audio')).toBeNull();
  });

  it('chưa có chương nào: nút tắt, kèm lý do', () => {
    render(<ScriptDownload storyId="s-x" chapters={0} />);
    const button = screen.getByRole('button', { name: 'Tải kịch bản (.txt)' });
    expect(button).toBeDisabled();
    expect(button).toHaveAccessibleDescription('Chưa có chương nào để tải.');
  });

  it('máy chủ giả: script.txt là văn các chương đã ghi, rỗng khi chưa có chương, 404 khi không có truyện', async () => {
    const server = withMock();
    const res = await server.fetch('/api/stories/s-chuong/script.txt');
    expect(res.headers.get('content-type')).toBe('text/plain; charset=utf-8');
    expect(res.headers.get('content-disposition')).toBe('attachment; filename="s-chuong.txt"');
    const text = await res.text();
    const chapters = text.split('\n\n');
    expect(chapters).toHaveLength(2);
    expect(chapters[0]).toMatch(/^Gió trên đèo Lạc Nhạn/);
    expect(await (await server.fetch('/api/stories/s-haidang/script.txt')).text()).toBe('');
    const missing = await server.fetch('/api/stories/khong-co/script.txt');
    expect(missing.status).toBe(404);
    expect((await missing.json()).code).toBe('STORY_NOT_FOUND');
  });
});

describe('tủ truyện', () => {
  it('truyện audio có nhãn "Audio", truyện chữ không', async () => {
    withMock();
    renderApp(<Library />);
    expect(await screen.findByText('Đài Phát Thanh Nửa Đêm')).toBeInTheDocument();
    expect(screen.getAllByText('Audio')).toHaveLength(1);
  });
});
