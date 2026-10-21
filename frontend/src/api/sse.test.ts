import { describe, expect, it } from 'vitest';
import { SseParser, readChapterEvents, toChapterEvent } from './sse';

function streamOf(chunks: (string | Uint8Array)[]): ReadableStream<Uint8Array> {
  const enc = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const c of chunks) controller.enqueue(typeof c === 'string' ? enc.encode(c) : c);
      controller.close();
    },
  });
}

async function collect(body: ReadableStream<Uint8Array>) {
  const out = [];
  for await (const e of readChapterEvents(body)) out.push(e);
  return out;
}

describe('SseParser', () => {
  it('tách sự kiện theo dòng trống, đọc event và data', () => {
    const p = new SseParser();
    const msgs = p.push('event: stage\ndata: {"a":1}\n\nevent: scene_ready\ndata: {"b":2}\n\n');
    expect(msgs).toEqual([
      { event: 'stage', data: '{"a":1}', id: null },
      { event: 'scene_ready', data: '{"b":2}', id: null },
    ]);
  });

  it('bỏ qua dòng chú thích ": ping" và sự kiện không có data', () => {
    const p = new SseParser();
    const msgs = p.push(': ping\n\n: ping - 2026-10-21\n\nevent: stage\n\ndata: x\n\n');
    expect(msgs).toEqual([{ event: 'message', data: 'x', id: null }]);
  });

  it('ghép chuỗi bị cắt giữa dòng, giữa tên trường và giữa CRLF', () => {
    const p = new SseParser();
    const all = [
      ...p.push('ev'),
      ...p.push('ent: sta'),
      ...p.push('ge\r'),
      ...p.push('\ndata: {"x":'),
      ...p.push('1}\r\n'),
      ...p.push('\r\n'),
    ];
    expect(all).toEqual([{ event: 'stage', data: '{"x":1}', id: null }]);
  });

  it('nối data nhiều dòng bằng LF, chấp nhận CR đơn làm hết dòng', () => {
    const p = new SseParser();
    expect(p.push('data: a\rdata: b\r\r')).toEqual([{ event: 'message', data: 'a\nb', id: null }]);
  });

  it('sự kiện chưa có dòng trống kết thúc thì không phát', () => {
    const p = new SseParser();
    expect(p.push('event: stage\ndata: {}')).toEqual([]);
    expect(p.end()).toEqual([]);
  });
});

describe('readChapterEvents', () => {
  it('đọc luồng có ping, ký tự tiếng Việt bị cắt giữa byte UTF-8', async () => {
    const enc = new TextEncoder();
    const scene = JSON.stringify({ type: 'scene_ready', scene: 1, text: '- Mưa rơi trên đèo.' });
    const bytes = enc.encode(`: ping\n\nevent: scene_ready\ndata: ${scene}\n\n`);
    // Cắt ngang chữ "ư" (2 byte) để kiểm TextDecoder dạng luồng.
    const cut = bytes.indexOf(0xc6) + 1;
    const events = await collect(streamOf([bytes.slice(0, cut), bytes.slice(cut)]));
    expect(events).toEqual([{ type: 'scene_ready', scene: 1, text: '- Mưa rơi trên đèo.' }]);
  });

  it('giữ nguyên dấu thoại và xuống dòng trong chữ cảnh', async () => {
    const text = '- Ai đó?\n- Tôi.';
    const events = await collect(
      streamOf([`event: scene_ready\ndata: ${JSON.stringify({ type: 'scene_ready', scene: 2, text })}\n\n`]),
    );
    expect(events[0]).toMatchObject({ text });
  });

  it('báo lỗi giao diện khi data không phải JSON hoặc type không khớp event', () => {
    expect(() => toChapterEvent({ event: 'stage', data: 'not json', id: null })).toThrow();
    expect(() =>
      toChapterEvent({ event: 'stage', data: JSON.stringify({ type: 'scene_ready', scene: 1, text: '' }), id: null }),
    ).toThrow();
    expect(() => toChapterEvent({ event: 'other', data: JSON.stringify({ type: 'other' }), id: null })).toThrow();
  });
});
