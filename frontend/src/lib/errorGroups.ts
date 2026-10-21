// Bố cục và nút của lỗi, chọn theo `code` (README bàn giao mục 6). Chữ luôn là `message` của
// máy chủ (`backend/src/writory/errors.py` MESSAGES); ở đây chỉ có nhãn nhóm và nhãn nút.

export type ErrorGroup =
  | 'key'
  | 'credits'
  | 'cost'
  | 'leak'
  | 'retry_limit'
  | 'rate'
  | 'action_input'
  | 'narrator_input'
  | 'narrator_limit'
  | 'busy'
  | 'not_found'
  | 'pending'
  | 'network'
  | 'generic';

const GROUP_OF: Record<string, ErrorGroup> = {
  PLAYER_KEY_MISSING: 'key',
  PLAYER_KEY_UNREADABLE: 'key',
  PLAYER_KEY_INVALID: 'key',
  LLM_AUTH_FAILED: 'key',
  LLM_INSUFFICIENT_CREDITS: 'credits',
  COST_LIMIT_SCENE: 'cost',
  COST_LIMIT_CHAPTER: 'cost',
  COST_LIMIT_STORY: 'cost',
  SCENE_LEAK_BLOCKED: 'leak',
  CHOICES_LEAK_BLOCKED: 'leak',
  RETRY_LIMIT_REACHED: 'retry_limit',
  LLM_RATE_LIMITED: 'rate',
  WRITORY_RATE_LIMITED: 'rate',
  ACTION_EMPTY: 'action_input',
  ACTION_TOO_LONG: 'action_input',
  ACTION_OUT_OF_STORY: 'action_input',
  ACTION_UNCLEAR: 'action_input',
  ACTION_FORBIDDEN: 'action_input',
  LLM_CONTENT_BLOCKED: 'action_input',
  INPUT_BLOCKED: 'action_input',
  NARRATOR_QUESTION_EMPTY: 'narrator_input',
  NARRATOR_QUESTION_TOO_LONG: 'narrator_input',
  NARRATOR_LIMIT_REACHED: 'narrator_limit',
  STORY_BUSY: 'busy',
  CHAPTER_OUT_OF_ORDER: 'busy',
  CHOICE_NOT_FOUND: 'busy',
  CHOICE_REQUIRED: 'busy',
  SETUP_STEP_NOT_READY: 'busy',
  STORY_COMPLETE: 'busy',
  STORY_NOT_FOUND: 'not_found',
  CHAPTER_NOT_FOUND: 'not_found',
  SETUP_NOT_FOUND: 'not_found',
  CHAPTER_PENDING: 'pending',
  CHAPTER_SAVE_FAILED: 'pending',
  CHAPTER_PACKAGE_INVALID: 'pending',
  CLIENT_NETWORK: 'network',
  CLIENT_STREAM_CUT: 'network',
};

/** Mã chưa có trong bảng (`INTERNAL_ERROR`, `LLM_*` còn lại, `CONFIG_*`, `REQUEST_INVALID`, mã mới)
 *  rơi về nhóm chung: Thử lại · Về tủ truyện. */
export function errorGroup(code: string): ErrorGroup {
  return GROUP_OF[code] ?? 'generic';
}

/** Nhãn nhỏ phía trên câu lỗi: nói lỗi thuộc phần nào, không nói thêm điều máy chủ không nói. */
export const GROUP_KICKER: Record<ErrorGroup, string> = {
  key: 'Khoá OpenRouter',
  credits: 'Credit OpenRouter',
  cost: 'Trần chi phí',
  leak: 'Viết cảnh',
  retry_limit: 'Viết cảnh',
  rate: 'Giới hạn tần suất',
  action_input: 'Ô tự viết',
  narrator_input: 'Hỏi người kể',
  narrator_limit: 'Hỏi người kể',
  busy: 'Phiên đọc',
  not_found: 'Không tìm thấy',
  pending: 'Lưu chương',
  network: 'Kết nối',
  generic: 'Sự cố',
};

export type ErrorAction =
  | 'paste_key'
  | 'home'
  | 'retry'
  | 'open_openrouter'
  | 'new_story'
  | 'back_to_choices'
  | 'reload'
  | 'back_to_reading';

export const ACTION_LABEL: Record<ErrorAction, string> = {
  paste_key: 'Dán khoá',
  home: 'Về tủ truyện',
  retry: 'Thử lại',
  open_openrouter: 'Mở OpenRouter',
  new_story: 'Bắt đầu truyện mới',
  back_to_choices: 'Quay về lựa chọn',
  reload: 'Tải lại',
  back_to_reading: 'Quay lại trang đọc',
};

/** Nút theo nhóm, nút đầu là nút chính. Không có "Nâng trần", không đếm ngược (mục 6). */
export const GROUP_ACTIONS: Record<ErrorGroup, ErrorAction[]> = {
  key: ['paste_key', 'home'],
  credits: ['retry', 'open_openrouter'],
  cost: ['retry', 'new_story'],
  leak: ['retry'],
  retry_limit: ['back_to_choices', 'home'],
  rate: ['retry'],
  action_input: [],
  narrator_input: [],
  narrator_limit: ['back_to_reading'],
  busy: ['reload'],
  not_found: ['home'],
  pending: ['retry'],
  network: ['retry'],
  generic: ['retry', 'home'],
};

/** Trang credit của OpenRouter (nút "Mở OpenRouter" của LLM_INSUFFICIENT_CREDITS). */
export const OPENROUTER_CREDITS_URL = 'https://openrouter.ai/settings/credits';
export const OPENROUTER_KEYS_URL = 'https://openrouter.ai/keys';
