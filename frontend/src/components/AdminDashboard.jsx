import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

/* ── Shared helpers ──────────────────────────────────────────────────────── */
const inputCls =
  'w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 ' +
  'placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 transition';
const textareaCls = inputCls + ' resize-none';

function FLabel({ label, hint, children }) {
  return (
    <div className="space-y-1">
      <label className="block text-sm font-semibold text-slate-300">
        {label} {hint && <span className="font-normal text-slate-500 text-xs">{hint}</span>}
      </label>
      {children}
    </div>
  );
}

function Toast({ msg, type }) {
  const bg = type === 'error' ? 'bg-red-600' : 'bg-emerald-600';
  return (
    <div className={`fixed top-5 left-1/2 -translate-x-1/2 z-50 px-5 py-3 rounded-xl
                    shadow-2xl text-white text-sm font-medium max-w-sm w-full mx-4 text-center ${bg}`}>
      {msg}
    </div>
  );
}

function ScoreCell({ score }) {
  if (score == null) return <span className="text-slate-600 text-xs">-</span>;
  const s = Number(score);
  const color = s >= 80 ? 'text-emerald-400' : s >= 60 ? 'text-blue-400' : s >= 40 ? 'text-amber-400' : 'text-red-400';
  return <span className={`font-bold text-sm ${color}`}>{s}</span>;
}

