import React from 'react';
import { NavLink } from 'react-router-dom';
import { Home, Mic, Book, History, Settings, LogOut } from 'lucide-react';
import { useAuth } from '../context/useAuth';

const Sidebar = () => {
  const { logout } = useAuth(); // Assuming useAuth has logout

  const navItems = [
    { icon: Home, label: 'Home', path: '/home' },
    { icon: Mic, label: 'Recordings', path: '/recordings' },
    { icon: Book, label: 'Journals', path: '/journals' },
    { icon: History, label: 'History', path: '/history' },
  ];

  const handleLogout = () => {
      // Mock logout for now if context doesn't fully support it yet
      window.location.href = '/login'; 
  }

  return (
    <aside className="sidebar">
      <div className="logo-section">
        <h1 className="logo-text">Pana</h1>
      </div>

      <nav className="nav-menu">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => 
              `nav-item ${isActive ? 'active' : ''}`
            }
          >
            <item.icon size={20} />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="bottom-section">
        <NavLink to="/preferences" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
           <Settings size={20} />
           <span>Preferences</span>
        </NavLink>
        <button onClick={handleLogout} className="nav-item logout-btn">
          <LogOut size={20} />
          <span>Logout</span>
        </button>
      </div>

      <style>{`
        .sidebar {
          width: 240px;
          height: 100%;
          background-color: var(--bg-secondary);
          display: flex;
          flex-direction: column;
          padding: 1.5rem 1.5rem 4rem 1.5rem; /* Increased bottom padding */
          border-right: 1px solid var(--bg-tertiary);
        }

        .logo-section {
          margin-bottom: 2rem;
          padding-left: 0.5rem;
        }

        .logo-text {
          font-size: 1.5rem;
          font-weight: 700;
          background: linear-gradient(to right, #c4b5fd, #8b5cf6);
          -webkit-background-clip: text;
          background-clip: text;
          color: transparent;
          margin: 0;
        }

        .nav-menu {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
          flex: 1;
        }

        .nav-item {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.75rem 1rem;
          border-radius: 12px;
          color: var(--text-secondary);
          text-decoration: none;
          transition: all 0.2s ease;
          border: none;
          background: none;
          width: 100%;
          font-size: 0.95rem;
          cursor: pointer;
        }

        .nav-item:hover {
          color: var(--text-primary);
          background-color: rgba(255, 255, 255, 0.03);
        }

        .nav-item.active {
          background-color: rgba(139, 92, 246, 0.1);
          color: var(--accent-secondary);
          font-weight: 500;
        }

        .bottom-section {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
          margin-top: auto;
          margin-bottom: 3rem; /* Forcefully lift up from bottom */
          border-top: 1px solid var(--bg-tertiary);
          padding-top: 1rem;
        }
        
        .logout-btn {
           color: #ef4444;
        }
        .logout-btn:hover {
           background-color: rgba(239, 68, 68, 0.1);
           color: #f87171;
        }
      `}</style>
    </aside>
  );
};

export default Sidebar;
