/**
 * Session state for the app.
 *
 * Startup has three outcomes and the UI must tell them apart: still checking
 * (show the splash), checked and signed in (show the shell), checked and not
 * signed in (show login). `status` carries exactly that, rather than leaving
 * callers to infer it from a null user.
 *
 * @module lib/AuthContext
 */

import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { onSessionExpired } from './apiClient.js';
import { hydrate, getAccessToken } from './tokenStore.js';
import { getCurrentUser, initGoogleAuth, signInWithGoogle, signOut } from './auth.service.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  /** @type {['checking'|'authenticated'|'anonymous', Function]} */
  const [status, setStatus] = useState('checking');
  const [user, setUser] = useState(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      // Tokens must be read off disk before the first request: the interceptor
      // reads them synchronously and would otherwise send an anonymous call.
      await hydrate();
      await initGoogleAuth().catch((error) =>
        console.warn('Google SDK failed to initialize', error),
      );

      if (!getAccessToken()) {
        if (!cancelled) setStatus('anonymous');
        return;
      }

      try {
        const me = await getCurrentUser();
        if (cancelled) return;
        setUser(me);
        setStatus('authenticated');
      } catch {
        // A stored token that no longer works is the same as no token; the
        // client has already tried to refresh it by this point.
        if (!cancelled) setStatus('anonymous');
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  // A 401 the client could not recover from ends the session wherever it
  // happens, including mid-upload, so the listener lives here rather than in
  // any one screen.
  useEffect(
    () =>
      onSessionExpired(() => {
        setUser(null);
        setStatus('anonymous');
      }),
    [],
  );

  const login = useCallback(async () => {
    await signInWithGoogle();
    const me = await getCurrentUser();
    setUser(me);
    setStatus('authenticated');
  }, []);

  const logout = useCallback(async () => {
    await signOut();
    setUser(null);
    setStatus('anonymous');
  }, []);

  return (
    <AuthContext.Provider value={{ status, user, login, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
}
