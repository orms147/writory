import { useId, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router';
import { api } from '../api/client';
import { asApiError, type ApiError } from '../api/errors';
import { Logo } from '../components/ui';
import { useAuth } from '../state/Auth';
import mountains from '../styles/mountains.svg';

// Đăng nhập bằng mã mời (D-89). Chủ dự án tạo mã cho từng người bạn; không có tạo tài khoản. Mã chỉ
// đi trong thân `POST /auth/login`, không lưu ở trình duyệt. Máy chủ chạy chế độ `dev` thì không
// cần đăng nhập (mọi người là người chơi dev, D-44).

export function Login() {
  const auth = useAuth();
  const navigate = useNavigate();
  const [code, setCode] = useState('');
  const [error, setError] = useState<ApiError | null>(null);
  const [sending, setSending] = useState(false);
  const ids = { code: useId(), error: useId() };
  const session = auth.data;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!code.trim() || sending) return;
    setSending(true);
    setError(null);
    try {
      const out = await api.login(code);
      setCode('');
      auth.set(out);
      navigate('/', { replace: true });
    } catch (err) {
      setError(asApiError(err));
      setSending(false);
    }
  };

  const logout = async () => {
    try {
      auth.set(await api.logout());
    } catch (err) {
      setError(asApiError(err));
    }
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
        <h2 className="font-display text-[34px] font-medium">Mừng bạn quay lại</h2>
        {session?.mode === 'dev' ? (
          <p role="note" className="mt-6 rounded-[12px] border border-cinnabar-400/50 bg-cinnabar-400/10 px-4 py-3 text-[14px] leading-relaxed text-cinnabar-100">
            Máy chủ đang chạy ở chế độ dev: không cần đăng nhập, mọi người dùng chung người chơi dev.{' '}
            <Link to="/" className="wt-link font-semibold text-cinnabar-200">
              Vào tủ truyện →
            </Link>
          </p>
        ) : session?.logged_in ? (
          <div className="mt-6 text-[15px] text-ink-100">
            <p>
              Bạn đang đăng nhập với tên <span className="font-semibold text-ink-50">{session.name}</span>.
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Link to="/" className="wt-btn wt-btn-primary inline-flex min-h-[52px] items-center rounded-[12px] bg-cinnabar-600 px-5 font-semibold text-on-cinnabar">
                Vào thư viện <span className="wt-arrow ml-2" aria-hidden="true">→</span>
              </Link>
              <button type="button" onClick={logout} className="wt-btn wt-btn-ghost inline-flex min-h-[52px] items-center rounded-[12px] border border-ink-600 px-5 font-semibold text-ink-50">
                Đăng xuất
              </button>
            </div>
          </div>
        ) : (
          <>
            <p className="text-[14px] text-ink-200">Nhập mã mời bạn nhận được để mở tủ truyện của mình.</p>
            <form onSubmit={submit} className="mt-6" noValidate>
              <label htmlFor={ids.code} className="block text-[14px] text-ink-100">
                Mã mời
              </label>
              <input
                id={ids.code}
                type="password"
                autoComplete="off"
                spellCheck={false}
                value={code}
                onChange={(e) => setCode(e.target.value)}
                aria-invalid={error ? true : undefined}
                aria-describedby={error ? ids.error : undefined}
                placeholder="wt-xxxx-xxxx-…"
                className="wt-input mt-2 block min-h-[52px] w-full rounded-[12px] border border-ink-700 bg-ink-900 px-4 font-mono text-[15px] text-ink-50"
              />
              {error && (
                <p id={ids.error} role="alert" className="mt-3 text-[14px] text-cinnabar-200">
                  {error.message}
                </p>
              )}
              <button
                type="submit"
                disabled={!code.trim() || sending}
                className="wt-btn wt-btn-primary mt-5 inline-flex min-h-[52px] w-full items-center justify-center gap-2 rounded-[12px] bg-cinnabar-600 text-[15px] font-semibold text-on-cinnabar disabled:opacity-50"
              >
                {sending ? 'Đang kiểm mã…' : 'Vào thư viện'} <span className="wt-arrow" aria-hidden="true">→</span>
              </button>
            </form>
          </>
        )}
        <p className="mt-6 border-t border-ink-750 pt-5 text-[13px] leading-relaxed text-ink-400">
          WriTory dùng khoá OpenRouter của chính bạn để viết truyện: bạn kết nối khoá sau khi vào, và tự trả phí gọi model theo từng chương.
        </p>
      </section>
    </main>
  );
}
