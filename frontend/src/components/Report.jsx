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
  const s = Number(score) || 0;
  const r = 54;
  const circ = 2 * Math.PI * r;
  const dash = (s / 100) * circ;
  const color = s >= 80 ? '#22c55e' : s >= 60 ? '#3b82f6' : s >= 40 ? '#f59e0b' : '#ef4444';

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
        <text x="70" y="65" textAnchor="middle" fill="#111827" fontSize="28" fontWeight="bold">{s}</text>
        <text x="70" y="85" textAnchor="middle" fill="#6b7280" fontSize="12">/ 100</text>
      </svg>
      <p className="text-sm font-semibold text-gray-600 mt-1">종합 점수</p>
    </div>
  );
}

/* ── Score Badge ─────────────────────────────────────────────────────────── */
function ScoreBadge({ label, score, color }) {
  const s = Number(score) || 0;
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <span className="text-sm font-bold" style={{ color }}>{s}점</span>
      </div>
      <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${s}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

/* ── Detail Card ─────────────────────────────────────────────────────────── */
function DetailCard({ icon, title, content, accent }) {
  return (
    <div className="bg-white rounded-xl border-l-4 p-5 shadow-sm" style={{ borderLeftColor: accent }}>
      <div className="flex items-center space-x-2 mb-2">
        <span className="text-xl">{icon}</span>
        <h3 className="font-semibold text-gray-800 text-sm">{title}</h3>
      </div>
      <p className="text-gray-600 text-sm leading-relaxed whitespace-pre-wrap">
        {content || '—'}
      </p>
    </div>
  );
}

/* ── Raw JSON Fallback ───────────────────────────────────────────────────── */
function RawFallback({ data }) {
  return (
    <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 mt-4">
      <p className="text-amber-700 font-semibold text-sm mb-2">⚠️ 일부 데이터가 예상 형식과 다릅니다. 원본 평가 결과:</p>
      <pre className="text-xs text-gray-600 whitespace-pre-wrap overflow-auto max-h-64">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

/* ── Safe number helper ──────────────────────────────────────────────────── */
const safeNum = (v) => Math.max(0, Math.min(100, Number(v) || 0));

/* ── Main Report ─────────────────────────────────────────────────────────── */
export default function Report() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [retries, setRetries] = useState(0);
  const [parseError, setParseError] = useState(false);
  const [transcript, setTranscript] = useState([]);

  useEffect(() => {
    let timer;
    const fetchReport = async () => {
      try {
        const { data } = await axios.get(
          `${API_BASE_URL}/api/interview/session/${sessionId}/report`
        );
        // Validate essential keys exist
        if (data && typeof data === 'object') {
          setReport(data);
          // Flag if key structure is unexpected
          if (data.tech_score === undefined && data.total_score === undefined) {
            setParseError(true);
          }
        } else {
          setParseError(true);
          setReport(data);
        }
        setLoading(false);
      } catch (err) {
        if (err?.response?.status === 404 && retries < 6) {
          timer = setTimeout(() => setRetries(r => r + 1), 5000);
        } else {
          setError(err?.response?.data?.detail ?? '리포트를 불러오지 못했습니다.');
          setLoading(false);
        }
      }
    };
    fetchReport();
    // Fetch transcript in parallel — don't fail report if this errors
    axios.get(`${API_BASE_URL}/api/interview/session/${sessionId}/transcript`)
      .then(({ data }) => setTranscript(Array.isArray(data) ? data : []))
      .catch(() => {});
    return () => clearTimeout(timer);
  }, [sessionId, retries]);

  /* ── Derived values — all guarded with ?. and || 0 ── */
  const techScore    = safeNum(report?.tech_score);
  const commScore    = safeNum(report?.communication_score);
  const probScore    = safeNum(report?.problem_solving_score);
  const nvScore      = safeNum(report?.non_verbal_score);
  const totalScore   = safeNum(report?.total_score || Math.round(techScore * 0.40 + commScore * 0.25 + probScore * 0.25 + nvScore * 0.10));
  const summary      = report?.summary || '';
  const details      = report?.details ?? {};
  const strengths          = details?.strengths || details?.strength || '';
  const weaknesses         = details?.weaknesses || details?.weakness || details?.improvements || '';
  const jdFit              = details?.jd_fit || details?.jd_fit_assessment || details?.fit || '';
  const nonVerbalFeedback  = details?.non_verbal_feedback || '';
  const totalTimeSec       = Number(details?.total_time) || 0;
  const formatTotalTime    = (s) => s > 0
    ? `${Math.floor(s / 60)}분 ${s % 60}초`
    : null;

  const radarData = report
    ? [
        { subject: '직무역량',   score: techScore },
        { subject: '의사소통',   score: commScore },
        { subject: '문제해결력', score: probScore },
        { subject: '면접 태도',  score: nvScore   },
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

  /* ── Fetch Error ── */
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

  /* ── No report data guard ── */
  if (!report) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow p-8 max-w-md text-center space-y-4">
          <div className="text-5xl">📄</div>
          <p className="text-gray-600 text-sm">데이터 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.</p>
          <button onClick={() => navigate('/')}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm">
            처음으로
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">

      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm print:hidden">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">면접 결과 리포트</h1>
            <p className="text-xs text-gray-500 mt-0.5">Session #{sessionId}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => window.print()}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
            >
              📄 PDF로 저장
            </button>
            <button onClick={() => navigate('/')}
              className="px-4 py-2 text-sm font-medium text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">
              새 면접 시작
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-8">

        {/* Parse warning banner */}
        {parseError && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-amber-700 text-sm">
            ⚠️ AI 리포트 형식이 일부 예상과 다릅니다. 가능한 데이터를 표시합니다.
          </div>
        )}

        {/* Score Overview */}
        <section className="bg-white rounded-2xl shadow-sm p-8">
          <div className="flex flex-col md:flex-row items-center gap-10">
            <div className="flex flex-col items-center">
              <ScoreRing score={totalScore} />
              {/* Total interview time badge */}
              {formatTotalTime(totalTimeSec) && (
                <div className="mt-3 flex items-center gap-1.5 px-3 py-1 bg-slate-100 rounded-full">
                  <span className="text-slate-400 text-xs">⏱</span>
                  <span className="text-slate-600 text-xs font-medium">중 총 {formatTotalTime(totalTimeSec)}</span>
                </div>
              )}
            </div>
            <div className="flex-1 w-full space-y-4">
              <ScoreBadge label="직무역량 (Hard Skill)"        score={techScore}  color="#3b82f6" />
              <ScoreBadge label="의사소통 (Communication)"     score={commScore}  color="#8b5cf6" />
              <ScoreBadge label="문제해결력 (Problem Solving)"  score={probScore}  color="#10b981" />
              <ScoreBadge label="면접 태도 (Non-verbal)"        score={nvScore}    color="#f59e0b" />
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

          {/* Non-verbal Attitude Feedback — dedicated 1-line badge */}
          {nonVerbalFeedback && (
            <div className="mt-4 flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
              <span className="text-amber-500 text-lg flex-shrink-0">📌</span>
              <div>
                <p className="text-xs font-semibold text-amber-700 mb-0.5">면접 태도 피드백</p>
                <p className="text-sm text-amber-800 leading-relaxed">{nonVerbalFeedback}</p>
              </div>
            </div>
          )}
        </section>

        {/* Summary */}
        {summary && (
          <section className="bg-blue-600 text-white rounded-2xl shadow-sm p-6">
            <h2 className="text-sm font-semibold uppercase tracking-wider opacity-75 mb-2">종합 평가</h2>
            <p className="text-lg leading-relaxed font-medium">{summary}</p>
          </section>
        )}

        {/* Detail Cards */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <DetailCard icon="💪" title="강점 (Strengths)"        content={strengths}  accent="#22c55e" />
          <DetailCard icon="📈" title="개선점 (Weaknesses)"     content={weaknesses} accent="#f59e0b" />
          <DetailCard icon="🎯" title="직무 적합도 (JD Fit)"    content={jdFit}      accent="#3b82f6" />
        </section>

        {/* Chat History for PDF */}
        {transcript.length > 0 && (() => {
          // Build (question, answer) exchange pairs from flat transcript list
          const exchanges = [];
          let pendingQ = null;
          for (const item of transcript) {
            if (item.sender === 'ai') {
              if (pendingQ) exchanges.push({ question: pendingQ, answer: null });
              pendingQ = item;
            } else if (item.sender === 'human' && pendingQ) {
              exchanges.push({ question: pendingQ, answer: item });
              pendingQ = null;
            }
          }
          if (pendingQ) exchanges.push({ question: pendingQ, answer: null });

          return (
            <section className="bg-white rounded-2xl shadow-sm p-6">
              <h2 className="text-base font-bold text-gray-800 mb-4 pb-2 border-b border-gray-200">
                💬 면접 대화 기록
              </h2>
              <div className="space-y-5">
                {exchanges.map((ex, idx) => (
                  <div key={idx} className="break-inside-avoid space-y-2">
                    {/* AI Question */}
                    <div className="flex gap-2">
                      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-bold mt-0.5">AI</span>
                      <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-2 text-sm text-gray-800 leading-relaxed flex-1">
                        {ex.question.content}
                      </div>
                    </div>
                    {/* Human Answer */}
                    {ex.answer && (
                      <>
                        <div className="flex gap-2 justify-end">
                          <div className="bg-gray-100 border border-gray-200 rounded-xl px-4 py-2 text-sm text-gray-800 leading-relaxed max-w-[85%]">
                            {ex.answer.content}
                            {ex.answer.answer_time > 0 && (
                              <p className="text-xs text-gray-400 mt-1">⏱ 답변 소요 시간: {ex.answer.answer_time}초</p>
                            )}
                          </div>
                          <span className="flex-shrink-0 w-6 h-6 rounded-full bg-gray-400 flex items-center justify-center text-white text-xs font-bold mt-0.5">나</span>
                        </div>
                        {/* Per-turn evaluation badge */}
                        {(ex.answer.score != null || ex.answer.feedback) && (
                          <div className="ml-8 flex items-start gap-2 bg-green-50 border border-green-200 rounded-lg px-3 py-2 text-xs text-green-800">
                            <span className="text-green-500 mt-0.5">✅</span>
                            <div>
                              {ex.answer.score != null && (
                                <span className="font-bold mr-2">AI 평가 {ex.answer.score}점</span>
                              )}
                              {ex.answer.feedback && (
                                <p className="mt-0.5 text-green-700 leading-relaxed">{ex.answer.feedback}</p>
                              )}
                            </div>
                          </div>
                        )}
                      </>
                    )}

                  </div>
                ))}
              </div>
            </section>
          );
        })()}


        {/* Raw JSON fallback — only shows if parse error AND no structured data */}
        {parseError && !strengths && !weaknesses && (
          <RawFallback data={report} />
        )}

        {/* Footer */}
        <div className="text-center text-xs text-gray-400 pb-4 print:hidden">
          Powered by AI Interview System · 평가는 AI 분석 기반이며 참고용입니다.
        </div>
      </main>
    </div>
  );
}
