/**
 * The opening screen.
 *
 * Shown while the session is being resolved, which is usually faster than the
 * eye can register. A minimum on-screen time is enforced by the caller so the
 * logo does not flash and vanish.
 *
 * @module screens/Splash
 */

import '../styles/splash.css';

export default function Splash() {
  return (
    <div className="splash">
      <img className="splash__logo" src="/logo-app.png" alt="Pana" />
      <span className="splash__word">Pana</span>
    </div>
  );
}
