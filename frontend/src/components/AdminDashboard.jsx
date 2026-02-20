import { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

/* ── Reusable input components ───────────────────────────────────────────── */
function Field({ label, hint, children }) {
  return (
    <div className="space-y-1">
      <label className="block text-sm font-semibold text-slate-300">
        {label} {hint && <span className="font-normal text-slate-500 text-xs">{hint}</span>}
      </label>
      {children}
    </div>
  );
}

const inputCls =
  'w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 ' +
  'placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 ' +
  'focus:border-transparent transition';

const textareaCls = inputCls + ' resize-none';

/* ── Toast ───────────────────────────────────────────────────────────────── */
function Toast({ msg, type }) {
  const bg = type === 'error' ? 'bg-red-600' : 'bg-emerald-600';
  return (
    <div
      className={`fixed top-5 left-1/2 -translate-x-1/2 z-50 px-5 py-3 rounded-xl
                  shadow-2xl text-white text-sm font-medium max-w-sm w-full mx-4 ${bg}`}
    >
      {msg}
    </div>
  );
}

/* ── Status Badge ────────────────────────────────────────────────────────── */
function Badge({ label, value }) {
  return value ? (
    <span className="inline-block bg-slate-700 text-slate-300 text-xs rounded px-2 py-0.5 mr-1 mb-1">
      {label}
    </span>
  ) : null;
}

/* ── JobCard ─────────────────────────────────────────────────────────────── */
function JobCard({ job, onDelete }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 hover:border-indigo-500 transition">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-xs text-indigo-400 font-mono mb-1">JD #{job.id}</p>
          <h3 className="text-base font-semibold text-white truncate">{job.title}</h3>
          <div className="flex flex-wrap mt-2">
            <Badge label="근무조건" value={job.conditions} />
            <Badge label="전형절차" value={job.procedures} />
            <Badge label="지원방법" value={job.application_method} />
          </div>
        </div>
        <div className="flex gap-2 shrink-0">
          <button
            onClick={() => setOpen(o => !o)}
            className="text-xs text-slate-400 hover:text-white border border-slate-600 hover:border-slate-400
                       rounded-lg px-3 py-1.5 transition"
          >
            {open ? '접기' : '상세'}
          </button>
          <button
            onClick={() => onDelete(job.id)}
            className="text-xs text-red-400 hover:text-red-300 border border-red-800 hover:border-red-500
                       rounded-lg px-3 py-1.5 transition"
          >
            삭제
          </button>
        </div>
      </div>

      {open && (
        <div className="mt-4 space-y-3 text-sm text-slate-300 border-t border-slate-700 pt-4">
          {job.description && (
            <div>
              <p className="text-xs text-slate-500 font-semibold mb-1">직무 설명</p>
              <p className="whitespace-pre-wrap leading-relaxed">{job.description}</p>
            </div>
          )}
          {job.requirements && (
            <div>
              <p className="text-xs text-slate-500 font-semibold mb-1">자격 요건</p>
              <p className="whitespace-pre-wrap">{job.requirements}</p>
            </div>
          )}
          {job.conditions && (
            <div>
              <p className="text-xs text-slate-500 font-semibold mb-1">근무 조건</p>
              <p className="whitespace-pre-wrap">{job.conditions}</p>
            </div>
          )}
          {job.procedures && (
            <div>
              <p className="text-xs text-slate-500 font-semibold mb-1">전형 절차</p>
              <p className="whitespace-pre-wrap">{job.procedures}</p>
            </div>
          )}
          {job.application_method && (
            <div>
              <p className="text-xs text-slate-500 font-semibold mb-1">지원 방법</p>
              <p className="whitespace-pre-wrap">{job.application_method}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── EMPTY FORM STATE ────────────────────────────────────────────────────── */
const EMPTY = {
  title: '',
  description: '',
  requirements: '',
  min_experience: 0,
  conditions: '',
  procedures: '',
  application_method: '',
};

/* ════════════════════════════════════════════════════════════════════════════
   AdminDashboard
══════════════════════════════════════════════════════════════════════════════ */
export default function AdminDashboard() {
  const [jobs, setJobs]       = useState([]);
  const [form, setForm]       = useState(EMPTY);
  const [loading, setLoading] = useState(false);
  const [toast, setToast]     = useState(null); // { msg, type }

  /* helpers */
  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  const set = (field) => (e) =>
    setForm(f => ({ ...f, [field]: e.target.value }));

  /* fetch jobs */
  const fetchJobs = async () => {
    try {
      const { data } = await axios.get(`${API_BASE_URL}/api/admin/jobs`);
      setJobs(data);
    } catch {
      showToast('공고 목록을 불러오지 못했습니다.', 'error');
    }
  };

  useEffect(() => { fetchJobs(); }, []);

  /* submit */
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.title.trim() || !form.description.trim()) {
      showToast('제목과 직무 설명은 필수입니다.', 'error');
      return;
    }
    setLoading(true);
    try {
      await axios.post(`${API_BASE_URL}/api/admin/jobs`, {
        ...form,
        min_experience: parseInt(form.min_experience, 10) || 0,
      });
      showToast('공고가 등록되었습니다!');
      setForm(EMPTY);
      fetchJobs();
    } catch (err) {
      showToast(err.response?.data?.detail ?? '등록 실패. 다시 시도해 주세요.', 'error');
    } finally {
      setLoading(false);
    }
  };

  /* delete */
  const handleDelete = async (id) => {
    if (!window.confirm(`JD #${id}를 삭제하시겠습니까?`)) return;
    try {
      await axios.delete(`${API_BASE_URL}/api/admin/jobs/${id}`);
      showToast('공고가 삭제되었습니다.');
      fetchJobs();
    } catch {
      showToast('삭제에 실패했습니다.', 'error');
    }
  };

  /* ─── Render ─────────────────────────────────────────────────────────── */
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 px-4 py-10">
      {toast && <Toast msg={toast.msg} type={toast.type} />}

      <div className="max-w-5xl mx-auto">

        {/* Header */}
        <div className="mb-10 flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-indigo-600 flex items-center justify-center shadow-lg">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Admin Dashboard</h1>
            <p className="text-slate-500 text-sm">채용 공고 · JD 관리</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">

          {/* ── Left: Create Form ─────────────────────────────────────────── */}
          <div className="lg:col-span-2">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
              <h2 className="text-base font-semibold mb-5 text-slate-200">새 채용 공고 등록</h2>
              <form onSubmit={handleSubmit} className="space-y-4">

                <Field label="공고 제목" hint="(필수)">
                  <input
                    className={inputCls} value={form.title} onChange={set('title')}
                    placeholder="예: Python Backend Developer" required
                  />
                </Field>

                <Field label="최소 경력 (년)">
                  <input
                    className={inputCls} type="number" min="0" value={form.min_experience}
                    onChange={set('min_experience')}
                  />
                </Field>

                <Field label="직무 설명 (JD)" hint="(필수)">
                  <textarea
                    className={textareaCls} rows={4} value={form.description}
                    onChange={set('description')}
                    placeholder="담당 업무, 기술 스택, 팀 소개 등" required
                  />
                </Field>

                <Field label="자격 요건">
                  <textarea
                    className={textareaCls} rows={3} value={form.requirements}
                    onChange={set('requirements')}
                    placeholder="필수/우대 기술, Python 3.8+, FastAPI..."
                  />
                </Field>

                <Field label="근무 조건">
                  <textarea
                    className={textareaCls} rows={2} value={form.conditions}
                    onChange={set('conditions')}
                    placeholder="재택/사무실, 급여, 근무시간..."
                  />
                </Field>

                <Field label="전형 절차">
                  <textarea
                    className={textareaCls} rows={2} value={form.procedures}
                    onChange={set('procedures')}
                    placeholder="서류 → 코딩테스트 → 기술면접 → 최종면접"
                  />
                </Field>

                <Field label="지원 방법">
                  <textarea
                    className={textareaCls} rows={2} value={form.application_method}
                    onChange={set('application_method')}
                    placeholder="이메일 제출 / 채용 사이트 지원"
                  />
                </Field>

                <button
                  type="submit" disabled={loading}
                  className="w-full bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white
                             font-semibold py-2.5 rounded-xl transition-all shadow-lg
                             disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? '등록 중...' : '공고 등록'}
                </button>
              </form>
            </div>
          </div>

          {/* ── Right: Job List ───────────────────────────────────────────── */}
          <div className="lg:col-span-3">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-slate-200">
                등록된 공고 <span className="text-indigo-400">({jobs.length})</span>
              </h2>
              <button
                onClick={fetchJobs}
                className="text-xs text-slate-500 hover:text-slate-300 border border-slate-700
                           hover:border-slate-500 rounded-lg px-3 py-1.5 transition"
              >
                새로고침
              </button>
            </div>

            {jobs.length === 0 ? (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-10 text-center text-slate-500">
                <svg className="w-10 h-10 mx-auto mb-3 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414A1 1 0 0119 9.414V19a2 2 0 01-2 2z" />
                </svg>
                <p className="text-sm">등록된 공고가 없습니다.<br />왼쪽 폼으로 첫 공고를 추가하세요.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {jobs.map(j => (
                  <JobCard key={j.id} job={j} onDelete={handleDelete} />
                ))}
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}
