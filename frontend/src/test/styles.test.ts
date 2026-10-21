// CSS toàn cục không được đè màu chữ, cỡ chữ, độ đậm mà class Tailwind đặt trên phần tử.
// Hồi quy 21/10/2026: `.wt button { font: inherit; color: inherit; }` (độ ưu tiên 0,1,1) thắng
// `.text-ink-950` (0,1,0), nên chữ trên nút nền sáng (ô đang chọn, nút trên trang giấy) mất màu.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const STYLES = join(__dirname, '..', 'styles');
const FILES = ['effects.css', 'index.css'];

// Luật có bộ chọn `.wt <thẻ>` (không bọc :where) mà đặt color hay font: đè class Tailwind.
const OVERRIDING = /(^|[},]\s*)\.wt\s+(?:button|a|input|textarea|select|label|span|p|div)\b[^{]*\{[^}]*\b(color|font|font-size|font-weight)\s*:/m;

describe('CSS toàn cục không đè class Tailwind', () => {
  for (const file of FILES) {
    it(`${file}: không có luật .wt <thẻ> đặt color/font mà không bọc :where`, () => {
      const css = readFileSync(join(STYLES, file), 'utf-8').replace(/\/\*[\s\S]*?\*\//g, '');
      expect(css).not.toMatch(OVERRIDING);
    });
  }

  it('luật kế thừa font và màu cho nút dùng :where(.wt)', () => {
    const css = readFileSync(join(STYLES, 'effects.css'), 'utf-8');
    expect(css).toContain(':where(.wt) button { font: inherit; color: inherit; }');
  });
});
