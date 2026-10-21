import { LinkButton } from '../components/ui';

/** Đường dẫn không có trong app (phía trình duyệt; lỗi máy chủ dùng ErrorBlock). */
export function NotFound() {
  return (
    <main className="wt relative grid min-h-screen place-items-center px-4">
      <div className="max-w-[480px] text-center">
        <h1 className="font-display text-[44px] font-medium">Trang này chưa được viết</h1>
        <p className="mt-2 text-[15px] text-ink-200">Đường dẫn không có trong WriTory.</p>
        <LinkButton to="/" className="mt-6">
          Về tủ truyện
        </LinkButton>
      </div>
    </main>
  );
}
