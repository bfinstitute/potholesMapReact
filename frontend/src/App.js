import { Routes, Route, Navigate } from 'react-router-dom';
import Home from './hub/components/Home';
import ChatPage from './pages/ChatPage';
import UploadPage from './hub/components/UploadPage';
import SubmissionsPage from './hub/components/SubmissionsPage';
import CSVEditor from './hub/components/CSVEditor';
import SuccessPage from './hub/components/SuccessPage';
import ProtectedRoute from './hub/components/ProtectedRoute';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route
        path="/chat"
        element={
          <ProtectedRoute>
            <ChatPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/sources"
        element={
          <ProtectedRoute>
            <UploadPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/queue"
        element={
          <ProtectedRoute>
            <SubmissionsPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/edit"
        element={
          <ProtectedRoute>
            <CSVEditor />
          </ProtectedRoute>
        }
      />
      <Route
        path="/success"
        element={
          <ProtectedRoute>
            <SuccessPage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
