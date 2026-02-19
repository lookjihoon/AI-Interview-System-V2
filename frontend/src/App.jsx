import { BrowserRouter, Routes, Route } from 'react-router-dom';
import InterviewSetup from './components/InterviewSetup';
import ChatRoom from './components/ChatRoom';
import Report from './components/Report';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<InterviewSetup />} />
        <Route path="/interview/:sessionId" element={<ChatRoom />} />
        <Route path="/report/:sessionId" element={<Report />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
