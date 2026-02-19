import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  PolarRadiusAxis, ResponsiveContainer, Tooltip
} from 'recharts';

const API_BASE_URL = 'http://localhost:8000';

/* ── Score Ring ──────────────────────────────────────────────────────────── */
function ScoreRing({ score }) {
  const r = 54;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  const color = score >= 80 ? '#22c55e' : score >= 60 ? '#3b82f6' : score >= 40 ? '#f59e0b' : '#ef4444';

  return (
    <div className="flex flex-col items-center">
      <svg width="140" height="140" viewBox="0 0 140 140">
        <circle cx="70" cy="70" r={r} fill="none" stroke="#e5e7eb" strokeWidth="12" />
        <circle
          cx="70" cy="70" r={r} fill="none"
          stroke={color} strokeWidth="12"
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          transform="rotate(-90 70 70)"
          style={{ transition: 'stroke-dasharray 1s ease' }}
        />
        <text x="70" y="65" textAnchor="middle" fill="#111827" fontSize="28" fontWeight="bold">{score}</text>
        <text x="70" y="85" textAnchor="middle" fill="#6b7280" fontSize="12">/ 100</text>
      </svg>
      <p className="text-sm font-semibold text-gray-600 mt-1">종합 점수</p>
    </div>
  );
}

/* ── Score Badge ─────────────────────────────────────────────────────────── */
function ScoreBadge({ label, score, color }) {
  const bar = { '--w': `${score}%` };
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <span className="text-sm font-bold" style={{ color }}>{score}점</span>
      </div>
      <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${score}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

/* ── Detail Card ─────────────────────────────────────────────────────────── */
function DetailCard({ icon, title, content, accent }) {
  return (
    <div className={`bg-white rounded-xl border-l-4 p-5 shadow-sm`} style={{ borderLeftColor: accent }}>
      <div className="flex items-center space-x-2 mb-2">
        <span className="text-xl">{icon}</span>
        <h3 className="font-semibold text-gray-800 text-sm">{title}</h3>
      </div>
      <p className="text-gray-600 text-sm leading-relaxed whitespace-pre-wrap">{content || '—'}</p>
    </div>
  );
}

/* ── Main Report ─────────────────────────────────────────────────────────── */
export default function Report() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retries, setRetries] = useState(0);

  useEffect(() => {
    let timer;
    const fetchReport = async () => {
      try {
        const { data } = await axios.get(
          `${API_BASE_URL}/api/interview/session/${sessionId}/report`
        );
        setReport(data);
        setLoading(false);
      } catch (err) {
        if (err?.response?.status === 404 && retries < 6) {
          // Report may still be generating — retry up to 6 times (30 s total)
          timer = setTimeout(() => setRetries(r => r + 1), 5000);
        } else {
          setError(err?.response?.data?.detail ?? '리포트를 불러오지 못했습니다.');
          setLoading(false);
        }
      }
    };
    fetchReport();
    return () => clearTimeout(timer);
  }, [sessionId, retries]);

  /* ── Radar data ── */
  const radarData = report
    ? [
        { subject: '직무역량',    score: report.tech_score ?? 0 },
        { subject: '의사소통',    score: report.communication_score ?? 0 },
        { subject: '문제해결력',  score: report.problem_solving_score ?? 0 },
      ]
    : [];

  /* ── Loading ── */
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="relative w-16 h-16 mx-auto">
            <div className="absolute inset-0 rounded-full border-4 border-blue-100" />
            <div className="absolute inset-0 rounded-full border-4 border-blue-600 border-t-transparent animate-spin" />
          </div>
          <p className="text-gray-700 font-semibold">
            {retries > 0 ? `AI 리포트 생성 중... (${retries}/6)` : '리포트 불러오는 중...'}
          </p>
          <p className="text-gray-400 text-sm">최대 30초 소요될 수 있습니다.</p>
        </div>
      </div>
    );
  }

  /* ── Error ── */
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow p-8 max-w-md text-center space-y-4">
          <div className="text-5xl">⚠️</div>
          <h2 className="text-lg font-bold text-gray-900">오류 발생</h2>
          <p className="text-gray-600 text-sm">{error}</p>
          <button onClick={() => navigate('/')}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm">
            처음으로
          </button>
        </div>
      </div>
    );
  }

  const details = report?.details ?? {};

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">

      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">면접 결과 리포트</h1>
            <p className="text-xs text-gray-500 mt-0.5">Session #{sessionId}</p>
          </div>
          <button onClick={() => navigate('/')}
            className="px-4 py-2 text-sm font-medium text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
            새 면접 시작
          </button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-8">

        {/* Score Overview */}
        <section className="bg-white rounded-2xl shadow-sm p-8">
          <div className="flex flex-col md:flex-row items-center gap-10">

            {/* Ring */}
            <ScoreRing score={report.total_score ?? 0} />

            {/* Bars + Radar */}
            <div className="flex-1 w-full space-y-4">
              <ScoreBadge label="직무역량 (Hard Skill)"   score={report.tech_score ?? 0}               color="#3b82f6" />
              <ScoreBadge label="의사소통 (Communication)"  score={report.communication_score ?? 0}      color="#8b5cf6" />
              <ScoreBadge label="문제해결력 (Problem Solving)" score={report.problem_solving_score ?? 0} color="#10b981" />
            </div>
          </div>
        </section>

        {/* Radar Chart */}
        <section className="bg-white rounded-2xl shadow-sm p-6">
          <h2 className="text-base font-bold text-gray-800 mb-4">역량 레이더 차트</h2>
          <ResponsiveContainer width="100%" height={320}>
            <RadarChart data={radarData} margin={{ top: 20, right: 30, bottom: 20, left: 30 }}>
              <PolarGrid stroke="#e5e7eb" />
              <PolarAngleAxis
                dataKey="subject"
                tick={{ fontSize: 13, fill: '#374151', fontWeight: 600 }}
              />
              <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10, fill: '#9ca3af' }} />
              <Radar
                name="점수"
                dataKey="score"
                stroke="#3b82f6"
                fill="#3b82f6"
                fillOpacity={0.25}
                strokeWidth={2}
              />
              <Tooltip
                formatter={(v) => [`${v}점`, '점수']}
                contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', fontSize: '13px' }}
              />
            </RadarChart>
          </ResponsiveContainer>
        </section>

        {/* Summary */}
        {report.summary && (
          <section className="bg-blue-600 text-white rounded-2xl shadow-sm p-6">
            <h2 className="text-sm font-semibold uppercase tracking-wider opacity-75 mb-2">종합 평가</h2>
            <p className="text-lg leading-relaxed font-medium">{report.summary}</p>
          </section>
        )}

        {/* Detail Cards */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <DetailCard
            icon="💪" title="강점 (Strengths)"
            content={details.strengths} accent="#22c55e"
          />
          <DetailCard
            icon="📈" title="개선점 (Weaknesses)"
            content={details.weaknesses} accent="#f59e0b"
          />
          <DetailCard
            icon="🎯" title="직무 적합도 (JD Fit)"
            content={details.jd_fit} accent="#3b82f6"
          />
        </section>

        {/* Footer */}
        <div className="text-center text-xs text-gray-400 pb-4">
          Powered by AI Interview System · 평가는 AI 분석 기반이며 참고용입니다.
        </div>
      </main>
    </div>
  );
}
