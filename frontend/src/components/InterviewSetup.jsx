import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

/* ─── 토스트 알림 ─────────────────────────────────────────────── */
function Toast({ message, onClose }) {
  return (
    <div className="fixed top-6 left-1/2 -translate-x-1/2 z-50 flex items-center space-x-3
                    bg-red-600 text-white px-5 py-3 rounded-xl shadow-xl max-w-sm w-full mx-4">
      <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
      </svg>
      <span className="text-sm font-medium flex-1">{message}</span>
      <button onClick={onClose} className="text-white/70 hover:text-white ml-1 flex-shrink-0">✕</button>
    </div>
  );
}

export default function InterviewSetup() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [userId, setUserId]           = useState(2);
  const [jobId, setJobId]             = useState('');
  const [jobs, setJobs]               = useState([]);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [resumeFile, setResumeFile]   = useState(null);
  const [loading, setLoading]         = useState(false);
  const [loadingMsg, setLoadingMsg]   = useState('');
  const [toast, setToast]             = useState('');

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(''), 5000);
  };

  /* JD 목록 가져오기 */
  useEffect(() => {
    axios.get(`${API_BASE_URL}/api/admin/jobs`)
      .then(({ data }) => {
        setJobs(data);
        if (data.length > 0) setJobId(String(data[0].id));
      })
      .catch(() => showToast('공고 목록을 불러오지 못했습니다. 관리자에게 문의하세요.'))
      .finally(() => setJobsLoading(false));
  }, []);

  /* 파일 선택 핸들러 */
  const handleFileChange = (e) => {
    const file = e.target.files?.[0] ?? null;
    if (file && !file.name.toLowerCase().endsWith('.pdf')) {
      showToast('PDF 파일만 업로드할 수 있습니다.');
      e.target.value = '';
      return;
    }
    setResumeFile(file);
  };

  /* 면접 시작 */
  const handleStart = async (e) => {
    e.preventDefault();
    setToast('');
    if (!jobId) { showToast('지원할 공고를 선택해 주세요.'); return; }
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('user_id', parseInt(userId, 10));
      formData.append('job_id',  parseInt(jobId,  10));
      if (resumeFile) {
        setLoadingMsg('이력서 분석 중... (최대 30초 소요)');
        formData.append('resume', resumeFile);
      } else {
        setLoadingMsg('면접 시작 중...');
      }

      const { data } = await axios.post(
        `${API_BASE_URL}/api/interview/start`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 60000 }
      );
      // Store greeting audio_url so ChatRoom can auto-play it on mount
      if (data.audio_url) {
        sessionStorage.setItem(`greeting_audio_${data.session_id}`, data.audio_url);
      }
      navigate(`/interview/${data.session_id}`);
    } catch (err) {
      if (!err.response) {
        showToast('서버에 연결할 수 없습니다. 백엔드(http://localhost:8000)가 실행 중인지 확인해 주세요.');
      } else if (err.response.status === 404) {
        showToast('사용자 또는 공고를 찾을 수 없습니다. ID를 다시 확인해 주세요.');
      } else if (err.response.status === 400) {
        showToast(err.response.data?.detail ?? '잘못된 요청입니다.');
      } else {
        showToast(err.response?.data?.detail ?? '면접 시작에 실패했습니다. 다시 시도해 주세요.');
      }
    } finally {
      setLoading(false);
      setLoadingMsg('');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      {toast && <Toast message={toast} onClose={() => setToast('')} />}

      {/* ── Full-screen loading overlay ── */}
      {loading && (
        <div className="fixed inset-0 z-50 bg-slate-900/80 backdrop-blur-sm flex flex-col items-center justify-center space-y-6">
          <div className="relative w-20 h-20">
            <div className="absolute inset-0 rounded-full border-4 border-blue-200/30" />
            <div className="absolute inset-0 rounded-full border-4 border-blue-400 border-t-transparent animate-spin" />
            <div className="absolute inset-2 rounded-full border-4 border-indigo-300/20" />
            <div className="absolute inset-2 rounded-full border-4 border-indigo-400 border-b-transparent animate-spin" style={{ animationDirection: 'reverse', animationDuration: '0.8s' }} />
          </div>
          <div className="text-center space-y-2">
            <p className="text-white font-semibold text-lg">면접이 곧 진행될 예정입니다.</p>
            <p className="text-blue-200 text-sm">잠시만 기다려 주세요...</p>
            {loadingMsg && (
              <p className="text-slate-400 text-xs animate-pulse mt-1">{loadingMsg}</p>
            )}
          </div>
        </div>
      )}

      <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md">

        {/* 헤더 */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-full mb-4 shadow-lg">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-1">AI Interview</h1>
          <p className="text-gray-500 text-sm">LangChain · RAG · llama3.1</p>
        </div>

        <form onSubmit={handleStart} className="space-y-5">

          {/* User ID */}
          <div>
            <label htmlFor="userId" className="block text-sm font-medium text-gray-700 mb-1.5">
              사용자 ID
            </label>
            <input
              type="number" id="userId" value={userId} min="1" required
              onChange={e => setUserId(e.target.value)}
              className="w-full px-4 py-3 bg-white text-gray-900 border border-gray-300 rounded-lg
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder-gray-400"
              placeholder="2"
            />
            <p className="mt-1 text-xs text-gray-400">기본값: 2 (Kim Developer)</p>
          </div>

          {/* Job Select — fetched from /api/admin/jobs */}
          <div>
            <label htmlFor="jobSelect" className="block text-sm font-medium text-gray-700 mb-1.5">
              지원 공고 선택
            </label>
            {jobsLoading ? (
              <div className="w-full px-4 py-3 border border-gray-200 rounded-lg bg-gray-50 text-gray-400 text-sm animate-pulse">
                공고 목록 불러오는 중...
              </div>
            ) : jobs.length === 0 ? (
              <div className="w-full px-4 py-3 border border-red-200 rounded-lg bg-red-50 text-red-500 text-sm">
                등록된 공고가 없습니다.{' '}
                <a href="/admin" className="underline font-semibold">관리자 페이지</a>에서 먼저 공고를 등록해 주세요.
              </div>
            ) : (
              <select
                id="jobSelect"
                value={jobId}
                onChange={e => setJobId(e.target.value)}
                required
                className="w-full px-4 py-3 bg-white text-gray-900 border border-gray-300 rounded-lg
                           focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {jobs.map(j => (
                  <option key={j.id} value={j.id}>#{j.id} — {j.title}</option>
                ))}
              </select>
            )}
          </div>

          {/* PDF Resume Upload */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              이력서 업로드 <span className="text-gray-400 font-normal">(선택 사항 · PDF)</span>
            </label>

            <div
              onClick={() => fileInputRef.current?.click()}
              className={`relative w-full border-2 border-dashed rounded-xl p-5 text-center cursor-pointer
                          transition-colors
                          ${resumeFile
                            ? 'border-blue-400 bg-blue-50'
                            : 'border-gray-300 bg-gray-50 hover:bg-blue-50 hover:border-blue-400'}`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={handleFileChange}
              />
              {resumeFile ? (
                <div className="flex items-center justify-center space-x-2">
                  <svg className="w-6 h-6 text-red-500 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd"/>
                  </svg>
                  <div className="text-left">
                    <p className="text-sm font-medium text-blue-700 truncate max-w-xs">{resumeFile.name}</p>
                    <p className="text-xs text-gray-500">{(resumeFile.size / 1024).toFixed(1)} KB</p>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => { e.stopPropagation(); setResumeFile(null); fileInputRef.current.value = ''; }}
                    className="ml-auto text-gray-400 hover:text-red-500 transition-colors"
                  >✕</button>
                </div>
              ) : (
                <div className="space-y-1">
                  <svg className="w-8 h-8 text-gray-400 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
                  </svg>
                  <p className="text-sm text-gray-500">클릭하여 PDF 이력서 선택</p>
                  <p className="text-xs text-gray-400">이력서 기반 맞춤형 질문이 제공됩니다</p>
                </div>
              )}
            </div>
          </div>

          {/* 시작 버튼 */}
          <button
            type="submit" disabled={loading || jobsLoading || jobs.length === 0}
            className="w-full bg-blue-600 hover:bg-blue-700 active:scale-95
                       text-white font-semibold py-3.5 px-6 rounded-xl
                       transition-all duration-150 shadow-lg
                       disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
          >
            {loading ? (
              <span className="flex items-center justify-center space-x-2">
                <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"/>
                </svg>
                <span>{loadingMsg || '면접 시작 중...'}</span>
              </span>
            ) : '면접 시작하기'}
          </button>
        </form>

        <div className="mt-6 flex justify-between items-center">
          <p className="text-xs text-gray-400">Powered by FastAPI · React · pgvector</p>
          <a href="/admin" className="text-xs text-blue-500 hover:text-blue-700 underline">관리자 →</a>
        </div>
      </div>
    </div>
  );
}
