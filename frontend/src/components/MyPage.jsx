import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

/* ── Score chip ──────────────────────────────────────────────────────────── */
function ScoreChip({ score }) {
  if (score == null) return <span className="text-gray-400 text-xs">-</span>;
  const s = Number(score);
  const color = s >= 80 ? 'bg-emerald-100 text-emerald-700'
              : s >= 60 ? 'bg-blue-100 text-blue-700'
              : s >= 40 ? 'bg-amber-100 text-amber-700'
              :           'bg-red-100 text-red-700';
  return <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${color}`}>{s}점</span>;
}

/* ── Toast ───────────────────────────────────────────────────────────────── */
function Toast({ msg, type }) {
  const bg = type === 'error' ? 'bg-red-500' : 'bg-emerald-500';
  return (
    <div className={`fixed top-5 left-1/2 -translate-x-1/2 z-50 px-5 py-3 rounded-xl shadow-xl text-white text-sm font-medium ${bg} max-w-xs w-full text-center`}>
      {msg}
    </div>
  );
}

/* ── Tab button ──────────────────────────────────────────────────────────── */
function Tab({ label, icon, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold rounded-xl transition-all
        ${active
          ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-200'
          : 'text-slate-500 hover:text-slate-800 hover:bg-slate-100'
        }`}
    >
      <span>{icon}</span>{label}
    </button>
  );
}

