// Định dạng số và chữ cho giao diện. Không có số liệu nghiệp vụ ở đây: mọi giới hạn, trần, chi
// phí đến từ máy chủ (README bàn giao mục 4, "Số liệu").

const usd = new Intl.NumberFormat('vi-VN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** 0.09 → "$0,09". Số dương nhỏ hơn một cent hiện "< $0,01" để không ghi nhầm là 0. */
export function formatUsd(value: number): string {
  if (value > 0 && value < 0.005) return `< $${usd.format(0.01)}`;
  return `$${usd.format(value)}`;
}

/** Trần có thể chưa đặt (null trong config). */
export function formatCap(value: number | null): string {
  return value === null ? 'chưa đặt' : formatUsd(value);
}

const DIGITS = ['không', 'một', 'hai', 'ba', 'bốn', 'năm', 'sáu', 'bảy', 'tám', 'chín'];

function belowHundred(n: number): string {
  if (n < 10) return DIGITS[n] ?? String(n);
  const tens = Math.floor(n / 10);
  const ones = n % 10;
  const head = tens === 1 ? 'mười' : `${DIGITS[tens]} mươi`;
  if (ones === 0) return head;
  if (ones === 5) return `${head} lăm`;
  if (ones === 1 && tens > 1) return `${head} mốt`;
  return `${head} ${DIGITS[ones]}`;
}

/** Số đếm bằng chữ: 2 → "hai", 21 → "hai mươi mốt", 105 → "một trăm linh năm". Từ 1000 trở lên
 *  trả chữ số. */
export function numberWords(n: number): string {
  if (!Number.isInteger(n) || n < 0 || n >= 1000) return String(n);
  if (n < 100) return belowHundred(n);
  const hundreds = Math.floor(n / 100);
  const rest = n % 100;
  const head = `${DIGITS[hundreds]} trăm`;
  if (rest === 0) return head;
  if (rest < 10) return `${head} linh ${DIGITS[rest]}`;
  return `${head} ${belowHundred(rest)}`;
}

export function capitalize(s: string): string {
  return s.charAt(0).toLocaleUpperCase('vi') + s.slice(1);
}

const ROMAN: [number, string][] = [
  [1000, 'M'], [900, 'CM'], [500, 'D'], [400, 'CD'], [100, 'C'], [90, 'XC'],
  [50, 'L'], [40, 'XL'], [10, 'X'], [9, 'IX'], [5, 'V'], [4, 'IV'], [1, 'I'],
];

export function roman(n: number): string {
  let rest = n;
  let out = '';
  for (const [value, sym] of ROMAN) {
    while (rest >= value) {
      out += sym;
      rest -= value;
    }
  }
  return out;
}

const relative = new Intl.RelativeTimeFormat('vi', { numeric: 'auto' });

/** "3 ngày trước", "hôm qua"… `now` truyền vào để test không phụ thuộc đồng hồ. */
export function relativeTime(iso: string, now: Date = new Date()): string {
  const then = new Date(iso);
  if (Number.isNaN(then.getTime())) return '';
  const seconds = Math.round((then.getTime() - now.getTime()) / 1000);
  const abs = Math.abs(seconds);
  if (abs < 60) return 'vừa xong';
  if (abs < 3600) return relative.format(Math.round(seconds / 60), 'minute');
  if (abs < 86400) return relative.format(Math.round(seconds / 3600), 'hour');
  if (abs < 86400 * 30) return relative.format(Math.round(seconds / 86400), 'day');
  return then.toLocaleDateString('vi-VN');
}

/** Chữ một cảnh → các đoạn. Máy chủ ngăn đoạn bằng xuống dòng; chữ trong đoạn giữ nguyên văn. */
export function paragraphs(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((p) => p.trim())
    .filter((p) => p.length > 0);
}
