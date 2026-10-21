/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// Máy chủ FastAPI không có tiền tố đường dẫn (`backend/src/writory/api/app.py`): `/api/stories`
// ở trình duyệt thành `/stories` ở máy chủ. Đổi đích bằng biến WRITORY_API_URL khi cần.
const apiTarget = process.env.WRITORY_API_URL ?? 'http://localhost:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    restoreMocks: true,
  },
});
