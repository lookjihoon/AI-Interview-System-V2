import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';

const API_BASE_URL = 'http://localhost:8000';

/* ─── 타이핑 인디케이터 ─────────────────────────────────────────── */
function TypingIndicator() {
  return (
    <div className="flex items-end space-x-3">
      <div className="flex-shrink-0 w-8 h-8 bg-slate-600 rounded-full flex items-center justify-center shadow">
        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      </div>
      <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-none px-4 py-3 shadow-sm">
        <div className="flex space-x-1.5 items-center h-5">
          {[0, 0.2, 0.4].map((delay, i) => (
            <span key={i} className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"
              style={{ animationDelay: `${delay}s` }} />
          ))}
        </div>
      </div>
    </div>
  );
}

/* ─── AI 말풍선 ─────────────────────────────────────────────────── */
function AiBubble({ content = '', category }) {
  return (
    <div className="flex items-end space-x-3">
      <div className="flex-shrink-0 w-8 h-8 bg-slate-600 rounded-full flex items-center justify-center shadow">
        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      </div>
      <div className="flex-1 max-w-2xl">
        <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-none px-4 py-3 shadow-sm">
          <div className="prose prose-sm max-w-none text-gray-800">
            <ReactMarkdown
              components={{
                code({ inline, children, ...props }) {
                  return inline
                    ? <code className="bg-gray-100 text-blue-700 px-1 py-0.5 rounded text-xs font-mono" {...props}>{children}</code>
                    : <pre className="bg-gray-900 text-green-400 rounded-lg p-3 overflow-x-auto text-xs font-mono my-2">
                        <code {...props}>{children}</code>
                      </pre>;
                },
              }}
            >
              {String(content)}
            </ReactMarkdown>
          </div>
        </div>
        {category && (
          <p className="text-xs text-gray-400 mt-1 ml-2"># {category}</p>
        )}
      </div>
    </div>
  );
}

/* ─── 사용자 말풍선 ──────────────────────────────────────────────── */
function UserBubble({ content = '' }) {
  return (
    <div className="flex items-end justify-end space-x-3">
      <div className="max-w-2xl bg-blue-600 text-white rounded-2xl rounded-br-none px-4 py-3 shadow">
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{content}</p>
      </div>
      <div className="flex-shrink-0 w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center shadow">
        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
      </div>
    </div>
  );
}

