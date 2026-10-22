// Đăng nhập bằng mã mời (D-89): luật hiển thị và cách gọi API, trên máy chủ giả.
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import { AppRoutes } from '../App';
import { api, setFetch } from '../api/client';
import { ApiError } from '../api/errors';
import { ErrorBlock } from '../components/ErrorBlock';
import { ConfigValue } from '../config/PublicConfig';
import { MOCK_ERRORS } from '../mock/messages';
import { MOCK_INVITE_CODE } from '../mock/server';
import { AuthProvider, RequireLogin } from '../state/Auth';
import { PlayerKeyProvider } from '../state/PlayerKey';
import { oddConfig, withMock } from './render';

function renderRoutes(route: string) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <ConfigValue value={oddConfig()}>
        <AuthProvider>
          <RequireLogin>
            <PlayerKeyProvider>
              <AppRoutes />
            </PlayerKeyProvider>
          </RequireLogin>
        </AuthProvider>
      </ConfigValue>
    </MemoryRouter>,
  );
}

describe('đăng nhập bằng mã mời', () => {
  it('chế độ invite, chưa đăng nhập: mọi màn chuyển về /dang-nhap', async () => {
    withMock({ auth: 'invite' });
    renderRoutes('/truyen/s-chuong');
    expect(await screen.findByLabelText('Mã mời')).toBeInTheDocument();
    expect(screen.queryByText('Chuông Đồng Đèo Gió')).toBeNull();
  });

  it('mã sai: hiện nguyên văn câu máy chủ; mã đúng: vào tủ truyện, không lưu gì ở trình duyệt', async () => {
    withMock({ auth: 'invite' });
    const log = vi.spyOn(console, 'log');
    renderRoutes('/dang-nhap');
    const box = await screen.findByLabelText('Mã mời');
    await userEvent.type(box, 'wt-sai');
    await userEvent.click(screen.getByRole('button', { name: /Vào thư viện/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent(MOCK_ERRORS.INVITE_CODE_INVALID?.message ?? '?');
    await userEvent.clear(box);
    await userEvent.type(box, MOCK_INVITE_CODE);
    await userEvent.click(screen.getByRole('button', { name: /Vào thư viện/ }));
    expect(await screen.findByText('Chuông Đồng Đèo Gió')).toBeInTheDocument();
    expect(screen.getByText('Bạn thử')).toBeInTheDocument();
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
    expect(document.cookie).not.toContain(MOCK_INVITE_CODE);
    expect(log.mock.calls.flat().join(' ')).not.toContain(MOCK_INVITE_CODE);
  });

  it('nút Đăng xuất ở thanh trên: đăng xuất rồi về màn đăng nhập', async () => {
    withMock({ auth: 'invite' });
    await api.login(MOCK_INVITE_CODE);
    renderRoutes('/');
    await userEvent.click(await screen.findByRole('button', { name: 'Đăng xuất' }));
    expect(await screen.findByLabelText('Mã mời')).toBeInTheDocument();
    await expect(api.stories()).rejects.toMatchObject({ code: 'AUTH_REQUIRED' });
  });

  it('chế độ dev: thanh trên ghi "dev", màn đăng nhập không có ô mã', async () => {
    withMock();
    renderRoutes('/');
    expect(await screen.findByRole('link', { name: 'dev' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Đăng xuất' })).toBeNull();
    renderRoutes('/dang-nhap');
    expect(await screen.findByText(/chế độ dev/)).toBeInTheDocument();
    expect(screen.queryByLabelText('Mã mời')).toBeNull();
  });

  it('phiên hết hạn giữa chừng: lỗi AUTH_REQUIRED có nút Đăng nhập', () => {
    const err = new ApiError({ code: 'AUTH_REQUIRED', message: 'Bạn chưa đăng nhập.' }, 401);
    render(
      <MemoryRouter>
        <ErrorBlock error={err} />
      </MemoryRouter>,
    );
    expect(screen.getByRole('link', { name: 'Đăng nhập' })).toHaveAttribute('href', '/dang-nhap');
  });
});

describe('chống CSRF: yêu cầu ghi luôn là JSON (D-89)', () => {
  it('POST không có thân vẫn gửi content-type application/json; GET thì không cần', async () => {
    const seen: { method: string; type: string | null }[] = [];
    setFetch(async (_url, init) => {
      seen.push({ method: init?.method ?? 'GET', type: new Headers(init?.headers).get('content-type') });
      return new Response('{}', { status: 200, headers: { 'content-type': 'application/json' } });
    });
    await api.logout();
    await api.choices('s1');
    await api.deletePlayerKey();
    await api.session();
    await waitFor(() => expect(seen).toHaveLength(4));
    expect(seen.slice(0, 3).map((s) => s.type)).toEqual(['application/json', 'application/json', 'application/json']);
    expect(seen[3]).toEqual({ method: 'GET', type: null });
  });

  it('máy chủ giả ở chế độ invite từ chối route ghi không phải JSON, như máy chủ thật', async () => {
    const server = withMock({ auth: 'invite' });
    const resp = await server.fetch('/api/auth/login', { method: 'POST', body: JSON.stringify({ code: MOCK_INVITE_CODE }) });
    expect(resp.status).toBe(403);
    expect((await resp.json()).code).toBe('REQUEST_ORIGIN_INVALID');
  });
});