function TabBtn({ label, icon, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-lg transition
        ${active ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
    >
      <span>{icon}</span>{label}
    </button>
  );
}

/* ── Empty form ──────────────────────────────────────────────────────────── */
const EMPTY = { title:'', description:'', requirements:'', min_experience:0, conditions:'', procedures:'', application_method:'' };

/* ════════════════════════════════════════════════════════════════════════════
   AdminDashboard
══════════════════════════════════════════════════════════════════════════════ */
export default function AdminDashboard() {
  const navigate = useNavigate();

  /* ─── UI ──────────────────────────────────────────────────────────────── */
  const [tab, setTab]             = useState('jobs');     // 'jobs' | 'leaderboard'
  const [toast, setToast]         = useState(null);

  /* ─── Jobs tab ────────────────────────────────────────────────────────── */
  const [jobs, setJobs]           = useState([]);
  const [form, setForm]           = useState(EMPTY);
  const [editId, setEditId]       = useState(null);       // null = create mode, number = edit mode
  const [submitting, setSubmitting] = useState(false);

  /* ─── Leaderboard tab ─────────────────────────────────────────────────── */
  const [selectedJob, setSelectedJob]     = useState(null);
  const [applicants, setApplicants]       = useState([]);
  const [applicantSort, setApplicantSort] = useState('total_score'); // column key
  const [sortDesc, setSortDesc]           = useState(true);
  const [loadingApplicants, setLoadingApplicants] = useState(false);

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3500);
  };

  /* ─── Fetch all jobs (both tabs need this) ────────────────────────────── */
  const fetchJobs = useCallback(async () => {
    try {
      const { data } = await axios.get(`${API_BASE_URL}/api/admin/jobs`);
      setJobs(data);
    } catch {
      showToast('공고 목록을 불러오지 못했습니다.', 'error');
    }
  }, []);

  useEffect(() => { fetchJobs(); }, [fetchJobs]);

  /* ─── Form helpers ────────────────────────────────────────────────────── */
  const set = (field) => (e) => setForm(f => ({ ...f, [field]: e.target.value }));

  const startEdit = (job) => {
    setEditId(job.id);
    setForm({
      title: job.title, description: job.description,
      requirements: job.requirements || '', min_experience: job.min_experience,
      conditions: job.conditions || '', procedures: job.procedures || '',
      application_method: job.application_method || '',
    });
  };

  const cancelEdit = () => { setEditId(null); setForm(EMPTY); };

  /* ─── Submit (create or update) ───────────────────────────────────────── */
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.title.trim() || !form.description.trim()) {
      showToast('제목과 직무 설명은 필수입니다.', 'error');
      return;
    }
    setSubmitting(true);
    try {
      const payload = { ...form, min_experience: parseInt(form.min_experience, 10) || 0 };
      if (editId) {
        await axios.put(`${API_BASE_URL}/api/admin/jobs/${editId}`, payload);
        showToast('공고가 수정되었습니다.');
        setEditId(null);
      } else {
        await axios.post(`${API_BASE_URL}/api/admin/jobs`, payload);
        showToast('공고가 등록되었습니다!');
      }
      setForm(EMPTY);
      fetchJobs();
    } catch (err) {
      showToast(err.response?.data?.detail ?? '저장 실패.', 'error');
    } finally { setSubmitting(false); }
  };

  /* ─── Delete / Copy ───────────────────────────────────────────────────── */
  const handleDelete = async (id) => {
    if (!window.confirm(`JD #${id}를 마감하시겠습니까?`)) return;
    await axios.delete(`${API_BASE_URL}/api/admin/jobs/${id}`);
    showToast('공고가 마감되었습니다.');
    fetchJobs();
  };

  const handleCopy = async (id) => {
    await axios.post(`${API_BASE_URL}/api/admin/jobs/${id}/copy`);
    showToast('공고가 복사되었습니다.');
    fetchJobs();
  };

  /* ─── Leaderboard ─────────────────────────────────────────────────────── */
  const loadApplicants = async (job) => {
    setSelectedJob(job);
    setLoadingApplicants(true);
    try {
      const { data } = await axios.get(`${API_BASE_URL}/api/admin/jobs/${job.id}/applicants`);
      setApplicants(data);
    } catch {
      showToast('지원자 목록을 불러오지 못했습니다.', 'error');
    } finally { setLoadingApplicants(false); }
  };

  const toggleSort = (col) => {
    if (applicantSort === col) setSortDesc(d => !d);
    else { setApplicantSort(col); setSortDesc(true); }
  };

  const sortedApplicants = [...applicants].sort((a, b) => {
    const av = a[applicantSort] ?? -1;
    const bv = b[applicantSort] ?? -1;
    return sortDesc ? bv - av : av - bv;
  });

  const rankColor = (i) => i === 0 ? 'text-yellow-400' : i === 1 ? 'text-slate-300' : i === 2 ? 'text-amber-600' : 'text-slate-500';
  const rankLabel = (i) => i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `${i + 1}`;

  /* ═══════════════════════════════════════════════════════════════════════
     RENDER
  ═══════════════════════════════════════════════════════════════════════ */
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 px-4 py-10">
      {toast && <Toast msg={toast.msg} type={toast.type} />}

      <div className="max-w-6xl mx-auto">

        {/* ── Header ────────────────────────────────────────────────────── */}
        <div className="mb-8 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-indigo-600 flex items-center justify-center shadow-lg">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">Admin Dashboard</h1>
              <p className="text-slate-500 text-sm">채용 공고 관리 · 지원자 现황</p>
            </div>
          </div>
          <button
            onClick={() => navigate('/')}
            className="text-sm text-slate-400 hover:text-white border border-slate-700 rounded-lg px-4 py-2 transition"
          >
            홈으로
          </button>
        </div>

        {/* ── Tabs ──────────────────────────────────────────────────────── */}
        <div className="flex gap-2 mb-8">
          <TabBtn label="공고 관리"       icon="📋" active={tab === 'jobs'}        onClick={() => setTab('jobs')} />
          <TabBtn label="지원자 랭킹"     icon="🏆" active={tab === 'leaderboard'} onClick={() => setTab('leaderboard')} />
        </div>

        {/* ════════════════════════════════════════════════════════════════
            TAB 1: JOB MANAGEMENT
        ════════════════════════════════════════════════════════════════ */}
        {tab === 'jobs' && (
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">

            {/* Create / Edit Form */}
            <div className="lg:col-span-2">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
                <h2 className="text-base font-semibold mb-5 text-slate-200">
                  {editId ? `✏️ 공고 수정 (JD #${editId})` : '새 채용 공고 등록'}
                </h2>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <FLabel label="공고 제목" hint="(필수)">
                    <input className={inputCls} value={form.title} onChange={set('title')} placeholder="예: Python Backend Developer" required />
                  </FLabel>
                  <FLabel label="최소 경력 (년)">
                    <input className={inputCls} type="number" min="0" value={form.min_experience} onChange={set('min_experience')} />
                  </FLabel>
                  <FLabel label="직무 설명 (JD)" hint="(필수)">
                    <textarea className={textareaCls} rows={4} value={form.description} onChange={set('description')} placeholder="담당 업무, 기술 스택, 팀 소개..." required />
                  </FLabel>
                  <FLabel label="자격 요건">
                    <textarea className={textareaCls} rows={3} value={form.requirements} onChange={set('requirements')} placeholder="필수/우대 기술..." />
                  </FLabel>
                  <FLabel label="근무 조건">
                    <textarea className={textareaCls} rows={2} value={form.conditions} onChange={set('conditions')} placeholder="재택/사무실, 급여..." />
                  </FLabel>
                  <FLabel label="전형 절차">
                    <textarea className={textareaCls} rows={2} value={form.procedures} onChange={set('procedures')} placeholder="서류 → 코딩테스트 → 면접" />
                  </FLabel>
                  <FLabel label="지원 방법">
                    <textarea className={textareaCls} rows={2} value={form.application_method} onChange={set('application_method')} placeholder="이메일 / 채용 사이트" />
                  </FLabel>

                  <div className="flex gap-2">
                    <button
                      type="submit" disabled={submitting}
                      className="flex-1 bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white font-semibold py-2.5 rounded-xl transition-all shadow-lg disabled:opacity-50"
                    >
                      {submitting ? '저장 중...' : editId ? '수정 완료' : '공고 등록'}
                    </button>
                    {editId && (
                      <button type="button" onClick={cancelEdit}
                        className="px-4 py-2.5 border border-slate-600 hover:border-slate-400 text-slate-400 hover:text-white rounded-xl text-sm transition"
                      >
                        취소
                      </button>
                    )}
                  </div>
                </form>
              </div>
            </div>

            {/* Job List */}
            <div className="lg:col-span-3">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-base font-semibold text-slate-200">
                  등록된 공고 <span className="text-indigo-400">({jobs.length})</span>
                </h2>
                <button onClick={fetchJobs}
                  className="text-xs text-slate-500 hover:text-slate-300 border border-slate-700 hover:border-slate-500 rounded-lg px-3 py-1.5 transition"
                >새로고침</button>
              </div>

              {jobs.length === 0 ? (
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-10 text-center text-slate-500">
                  <p className="text-sm">등록된 공고가 없습니다.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {jobs.map(job => (
                    <JobCard
                      key={job.id} job={job}
                      onEdit={() => startEdit(job)}
                      onDelete={() => handleDelete(job.id)}
                      onCopy={() => handleCopy(job.id)}
                      onLeaderboard={() => { setTab('leaderboard'); loadApplicants(job); }}
                    />
                  ))}
                </div>
              )}
            </div>

          </div>
        )}

        {/* ════════════════════════════════════════════════════════════════
            TAB 2: APPLICANT LEADERBOARD
        ════════════════════════════════════════════════════════════════ */}
        {tab === 'leaderboard' && (
          <div className="space-y-6">

            {/* Job selector */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
              <p className="text-slate-400 text-xs font-semibold uppercase tracking-widest mb-3">공고 선택</p>
              <div className="flex flex-wrap gap-2">
                {jobs.map(j => (
                  <button
                    key={j.id}
                    onClick={() => loadApplicants(j)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium border transition
                      ${selectedJob?.id === j.id
                        ? 'bg-indigo-600 border-indigo-500 text-white'
                        : 'bg-slate-800 border-slate-700 text-slate-300 hover:border-indigo-500 hover:text-white'
                      }`}
                  >
                    JD #{j.id} · {j.title}
                  </button>
                ))}
              </div>
            </div>

            {/* Leaderboard table */}
            {selectedJob && (
              <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
                  <div>
                    <h2 className="font-bold text-white">{selectedJob.title}</h2>
                    <p className="text-slate-400 text-xs mt-0.5">
                      지원자 {applicants.length}명 · 완료된 AI 면접 기준
                    </p>
                  </div>
                  <button onClick={() => loadApplicants(selectedJob)}
                    className="text-xs text-slate-500 hover:text-slate-300 border border-slate-700 rounded-lg px-3 py-1.5 transition"
                  >새로고침</button>
                </div>

                {loadingApplicants ? (
                  <div className="p-12 text-center text-slate-500">
                    <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                    <p className="text-sm">로딩 중...</p>
                  </div>
                ) : applicants.length === 0 ? (
                  <div className="p-12 text-center text-slate-500">
                    <p className="text-4xl mb-3">📭</p>
                    <p className="text-sm">이 공고에 완료된 AI 면접이 없습니다.</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-slate-800/60 text-slate-400 text-xs font-semibold uppercase tracking-wide">
                        <tr>
                          <th className="px-5 py-3 text-left w-10">#</th>
                          <th className="px-4 py-3 text-left">지원자</th>
                          <th className="px-4 py-3 text-left">면접일</th>
                          {[
                            { key: 'total_score',         label: '종합' },
                            { key: 'tech_score',          label: '직무역량' },
                            { key: 'communication_score', label: '의사소통' },
                            { key: 'non_verbal_score',    label: '면접태도' },
                          ].map(col => (
                            <th key={col.key}
                              onClick={() => toggleSort(col.key)}
                              className="px-4 py-3 text-center cursor-pointer hover:text-indigo-300 transition select-none"
                            >
                              {col.label}
                              {applicantSort === col.key && (
                                <span className="ml-1 text-indigo-400">{sortDesc ? '↓' : '↑'}</span>
                              )}
                            </th>
                          ))}
                          <th className="px-4 py-3 text-center">리포트</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800">
                        {sortedApplicants.map((row, i) => (
                          <tr key={row.session_id} className="hover:bg-slate-800/40 transition">
                            <td className="px-5 py-3">
                              <span className={`text-base font-bold ${rankColor(i)}`}>{rankLabel(i)}</span>
                            </td>
                            <td className="px-4 py-3">
                              <p className="font-semibold text-white">{row.candidate_name}</p>
                              <p className="text-slate-500 text-xs">{row.candidate_email}</p>
                            </td>
                            <td className="px-4 py-3 text-slate-400 text-xs whitespace-nowrap">
                              {new Date(row.interview_date).toLocaleDateString('ko-KR')}
                            </td>
                            <td className="px-4 py-3 text-center"><ScoreCell score={row.total_score} /></td>
                            <td className="px-4 py-3 text-center"><ScoreCell score={row.tech_score} /></td>
                            <td className="px-4 py-3 text-center"><ScoreCell score={row.communication_score} /></td>
                            <td className="px-4 py-3 text-center"><ScoreCell score={row.non_verbal_score} /></td>
                            <td className="px-4 py-3 text-center">
                              {row.has_report ? (
                                <button
                                  onClick={() => navigate(`/report/${row.session_id}`)}
                                  className="text-xs text-indigo-400 hover:text-indigo-200 border border-indigo-800 hover:border-indigo-500 rounded-lg px-3 py-1 transition"
                                >
                                  상세 리포트
                                </button>
                              ) : (
                                <span className="text-slate-600 text-xs">-</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {!selectedJob && (
              <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-500">
                <p className="text-4xl mb-3">🏆</p>
                <p className="text-sm">위에서 공고를 선택하면 지원자 랭킹이 표시됩니다.</p>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}

/* ── JobCard ─────────────────────────────────────────────────────────────── */
function JobCard({ job, onEdit, onDelete, onCopy, onLeaderboard }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 hover:border-indigo-500/50 transition">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-xs text-indigo-400 font-mono mb-1">JD #{job.id}</p>
          <h3 className="text-base font-semibold text-white truncate">{job.title}</h3>
          <p className="text-slate-500 text-xs mt-1">경력 {job.min_experience}년 이상</p>
        </div>
        <div className="flex gap-1.5 shrink-0 flex-wrap justify-end">
          <button onClick={() => setOpen(o => !o)}
            className="text-xs text-slate-400 hover:text-white border border-slate-600 hover:border-slate-400 rounded-lg px-3 py-1.5 transition">
            {open ? '접기' : '상세'}
          </button>
          <button onClick={onEdit}
            className="text-xs text-blue-400 hover:text-blue-200 border border-blue-800 hover:border-blue-500 rounded-lg px-3 py-1.5 transition">
            수정
          </button>
          <button onClick={onCopy}
            className="text-xs text-slate-400 hover:text-white border border-slate-600 hover:border-slate-400 rounded-lg px-3 py-1.5 transition">
            복사
          </button>
          <button onClick={onLeaderboard}
            className="text-xs text-emerald-400 hover:text-emerald-200 border border-emerald-800 hover:border-emerald-500 rounded-lg px-3 py-1.5 transition">
            지원자 보기
          </button>
          <button onClick={onDelete}
            className="text-xs text-red-400 hover:text-red-200 border border-red-800 hover:border-red-500 rounded-lg px-3 py-1.5 transition">
            마감
          </button>
        </div>
      </div>

      {open && (
        <div className="mt-4 space-y-3 text-sm text-slate-300 border-t border-slate-700 pt-4">
          {job.description && <div><p className="text-xs text-slate-500 mb-1">직무 설명</p><p className="whitespace-pre-wrap leading-relaxed">{job.description}</p></div>}
          {job.requirements && <div><p className="text-xs text-slate-500 mb-1">자격 요건</p><p className="whitespace-pre-wrap">{job.requirements}</p></div>}
          {job.conditions && <div><p className="text-xs text-slate-500 mb-1">근무 조건</p><p className="whitespace-pre-wrap">{job.conditions}</p></div>}
          {job.procedures && <div><p className="text-xs text-slate-500 mb-1">전형 절차</p><p className="whitespace-pre-wrap">{job.procedures}</p></div>}
          {job.application_method && <div><p className="text-xs text-slate-500 mb-1">지원 방법</p><p className="whitespace-pre-wrap">{job.application_method}</p></div>}
        </div>
      )}
    </div>
  );
}
