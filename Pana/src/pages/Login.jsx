import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { API_ROUTES } from '../api/routes';
import { useAuth } from '../context/useAuth';
import '../styles/themes.css';

const Login = () => {
  const navigate = useNavigate();
  const { user, loading } = useAuth();

  useEffect(() => {
    if (!loading && user) {
      navigate('/home');
    }
  }, [user, loading, navigate]);

  const handleGoogleClick = () => {
    const baseUrl = import.meta.env.VITE_BASE_API_URL || 'http://localhost:8000';
    window.location.href = `${baseUrl}${API_ROUTES.AUTH.GOOGLE_LOGIN}`;
  };

  if (loading || user) {
    return (
      <div className="login-loading">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  return (
    <div className="login-page">
      {/* Left Panel - Branding */}
      <div className="login-left">
        <div className="brand-content">
          <h1 className="brand-logo">Pana</h1>
          <p className="brand-tagline">Your personal voice companion</p>
          
          <div className="feature-list">
            <div className="feature-item">
              <div className="feature-icon">🎙️</div>
              <div className="feature-text">
                <h3>Record Effortlessly</h3>
                <p>Capture your thoughts with premium audio quality</p>
              </div>
            </div>
            
            <div className="feature-item">
              <div className="feature-icon">📝</div>
              <div className="feature-text">
                <h3>Organize Seamlessly</h3>
                <p>Keep your recordings and journals in perfect order</p>
              </div>
            </div>
            
            <div className="feature-item">
              <div className="feature-icon">🔍</div>
              <div className="feature-text">
                <h3>Find Instantly</h3>
                <p>Search through your entire voice library</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right Panel - Login */}
      <div className="login-right">
        <div className="login-card">
          <div className="login-header">
            <h2>Welcome Back</h2>
            <p>Sign in to continue your journey</p>
          </div>

          <button onClick={handleGoogleClick} className="google-signin-btn">
            <svg className="google-icon" viewBox="0 0 24 24" width="20" height="20">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            <span>Continue with Google</span>
          </button>

          <div className="login-footer">
            <p>By signing in, you agree to our Terms of Service and Privacy Policy</p>
          </div>
        </div>
      </div>

      <style>{`
        .login-page {
          display: flex;
          height: 100vh;
          background: var(--bg-primary);
        }

        .login-left {
          flex: 1;
          background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 3rem;
          position: relative;
          overflow: hidden;
        }

        .login-left::before {
          content: '';
          position: absolute;
          top: -50%;
          right: -50%;
          width: 100%;
          height: 100%;
          background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
          animation: float 20s ease-in-out infinite;
        }

        @keyframes float {
          0%, 100% { transform: translate(0, 0); }
          50% { transform: translate(-20px, -20px); }
        }

        .brand-content {
          max-width: 500px;
          color: white;
          position: relative;
          z-index: 1;
        }

        .brand-logo {
          font-size: 4rem;
          font-weight: 700;
          margin-bottom: 1rem;
          text-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }

        .brand-tagline {
          font-size: 1.5rem;
          font-weight: 300;
          margin-bottom: 4rem;
          opacity: 0.95;
        }

        .feature-list {
          display: flex;
          flex-direction: column;
          gap: 2rem;
        }

        .feature-item {
          display: flex;
          gap: 1.5rem;
          align-items: flex-start;
        }

        .feature-icon {
          font-size: 2.5rem;
          flex-shrink: 0;
        }

        .feature-text h3 {
          font-size: 1.25rem;
          font-weight: 600;
          margin-bottom: 0.5rem;
        }

        .feature-text p {
          font-size: 1rem;
          opacity: 0.9;
          line-height: 1.5;
        }

        .login-right {
          flex: 1;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 3rem;
          background: var(--bg-secondary);
        }

        .login-card {
          width: 100%;
          max-width: 450px;
          background: var(--bg-card);
          padding: 3rem;
          border-radius: var(--radius-xl);
          box-shadow: var(--shadow-xl);
        }

        .login-header {
          text-align: center;
          margin-bottom: 3rem;
        }

        .login-header h2 {
          font-size: 2rem;
          font-weight: 700;
          color: var(--text-primary);
          margin-bottom: 0.5rem;
        }

        .login-header p {
          font-size: 1rem;
          color: var(--text-secondary);
        }

        .google-signin-btn {
          width: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 1rem;
          padding: 1rem 2rem;
          background: white;
          border: 2px solid #e5e7eb;
          border-radius: var(--radius-lg);
          font-size: 1rem;
          font-weight: 500;
          color: #1a202c;
          cursor: pointer;
          transition: all 0.3s ease;
          box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }

        .google-signin-btn:hover {
          border-color: var(--accent-primary);
          box-shadow: 0 4px 16px rgba(79, 209, 197, 0.2);
          transform: translateY(-2px);
        }

        .google-icon {
          flex-shrink: 0;
        }

        .login-footer {
          margin-top: 2rem;
          text-align: center;
        }

        .login-footer p {
          font-size: 0.75rem;
          color: var(--text-tertiary);
          line-height: 1.5;
        }

        .login-loading {
          display: flex;
          align-items: center;
          justify-content: center;
          height: 100vh;
          background: var(--bg-primary);
        }

        .loading-spinner {
          width: 50px;
          height: 50px;
          border: 4px solid var(--bg-tertiary);
          border-top-color: var(--accent-primary);
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        @media (max-width: 768px) {
          .login-page {
            flex-direction: column;
          }

          .login-left {
            padding: 2rem;
            min-height: 40vh;
          }

          .brand-logo {
            font-size: 3rem;
          }

          .feature-list {
            display: none;
          }

          .login-card {
            padding: 2rem;
          }
        }
      `}</style>
    </div>
  );
};

export default Login;
