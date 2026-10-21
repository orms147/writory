import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, asApiError } from '../api/errors';

export interface Resource<T> {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
  reload: () => void;
  set: (value: T) => void;
}

/** Tải một tài nguyên khi mount và khi `key` đổi. Lỗi giữ nguyên ApiError để hiện theo `code`. */
export function useResource<T>(load: () => Promise<T>, key: string): Resource<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const loadRef = useRef(load);
  loadRef.current = load;

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    loadRef.current().then(
      (value) => {
        if (!alive) return;
        setData(value);
        setLoading(false);
      },
      (err: unknown) => {
        if (!alive) return;
        setError(asApiError(err));
        setLoading(false);
      },
    );
    return () => {
      alive = false;
    };
  }, [key, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, reload, set: setData };
}
