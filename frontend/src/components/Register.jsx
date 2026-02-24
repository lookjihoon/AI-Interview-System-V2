import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';

const API = 'http://localhost:8000';

function Field({ label, children, error }) {
  return (
    <div>
      <label className="block text-sm font-semibold text-gray-700 mb-1">{label}</label>
      {children}
      {error && <p className="text-red-500 text-xs mt-1">{error}</p>}
    </div>
  );
}

const cls = "w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 transition";

export default function Register() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    email: '', password: '', name: '', phone: '', birth_date: '', address: '',
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [apiError, setApiError] = useState('');
  const [loading, setLoading] = useState(false);

  const set = f => e => setForm(prev => ({ ...prev, [f]: e.target.value }));

  /* ── Validation ──────────────────────────────────────────────────────────── */
  const validate = () => {
    const errs = {};
    if (!form.email)    errs.email    = '이메일을 입력해주세요.';
    if (!form.name)     errs.name     = '이름을 입력해주세요.';
    if (form.password.length < 4) errs.password = '비밀번호는 4자 이상이어야 합니다.';
    const hasLetter = /[a-zA-Z가-힣]/.test(form.password);
    const hasDigit  = /\d/.test(form.password);
    if (!hasLetter || !hasDigit)
      errs.password = '비밀번호는 영문자와 숫자를 모두 포함해야 합니다.';
    if (form.phone && !/^[\d\-+() ]+$/.test(form.phone))
      errs.phone = '올바른 전화번호 형식으로 입력해주세요.';
    return errs;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setApiError('');
    const errs = validate();
    if (Object.keys(errs).length) { setFieldErrors(errs); return; }
    setFieldErrors({});
    setLoading(true);
    try {
      const payload = { ...form };
      if (!payload.birth_date) delete payload.birth_date;
      if (!payload.phone)      delete payload.phone;
      if (!payload.address)    delete payload.address;
      await axios.post(`${API}/api/auth/register`, payload);
      navigate('/login', { state: { registered: true } });
    } catch (err) {
      setApiError(err.response?.data?.detail ?? '회원가입에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-slate-100 flex items-center justify-center p-4 py-12">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex w-16 h-16 rounded-2xl bg-indigo-600 items-center justify-center shadow-lg mb-4">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900">회원가입</h1>
          <p className="text-gray-400 text-sm mt-1">AI 면접 시스템에 오신 것을 환영합니다</p>
        </div>

        {/* Form card */}
        <div className="bg-white rounded-2xl shadow-xl p-8 space-y-5">
          <form onSubmit={handleSubmit} className="space-y-4">

            <Field label="이메일 *" error={fieldErrors.email}>
              <input type="email" required value={form.email} onChange={set('email')}
                placeholder="hong@example.com" className={cls} />
            </Field>

            <Field label="비밀번호 *" error={fieldErrors.password}>
              <input type="password" required value={form.password} onChange={set('password')}
                placeholder="영문자 + 숫자 조합 4자 이상" className={cls} />
            </Field>

            <Field label="이름 *" error={fieldErrors.name}>
              <input type="text" required value={form.name} onChange={set('name')}
                placeholder="홍길동" className={cls} />
            </Field>

            <Field label="전화번호" error={fieldErrors.phone}>
              <input type="tel" value={form.phone} onChange={set('phone')}
                placeholder="010-1234-5678" className={cls} />
            </Field>

            <Field label="생년월일">
              <input type="date" value={form.birth_date} onChange={set('birth_date')} className={cls} />
            </Field>

            <Field label="주소">
              <input type="text" value={form.address} onChange={set('address')}
                placeholder="서울특별시 강남구..." className={cls} />
            </Field>

            {apiError && (
              <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-2.5 text-red-600 text-sm">
                {apiError}
              </div>
            )}

            <button
              type="submit" disabled={loading}
              className="w-full bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white font-semibold rounded-xl py-2.5 text-sm shadow-lg transition-all disabled:opacity-60"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  가입 중...
                </span>
              ) : '가입하기'}
            </button>
          </form>

          <div className="text-center text-sm text-gray-400">
            이미 계정이 있으신가요?{' '}
            <Link to="/login" className="text-indigo-600 font-semibold hover:underline">
              로그인
            </Link>
          </div>

          <div className="text-center">
            <Link to="/" className="text-xs text-gray-300 hover:text-gray-500">← 홈으로</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
