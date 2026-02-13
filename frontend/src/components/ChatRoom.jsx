import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export default function ChatRoom() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const messagesEndRef = useRef(null);
  
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionData, setSessionData] = useState(null);
  const [error, setError] = useState('');
  const [isInitializing, setIsInitializing] = useState(true);
  const hasInitialized = useRef(false);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load session data and transcript
  useEffect(() => {
    // Prevent double execution in React Strict Mode
    if (hasInitialized.current) return;
    hasInitialized.current = true;

    const loadSession = async () => {
      try {
        const response = await axios.get(`${API_BASE_URL}/api/interview/session/${sessionId}`);
        const data = response.data;
        
        setSessionData({
          userName: data.user_name,
          jobTitle: data.job_title,
          status: data.status
        });

        // Convert transcript to messages format
        const formattedMessages = data.transcript.map(item => ({
          sender: item.sender,
          content: item.content,
          timestamp: item.timestamp
        }));

        setMessages(formattedMessages);

        // If no questions asked yet (only greeting), request first question
        const aiMessages = formattedMessages.filter(msg => msg.sender === 'ai');
        const hasQuestions = aiMessages.length > 1; // More than just the greeting

        if (!hasQuestions) {
          await getFirstQuestion();
        }

        setIsInitializing(false);
      } catch (err) {
        console.error('Error loading session:', err);
        setError('Failed to load interview session. Please try again.');
        setIsInitializing(false);
      }
    };

    loadSession();
  }, []); // Empty dependency array - only run once

  // Get first question
  const getFirstQuestion = async () => {
    try {
      setIsLoading(true);
      const response = await axios.post(`${API_BASE_URL}/api/interview/chat`, {
        session_id: parseInt(sessionId)
      });

      const { next_question, category } = response.data;
      
      setMessages(prev => [...prev, {
        sender: 'ai',
        content: next_question,
        category: category,
        timestamp: new Date().toISOString()
      }]);
    } catch (err) {
      console.error('Error getting first question:', err);
      setError('Failed to get first question.');
    } finally {
      setIsLoading(false);
    }
  };

  // Send message
  const handleSend = async (e) => {
    e.preventDefault();
    
    if (!inputValue.trim() || isLoading) return;

    const userMessage = inputValue.trim();
    setInputValue('');

    // Add user message to UI immediately
    setMessages(prev => [...prev, {
      sender: 'human',
      content: userMessage,
      timestamp: new Date().toISOString()
    }]);

    setIsLoading(true);
    setError('');

    try {
      const response = await axios.post(`${API_BASE_URL}/api/interview/chat`, {
        session_id: parseInt(sessionId),
        user_answer: userMessage
      });

      const { evaluation, next_question, category } = response.data;

      // Add evaluation if present
      if (evaluation) {
        setMessages(prev => [...prev, {
          sender: 'evaluation',
          content: evaluation,
          timestamp: new Date().toISOString()
        }]);
      }

      // Add AI's next question
      setMessages(prev => [...prev, {
        sender: 'ai',
        content: next_question,
        category: category,
        timestamp: new Date().toISOString()
      }]);

    } catch (err) {
      console.error('Error sending message:', err);
      setError(err.response?.data?.detail || 'Failed to send message. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // End interview
  const handleEndInterview = async () => {
    if (!window.confirm('Are you sure you want to end this interview?')) return;

    try {
      await axios.post(`${API_BASE_URL}/api/interview/session/${sessionId}/end`);
      navigate('/');
    } catch (err) {
      console.error('Error ending interview:', err);
      setError('Failed to end interview.');
    }
  };

  if (isInitializing) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading interview session...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                {sessionData?.jobTitle || 'Interview Session'}
              </h1>
              <p className="text-sm text-gray-600">
                Candidate: {sessionData?.userName || 'Loading...'}
              </p>
            </div>
            <button
              onClick={handleEndInterview}
              className="px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            >
              End Interview
            </button>
          </div>
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-4 py-6 space-y-4">
          {messages.map((message, index) => (
            <div key={index}>
              {message.sender === 'ai' && (
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <div className="flex-1">
                    <div className="bg-gray-100 rounded-2xl rounded-tl-none px-4 py-3 max-w-3xl">
                      <p className="text-gray-800 whitespace-pre-wrap">{message.content}</p>
                    </div>
                    {message.category && (
                      <p className="text-xs text-gray-500 mt-1 ml-2">
                        Category: {message.category}
                      </p>
                    )}
                  </div>
                </div>
              )}

              {message.sender === 'human' && (
                <div className="flex items-start space-x-3 justify-end">
                  <div className="flex-1 flex justify-end">
                    <div className="bg-blue-600 rounded-2xl rounded-tr-none px-4 py-3 max-w-3xl">
                      <p className="text-white whitespace-pre-wrap">{message.content}</p>
                    </div>
                  </div>
                  <div className="flex-shrink-0 w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                  </div>
                </div>
              )}

              {message.sender === 'evaluation' && (
                <div className="flex justify-end mb-4">
                  <div className="max-w-3xl w-full bg-green-50 border border-green-200 rounded-lg p-4 mr-11">
                    <div className="flex items-center mb-2">
                      <svg className="w-5 h-5 text-green-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <h4 className="font-semibold text-green-900">Evaluation</h4>
                    </div>
                    <div className="space-y-2">
                      <div className="flex items-center">
                        <span className="text-sm font-medium text-green-800 mr-2">Score:</span>
                        <span className="text-lg font-bold text-green-600">
                          {message.content.score}/100
                        </span>
                      </div>
                      <div>
                        <span className="text-sm font-medium text-green-800 block mb-1">Feedback:</span>
                        <p className="text-sm text-green-700">{message.content.feedback}</p>
                      </div>
                      {message.content.follow_up_question && (
                        <div>
                          <span className="text-sm font-medium text-green-800 block mb-1">Follow-up:</span>
                          <p className="text-sm text-green-700 italic">{message.content.follow_up_question}</p>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0 w-8 h-8 bg-gray-600 rounded-full flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <div className="bg-gray-100 rounded-2xl rounded-tl-none px-4 py-3">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="max-w-4xl mx-auto px-4 py-2">
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-lg text-sm">
            {error}
          </div>
        </div>
      )}

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 shadow-lg">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <form onSubmit={handleSend} className="flex space-x-4">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Type your answer here..."
              className="flex-1 px-4 py-3 bg-white text-gray-900 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder-gray-400"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !inputValue.trim()}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Sending...' : 'Send'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
