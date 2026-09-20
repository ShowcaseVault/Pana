/**
 * Sign-in.
 *
 * One control. The Google SDK presents its own account picker over the app, so
 * nothing navigates away and there is no redirect to handle on the way back.
 *
 * @module screens/Login
 */

import { useState } from 'react';
import { toast } from 'sonner';
import { useAuth } from '../lib/AuthContext.jsx';
import { USER_CANCELLED } from '../lib/auth.service.js';
import { CAN_OVERRIDE, getServerOrigin, setServerOrigin } from '../lib/serverStore.js';
import '../styles/login.css';

export default function Login() {
  const { login } = useAuth();
  const [busy, setBusy] = useState(false);

  // Only a build that permits it shows the server field at all, and in a
  // release build the whole block is removed by the bundler rather than
  // hidden: an app that can be pointed anywhere is an app that can be talked
  // into handing a session token to someone else's server.
  const [server, setServer] = useState(getServerOrigin);
  const [savingServer, setSavingServer] = useState(false);

  const handleSaveServer = async () => {
    setSavingServer(true);
    try {
      await setServerOrigin(server);
      setServer(getServerOrigin());
      toast.success(`Server set to ${getServerOrigin()}`);
    } catch (error) {
      console.error('Could not save the server address', error);
      toast.error('Could not save that address');
    } finally {
      setSavingServer(false);
    }
  };

  const handleSignIn = async () => {
    setBusy(true);
    try {
      await login();
    } catch (error) {
      // A cancelled picker is a deliberate act, not a failure worth a toast.
      const cancelled = error?.code === USER_CANCELLED;
      if (!cancelled) {
        console.error('Sign-in failed', error);
        toast.error(error?.message ?? 'Sign-in failed');
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login">
      <div className="login__brand">
        <img className="login__logo" src="/logo-app.png" alt="" />
        <h1 className="login__title">Pana</h1>
        <p className="login__tagline">Speak your day. Read it back.</p>
      </div>

      <button type="button" className="login__button" onClick={handleSignIn} disabled={busy}>
        <svg className="login__g" viewBox="0 0 48 48" aria-hidden="true">
          <path fill="#4285F4" d="M45.1 24.5c0-1.6-.1-3.2-.4-4.7H24v8.9h11.8c-.5 2.7-2 5-4.4 6.6v5.5h7.1c4.1-3.8 6.6-9.4 6.6-16.3z"/>
          <path fill="#34A853" d="M24 46c5.9 0 10.9-2 14.5-5.3l-7.1-5.5c-2 1.3-4.5 2.1-7.4 2.1-5.7 0-10.5-3.8-12.2-9H4.5v5.7C8.1 41.2 15.5 46 24 46z"/>
          <path fill="#FBBC05" d="M11.8 28.3c-.4-1.3-.7-2.7-.7-4.3s.3-3 .7-4.3v-5.7H4.5C2.9 17.1 2 20.4 2 24s.9 6.9 2.5 10l7.3-5.7z"/>
          <path fill="#EA4335" d="M24 10.8c3.2 0 6.1 1.1 8.4 3.3l6.3-6.3C34.9 4.1 29.9 2 24 2 15.5 2 8.1 6.8 4.5 14l7.3 5.7c1.7-5.2 6.5-8.9 12.2-8.9z"/>
        </svg>
        {busy ? 'Signing in…' : 'Continue with Google'}
      </button>

      <p className="login__legal">Your recordings stay private to your account.</p>

      {CAN_OVERRIDE && (
        <div className="login__server">
          <label className="login__server-label" htmlFor="server">
            Server
          </label>
          <div className="login__server-row">
            <input
              id="server"
              className="login__server-input"
              type="url"
              inputMode="url"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck="false"
              placeholder="http://192.168.1.10:8000"
              value={server}
              onChange={(event) => setServer(event.target.value)}
            />
            <button
              type="button"
              className="login__server-save"
              onClick={handleSaveServer}
              disabled={savingServer}
            >
              Save
            </button>
          </div>
          <p className="login__server-hint">
            The address of your Pana API, as the phone sees it. Sign in again after changing it.
          </p>
        </div>
      )}
    </div>
  );
}
