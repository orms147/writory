import type { ApiErrorBody } from './types';

/** Lỗi máy chủ trả theo G12: `{code, message, fields?}`. Giao diện hiện nguyên văn `message`
 *  và chọn bố cục theo `code` (README bàn giao mục 6); không bao giờ hiện `code`. */
export class ApiError extends Error {
  readonly code: string;
  readonly fields: readonly string[];
  readonly status: number | null;

  constructor(body: ApiErrorBody, status: number | null = null) {
    super(body.message);
    this.name = 'ApiError';
    this.code = body.code;
    this.fields = body.fields ?? [];
    this.status = status;
  }

  hasField(name: string): boolean {
    return this.fields.includes(name);
  }
}

/** Mã của các lỗi phía trình duyệt (không do máy chủ trả). Câu của chúng là chữ giao diện. */
export const CLIENT_CODES = {
  network: 'CLIENT_NETWORK',
  badResponse: 'CLIENT_BAD_RESPONSE',
  streamCut: 'CLIENT_STREAM_CUT',
} as const;

export const CLIENT_MESSAGES: Record<(typeof CLIENT_CODES)[keyof typeof CLIENT_CODES], string> = {
  CLIENT_NETWORK:
    'Mất kết nối tới máy chủ. Phần chữ đã hiện vẫn được giữ; kiểm tra mạng rồi bấm thử lại.',
  CLIENT_BAD_RESPONSE:
    'Máy chủ trả về dữ liệu giao diện không đọc được. Tải lại trang rồi thử lại.',
  CLIENT_STREAM_CUT:
    'Kết nối bị ngắt giữa chừng. Phần chữ đã hiện vẫn được giữ; bấm thử lại để nối tiếp.',
};

export function clientError(code: keyof typeof CLIENT_MESSAGES): ApiError {
  return new ApiError({ code, message: CLIENT_MESSAGES[code] });
}

function isErrorBody(value: unknown): value is ApiErrorBody {
  if (typeof value !== 'object' || value === null) return false;
  const v = value as Record<string, unknown>;
  if (typeof v.code !== 'string' || typeof v.message !== 'string') return false;
  if (v.fields !== undefined && !(Array.isArray(v.fields) && v.fields.every((f) => typeof f === 'string'))) {
    return false;
  }
  return true;
}

/** Đọc thân lỗi của một phản hồi không `ok`. Thân không đúng dạng G12 thì là lỗi phía giao diện,
 *  không tự bịa câu cho máy chủ. */
export async function errorFromResponse(response: Response): Promise<ApiError> {
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return new ApiError({ code: CLIENT_CODES.badResponse, message: CLIENT_MESSAGES.CLIENT_BAD_RESPONSE }, response.status);
  }
  if (!isErrorBody(body)) {
    return new ApiError({ code: CLIENT_CODES.badResponse, message: CLIENT_MESSAGES.CLIENT_BAD_RESPONSE }, response.status);
  }
  return new ApiError(
    { code: body.code, message: body.message, ...(body.fields ? { fields: body.fields } : {}) },
    response.status,
  );
}

export function isAbortError(err: unknown): boolean {
  return typeof err === 'object' && err !== null && (err as { name?: unknown }).name === 'AbortError';
}

/** Mọi lỗi không phải ApiError (fetch ném TypeError khi mất mạng) là lỗi mạng phía trình duyệt. */
export function asApiError(err: unknown): ApiError {
  if (err instanceof ApiError) return err;
  return clientError('CLIENT_NETWORK');
}
