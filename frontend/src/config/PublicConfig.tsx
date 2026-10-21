import { createContext, useContext, type ReactNode } from 'react';
import { api } from '../api/client';
import type { PublicConfig, StoryLengthOption } from '../api/types';
import { ErrorBlock } from '../components/ErrorBlock';
import { useResource } from '../lib/useResource';

// Mọi giới hạn, trần và nhãn độ dài đến từ `GET /config/public` (máy chủ đọc `config/*.yaml`).
// Giao diện không tự đặt số (README bàn giao mục 4).

const ConfigContext = createContext<PublicConfig | null>(null);

export function PublicConfigProvider({ children }: { children: ReactNode }) {
  const res = useResource(() => api.publicConfig(), 'config');
  if (res.error) {
    return (
      <main className="wt relative grid min-h-screen place-items-center px-4">
        <ErrorBlock error={res.error} onRetry={res.reload} />
      </main>
    );
  }
  if (!res.data) {
    return (
      <main className="wt relative min-h-screen" aria-busy="true">
        <span className="sr-only" role="status">
          Đang tải
        </span>
      </main>
    );
  }
  return <ConfigContext.Provider value={res.data}>{children}</ConfigContext.Provider>;
}

/** Cho test và lớp bọc: cấp config có sẵn. */
export function ConfigValue({ value, children }: { value: PublicConfig; children: ReactNode }) {
  return <ConfigContext.Provider value={value}>{children}</ConfigContext.Provider>;
}

export function usePublicConfig(): PublicConfig {
  const value = useContext(ConfigContext);
  if (!value) throw new Error('usePublicConfig ngoài PublicConfigProvider');
  return value;
}

export function useStoryLength(key: string): StoryLengthOption | null {
  return usePublicConfig().story_lengths.find((l) => l.key === key) ?? null;
}

/** "Truyện dài · 20–35 chương": khoảng chương cố định của mức độ dài, không phải tổng số chương
 *  của truyện (README bàn giao mục 4). */
export function lengthText(level: StoryLengthOption | null, fallbackLabel?: string): string {
  if (!level) return fallbackLabel ?? '';
  return `${level.label} · ${level.chapters_min}–${level.chapters_max} chương`;
}
