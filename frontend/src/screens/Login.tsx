import { useId, useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import { Logo, cx } from '../components/ui';
import mountains from '../styles/mountains.svg';

// Đăng nhập / tạo tài khoản (D-/M-DangNhap): chỉ là giao diện. Máy chủ chưa có đăng nhập, mọi
// người là người chơi dev (D-44). Form không gửi gì đi: không có endpoint nào nhận mật khẩu.

export function Login() {
  const [tab, setTab] = useState<'in' | 'up'>('in');
  const [tried, setTried] = useState(false);
  const ids = { email: useId(), pass: useId(), note: useId() };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setTried(true);
  };

  return (
    <main className="wt relative grid min-h-screen overflow-hidden md:grid-cols-[1fr_536px]">
      <section className="relative flex min-h-[340px] flex-col justify-between overflow-hidden px-6 py-8 md:px-[72px] md:py-12">
        <img src={mountains} alt="" aria-hidden="true" className="absolute inset-0 h-full w-full object-cover" />
        <div className="relative">
          <Logo />
        </div>
        <div className="relative mt-16">
          <h1 className="font-display text-[44px] font-medium leading-[1.02] md:text-[76px]">
            Bạn sống
            <br />
            từng lựa chọn.
            <br />
            <span className="italic text-cinnabar-400">Ngòi bút</span> viết thành tiểu thuyết.
          </h1>
          <p className="mt-5 max-w-[520px] text-[15px] leading-relaxed text-ink-100 md:text-[17px]">
            Truyện tương tác tiếng Việt. Thế giới nhớ những gì bạn đã làm, và cả những lời bạn đã nói dối.
          </p>
        </div>
      </section>

      <section className="border-ink-750 px-6 py-10 md:border-l md:px-[56px] md:py-[170px]">
        <div role="tablist" aria-label="Đăng nhập hoặc tạo tài khoản" className="flex gap-1 rounded-[14px] border border-ink-700 bg-ink-900 p-1">
          {(['in', 'up'] as const).map((t) => (
            <button
              key={t}
              type="button"
              role="tab"
              aria-selected={tab === t}
              onClick={() => setTab(t)}
              className={cx('min-h-tap flex-1 rounded-[10px] text-[15px] font-semibold', tab === t ? 'bg-ink-50 text-ink-950' : 'text-ink-200')}
            >
              {t === 'in' ? 'Đăng nhập' : 'Tạo tài khoản'}
            </button>
          ))}
        </div>

        <p id={ids.note} role="note" className="mt-6 rounded-[12px] border border-cinnabar-400/50 bg-cinnabar-400/10 px-4 py-3 text-[14px] leading-relaxed text-cinnabar-100">
          Máy chủ chưa có đăng nhập. Mọi người đang dùng chung tài khoản người chơi dev, nên màn này chỉ là giao diện và không gửi gì đi.
        </p>

        <h2 className="mt-7 font-display text-[34px] font-medium">{tab === 'in' ? 'Mừng bạn quay lại' : 'Mở một tủ truyện mới'}</h2>
        <p className="text-[14px] text-ink-200">
          {tab === 'in' ? 'Truyện của bạn vẫn đang chờ ở trang bạn bỏ dở.' : 'Một tài khoản, một tủ truyện, một khoá OpenRouter.'}
        </p>

        <form onSubmit={submit} className="mt-6" aria-describedby={ids.note} noValidate>
          <label htmlFor={ids.email} className="block text-[14px] text-ink-100">
            Email
          </label>
          <input id={ids.email} type="email" autoComplete="off" className="wt-input mt-2 block min-h-[52px] w-full rounded-[12px] border border-ink-700 bg-ink-900 px-4 text-[15px] text-ink-50" />
          <label htmlFor={ids.pass} className="mt-4 block text-[14px] text-ink-100">
            Mật khẩu
          </label>
          <input id={ids.pass} type="password" autoComplete="off" className="wt-input mt-2 block min-h-[52px] w-full rounded-[12px] border border-ink-700 bg-ink-900 px-4 text-[15px] text-ink-50" />
          <button type="submit" className="wt-btn wt-btn-primary mt-5 inline-flex min-h-[52px] w-full items-center justify-center gap-2 rounded-[12px] bg-cinnabar-600 text-[15px] font-semibold text-on-cinnabar">
            {tab === 'in' ? 'Vào thư viện' : 'Tạo tài khoản'} <span className="wt-arrow" aria-hidden="true">→</span>
          </button>
          {tried && (
            <p role="status" className="mt-3 text-[14px] text-ink-100">
              Chưa đăng nhập được vì máy chủ chưa có tính năng này.{' '}
              <Link to="/" className="wt-link font-semibold text-cinnabar-200">
                Vào tủ truyện với người chơi dev →
              </Link>
            </p>
          )}
        </form>
        <p className="mt-6 border-t border-ink-750 pt-5 text-[13px] leading-relaxed text-ink-400">
          WriTory dùng khoá OpenRouter của chính bạn để viết truyện: bạn kết nối khoá sau khi vào, và tự trả phí gọi model theo từng chương.
        </p>
      </section>
    </main>
  );
}
