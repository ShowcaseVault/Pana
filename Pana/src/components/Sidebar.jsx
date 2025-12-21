import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { Home, Mic, Book, Calendar,Settings, LogOut } from 'lucide-react';
import axiosClient from '../api/axiosClient';
import { API_ROUTES } from '../api/routes';
import { useAuth } from '../context/useAuth';
import '../styles/themes.css';

const Sidebar = () => {
  const navigate = useNavigate();
  const { logout } = useAuth();

  const now = new Date();
  const currentYearMonth = `${now.getFullYear()}/${now.getMonth() + 1}`;

  const navItems = [
    { icon: Home, label: 'Home', path: '/home' },
    { icon: Mic, label: 'Recordings', path: '/recordings' },
    { icon: Book, label: 'Diary', path: '/diary' },
    { icon: Calendar, label: 'Calendar', path: `/calendar/${currentYearMonth}` },
    { icon: Settings, label: 'Preferences', path: '/preferences' },
  ];

  const isCalendarActive = (path, currentPath) => {
    if (path.startsWith('/calendar')) {
      return currentPath.startsWith('/calendar');
    }
    return path === currentPath;
  };

  const handleLogout = async () => {
    try {
      await axiosClient.post(API_ROUTES.AUTH.LOGOUT);
    } catch (e) {
      // Even if backend logout fails, clear local state and redirect.
    } finally {
      logout();
      navigate('/login', { replace: true });
    }
  };

  return (
    <aside className="sidebar-premium">
      <div className="logo-section">
        <h1 className="logo-text">Pana</h1>
      </div>

      <nav className="nav-menu">
        {navItems.map((item) => (
          <NavLink
            key={item.label}
            to={item.path}
            className={({ isActive }) => 
              `nav-item ${(isActive || (item.label === 'Calendar' && window.location.pathname.startsWith('/calendar'))) ? 'active' : ''}`
            }
          >
            <div className="nav-icon-wrapper">
              <item.icon size={22} />
            </div>
            <span className="nav-label">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="bottom-section">
        <button onClick={handleLogout} className="nav-item logout-btn">
          <div className="nav-icon-wrapper">
            <LogOut size={22} />
          </div>
          <span className="nav-label">Logout</span>
        </button>
      </div>

      <style>{`
        .sidebar-premium {
          width: 100px;
          height: 100%;
          background: var(--bg-secondary);
          display: flex;
          flex-direction: column;
          padding: 1.25rem 0.25rem;
          align-items: center;
        }

        .logo-section {
          margin-bottom: 2rem;
          text-align: center;
        }

        .logo-text {
          font-size: 1.25rem;
          font-weight: 600;
          color: var(--text-primary);
          margin: 0;
        }

        .nav-menu {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
          width: 100%;
          align-items: center;
          flex: 1;
        }

        .nav-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.25rem;
          padding: 0.5rem 0.25rem;
          border-radius: 12px;
          color: var(--text-secondary);
          text-decoration: none;
          transition: all 0.2s ease;
          width: 90%;
          cursor: pointer;
          background: none;
          border: none;
        }

        .nav-icon-wrapper {
          width: 48px;
          height: 48px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.2s ease;
          background: transparent;
        }

        .nav-item:hover .nav-icon-wrapper {
          background: var(--bg-tertiary);
        }

        .nav-item.active .nav-icon-wrapper {
          background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
          color: white;
          box-shadow: 0 4px 12px rgba(79, 209, 197, 0.3);
        }

        .nav-item.active {
          color: var(--text-primary);
        }

        .nav-label {
          font-size: 0.6rem;
          font-weight: 500;
          text-align: center;
        }

        .nav-item.active .nav-label {
          color: var(--accent-secondary);
          font-weight: 600;
        }

        .bottom-section {
          width: 100%;
          display: flex;
          flex-direction: column;
          align-items: center;
          padding-top: 1rem;
          border-top: 1px solid var(--bg-tertiary);
          margin-top: auto;
        }

        .logout-btn {
          color: #ef4444;
        }

        .logout-btn:hover .nav-icon-wrapper {
          background: rgba(239, 68, 68, 0.1);
        }

        .logout-btn .nav-label {
          color: #ef4444;
        }
      `}</style>
    </aside>
  );
};

export default Sidebar;