/* ════════════════════════════════════════════════════════════════════════════
   MyPage — Candidate Dashboard
══════════════════════════════════════════════════════════════════════════════ */
export default function MyPage() {
  const navigate = useNavigate();

  /* ─── Identity (simple session — no auth) ────────────────────────────── */
  const [userId, setUserId]         = useState(() => sessionStorage.getItem('mypage_uid') || '');
  const [userInfo, setUserInfo]     = useState(null);
  const [idInput, setIdInput]       = useState('');
  const [idError, setIdError]       = useState('');

  /* ─── UI state ────────────────────────────────────────────────────────── */
  const [tab, setTab]               = useState('resume');   // 'resume' | 'jobs' | 'history'
  const [toast, setToast]           = useState(null);

  /* ─── Data ────────────────────────────────────────────────────────────── */
  const [resume, setResume]         = useState('');
  const [savingResume, setSavingResume] = useState(false);
  const [jobs, setJobs]             = useState([]);
  const [jobSearch, setJobSearch]   = useState('');
  const [history, setHistory]       = useState([]);
  const [historySortDesc, setHistorySortDesc] = useState(true);

  const showToast = (msg, type = 'success') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  /* ─── Load user info ─────────────────────────────────────────────────── */
  const loadUser = useCallback(async (uid) => {
    try {
      const { data } = await axios.get(`${API_BASE_URL}/api/candidate/users/${uid}`);
      setUserInfo(data);
      sessionStorage.setItem('mypage_uid', uid);
      // Load resume
      try {
        const r = await axios.get(`${API_BASE_URL}/api/candidate/users/${uid}/resume`);
        setResume(r.data.resume_text || '');
      } catch { setResume(''); }
    } catch {
      setIdError('해당 ID의 사용자를 찾을 수 없습니다.');
      setUserInfo(null);
    }
  }, []);

  useEffect(() => {
    if (userId) loadUser(userId);
  }, [userId, loadUser]);

  /* ─── Load jobs & history on tab change ──────────────────────────────── */
  useEffect(() => {
    if (!userInfo) return;
    if (tab === 'jobs') {
      axios.get(`${API_BASE_URL}/api/admin/jobs`)
        .then(r => setJobs(r.data))
        .catch(() => showToast('공고를 불러오지 못했습니다.', 'error'));
    }
    if (tab === 'history') {
      axios.get(`${API_BASE_URL}/api/candidate/users/${userId}/interviews`)
        .then(r => setHistory(r.data))
        .catch(() => showToast('이력을 불러오지 못했습니다.', 'error'));
    }
  }, [tab, userInfo, userId]);

  /* ─── Handlers ───────────────────────────────────────────────────────── */
  const handleLogin = async (e) => {
    e.preventDefault();
    setIdError('');
    setUserId(idInput.trim());
  };

  const handleSaveResume = async () => {
    if (!resume.trim()) { showToast('이력서 내용을 입력해주세요.', 'error'); return; }
    setSavingResume(true);
    try {
      await axios.post(`${API_BASE_URL}/api/candidate/resumes`, {
        user_id: parseInt(userId, 10),
        content: resume,
      });
      showToast('이력서가 저장되었습니다!');
    } catch (err) {
      showToast(err.response?.data?.detail ?? '저장 실패.', 'error');
    } finally { setSavingResume(false); }
  };

  const handleStartInterview = async (job) => {
    try {
      const { data } = await axios.post(`${API_BASE_URL}/api/interview/sessions`, {
        user_id: parseInt(userId, 10),
        job_posting_id: job.id,
        resume_text: resume || undefined,
      });
      navigate(`/interview/${data.session_id ?? data.id}`);
    } catch (err) {
      showToast(err.response?.data?.detail ?? '면접 시작 실패.', 'error');
    }
  };

  /* ─── Derived ─────────────────────────────────────────────────────────── */
  const filteredJobs = jobs.filter(j =>
    j.title.toLowerCase().includes(jobSearch.toLowerCase()) ||
    (j.requirements || '').toLowerCase().includes(jobSearch.toLowerCase())
  );

  const sortedHistory = [...history].sort((a, b) =>
    historySortDesc
      ? (b.total_score ?? -1) - (a.total_score ?? -1)
      : (a.total_score ?? -1) - (b.total_score ?? -1)
  );

  /* ═══════════════════════════════════════════════════════════════════════
     IDENTITY GATE
  ═══════════════════════════════════════════════════════════════════════ */
  if (!userInfo) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-slate-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-sm space-y-6">
          <div className="text-center">
            <div className="w-16 h-16 bg-indigo-100 rounded-full flex items-center justify-center mx-auto mb-3">
              <span className="text-3xl">👤</span>
            </div>
            <h1 className="text-xl font-bold text-gray-900">마이페이지</h1>
            <p className="text-gray-500 text-sm mt-1">사용자 ID를 입력해 로그인하세요</p>
          </div>
          <form onSubmit={handleLogin} className="space-y-3">
            <input
              type="number" min="1"
              value={idInput}
              onChange={e => setIdInput(e.target.value)}
              placeholder="User ID (예: 1)"
              className="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              required
            />
            {idError && <p className="text-red-500 text-xs">{idError}</p>}
            <button
              type="submit"
              className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl py-2.5 text-sm transition"
            >
              입장하기
            </button>
          </form>
          <button
            onClick={() => navigate('/')}
            className="w-full text-gray-400 text-xs hover:text-gray-600 text-center"
          >
            ← 홈으로
          </button>
        </div>
      </div>
    );
  }

  /* ═══════════════════════════════════════════════════════════════════════
     MAIN DASHBOARD
  ═══════════════════════════════════════════════════════════════════════ */
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50">
      {toast && <Toast msg={toast.msg} type={toast.type} />}

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center text-lg">
              👤
            </div>
            <div>
              <h1 className="font-bold text-gray-900">{userInfo.name}</h1>
              <p className="text-xs text-gray-400">{userInfo.email} · ID #{userId}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => navigate('/')}
              className="text-sm text-gray-500 hover:text-gray-800 border border-gray-200 rounded-lg px-3 py-1.5 transition"
            >
              홈
            </button>
            <button
              onClick={() => { sessionStorage.removeItem('mypage_uid'); setUserId(''); setUserInfo(null); setIdInput(''); }}
              className="text-sm text-red-400 hover:text-red-600 border border-red-200 rounded-lg px-3 py-1.5 transition"
            >
              로그아웃
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">

        {/* ── Tabs ──────────────────────────────────────────────────────── */}
        <div className="flex gap-2 mb-8">
          <Tab label="이력서 관리"       icon="📄" active={tab === 'resume'}  onClick={() => setTab('resume')} />
          <Tab label="채용 공고"         icon="🏢" active={tab === 'jobs'}    onClick={() => setTab('jobs')} />
          <Tab label="면접 히스토리"     icon="📊" active={tab === 'history'} onClick={() => setTab('history')} />
        </div>

        {/* ══════════════════════════════════════════════════════════════
            TAB 1: RESUME MANAGEMENT
        ══════════════════════════════════════════════════════════════ */}
        {tab === 'resume' && (
          <div className="bg-white rounded-2xl shadow-sm p-8 space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold text-gray-900">이력서 관리</h2>
                <p className="text-sm text-gray-500 mt-0.5">계정당 1개의 이력서만 유지됩니다. 저장 시 기존 이력서가 대체됩니다.</p>
              </div>
              <span className={`text-xs font-semibold px-3 py-1 rounded-full ${resume ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                {resume ? '✅ 등록됨' : '미등록'}
              </span>
            </div>

            <textarea
              value={resume}
              onChange={e => setResume(e.target.value)}
              placeholder={"이름 / 학교 / 경력 / 기술스택 등을 자유 형식으로 입력하세요.\n\n예시:\n이름: 김개발\n경력: FastAPI 3년, React 2년\n기술: Python, PostgreSQL, Docker"}
              rows={14}
              className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none leading-relaxed"
            />

            <div className="flex justify-between items-center">
              <p className="text-xs text-gray-400">{resume.length.toLocaleString()}자</p>
              <button
                onClick={handleSaveResume}
                disabled={savingResume}
                className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold px-6 py-2.5 rounded-xl text-sm shadow-sm transition disabled:opacity-50"
              >
                {savingResume ? '저장 중...' : '💾 이력서 저장'}
              </button>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════
            TAB 2: JOB BOARD
        ══════════════════════════════════════════════════════════════ */}
        {tab === 'jobs' && (
          <div className="space-y-5">
            {/* Search bar */}
            <div className="relative">
              <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400">🔍</span>
              <input
                value={jobSearch}
                onChange={e => setJobSearch(e.target.value)}
                placeholder="공고 제목 또는 요구 기술로 검색..."
                className="w-full pl-10 pr-4 py-3 border border-gray-200 bg-white rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400 shadow-sm"
              />
            </div>

            {filteredJobs.length === 0 ? (
              <div className="bg-white rounded-2xl p-12 text-center text-gray-400 shadow-sm">
                <p className="text-4xl mb-3">📭</p>
                <p className="text-sm">표시할 채용 공고가 없습니다.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {filteredJobs.map(job => (
                  <div key={job.id} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 hover:shadow-md hover:border-indigo-200 transition-all flex flex-col">
                    <div className="flex-1">
                      <p className="text-xs text-indigo-500 font-mono mb-1">JD #{job.id}</p>
                      <h3 className="font-bold text-gray-900 text-base leading-snug mb-2">{job.title}</h3>
                      {job.min_experience > 0 && (
                        <span className="inline-block text-xs bg-slate-100 text-slate-600 rounded px-2 py-0.5 mb-2">
                          경력 {job.min_experience}년 이상
                        </span>
                      )}
                      {job.requirements && (
                        <p className="text-xs text-gray-500 leading-relaxed line-clamp-3">{job.requirements}</p>
                      )}
                    </div>
                    <button
                      onClick={() => handleStartInterview(job)}
                      className="mt-4 w-full bg-indigo-600 hover:bg-indigo-500 active:scale-95 text-white text-sm font-semibold py-2.5 rounded-xl transition-all shadow-sm"
                    >
                      지원 및 면접 시작하기 →
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════
            TAB 3: INTERVIEW HISTORY
        ══════════════════════════════════════════════════════════════ */}
        {tab === 'history' && (
          <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <h2 className="font-bold text-gray-900">면접 결과 이력 <span className="text-indigo-500">({history.length})</span></h2>
              <button
                onClick={() => setHistorySortDesc(d => !d)}
                className="text-xs text-gray-500 hover:text-gray-800 border border-gray-200 rounded-lg px-3 py-1.5 transition flex items-center gap-1"
              >
                점수 {historySortDesc ? '↓ 높은순' : '↑ 낮은순'}
              </button>
            </div>

            {sortedHistory.length === 0 ? (
              <div className="p-12 text-center text-gray-400">
                <p className="text-4xl mb-3">📋</p>
                <p className="text-sm">완료된 면접 이력이 없습니다.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50 text-slate-500 text-xs font-semibold uppercase tracking-wide">
                    <tr>
                      <th className="px-5 py-3 text-left">공고명</th>
                      <th className="px-4 py-3 text-left">날짜</th>
                      <th className="px-4 py-3 text-center">종합</th>
                      <th className="px-4 py-3 text-center">직무역량</th>
                      <th className="px-4 py-3 text-center">의사소통</th>
                      <th className="px-4 py-3 text-center">면접태도</th>
                      <th className="px-4 py-3 text-center">리포트</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {sortedHistory.map(row => (
                      <tr key={row.session_id} className="hover:bg-slate-50 transition">
                        <td className="px-5 py-3 font-medium text-gray-900 max-w-[200px] truncate">{row.job_title}</td>
                        <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                          {new Date(row.date).toLocaleDateString('ko-KR', { year:'2-digit', month:'2-digit', day:'2-digit' })}
                        </td>
                        <td className="px-4 py-3 text-center"><ScoreChip score={row.total_score} /></td>
                        <td className="px-4 py-3 text-center"><ScoreChip score={row.tech_score} /></td>
                        <td className="px-4 py-3 text-center"><ScoreChip score={row.communication_score} /></td>
                        <td className="px-4 py-3 text-center"><ScoreChip score={row.non_verbal_score} /></td>
                        <td className="px-4 py-3 text-center">
                          <button
                            onClick={() => navigate(`/report/${row.session_id}`)}
                            className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold border border-indigo-200 hover:border-indigo-400 rounded-lg px-3 py-1 transition"
                          >
                            결과 보기
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

      </main>
    </div>
  );
}
