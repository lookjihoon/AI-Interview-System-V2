import { BrowserRouter, Routes, Route } from 'react-router-dom';
import InterviewSetup from './components/InterviewSetup';
import ChatRoom from './components/ChatRoom';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<InterviewSetup />} />
        <Route path="/interview/:sessionId" element={<ChatRoom />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
