/**
 * What the app shows, and when.
 *
 * Three states, one each: resolving the session, no session, session. The
 * splash is held for a moment past the point the answer arrives -- a resolved
 * session is often faster than a frame, and a logo that flashes and vanishes
 * reads as a glitch rather than as an opening.
 *
 * @module App
 */

import { useEffect, useState } from 'react';
import { Toaster } from 'sonner';
import { useAuth } from './lib/AuthContext.jsx';
import Splash from './screens/Splash.jsx';
import Login from './screens/Login.jsx';
import Shell from './screens/Shell.jsx';

/** How long the logo stays up regardless of how fast the session resolves. */
const SPLASH_MS = 1400;

export default function App() {
  const { status } = useAuth();
  const [splashDone, setSplashDone] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setSplashDone(true), SPLASH_MS);
    return () => clearTimeout(timer);
  }, []);

  if (!splashDone || status === 'checking') return <Splash />;

  return (
    <>
      {status === 'authenticated' ? <Shell /> : <Login />}
      <Toaster position="top-center" richColors />
    </>
  );
}
