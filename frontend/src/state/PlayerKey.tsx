import { createContext, useContext, type ReactNode } from 'react';
import { api } from '../api/client';
import type { PlayerKeyOut } from '../api/types';
import { useResource, type Resource } from '../lib/useResource';

// Trạng thái key người chơi: chỉ `has_key` và `last4` (G7). Key gốc không bao giờ nằm ở đây.

const KeyContext = createContext<Resource<PlayerKeyOut> | null>(null);

export function PlayerKeyProvider({ children }: { children: ReactNode }) {
  const res = useResource(() => api.playerKey(), 'player-key');
  return <KeyContext.Provider value={res}>{children}</KeyContext.Provider>;
}

export function usePlayerKey(): Resource<PlayerKeyOut> {
  const value = useContext(KeyContext);
  if (!value) throw new Error('usePlayerKey ngoài PlayerKeyProvider');
  return value;
}

/** "•••• 7f3a": chỉ 4 ký tự cuối máy chủ trả. */
export function maskedKey(last4: string | null, dots = '••••'): string {
  return last4 ? `${dots} ${last4}` : dots;
}
