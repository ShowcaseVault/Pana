import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { API_ROUTES } from '../api/routes';
import { useAuth } from '../context/useAuth';

const Login = () => {
  const navigate = useNavigate();
  const { user, loading } = useAuth();

  useEffect(() => {
    if (!loading && user) {
      navigate('/home');
    }
  }, [user, loading, navigate]);

  const handleGoogleClick = () => {
    // Redirect to backend endpoint which handles the actual Google OAuth redirection
    // and subsequent callback/session management.
    const baseUrl = import.meta.env.VITE_BASE_API_URL || 'http://localhost:8000';
    window.location.href = `${baseUrl}${API_ROUTES.AUTH.GOOGLE_LOGIN}`;
  };

  // If loading, show nothing or spinner. If user exists, we are redirecting.
  // We only show login UI if not loading and no user.
  if (loading || user) {
    return null; // Or a spinner
  }

  return (
    <div className="login-container">
      <h1>Welcome to Pana</h1>
      <p>Please sign in to continue</p>
      <button onClick={handleGoogleClick} style={{ padding: '10px 20px', cursor: 'pointer' }}>
        Sign in with Google
      </button>
    </div>
  );
};

export default Login;
