import { describe, expect, it } from 'vitest';
import { api, setFetch } from './client';
import { ApiError } from './errors';

function json(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });
}

describe('client lỗi', () => {
  it('đọc code, message và fields của phản hồi lỗi', async () => {
    setFetch(async () =>
      json({ code: 'CHARACTER_EDIT_INVALID', message: 'Câu của máy chủ.', fields: ['name', 'backstory'] }, 422),
    );
    const err = await api.setup('s1').catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    const e = err as ApiError;
    expect(e.code).toBe('CHARACTER_EDIT_INVALID');
    expect(e.message).toBe('Câu của máy chủ.');
    expect(e.fields).toEqual(['name', 'backstory']);
    expect(e.status).toBe(422);
    expect(e.hasField('backstory')).toBe(true);
  });

  it('không có fields thì danh sách rỗng', async () => {
    setFetch(async () => json({ code: 'STORY_NOT_FOUND', message: 'Không tìm thấy truyện này.' }, 404));
    const e = (await api.story('x').catch((x: unknown) => x)) as ApiError;
    expect(e.code).toBe('STORY_NOT_FOUND');
    expect(e.fields).toEqual([]);
  });

  it('thân lỗi sai dạng thì là lỗi phía giao diện, không bịa mã máy chủ', async () => {
    setFetch(async () => new Response('<html>502</html>', { status: 502 }));
    const e = (await api.story('x').catch((x: unknown) => x)) as ApiError;
    expect(e.code).toBe('CLIENT_BAD_RESPONSE');
  });

  it('fetch ném lỗi (mất mạng) thì là CLIENT_NETWORK', async () => {
    setFetch(async () => {
      throw new TypeError('Failed to fetch');
    });
    const e = (await api.stories().catch((x: unknown) => x)) as ApiError;
    expect(e.code).toBe('CLIENT_NETWORK');
  });

  it('gửi đúng đường dẫn có tiền tố /api và thân JSON', async () => {
    const calls: { url: string; init?: RequestInit }[] = [];
    setFetch(async (url, init) => {
      calls.push({ url, init });
      return json({ for_chapter: 3, source: 'custom', text: 'x' }, 200);
    });
    await api.customAction('story-1', 'Tôi mở cửa.');
    expect(calls[0]?.url).toBe('/api/stories/story-1/action');
    expect(calls[0]?.init?.method).toBe('POST');
    expect(calls[0]?.init?.body).toBe(JSON.stringify({ text: 'Tôi mở cửa.' }));
  });
});
