import React from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { Home, Mic, BookOpen, CalendarDays, LogOut } from 'lucide-react';
import { useAuth } from '../context/useAuth';
import '../styles/shell.css';

/**
 * Primary navigation.
 *
 * A narrow rail of stacked icons, each with its word beneath. The glyph is
 * what the eye finds once the app is familiar; the word removes the guesswork
 * the first time. Stacking them keeps the rail thin, which is the point -- the
 * chrome should take as little width as it can so the screen belongs to the
 * content.
 */
const Sidebar = () => {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const { logout } = useAuth();

  const now = new Date();
  const thisMonth = `${now.getFullYear()}/${now.getMonth() + 1}`;

  const destinations = [
    { label: 'Today', path: '/home', Icon: Home },
    { label: 'Record', path: '/recordings', Icon: Mic },
    { label: 'Diary', path: '/diary', Icon: BookOpen },
    { label: 'Calendar', path: `/calendar/${thisMonth}`, Icon: CalendarDays },
  ];

  const handleSignOut = async () => {
    // The context clears cached data whether or not the server call succeeds,
    // so the redirect is unconditional.
    try {
      await logout();
    } finally {
      navigate('/login', { replace: true });
    }
  };

  return (
    <aside className="rail">
      <div className="rail__mark">
        <span className="rail__wordmark">Pana</span>
      </div>

      <nav className="rail__nav">
        {destinations.map((destination) => (
          <NavLink
            key={destination.label}
            to={destination.path}
            // Calendar's path carries a year and month, so an exact match would
            // never mark it active once the user moves off the current month.
            className={({ isActive }) =>
              `rail__link${
                isActive ||
                (destination.label === 'Calendar' &&
                  pathname.startsWith('/calendar'))
                  ? ' rail__link--active'
                  : ''
              }`
            }
          >
            <destination.Icon
              size={18}
              strokeWidth={1.75}
              className="rail__icon"
              aria-hidden="true"
            />
            <span className="rail__label">{destination.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="rail__foot">
        <button type="button" className="rail__link" onClick={handleSignOut}>
          <LogOut size={18} strokeWidth={1.75} className="rail__icon" aria-hidden="true" />
          <span className="rail__label">Logout</span>
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
