import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import authService from '../services/auth.service';
import { useAuth } from '../context/useAuth';
import { useDocumentTitle } from '../hooks/useDocumentTitle';
import '../styles/login.css';

/** Google's mark, inline so the page holds no external image request. */
const GoogleMark = () => (
  <svg width="17" height="17" viewBox="0 0 18 18" aria-hidden="true">
    <path
      fill="#4285F4"
      d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62z"
    />
    <path
      fill="#34A853"
      d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A9 9 0 0 0 9 18z"
    />
    <path
      fill="#FBBC05"
      d="M3.97 10.72a5.41 5.41 0 0 1 0-3.44V4.95H.96a9 9 0 0 0 0 8.1l3.01-2.33z"
    />
    <path
      fill="#EA4335"
      d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .96 4.95l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58z"
    />
  </svg>
);

const Login = () => {
  useDocumentTitle("Sign in");

  const navigate = useNavigate();
  const { user, loading } = useAuth();
  const [params] = useSearchParams();

  // The backend redirects here with ?error=... when the Google flow fails.
  const error = params.get('error');

  useEffect(() => {
    if (!loading && user) navigate('/home', { replace: true });
  }, [user, loading, navigate]);

  if (loading || user) {
    return <div className="login__waiting">One moment</div>;
  }

  return (
    <div className="login">
      <div className="login__inner">
        <img className="login__logo" src="/logo-app.png" alt="" width="72" height="72" />
        <h1 className="login__wordmark">Pana</h1>

        <p className="login__line">Say what happened. Read it back as a diary.</p>

        <div className="login__action">
          <button type="button" className="login__google" onClick={() => authService.startGoogleLogin()}>
            <GoogleMark />
            Continue with Google
          </button>
        </div>

        {error ? (
          <p className="login__error">
            That sign-in did not complete. Try again.
          </p>
        ) : (
          <p className="login__note">Your recordings stay private to your account.</p>
        )}
      </div>
    </div>
  );
};

export default Login;
