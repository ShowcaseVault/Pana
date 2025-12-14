import { useAuth } from '../context/useAuth';

const Dashboard = () => {
  const { user, logout } = useAuth();

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
         <h1>Dashboard</h1>
         <p className="welcome-text">Welcome back to your personal space.</p>
      </header>

      {user ? (
        <div className="profile-card">
          <div className="profile-header">
             <div className="profile-image-wrapper">
                {user.picture ? (
                   <img src={user.picture} alt={user.name} className="profile-image" />
                ) : (
                   <div className="profile-placeholder">{user.name?.charAt(0)}</div>
                )}
             </div>
             <div className="profile-info">
                <h2>{user.name}</h2>
                <p className="email">{user.email}</p>
             </div>
          </div>
          
          <div className="stats-grid">
               {/* Placeholders for future stats */}
               <div className="stat-card">
                   <span className="stat-label">Total Recordings</span>
                   <span className="stat-value">-</span>
               </div>
               <div className="stat-card">
                   <span className="stat-label">Last Active</span>
                   <span className="stat-value">Today</span>
               </div>
          </div>
        </div>
      ) : (
        <div className="loading-state">Loading user profile...</div>
      )}

      <style>{`
        .dashboard-container {
            padding: 2rem 3rem;
            max-width: 1200px;
            margin: 0 auto;
        }

        .dashboard-header {
            margin-bottom: 3rem;
        }

        .dashboard-header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            background: linear-gradient(to right, #fff, #9ca3af);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .welcome-text {
            color: var(--text-secondary);
            font-size: 1.1rem;
        }

        .profile-card {
            background: var(--bg-secondary);
            border-radius: 24px;
            padding: 2rem;
            border: 1px solid var(--bg-tertiary);
        }

        .profile-header {
            display: flex;
            align-items: center;
            gap: 2rem;
            margin-bottom: 3rem;
        }

        .profile-image-wrapper {
            position: relative;
        }

        .profile-image {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            object-fit: cover;
            border: 4px solid var(--bg-tertiary);
        }

        .profile-placeholder {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2.5rem;
            font-weight: 700;
            color: white;
            border: 4px solid var(--bg-tertiary);
        }

        .profile-info h2 {
            font-size: 2rem;
            font-weight: 600;
            margin-bottom: 0.25rem;
        }

        .email {
            color: var(--text-secondary);
            font-size: 1rem;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
        }

        .stat-card {
            background: var(--bg-tertiary);
            padding: 1.5rem;
            border-radius: 16px;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .stat-label {
            color: var(--text-secondary);
            font-size: 0.9rem;
        }

        .stat-value {
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--text-primary);
        }

        .loading-state {
            color: var(--text-secondary);
            text-align: center;
            padding: 4rem;
        }
      `}</style>
    </div>
  );
};

export default Dashboard;
