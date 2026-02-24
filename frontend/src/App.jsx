import { BrowserRouter, Routes, Route } from 'react-router-dom';
import InterviewSetup from './components/InterviewSetup';
import ChatRoom from './components/ChatRoom';
import Report from './components/Report';
import AdminDashboard from './components/AdminDashboard';
import MyPage from './components/MyPage';
import Login from './components/Login';
import Register from './components/Register';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"                    element={<InterviewSetup />} />
        <Route path="/interview/:sessionId" element={<ChatRoom />} />
        <Route path="/report/:sessionId"    element={<Report />} />
        <Route path="/admin"               element={<AdminDashboard />} />
        <Route path="/mypage"              element={<MyPage />} />
        <Route path="/login"              element={<Login />} />
        <Route path="/register"           element={<Register />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
