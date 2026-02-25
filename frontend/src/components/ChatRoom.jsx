import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';

const API_BASE_URL = 'http://localhost:8000';
const VISION_INTERVAL_MS = 3000; // capture every 3 seconds

/* ─── Typing Indicator ──────────────────────────────────────────────── */
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

/* ─── AI Bubble ─────────────────────────────────────────────────────── */
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
        {category && <p className="text-xs text-gray-400 mt-1 ml-2"># {category}</p>}
      </div>
    </div>
  );
}

/* ─── User Bubble ───────────────────────────────────────────────────── */
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

/* ─── Evaluation Box ────────────────────────────────────────────────── */
function EvaluationBox({ content }) {
  const [open, setOpen] = useState(true);
  if (!content || typeof content !== 'object') return null;
  const score = typeof content.score === 'number' ? content.score : 0;
  const scoreColor = score >= 80 ? 'text-green-600' : score >= 50 ? 'text-yellow-600' : 'text-red-500';
  const barColor   = score >= 80 ? 'bg-green-500'  : score >= 50 ? 'bg-yellow-400'  : 'bg-red-400';
  return (
    <div className="flex justify-end mr-11">
      <div className="w-full max-w-2xl bg-green-50 border border-green-200 rounded-xl overflow-hidden shadow-sm">
        <button onClick={() => setOpen(o => !o)}
          className="w-full flex items-center justify-between px-4 py-2 bg-green-100 hover:bg-green-200 transition-colors text-left">
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
            {content.feedback && <div><p className="text-xs font-semibold text-green-800 mb-1">피드백</p><p className="text-sm text-gray-700 leading-relaxed">{content.feedback}</p></div>}
            {content.follow_up_question && <div><p className="text-xs font-semibold text-green-800 mb-1">추가 질문</p><p className="text-sm text-gray-600 italic">{content.follow_up_question}</p></div>}
          </div>
        )}
      </div>
    </div>
  );
}

/* ─── Mic Button (STT) ──────────────────────────────────────────────── */
function MicButton({ onResult, disabled }) {
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef(null);
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return null;

  const startListening = () => {
    if (listening) { recognitionRef.current?.stop(); return; }
    const rec = new SpeechRecognition();
    rec.lang = 'ko-KR';
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.continuous = true;

    rec.onstart = () => setListening(true);
    rec.onend   = () => setListening(false);
    rec.onerror = (e) => {
      if (e.error !== 'no-speech') setListening(false);
    };
    rec.onresult = (e) => {
      let combined = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) combined += e.results[i][0].transcript;
      }
      if (combined.trim()) onResult(combined.trim());
    };
    recognitionRef.current = rec;
    rec.start();
  };

  return (
    <button type="button" onClick={startListening} disabled={disabled}
      title={listening ? '듣는 중... (클릭하여 중지)' : '마이크로 답변하기'}
      className={`flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center transition-all
        ${listening ? 'bg-red-500 hover:bg-red-600 shadow-lg shadow-red-200 animate-pulse' : 'bg-slate-100 hover:bg-slate-200 text-slate-600'}
        disabled:opacity-40 disabled:cursor-not-allowed`}>
      {listening ? (
        <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
          <rect x="2" y="9" width="2" height="6" rx="1"/><rect x="6" y="5" width="2" height="14" rx="1"/>
          <rect x="10" y="3" width="2" height="18" rx="1"/><rect x="14" y="5" width="2" height="14" rx="1"/>
          <rect x="18" y="9" width="2" height="6" rx="1"/>
        </svg>
      ) : (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"/>
        </svg>
      )}
    </button>
  );
}

