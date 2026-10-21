// Bộ đọc SSE cho `POST /stories/{id}/chapters/next` (D-46, D-69).
//
// EventSource chỉ gửi GET, nên đọc bằng fetch + ReadableStream. Tách sự kiện theo chuẩn
// text/event-stream (WHATWG HTML, mục "Server-sent events"):
// - dòng kết thúc bằng LF, CRLF hoặc CR; chunk có thể cắt ngang dòng, ngang CRLF, ngang ký tự UTF-8;
// - dòng bắt đầu bằng ":" là chú thích (máy chủ gửi `: ping` để giữ kết nối): bỏ qua;
// - `data:` nhiều dòng nối bằng LF; dòng trống phát sự kiện; sự kiện không có `data` thì bỏ.

import { ApiError, CLIENT_CODES, CLIENT_MESSAGES } from './errors';
import type { ChapterEvent } from './types';

export interface SseMessage {
  event: string;
  data: string;
  id: string | null;
}

export class SseParser {
  private buffer = '';
  private dataLines: string[] = [];
  private eventName = '';
  private lastId: string | null = null;
  private pendingCR = false;

  /** Nạp một đoạn chữ (đã giải mã UTF-8); trả các sự kiện đã trọn. */
  push(chunk: string): SseMessage[] {
    let text = chunk;
    if (this.pendingCR) {
      // CR ở cuối đoạn trước đã kết thúc dòng; LF đầu đoạn này là nửa sau của CRLF.
      if (text.startsWith('\n')) text = text.slice(1);
      this.pendingCR = false;
    }
    this.buffer += text;
    const out: SseMessage[] = [];
    let start = 0;
    for (let i = 0; i < this.buffer.length; i++) {
      const ch = this.buffer[i];
      if (ch !== '\n' && ch !== '\r') continue;
      const line = this.buffer.slice(start, i);
      if (ch === '\r') {
        if (i + 1 < this.buffer.length) {
          if (this.buffer[i + 1] === '\n') i++;
        } else {
          this.pendingCR = true;
        }
      }
      start = i + 1;
      const msg = this.line(line);
      if (msg) out.push(msg);
    }
    this.buffer = this.buffer.slice(start);
    return out;
  }

  /** Hết luồng: dòng dở cuối cùng được xử lý; sự kiện chưa có dòng trống kết thúc thì bỏ (chuẩn). */
  end(): SseMessage[] {
    if (this.buffer) {
      this.line(this.buffer);
      this.buffer = '';
    }
    this.dataLines = [];
    this.eventName = '';
    return [];
  }

  private line(line: string): SseMessage | null {
    if (line === '') return this.dispatch();
    if (line.startsWith(':')) return null; // chú thích, ví dụ ": ping"
    const colon = line.indexOf(':');
    const field = colon === -1 ? line : line.slice(0, colon);
    let value = colon === -1 ? '' : line.slice(colon + 1);
    if (value.startsWith(' ')) value = value.slice(1);
    switch (field) {
      case 'data':
        this.dataLines.push(value);
        break;
      case 'event':
        this.eventName = value;
        break;
      case 'id':
        if (!value.includes('\0')) this.lastId = value;
        break;
      default:
        break; // `retry` và trường lạ: không dùng
    }
    return null;
  }

  private dispatch(): SseMessage | null {
    if (this.dataLines.length === 0) {
      this.eventName = '';
      return null;
    }
    const msg: SseMessage = {
      event: this.eventName || 'message',
      data: this.dataLines.join('\n'),
      id: this.lastId,
    };
    this.dataLines = [];
    this.eventName = '';
    return msg;
  }
}

const EVENT_TYPES = new Set<ChapterEvent['type']>([
  'stage',
  'scene_ready',
  'scene_blocked',
  'chapter_committed',
  'choices_ready',
  'story_finished',
  'error',
]);

/** Một sự kiện SSE → sự kiện chương. `data` là JSON của schema người chơi (`pipeline/events.py`);
 *  `type` trong JSON phải khớp tên `event:`. Sai dạng thì là lỗi phía giao diện. */
export function toChapterEvent(msg: SseMessage): ChapterEvent {
  let parsed: unknown;
  try {
    parsed = JSON.parse(msg.data);
  } catch {
    throw badStream();
  }
  if (typeof parsed !== 'object' || parsed === null) throw badStream();
  const type = (parsed as { type?: unknown }).type;
  if (typeof type !== 'string' || !EVENT_TYPES.has(type as ChapterEvent['type'])) throw badStream();
  if (msg.event !== 'message' && msg.event !== type) throw badStream();
  return parsed as ChapterEvent;
}

function badStream(): ApiError {
  return new ApiError({ code: CLIENT_CODES.badResponse, message: CLIENT_MESSAGES.CLIENT_BAD_RESPONSE });
}

/** Đọc thân phản hồi SSE, trả từng sự kiện chương theo thứ tự. */
export async function* readChapterEvents(body: ReadableStream<Uint8Array>): AsyncGenerator<ChapterEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder('utf-8');
  const parser = new SseParser();
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      for (const msg of parser.push(decoder.decode(value, { stream: true }))) {
        yield toChapterEvent(msg);
      }
    }
    for (const msg of parser.push(decoder.decode())) yield toChapterEvent(msg);
    parser.end();
  } finally {
    reader.releaseLock();
  }
}

/** Sự kiện kết thúc một lần viết chương: sau nó máy chủ đóng luồng. */
export function isTerminal(event: ChapterEvent): boolean {
  return (
    event.type === 'choices_ready' ||
    event.type === 'story_finished' ||
    event.type === 'scene_blocked' ||
    event.type === 'error'
  );
}
