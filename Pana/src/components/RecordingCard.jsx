import React from 'react';
import { Play, MoreHorizontal, Volume2 } from 'lucide-react';

const RecordingCard = ({ recording, onPlay, onDelete, compact = false }) => {
  const formatTime = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    });
  };

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (compact) {
    return (
      <div className="recording-card-compact">
        <div className="compact-icon">
          <Volume2 size={16} />
        </div>
        <div className="compact-info">
          <div className="compact-title">{recording.location_text || 'Untitled'}</div>
          <div className="compact-meta">
            {formatTime(recording.recorded_at)} · {formatDuration(recording.duration_seconds)}
          </div>
        </div>
        
        <style>{`
          .recording-card-compact {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.75rem 1rem;
            background: var(--bg-card);
            border-radius: var(--radius-md);
            box-shadow: var(--shadow-sm);
            cursor: pointer;
            transition: all 0.2s ease;
            margin-bottom: 0.5rem;
          }
          
          .recording-card-compact:hover {
            box-shadow: var(--shadow-md);
            transform: translateX(4px);
          }
          
          .compact-icon {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: linear-gradient(135deg, #e5e7eb, #d1d5db);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #6b7280;
          }
          
          .compact-info {
            flex: 1;
          }
          
          .compact-title {
            font-size: 0.875rem;
            font-weight: 500;
            color: var(--text-primary);
            margin-bottom: 0.125rem;
          }
          
          .compact-meta {
            font-size: 0.75rem;
            color: var(--text-secondary);
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className="recording-card">
      <button className="play-button" onClick={() => onPlay?.(recording)}>
        <Play size={14} fill="#4b5563" stroke="#4b5563" />
      </button>
      
      <div className="card-content">
        <div className="card-title-row">
          <span className="card-title">{recording.location_text || 'In My Head'}</span>
          <Volume2 size={14} className="speaker-icon" />
        </div>
        <div className="card-meta">
          {formatTime(recording.recorded_at)} - {formatDuration(recording.duration_seconds)}
        </div>
      </div>
      
      <button className="menu-button">
        <MoreHorizontal size={18} />
      </button>

      <style>{`
        .recording-card {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.875rem 1rem;
          background: var(--bg-card);
          border-radius: 4px;
          box-shadow: var(--shadow-sm);
          margin-bottom: 0.75rem;
          transition: all 0.2s ease;
          cursor: pointer;
        }
        
        .recording-card:hover {
          box-shadow: var(--shadow-md);
          transform: translateY(-2px);
        }
        
        .play-button {
          width: 36px;
          height: 36px;
          border-radius: 50%;
          background: #e5e7eb;
          border: none;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.2s ease;
          flex-shrink: 0;
        }
        
        .play-button:hover {
          background: #d1d5db;
        }
        
        .card-content {
          flex: 1;
          min-width: 0;
        }
        
        .card-title-row {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin-bottom: 0.125rem;
        }
        
        .card-title {
          font-size: 0.875rem;
          font-weight: 500;
          color: var(--text-primary);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        
        .speaker-icon {
          color: var(--text-tertiary);
          flex-shrink: 0;
        }
        
        .card-meta {
          font-size: 0.75rem;
          color: var(--text-secondary);
        }
        
        .menu-button {
          width: 28px;
          height: 28px;
          border-radius: 50%;
          background: transparent;
          border: none;
          color: var(--text-secondary);
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.2s ease;
          flex-shrink: 0;
        }
        
        .menu-button:hover {
          background: var(--bg-tertiary);
          color: var(--text-primary);
        }
      `}</style>
    </div>
  );
};

export default RecordingCard;
