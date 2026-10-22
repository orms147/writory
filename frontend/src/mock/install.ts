import { setFetch } from '../api/client';
import { createMockServer } from './server';

/** Bật lớp mock trong trình duyệt (`npm run dev:mock`). Kịch bản đọc từ URL:
 *  `?mock=rong` lúc mở trang (tủ trống, chưa có khoá); `?auth=invite` lúc mở trang (phải đăng nhập
 *  bằng `MOCK_INVITE_CODE`, D-89); `?loi=<MÃ>` ở mỗi lời gọi (lỗi giả lập). */
export function installMock() {
  const params = new URLSearchParams(window.location.search);
  const server = createMockServer({
    scenario: params.get('mock'),
    auth: params.get('auth') === 'invite' ? 'invite' : 'dev',
    fault: () => new URLSearchParams(window.location.search).get('loi'),
  });
  setFetch(server.fetch);
}