/* ─── Main Component ─────────────────────────────────────────────────── */
export default function ChatRoom() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const messagesEndRef  = useRef(null);
  const hasInitialized  = useRef(false);
  const audioRef        = useRef(null);
  const canvasRef        = useRef(null);
  const visionTimerRef   = useRef(null);
  const mediaStreamRef   = useRef(null);  // always holds the live MediaStream

  // Ref-callback: fires the moment React attaches the <video> DOM node.
  // This avoids the race where cameraStream state updates before the element exists.
  const userVideoRef = useCallback((videoEl) => {
    if (!videoEl) return;
    if (mediaStreamRef.current) {
      videoEl.srcObject = mediaStreamRef.current;
      videoEl.play().catch(() => {});
    }
  }, []);

  const [messages, setMessages]             = useState([]);
  const [inputValue, setInputValue]         = useState('');
  const [isLoading, setIsLoading]           = useState(false);
  const [sessionData, setSessionData]       = useState(null);
  const [error, setError]                   = useState('');
  const [isInitializing, setIsInitializing] = useState(true);
  const [isCompleted, setIsCompleted]       = useState(false);
  const [ttsEnabled, setTtsEnabled]         = useState(true);
  const [isPlaying, setIsPlaying]           = useState(false); // TTS currently playing
  const [isStarted, setIsStarted]           = useState(false); // Forces initial user interaction
  const [cameraActive, setCameraActive]     = useState(false);
  const [cameraStream, setCameraStream]     = useState(null);
  const [emotionStats, setEmotionStats]     = useState({}); // { emotion: count } tally
  const [visionAnalyzing, setVisionAnalyzing] = useState(false);
  const [faceError, setFaceError]           = useState(false); // no face detected
  const [totalSeconds, setTotalSeconds]     = useState(0);    // global interview timer
  const [turnStartTime, setTurnStartTime]   = useState(() => Date.now()); // per-turn answer timer

  /* smooth scroll */
  const scrollToBottom = useCallback(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, []);
  useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

  /* ── Global interview timer (MM:SS) — stops when interview completes ───── */
  useEffect(() => {
    if (isCompleted) return;               // don't start a new interval after end
    const t = setInterval(() => setTotalSeconds(s => s + 1), 1000);
    return () => clearInterval(t);         // cleanup on unmount OR when isCompleted flips
  }, [isCompleted]);
  const formatTime = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

  /* ── Per-turn timer: reset when AI stops speaking ───────────────────────── */
  useEffect(() => {
    if (!isPlaying) setTurnStartTime(Date.now());
  }, [isPlaying]);


  const appendMsg = (msg) => setMessages(prev => [...prev, msg]);

  /* ── TTS auto-play (tracks isPlaying for avatar animation) ── */
  const playAudio = useCallback((audioUrl) => {
    if (!audioUrl || !ttsEnabled) return;
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
    const audio = new Audio(`${API_BASE_URL}${audioUrl}`);
    audioRef.current = audio;
    setIsPlaying(true);
    audio.onended = () => setIsPlaying(false);
    audio.onerror = () => setIsPlaying(false);
    if (isStarted) {
      audio.play().catch(err => {
        console.warn('[TTS] play failed:', err);
        setIsPlaying(false);
      });
    }
  }, [ttsEnabled, isStarted]);

  /* ── Issue 2: Handle TTS race condition ── */
  useEffect(() => {
    if (!isStarted) return;
    
    // Play the first AI message if it just arrived and is the first message
    if (messages?.length === 1 && messages[0].sender === 'ai') {
      const firstTx = messages[0];
      
      // Fallback to deterministic static path if audio_url is missing
      const audioUrl = firstTx.audio_url || firstTx.content?.audio_url || `/uploads/audio/session_${sessionId}_turn_0.mp3`;
      
      if (audioUrl) {
        const cleanUrl = audioUrl.startsWith('/') ? audioUrl : `/${audioUrl}`;
        const audio = new Audio(`${API_BASE_URL}${cleanUrl}`);
        setIsPlaying(true);
        audio.onended = () => setIsPlaying(false);
        audio.onerror = () => setIsPlaying(false);
        audio.play().catch(e => {
          console.error("Audio play failed on start:", e);
          setIsPlaying(false);
        });
      }
    }
  }, [messages, isStarted, sessionId]);

  /* ── Frame capture function (standalone, no React state deps) ─── */
  const captureAndSendFrame = useCallback(async () => {
    const videoEl = document.getElementById('user-webcam-video');
    const canvas  = canvasRef.current;
    if (!canvas || !videoEl || videoEl.readyState < 2 || videoEl.videoWidth === 0) {
      console.log('[VISION] Frame skip — video not ready (readyState=', videoEl?.readyState, videoEl?.videoWidth, ')');
      return;
    }
    const ctx = canvas.getContext('2d');
    canvas.width  = videoEl.videoWidth;
    canvas.height = videoEl.videoHeight;
    ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);
    const b64 = canvas.toDataURL('image/jpeg', 0.75);
    console.log('[VISION] Sending frame', canvas.width, 'x', canvas.height);
    setVisionAnalyzing(true);
    try {
      const { data } = await axios.post(`${API_BASE_URL}/api/interview/vision`, { image_b64: b64 });
      console.log('[VISION] Response:', data?.status, data?.dominant_emotion);
      if (data?.status === 'no_face_detected') {
        setFaceError(true);
      } else if (data?.dominant_emotion) {
        setFaceError(false);
        setEmotionStats(prev => ({ ...prev, [data.dominant_emotion]: (prev[data.dominant_emotion] || 0) + 1 }));
      }
    } catch (err) {
      console.error('[VISION] POST error:', err?.response?.status, err?.message);
    } finally { setVisionAnalyzing(false); }
  }, []);

  /* ── Webcam startup — vision loop started INSIDE getUserMedia resolution ── */
  useEffect(() => {
    let stream;
    const startCamera = async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia(
          { video: { width: 320, height: 240, facingMode: 'user' }, audio: false }
        );

        // 1. Attach stream to the video DOM element immediately
        const vid = document.getElementById('user-webcam-video');
        if (vid) { vid.srcObject = stream; vid.play().catch(() => {}); }

        // 2. Keep refs/state in sync for UI
        mediaStreamRef.current = stream;
        setCameraStream(stream);
        setCameraActive(true);

        // 3. ✅ Start vision interval DIRECTLY here — bypasses all React state timing
        if (!visionTimerRef.current) {
          console.log('✅ VISION LOOP EXPLICITLY STARTED');
          visionTimerRef.current = setInterval(() => { captureAndSendFrame(); }, VISION_INTERVAL_MS);
        }
      } catch (e) { console.warn('[VISION] Camera unavailable:', e.message); }
    };
    startCamera();
    return () => {
      stream?.getTracks().forEach(t => t.stop());
      mediaStreamRef.current = null;
      if (visionTimerRef.current) { clearInterval(visionTimerRef.current); visionTimerRef.current = null; }
    };
  }, [captureAndSendFrame]);

  /* ── Re-attach stream on hot-reload / state change (belt-and-suspenders) ── */
  useEffect(() => {
    const vid = document.getElementById('user-webcam-video');
    if (!vid || !cameraStream) return;
    if (vid.srcObject !== cameraStream) {
      vid.srcObject = cameraStream;
      vid.play().catch(() => {});
    }
  }, [cameraStream]);


  /* ── First question ─────────────────────────────────────────── */
  const getFirstQuestion = useCallback(async () => {
    try {
      setIsLoading(true);
      const { data } = await axios.post(`${API_BASE_URL}/api/interview/chat`, { session_id: parseInt(sessionId, 10) });
      if (data?.next_question) {
        appendMsg({ sender: 'ai', content: data.next_question, category: data.category ?? '', timestamp: new Date().toISOString() });
        playAudio(data.audio_url);
      }
    } catch { setError('첫 질문을 가져오지 못했습니다.'); }
    finally  { setIsLoading(false); }
  }, [sessionId, playAudio]);

  /* ── Load session & history ─────────────────────────────────── */
  useEffect(() => {
    if (hasInitialized.current) return;
    hasInitialized.current = true;
    const init = async () => {
      try {
        const { data: sess } = await axios.get(`${API_BASE_URL}/api/interview/session/${sessionId}`);
        setSessionData(sess);

        // Use transcript embedded in session response (avoids separate round-trip).
        // Fall back to the /transcript endpoint for older API versions.
        let transcriptItems = [];
        if (Array.isArray(sess.transcript)) {
          transcriptItems = sess.transcript;
        } else {
          try {
            const { data: txData } = await axios.get(`${API_BASE_URL}/api/interview/session/${sessionId}/transcript`);
            transcriptItems = Array.isArray(txData) ? txData : [];
          } catch (txErr) {
            // 404 = brand-new session with no messages yet → treat as empty history
            if (txErr?.response?.status !== 404) {
              console.warn('[INIT] transcript fetch failed:', txErr?.message);
            }
            transcriptItems = [];
          }
        }

        const formatted = transcriptItems.map(t => ({ sender: t?.sender ?? 'ai', content: t?.content ?? '', timestamp: t?.timestamp ?? new Date().toISOString() }));
        setMessages(formatted);

        // Auto-play greeting TTS if InterviewSetup stored an audio_url for this session
        const greetingAudioUrl = sessionStorage.getItem(`greeting_audio_${sessionId}`);
        if (greetingAudioUrl) {
          sessionStorage.removeItem(`greeting_audio_${sessionId}`);
          playAudio(greetingAudioUrl);
        }

        const alreadyHasQ = formatted.some(m => m.sender === 'ai' &&
          (String(m.content).includes('자기소개') || String(m.content).includes('자신을 소개')));
        if (!alreadyHasQ) await getFirstQuestion();
      } catch (err) {
        const status = err?.response?.status;
        if (status === 404)         setError('세션을 찾을 수 없습니다. 면접을 새로 시작해 주세요.');
        else if (!err.response)     setError('서버에 연결할 수 없습니다. 백엔드가 실행 중인지 확인해 주세요.');
        else                        setError('세션 로딩에 실패했습니다. 잠시 후 다시 시도해 주세요.');
      } finally { setIsInitializing(false); }
    };
    init();
  }, [sessionId, getFirstQuestion]);

  /* ── Initial-message TTS: load greeting audio without auto-playing ── */
  const initialAudioFiredRef = useRef(false);
  useEffect(() => {
    // Only fire once, and only when messages are freshly loaded (not on every render)
    if (initialAudioFiredRef.current || messages.length === 0) return;
    // Check if this looks like a session that was resumed (already has user replies)
    const hasUserMsg = messages.some(m => m.sender === 'human');
    if (hasUserMsg) { 
      initialAudioFiredRef.current = true; 
      setIsStarted(true); // Auto-start if it's a resumed session
      return; 
    }
    // Find the first AI message that has an audio_url via sessionStorage key set by InterviewSetup
    const greetingAudio = sessionStorage.getItem(`greeting_audio_${sessionId}`);
    if (greetingAudio) {
      initialAudioFiredRef.current = true;
      sessionStorage.removeItem(`greeting_audio_${sessionId}`);
      if (!audioRef.current) {
        audioRef.current = new Audio();
      }
      audioRef.current.src = `${API_BASE_URL}${greetingAudio}`;
      audioRef.current.onended = () => setIsPlaying(false);
      audioRef.current.onerror = () => setIsPlaying(false);
    } else if (messages.length === 1 && messages[0].sender === 'ai' && messages[0].audio_url) {
      initialAudioFiredRef.current = true;
      if (!audioRef.current) {
        audioRef.current = new Audio();
      }
      audioRef.current.src = `${API_BASE_URL}${messages[0].audio_url}`;
      audioRef.current.onended = () => setIsPlaying(false);
      audioRef.current.onerror = () => setIsPlaying(false);
    }
  }, [messages, sessionId]);



  /* ── Send answer ────────────────────────────────────────────── */
  const handleSend = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || isLoading) return;
    const answer = inputValue.trim();
    setInputValue(''); setError('');
    appendMsg({ sender: 'human', content: answer, timestamp: new Date().toISOString() });
    setIsLoading(true);

    // Send raw emotion counts — backend formula works directly with counts
    const total_samples = Object.values(emotionStats).reduce((s, c) => s + c, 0);
    const vision_data = total_samples > 0 ? { ...emotionStats } : null;
    const answer_time = Math.floor((Date.now() - turnStartTime) / 1000);

    try {
      const { data } = await axios.post(`${API_BASE_URL}/api/interview/chat`, {
        session_id:  parseInt(sessionId, 10),
        user_answer: answer,
        vision_data,
        answer_time,
        total_time:  totalSeconds,   // always send; backend stores in details on final turn
      });
      // Reset turn timer for next question
      setTurnStartTime(Date.now());
      if (data?.evaluation && typeof data.evaluation === 'object') {
        appendMsg({ sender: 'evaluation', content: data.evaluation, timestamp: new Date().toISOString() });
      }
      if (data?.next_question) {
        appendMsg({ sender: 'ai', content: data.next_question, category: data.category ?? '', timestamp: new Date().toISOString() });
        playAudio(data.audio_url);
      }
      if ((data?.category?.includes('면접 종료') || data?.category?.includes('CLOSING'))
          && data?.next_question?.includes('종료') && !data?.evaluation) {
        // Stop vision loop immediately — interview is done
        if (visionTimerRef.current) {
          clearInterval(visionTimerRef.current);
          visionTimerRef.current = null;
          console.log('🛑 Vision loop stopped on interview end.');
        }
        setIsCompleted(true);
      }
    } catch (err) {
      setError(err?.response?.data?.detail ?? '메시지 전송에 실패했습니다. 다시 시도해 주세요.');
    } finally { setIsLoading(false); }
  };

  const handleKeyDown = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(e); } };
  const handleSpeechResult = (t) => setInputValue(prev => prev ? `${prev} ${t}` : t);

  const handleEnd = async () => {
    if (!window.confirm('면접을 종료하시겠습니까?')) return;
    // Stop vision loop immediately
    if (visionTimerRef.current) {
      clearInterval(visionTimerRef.current);
      visionTimerRef.current = null;
      console.log('🛑 Vision loop stopped on handleEnd.');
    }
    try { await axios.post(`${API_BASE_URL}/api/interview/session/${sessionId}/end`); navigate('/'); }
    catch { setError('면접 종료에 실패했습니다.'); }
  };

  /* ── Loading & Error screens ────────────────────────────────── */
  if (isInitializing) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="text-center space-y-4">
        <div className="relative w-16 h-16 mx-auto">
          <div className="absolute inset-0 rounded-full border-4 border-blue-100" />
          <div className="absolute inset-0 rounded-full border-4 border-blue-600 border-t-transparent animate-spin" />
        </div>
        <p className="text-gray-600 font-medium">면접 로딩 중...</p>
      </div>
    </div>
  );

  if (error && messages.length === 0) return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow p-8 max-w-md text-center space-y-4">
        <div className="text-red-500 text-5xl">⚠️</div>
        <h2 className="text-lg font-bold text-gray-900">오류 발생</h2>
        <p className="text-gray-600 text-sm">{error}</p>
        <button onClick={() => navigate('/')} className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm">처음으로 돌아가기</button>
      </div>
    </div>
  );

  /* ── Main render: split-screen ──────────────────────────────── */
  return (
    <div className="flex h-screen bg-slate-900 md:flex-row flex-col overflow-hidden relative">

      {/* Full screen interaction overlay */}
      {!isStarted && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-gray-900/90 backdrop-blur-sm">
          <button 
            onClick={() => setIsStarted(true)}
            className="px-8 py-4 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xl rounded-full shadow-lg animate-pulse"
          >
            ▶️ 면접 시작하기
          </button>
        </div>
      )}

      {/* Hidden canvas for vision capture */}
      <canvas ref={canvasRef} className="hidden" />

      {/* ══ LEFT PANE — AI Avatar + User Webcam (40%) ══ */}
      <div className="flex flex-col items-center justify-between bg-gradient-to-b from-slate-800 to-slate-900 md:w-2/5 p-6 border-r border-slate-700/50">

        {/* Session info + global timer */}
        <div className="w-full text-center mb-4">
          <p className="text-slate-400 text-xs font-medium uppercase tracking-widest">AI 면접관</p>
          <h2 className="text-white font-bold text-sm mt-1">{sessionData?.jobTitle ?? '면접 세션'}</h2>
          <p className="text-slate-500 text-xs mt-1 bg-slate-800/50 inline-block px-3 py-1 rounded-full border border-slate-700/50">
            지원자: {(function() { try { return JSON.parse(localStorage.getItem('auth_user'))?.name; } catch { return null; } })() || sessionData?.userName || '익명'}
          </p>
          {/* Global timer badge */}
          <div className="inline-flex items-center gap-1.5 mt-2 px-3 py-1 bg-slate-700/60 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" />
            <span className="text-red-300 font-mono text-xs font-semibold tracking-wider">{formatTime(totalSeconds)}</span>
            <span className="text-slate-500 text-xs">경과</span>
          </div>
        </div>

        {/* AI Avatar */}
        <div className="flex flex-col items-center space-y-4 flex-shrink-0">
          <div className={`relative rounded-full p-1 transition-all duration-300 ${
            isPlaying
              ? 'ring-4 ring-blue-400 ring-offset-4 ring-offset-slate-800 shadow-[0_0_30px_rgba(59,130,246,0.6)] animate-pulse'
              : 'ring-2 ring-slate-600 ring-offset-2 ring-offset-slate-800'
          }`}>
            <div className="w-32 h-32 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-2xl">
              <svg className="w-16 h-16 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
              </svg>
            </div>
            {isPlaying && (
              <div className="absolute -bottom-1 -right-1 bg-blue-500 rounded-full w-6 h-6 flex items-center justify-center shadow">
                <svg className="w-3.5 h-3.5 text-white" fill="currentColor" viewBox="0 0 24 24">
                  <rect x="2" y="9" width="2" height="6" rx="1"/><rect x="6" y="5" width="2" height="14" rx="1"/>
                  <rect x="10" y="3" width="2" height="18" rx="1"/><rect x="14" y="5" width="2" height="14" rx="1"/>
                  <rect x="18" y="9" width="2" height="6" rx="1"/>
                </svg>
              </div>
            )}
          </div>
          <div className="text-center">
            <p className="text-white font-semibold text-sm">AI 면접관</p>
            <p className={`text-xs mt-0.5 ${isPlaying ? 'text-blue-400 animate-pulse' : 'text-slate-500'}`}>
              {isPlaying ? '🔊 답변 읽는 중...' : '● 대기 중'}
            </p>
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-full max-w-xs space-y-1.5 my-4">
          {(() => {
            const TOTAL_TURNS = 7;
            const aiTurn = messages.filter(m => m.sender === 'ai').length;
            const pct = Math.min(Math.round((aiTurn / TOTAL_TURNS) * 100), 100);
            const barColor = pct >= 100 ? 'bg-green-500' : pct >= 70 ? 'bg-yellow-400' : 'bg-blue-500';
            return (
              <>
                <div className="flex justify-between text-xs text-slate-400">
                  <span>진행도: {Math.min(aiTurn, TOTAL_TURNS)}/{TOTAL_TURNS}</span>
                  <span>{pct}%</span>
                </div>
                <div className="h-1.5 w-full bg-slate-700 rounded-full overflow-hidden">
                  <div className={`h-full ${barColor} rounded-full transition-all duration-700`} style={{ width: `${pct}%` }} />
                </div>
              </>
            );
          })()}
        </div>

        {/* User webcam */}
        <div className="w-full flex-1 flex flex-col items-center min-h-0">
          {/* Fixed-height emotion stats row — reserves space so layout never shifts */}
          <div className="h-8 flex items-center justify-start text-sm text-gray-300 font-mono tabular-nums overflow-hidden">
            {Object.keys(emotionStats).length > 0
              ? Object.entries(emotionStats)
                  .sort((a, b) => b[1] - a[1])
                  .slice(0, 4)
                  .map(([em, cnt]) => `${em} ${cnt}`)
                  .join(' | ')
              : <span className="text-slate-600 text-xs">대기 중...​</span>
            }
          </div>

          {/* Static vision status badge — never toggles so layout stays stable */}
          {cameraActive && (
            <div className="flex items-center space-x-1.5 text-xs text-red-400 mb-1">
              <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
              <span>실시간 비전 분석 작동 중</span>
            </div>
          )}
          <div className={`relative w-full rounded-xl overflow-hidden border-2 transition-colors bg-slate-900 ${
            cameraActive ? 'border-green-500/60' : 'border-slate-700'
          }`} style={{ height: '38vh', minHeight: '200px', maxHeight: '340px' }}>
            <video
              id="user-webcam-video"
              ref={userVideoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-contain"
              style={{ transform: 'scaleX(-1)' }}
            />
            {/* No-face detected overlay */}
            {faceError && cameraActive && (
              <div className="absolute inset-0 bg-black/75 flex flex-col items-center justify-center z-20 rounded-xl">
                <span className="text-3xl mb-2">👤❌</span>
                <p className="text-white text-xs text-center px-4 leading-relaxed">
                  카메라에 얼굴 인식이<br/>제대로 이루어지지 않고 있습니다.
                </p>
              </div>
            )}
            {!cameraActive && (
              <div className="absolute inset-0 bg-slate-800 flex flex-col items-center justify-center">
                <svg className="w-8 h-8 text-slate-600 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M15 10l4.553-2.069A1 1 0 0121 8.847v6.306a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                </svg>
                <span className="text-slate-500 text-xs">카메라 꺼짐</span>
              </div>
            )}
            <div className={`absolute top-2 left-2 flex items-center space-x-1 px-2 py-0.5 rounded-full text-xs font-semibold ${
              cameraActive ? 'bg-green-500/80 text-white' : 'bg-slate-700/80 text-slate-400'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${cameraActive ? 'bg-white animate-pulse' : 'bg-slate-500'}`} />
              <span>{cameraActive ? 'LIVE' : 'OFF'}</span>
            </div>

            {Object.values(emotionStats).reduce((a, b) => a + b, 0) > 0 && (
              <div className="absolute bottom-2 right-2 text-xs bg-black/50 text-slate-300 px-1.5 py-0.5 rounded">
                📷 {Object.values(emotionStats).reduce((a, b) => a + b, 0)}샘플
              </div>
            )}
          </div>
          <p className="text-slate-500 text-xs mt-1.5">나의 화면</p>
        </div>

        {/* Controls */}
        <div className="flex items-center space-x-2 mt-3">
          <button
            onClick={() => { if (ttsEnabled && audioRef.current) { audioRef.current.pause(); audioRef.current = null; setIsPlaying(false); } setTtsEnabled(v => !v); }}
            title={ttsEnabled ? '음성 끄기' : '음성 켜기'}
            className={`w-9 h-9 rounded-lg flex items-center justify-center transition-colors ${ttsEnabled ? 'bg-blue-500/20 text-blue-400 hover:bg-blue-500/30' : 'bg-slate-700 text-slate-500 hover:bg-slate-600'}`}>
            {ttsEnabled ? (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072M19.07 4.93a10 10 0 010 14.14M12 6v12M9 9l-3 3H3v0h3l3 3"/>
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"/>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2"/>
              </svg>
            )}
          </button>
          <button onClick={handleEnd}
            className="flex items-center space-x-1 px-3 py-2 text-xs font-medium text-red-400 border border-red-800/60 rounded-lg hover:bg-red-900/30 transition-colors">
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12"/>
            </svg>
            <span>면접 종료</span>
          </button>
        </div>
      </div>

      {/* ══ RIGHT PANE — Chat UI (60%) ══ */}
      <div className="flex flex-col flex-1 md:w-3/5 bg-gray-50 min-h-0 overflow-hidden">

        {/* Right header */}
        <div className="bg-white border-b border-gray-200 px-5 py-3 flex-shrink-0">
          <p className="text-sm font-semibold text-gray-800">{sessionData?.jobTitle ?? '면접'} — 대화</p>
          <p className="text-xs text-gray-400">답변을 입력하거나 마이크 버튼을 누르세요</p>
        </div>

        {/* Chat messages */}
        <div className="flex-1 overflow-y-auto">
          <div className="px-5 py-5 space-y-5">
            {messages.map((msg, i) => {
              if (!msg) return null;
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

        {/* Error banner */}
        {error && messages.length > 0 && (
          <div className="px-5 py-2 flex-shrink-0">
            <div className="flex items-center space-x-2 bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-lg text-sm">
              <span className="flex-1">{error}</span>
              <button onClick={() => setError('')} className="text-red-400 hover:text-red-600">✕</button>
            </div>
          </div>
        )}

        {/* Input area */}
        <div className="flex-shrink-0 bg-white border-t border-gray-200">
          {isCompleted ? (
            <div className="bg-green-50 px-5 py-5 text-center space-y-3">
              <p className="text-green-700 font-semibold">🎉 면접이 완료되었습니다. 수고하셨습니다!</p>
              <p className="text-xs text-gray-400">AI가 결과를 분석 중입니다. 리포트 생성까지 최대 1분 소요될 수 있습니다.</p>
              <div className="flex justify-center gap-3 pt-1">
                <button onClick={() => navigate(`/report/${sessionId}`)}
                  className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors shadow">
                  📊 결과 리포트 보기
                </button>
                <button onClick={() => navigate('/')}
                  className="px-5 py-2.5 border border-gray-300 text-gray-600 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors">
                  처음으로 돌아가기
                </button>
              </div>
            </div>
          ) : (
            <div className="px-4 py-3">
              <form onSubmit={handleSend} className="flex items-end space-x-2">
                <MicButton onResult={handleSpeechResult} disabled={isLoading} />
                <textarea
                  value={inputValue}
                  onChange={e => setInputValue(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="답변을 입력하거나 마이크를 사용하세요... (Enter: 전송 / Shift+Enter: 줄바꿈)"
                  rows={3}
                  className="flex-1 resize-none px-4 py-3 bg-white text-gray-900 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder-gray-400 text-sm leading-relaxed"
                  disabled={isLoading}
                />
                <button type="submit" disabled={isLoading || !inputValue.trim()}
                  className="flex-shrink-0 px-5 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"/>
                  </svg>
                </button>
              </form>
              <div className="flex items-center justify-between mt-1.5 ml-1">
                <p className="text-xs text-gray-400">Enter: 전송 · Shift+Enter: 줄바꿈</p>
                <div className="flex items-center space-x-2 text-xs text-gray-400">
                  {cameraActive && <span>📷 {Object.values(emotionStats || {}).reduce((a, b) => a + b, 0)}개 감정 분석됨</span>}
                  {(window.SpeechRecognition || window.webkitSpeechRecognition) && <span>🎤 음성 입력 가능</span>}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
