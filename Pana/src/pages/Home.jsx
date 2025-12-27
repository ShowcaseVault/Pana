import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/useAuth';
import { useNavigate } from 'react-router-dom';
import RecordingCard from '../components/RecordingCard';
import { Mic, TrendingUp, Clock } from 'lucide-react';
import axiosClient from '../api/axiosClient';
import { API_ROUTES } from '../api/routes';
import '../styles/themes.css';

const Home = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showName, setShowName] = useState(false);

  useEffect(() => {
    fetchRecentRecordings();
  }, []);

  const fetchRecentRecordings = async () => {
    try {
      const res = await axiosClient.get(`${API_ROUTES.RECORDINGS.LIST}?limit=5`);
      if (res.data.code === 'SUCCESS') {
        const records = res.data.data.data ? res.data.data.data : res.data.data;
        setRecordings(records);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const getTotalDuration = () => {
    return recordings.reduce((sum, r) => sum + r.duration_seconds, 0);
  };

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    return `${mins} min`;
  };

  return (
    <div className="dashboard-page">
      {/* Left Panel - Recent Activity */}
      <div className="activity-sidebar">
        <h2 className="sidebar-title">Recent Activity</h2>
        <div className="activity-list">
          {loading ? (
            <div className="loading-state">Loading...</div>
          ) : recordings.length > 0 ? (
            recordings.map(recording => (
              <RecordingCard 
                key={recording.id} 
                recording={recording}
                compact={true}
              />
            ))
          ) : (
            <div className="empty-state">
              <p>No recordings yet</p>
              <span>Start your first recording</span>
            </div>
          )}
        </div>
      </div>

      {/* Right Panel - Welcome Area */}
      <div className="welcome-panel">
        <div className="welcome-content">
          <div className="greeting-section">
            <h1 className="greeting">Hello, {user?.name?.split(' ')[0] || 'there'}!</h1>
            <p className="welcome-text">Welcome back to your personal space.</p>
          </div>

          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon">
                <Mic size={24} />
              </div>
              <div className="stat-content">
                <div className="stat-label">Total Recordings</div>
                <div className="stat-value">{recordings.length}</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">
                <Clock size={24} />
              </div>
              <div className="stat-content">
                <div className="stat-label">Total Duration</div>
                <div className="stat-value">{formatDuration(getTotalDuration())}</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">
                <TrendingUp size={24} />
              </div>
              <div className="stat-content">
                <div className="stat-label">This Week</div>
                <div className="stat-value">{recordings.length}</div>
              </div>
            </div>
          </div>

          <button className="quick-action-btn" onClick={() => navigate('/recordings')}>
            <Mic size={20} />
            <span>Start Recording</span>
          </button>
        </div>
      </div>

       {/* Profile Section - Absolute Top Right */}
       <div className="profile-section">
        <div 
            className="profile-icon-wrapper"
            onClick={() => setShowName(!showName)}
        >
            {user?.picture ? (
                <img src={user.picture} alt="Profile" className="profile-img" />
            ) : (
                <div className="profile-placeholder">
                    {user?.name?.charAt(0) || 'U'}
                </div>
            )}
        </div>
        {showName && (
            <div className="profile-popover">
                {user?.name || 'User'}
            </div>
        )}
      </div>

      <style>{`
        .dashboard-page {
          display: flex;
          height: 100vh;
          background: var(--bg-primary);
          position: relative; /* Context for profile absolute position */
        }
        
        .profile-section {
            position: absolute;
            top: 1.5rem;
            right: 2rem;
            z-index: 100;
            display: flex;
            flex-direction: column;
            align-items: flex-end;
        }

        .profile-icon-wrapper {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            cursor: pointer;
            overflow: hidden;
            border: 2px solid white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s;
            background: #e5e7eb;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .profile-icon-wrapper:hover {
            transform: scale(1.05);
        }

        .profile-img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        .profile-placeholder {
            font-weight: 600;
            color: #6b7280;
            text-transform: uppercase;
        }

        .profile-popover {
            margin-top: 0.5rem;
            background: white;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            font-size: 0.875rem;
            font-weight: 600;
            color: var(--text-primary);
            white-space: nowrap;
            animation: fadeIn 0.2s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-4px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .activity-sidebar {
          width: 25%;
          min-width: 260px;
          max-width: 350px;
          background: transparent;
          padding: 2rem 1.25rem;
          overflow-y: auto;
        }

        .sidebar-title {
          font-size: 1.25rem;
          font-weight: 600;
          color: var(--text-primary);
          margin-bottom: 1.5rem;
        }

        .activity-list {
          display: flex;
          flex-direction: column;
        }

        .welcome-panel {
          flex: 1;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 3rem;
        }

        .welcome-content {
          max-width: 800px;
          width: 100%;
        }

        .greeting-section {
          margin-bottom: 3rem;
        }

        .greeting {
          font-size: 3rem;
          font-weight: 700;
          margin-bottom: 0.5rem;
          background: linear-gradient(to right, var(--text-primary), var(--text-secondary));
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }

        .welcome-text {
          color: var(--text-secondary);
          font-size: 1.25rem;
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 1.5rem;
          margin-bottom: 3rem;
        }

        .stat-card {
          background: var(--bg-card);
          padding: 1.5rem;
          border-radius: var(--radius-lg);
          box-shadow: var(--shadow-md);
          display: flex;
          align-items: center;
          gap: 1rem;
          transition: all 0.3s ease;
        }

        .stat-card:hover {
          transform: translateY(-4px);
          box-shadow: var(--shadow-lg);
        }

        .stat-icon {
          width: 48px;
          height: 48px;
          border-radius: var(--radius-md);
          background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
        }

        .stat-content {
          flex: 1;
        }

        .stat-label {
          font-size: 0.875rem;
          color: var(--text-secondary);
          margin-bottom: 0.25rem;
        }

        .stat-value {
          font-size: 1.75rem;
          font-weight: 600;
          color: var(--text-primary);
        }

        .quick-action-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 0.75rem;
          padding: 1rem 2rem;
          background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
          color: white;
          border: none;
          border-radius: var(--radius-lg);
          font-size: 1rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.3s ease;
          box-shadow: 0 8px 24px rgba(79, 209, 197, 0.3);
        }

        .quick-action-btn:hover {
          transform: translateY(-2px);
          box-shadow: 0 12px 32px rgba(79, 209, 197, 0.4);
        }

        .loading-state, .empty-state {
          text-align: center;
          padding: 2rem;
          color: var(--text-secondary);
        }

        .empty-state p {
          font-size: 1rem;
          margin-bottom: 0.5rem;
          color: var(--text-primary);
        }

        .empty-state span {
          font-size: 0.875rem;
        }
      `}</style>
    </div>
  );
};

export default Home;
