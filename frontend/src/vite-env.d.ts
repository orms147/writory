/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Tiền tố đường dẫn API ở trình duyệt; mặc định `/api` (proxy Vite, docs/runbook.md). */
  readonly VITE_API_BASE?: string;
  /** `1`: chạy với lớp mock trong trình duyệt, không cần máy chủ (`src/mock/`). */
  readonly VITE_MOCK?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
