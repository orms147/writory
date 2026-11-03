import type { StoryStyle } from '../api/types';

// Nháp màn khuôn truyện (D-160, sau review): ý tưởng gõ tay không mất khi phiên khởi tạo bị chặn (kiểm duyệt) và người
// chơi quay lại sửa. Chỉ là tiện ích theo trình duyệt (sessionStorage): đọc, ghi đều bọc try/catch, không có cũng chạy.

const KEY = 'writory:setup-draft';

export interface SetupDraft {
  genres: string[];
  idea: string;
  style: StoryStyle;
  length: string | null;
  voice: string | null;
}

export function readSetupDraft(): Partial<SetupDraft> {
  try {
    const raw = sessionStorage.getItem(KEY);
    const data: unknown = raw ? JSON.parse(raw) : null;
    if (!data || typeof data !== 'object') return {};
    const d = data as Record<string, unknown>;
    return {
      genres: Array.isArray(d.genres) ? d.genres.filter((g): g is string => typeof g === 'string') : undefined,
      idea: typeof d.idea === 'string' ? d.idea : undefined,
      style: d.style === 'audio' || d.style === 'prose' ? d.style : undefined,
      length: typeof d.length === 'string' ? d.length : undefined,
      voice: typeof d.voice === 'string' ? d.voice : undefined,
    };
  } catch {
    return {};
  }
}

export function saveSetupDraft(draft: SetupDraft): void {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(draft));
  } catch {
    // không lưu được (chế độ riêng tư, chặn lưu trữ): bỏ qua
  }
}

export function clearSetupDraft(): void {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    // như trên
  }
}