/* ─── 평가 박스 ──────────────────────────────────────────────────── */
function EvaluationBox({ content }) {
  const [open, setOpen] = useState(true);
  if (!content || typeof content !== 'object') return null;

  const score = typeof content.score === 'number' ? content.score : 0;
  const scoreColor = score >= 80 ? 'text-green-600' : score >= 50 ? 'text-yellow-600' : 'text-red-500';
  const barColor   = score >= 80 ? 'bg-green-500'  : score >= 50 ? 'bg-yellow-400'  : 'bg-red-400';

  return (
    <div className="flex justify-end mr-11">
      <div className="w-full max-w-2xl bg-green-50 border border-green-200 rounded-xl overflow-hidden shadow-sm">
        <button
          onClick={() => setOpen(o => !o)}
          className="w-full flex items-center justify-between px-4 py-2 bg-green-100 hover:bg-green-200 transition-colors text-left"
        >
          <div className="flex items-center space-x-2">
            <svg className="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
            </svg>
            <span className="text-sm font-semibold text-green-800">AI 평가</span>
            <span className={`text-sm font-bold ${scoreColor}`}>{score}점</span>
          </div>
          <svg className={`w-4 h-4 text-green-600 transition-transform ${open ? 'rotate-180' : ''}`}
            fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7"/>
          </svg>
        </button>

        {open && (
          <div className="px-4 py-3 space-y-3">
            <div>
              <div className="flex justify-between text-xs text-gray-500 mb-1"><span>점수</span><span>{score}/100</span></div>
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div className={`h-full ${barColor} rounded-full transition-all duration-500`} style={{ width: `${score}%` }} />
              </div>
            </div>
            {content.feedback && (
              <div>
                <p className="text-xs font-semibold text-green-800 mb-1">피드백</p>
                <p className="text-sm text-gray-700 leading-relaxed">{content.feedback}</p>
              </div>
            )}
            {content.follow_up_question && (
              <div>
                <p className="text-xs font-semibold text-green-800 mb-1">추가 질문</p>
                <p className="text-sm text-gray-600 italic">{content.follow_up_question}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── 메인 컴포넌트 ──────────────────────────────────────────────── */
export default function ChatRoom() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const messagesEndRef = useRef(null);
  const hasInitialized = useRef(false);

  // State – safe defaults (never null)
  const [messages, setMessages]             = useState([]);   // always array
  const [inputValue, setInputValue]         = useState('');
  const [isLoading, setIsLoading]           = useState(false);
  const [sessionData, setSessionData]       = useState(null);
  const [error, setError]                   = useState('');
  const [isInitializing, setIsInitializing] = useState(true); // show spinner until ready

  /* smooth scroll */
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);
  useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

  /* append helper */
  const appendMsg = (msg) => setMessages(prev => [...prev, msg]);

  /* ── 첫 질문 요청 ── */
  const getFirstQuestion = useCallback(async () => {
    try {
      setIsLoading(true);
      const { data } = await axios.post(`${API_BASE_URL}/api/interview/chat`, {
        session_id: parseInt(sessionId, 10)
      });
      if (data?.next_question) {
        appendMsg({
          sender: 'ai',
          content: data.next_question,
          category: data.category ?? '',
          timestamp: new Date().toISOString()
        });
      }
    } catch {
      setError('첫 질문을 가져오지 못했습니다.');
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  /* ── 세션 초기화 (Strict Mode 이중 실행 방지) ── */
  useEffect(() => {
    if (hasInitialized.current) return;
    hasInitialized.current = true;

    const init = async () => {
      try {
        const { data } = await axios.get(`${API_BASE_URL}/api/interview/session/${sessionId}`);

        setSessionData({
          userName: data?.user_name ?? '지원자',
          jobTitle: data?.job_title ?? '면접 세션',
          status:   data?.status   ?? 'unknown'
        });

        // transcript → messages (safe mapping)
        const transcript = Array.isArray(data?.transcript) ? data.transcript : [];
        const formatted = transcript.map(t => ({
          sender:    t?.sender    ?? 'ai',
          content:   t?.content   ?? '',
          timestamp: t?.timestamp ?? new Date().toISOString()
        }));
        setMessages(formatted);

        // 자기소개 질문이 아직 없으면 첫 질문 요청
        const alreadyHasQ = formatted.some(
          m => m.sender === 'ai' && String(m.content).includes('자기소개')
        );
        if (!alreadyHasQ) {
          await getFirstQuestion();
        }
      } catch (err) {
        const status = err?.response?.status;
        if (status === 404) {
          setError('세션을 찾을 수 없습니다. 면접을 새로 시작해 주세요.');
        } else if (!err.response) {
          setError('서버에 연결할 수 없습니다. 백엔드가 실행 중인지 확인해 주세요.');
        } else {
          setError('세션 로딩에 실패했습니다. 잠시 후 다시 시도해 주세요.');
        }
      } finally {
        setIsInitializing(false);
      }
    };

    init();
  }, [sessionId, getFirstQuestion]);

  /* ── 답변 전송 ── */
  const handleSend = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const answer = inputValue.trim();
    setInputValue('');
    setError('');
    appendMsg({ sender: 'human', content: answer, timestamp: new Date().toISOString() });
    setIsLoading(true);

    try {
      const { data } = await axios.post(`${API_BASE_URL}/api/interview/chat`, {
        session_id:  parseInt(sessionId, 10),
        user_answer: answer
      });

      if (data?.evaluation && typeof data.evaluation === 'object') {
        appendMsg({ sender: 'evaluation', content: data.evaluation, timestamp: new Date().toISOString() });
      }
      if (data?.next_question) {
        appendMsg({ sender: 'ai', content: data.next_question, category: data.category ?? '', timestamp: new Date().toISOString() });
      }
    } catch (err) {
      setError(err?.response?.data?.detail ?? '메시지 전송에 실패했습니다. 다시 시도해 주세요.');
    } finally {
      setIsLoading(false);
    }
  };

  /* Enter = 전송, Shift+Enter = 줄바꿈 */
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(e); }
  };

  /* ── 면접 종료 ── */
  const handleEnd = async () => {
    if (!window.confirm('면접을 종료하시겠습니까?')) return;
    try {
      await axios.post(`${API_BASE_URL}/api/interview/session/${sessionId}/end`);
      navigate('/');
    } catch {
      setError('면접 종료에 실패했습니다. 다시 시도해 주세요.');
    }
  };

  /* ── 로딩 화면 ── */
  if (isInitializing) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="relative w-16 h-16 mx-auto">
            <div className="absolute inset-0 rounded-full border-4 border-blue-100" />
            <div className="absolute inset-0 rounded-full border-4 border-blue-600 border-t-transparent animate-spin" />
          </div>
          <p className="text-gray-600 font-medium">면접 로딩 중...</p>
        </div>
      </div>
    );
  }

  /* ── 에러 전용 화면 (세션을 아예 못 가져온 경우) ── */
  if (error && messages.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow p-8 max-w-md text-center space-y-4">
          <div className="text-red-500 text-5xl">⚠️</div>
          <h2 className="text-lg font-bold text-gray-900">오류 발생</h2>
          <p className="text-gray-600 text-sm">{error}</p>
          <button onClick={() => navigate('/')}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm">
            처음으로 돌아가기
          </button>
        </div>
      </div>
    );
  }

  /* ── 메인 레이아웃 ── */
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">

      {/* 헤더 */}
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-gray-900">
              {sessionData?.jobTitle ?? '면접 세션'}
            </h1>
            <p className="text-xs text-gray-500">지원자: {sessionData?.userName ?? '-'}</p>
          </div>
          <button onClick={handleEnd}
            className="flex items-center space-x-1 px-4 py-2 text-sm font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition-colors">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/>
            </svg>
            <span>면접 종료</span>
          </button>
        </div>
      </header>

      {/* 채팅 영역 */}
      <div className="flex-1 overflow-y-auto bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 py-6 space-y-5">

          {messages.map((msg, i) => {
            if (!msg) return null; // null guard
            return (
              <div key={i}>
                {msg.sender === 'ai'         && <AiBubble content={msg.content} category={msg.category} />}
                {msg.sender === 'human'      && <UserBubble content={msg.content} />}
                {msg.sender === 'evaluation' && <EvaluationBox content={msg.content} />}
              </div>
            );
          })}

          {isLoading && <TypingIndicator />}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* 인라인 에러 배너 */}
      {error && messages.length > 0 && (
        <div className="max-w-4xl mx-auto w-full px-4 py-2">
          <div className="flex items-center space-x-2 bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-lg text-sm">
            <svg className="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd"/>
            </svg>
            <span className="flex-1">{error}</span>
            <button onClick={() => setError('')} className="text-red-400 hover:text-red-600">✕</button>
          </div>
        </div>
      )}

      {/* 입력 영역 */}
      <div className="bg-white border-t border-gray-200 shadow-lg">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <form onSubmit={handleSend} className="flex items-end space-x-3">
            <textarea
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="답변을 입력하세요... (Enter: 전송 / Shift+Enter: 줄바꿈)"
              rows={3}
              className="flex-1 resize-none px-4 py-3 bg-white text-gray-900 border border-gray-300 rounded-xl
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent
                         placeholder-gray-400 text-sm leading-relaxed"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !inputValue.trim()}
              className="flex-shrink-0 px-5 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold
                         rounded-xl transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
              </svg>
            </button>
          </form>
          <p className="text-xs text-gray-400 mt-1.5 ml-1">Enter: 전송 · Shift+Enter: 줄바꿈</p>
        </div>
      </div>

    </div>
  );
}
