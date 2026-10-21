// Gộp các lời gọi trùng đang chạy (StrictMode chạy effect hai lần; bấm đúp). Lời gọi có thể gọi
// model nên không được gửi hai lần: máy chủ sẽ trả STORY_BUSY cho lần thứ hai (G8, D-56).
const running = new Map<string, Promise<unknown>>();

export function once<T>(key: string, fn: () => Promise<T>): Promise<T> {
  const existing = running.get(key);
  if (existing) return existing as Promise<T>;
  const p = fn().finally(() => running.delete(key));
  running.set(key, p);
  return p;
}
