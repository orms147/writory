import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import './styles/index.css';

async function boot() {
  // Lớp mock chỉ nạp khi bật (`npm run dev:mock` hoặc VITE_MOCK=1); bản build thường không có nó.
  if (import.meta.env.VITE_MOCK === '1' || import.meta.env.MODE === 'mock') {
    const { installMock } = await import('./mock/install');
    installMock();
  }
  const root = document.getElementById('root');
  if (!root) return;
  createRoot(root).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}

void boot();
