import { useSyncExternalStore } from 'react';

const subscribers = new Map<string, (onChange: () => void) => () => void>();

function subscribe(query: string) {
  const cached = subscribers.get(query);
  if (cached) return cached;
  const fn = (onChange: () => void) => {
    if (typeof window === 'undefined' || !window.matchMedia) return () => {};
    const mql = window.matchMedia(query);
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  };
  subscribers.set(query, fn);
  return fn;
}

function matches(query: string): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return false;
  return window.matchMedia(query).matches;
}

export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(subscribe(query), () => matches(query), () => false);
}

export const REDUCED_MOTION = '(prefers-reduced-motion: reduce)';
/** Con trỏ giọt mực và vầng mực chỉ dùng với chuột/bút chính xác (README bàn giao mục 7). */
export const FINE_POINTER = '(hover: hover) and (pointer: fine)';

export function usePrefersReducedMotion(): boolean {
  return useMediaQuery(REDUCED_MOTION);
}

export function useFinePointer(): boolean {
  return useMediaQuery(FINE_POINTER);
}

export function prefersReducedMotion(): boolean {
  return matches(REDUCED_MOTION);
}
