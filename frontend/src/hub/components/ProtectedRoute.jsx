import { useAuth } from '../../context/AuthContext';
import { Navigate } from 'react-router-dom';

export default function ProtectedRoute({ children }) {
  const { signedIn } = useAuth();
  return signedIn ? children : <Navigate to="/" />;
}
