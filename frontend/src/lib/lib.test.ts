import { describe, expect, it } from 'vitest';
import { GROUP_ACTIONS, errorGroup } from './errorGroups';
import { formatUsd, numberWords, paragraphs, relativeTime, roman } from './format';

describe('định dạng', () => {
  it('số bằng chữ cho "Chương hai"', () => {
    expect([1, 2, 10, 11, 15, 21, 25, 34, 100, 105, 120].map(numberWords)).toEqual([
      'một', 'hai', 'mười', 'mười một', 'mười lăm', 'hai mươi mốt', 'hai mươi lăm', 'ba mươi bốn',
      'một trăm', 'một trăm linh năm', 'một trăm hai mươi',
    ]);
  });
  it('tiền và số La Mã', () => {
    expect(formatUsd(0.09)).toBe('$0,09');
    expect(formatUsd(1)).toBe('$1,00');
    expect(formatUsd(0.001)).toBe('< $0,01');
    expect(roman(4)).toBe('IV');
    expect(roman(14)).toBe('XIV');
  });
  it('tách đoạn theo xuống dòng, giữ nguyên chữ trong đoạn', () => {
    expect(paragraphs('- Ai?\n\n- Tôi.\r\nHết.')).toEqual(['- Ai?', '- Tôi.', 'Hết.']);
  });
  it('thời gian tương đối dùng đồng hồ truyền vào', () => {
    const now = new Date('2026-10-21T12:00:00Z');
    expect(relativeTime('2026-10-18T12:00:00Z', now)).toBe('3 ngày trước');
  });
});

describe('nhóm lỗi theo code', () => {
  it('bố cục và nút theo bảng mục 6', () => {
    expect(GROUP_ACTIONS[errorGroup('PLAYER_KEY_MISSING')]).toEqual(['paste_key', 'home']);
    expect(GROUP_ACTIONS[errorGroup('LLM_INSUFFICIENT_CREDITS')]).toEqual(['retry', 'open_openrouter']);
    expect(GROUP_ACTIONS[errorGroup('COST_LIMIT_CHAPTER')]).toEqual(['retry', 'new_story']);
    expect(GROUP_ACTIONS[errorGroup('RETRY_LIMIT_REACHED')]).toEqual(['back_to_choices', 'home']);
    // Cảnh chiều theo hành động vượt luật (G6, D-137): thử lại hoặc quay về đổi hành động.
    expect(GROUP_ACTIONS[errorGroup('SCENE_OVERREACH_BLOCKED')]).toEqual(['retry', 'back_to_choices']);
    expect(GROUP_ACTIONS[errorGroup('SCENE_LEAK_BLOCKED')]).toEqual(['retry']);
    // Quá hạn tổng một lời gọi (D-113): chữ là message của máy chủ, bố cục chung "Thử lại · Về tủ truyện".
    expect(errorGroup('LLM_TIMEOUT')).toBe('generic');
    expect(GROUP_ACTIONS[errorGroup('STORY_BUSY')]).toEqual(['reload']);
    expect(errorGroup('ACTION_FORBIDDEN')).toBe('action_input');
    expect(errorGroup('NARRATOR_LIMIT_REACHED')).toBe('narrator_limit');
    // Mã lạ (mã mới của máy chủ) rơi về nhóm chung.
    expect(GROUP_ACTIONS[errorGroup('SOMETHING_NEW')]).toEqual(['retry', 'home']);
  });
});
