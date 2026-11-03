// Tủ truyện: nút "Viết truyện mới" ở đầu trang (D-159), để không phải cuộn tới hàng cuối mới mở được truyện mới.
import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Library } from '../screens/Library';
import { renderApp, withMock } from './render';

describe('tủ truyện: nút Viết truyện mới', () => {
  it('đứng ở đầu trang, trước danh sách truyện, dẫn tới /moi', async () => {
    withMock();
    renderApp(<Library />);
    const list = (await screen.findByText('Đài Phát Thanh Nửa Đêm')).closest('ol');
    const button = screen.getByRole('link', { name: /Viết truyện mới/ });
    expect(button).toHaveAttribute('href', '/moi');
    expect(list).not.toBeNull();
    // Đứng trước danh sách theo thứ tự đọc: thấy ngay khi mở trang.
    expect(button.compareDocumentPosition(list as Node) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('tủ trống và chưa có khoá: nút tắt, kèm lý do', async () => {
    withMock({ scenario: 'rong' });
    renderApp(<Library />);
    const button = await screen.findByText(/Viết truyện mới/);
    const holder = button.closest('[aria-disabled]');
    expect(holder).toHaveAttribute('aria-disabled', 'true');
    expect(screen.queryByRole('link', { name: /Viết truyện mới/ })).toBeNull();
    expect(holder).toHaveTextContent('sau khi có khoá');
  });
});
