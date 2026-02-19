import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

/* ── 토스트 알림 ────────────────────────────────────────────────── */
function Toast({ message, onClose }) {
  return (
    <div className="fixed top-6 left-1/2 -translate-x-1/2 z-50 flex items-center space-x-3 bg-red-600 text-white px-5 py-3 rounded-xl shadow-xl animate-bounce-once">
      <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
      </svg>
      <span className="text-sm font-medium">{message}</span>
      <button onClick={onClose} className="text-white/70 hover:text-white ml-1">✕</button>
    </div>
  );
}

export default function InterviewSetup() {
  const navigate = useNavigate();
  const [userId, setUserId]   = useState(2);
  const [jobId, setJobId]     = useState(1);
  const [loading, setLoading] = useState(false);
  const [toast, setToast]     = useState('');

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(''), 4000);
  };

  const handleStart = async (e) => {
    e.preventDefault();
    setToast('');
    setLoading(true);

    try {
      const { data } = await axios.post(
        `${API_BASE_URL}/api/interview/start`,
        { user_id: parseInt(userId), job_id: parseInt(jobId) },
        { timeout: 8000 }
      );
      navigate(`/interview/${data.session_id}`);
    } catch (err) {
      if (!err.response) {
        // 네트워크 / 서버 오프라인
        showToast('서버에 연결할 수 없습니다. 백엔드(http://localhost:8000)가 실행 중인지 확인해 주세요.');
      } else if (err.response.status === 404) {
        showToast('사용자 또는 공고를 찾을 수 없습니다. ID를 확인해 주세요.');
      } else {
        showToast(err.response?.data?.detail || '면접 시작에 실패했습니다. 다시 시도해 주세요.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">

      {/* 토스트 */}
      {toast && <Toast message={toast} onClose={() => setToast('')} />}

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

        {/* 폼 */}
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
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         placeholder-gray-400 transition-all"
              placeholder="2"
            />
            <p className="mt-1 text-xs text-gray-400">기본값: 2 (Kim Developer)</p>
          </div>

          {/* Job ID */}
          <div>
            <label htmlFor="jobId" className="block text-sm font-medium text-gray-700 mb-1.5">
              공고 ID
            </label>
            <input
              type="number" id="jobId" value={jobId} min="1" required
              onChange={e => setJobId(e.target.value)}
              className="w-full px-4 py-3 bg-white text-gray-900 border border-gray-300 rounded-lg
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         placeholder-gray-400 transition-all"
              placeholder="1"
            />
            <p className="mt-1 text-xs text-gray-400">기본값: 1 (Python Backend Developer)</p>
          </div>

          {/* 버튼 */}
          <button
            type="submit" disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 active:scale-95
                       text-white font-semibold py-3.5 px-6 rounded-xl
                       transition-all duration-150 shadow-lg
                       disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100"
          >
            {loading ? (
              <span className="flex items-center justify-center space-x-2">
                <svg className="animate-spin h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <span>면접 시작 중...</span>
              </span>
            ) : '면접 시작하기'}
          </button>
        </form>

        {/* 푸터 */}
        <p className="mt-6 text-center text-xs text-gray-400">
          Powered by FastAPI · React · pgvector
        </p>
      </div>
    </div>
  );
}
