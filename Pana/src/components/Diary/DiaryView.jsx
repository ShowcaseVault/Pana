import React, { useState, useRef, useEffect } from 'react';
import { Play, CheckCircle, Circle, MapPin, Clock, RotateCw, Pause } from 'lucide-react';
import './Diary.css';
import { BASE_URL, API_ROUTES } from '../../api/routes';

const DiaryView = ({ diary, recordings = [], onRegenerate, loading = false }) => {
  const [activeId, setActiveId] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const audioRef = useRef(new Audio());

  const { diary_date, mood, content, actions } = diary;

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  const handlePlay = (recording) => {
    // If interacting with the currently active recording
    if (activeId === recording.id) {
      if (isPlaying) {
        audioRef.current.pause();
        setIsPlaying(false);
      } else {
        audioRef.current.play().catch(e => console.error("Resume failed:", e));
        setIsPlaying(true);
      }
      return;
    } 

    // Switching to a new recording
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
    }
    
    // Create new audio instance if needed (though ref persists)
    if (!audioRef.current) audioRef.current = new Audio();
      
    // Clean path logic
    let filePath = recording.file_path;
    if (filePath) {
      filePath = filePath.replace(/\\/g, '/');
    } else {
      console.error("No file path for recording", recording);
      return;
    }
    
    const audioBase = API_ROUTES.AUDIO_BASE.replace(/\/$/, '');
    const relativePath = filePath.replace(/^\//, '');
    const audioUrl = `${BASE_URL}${audioBase}/${relativePath}`;
    
    audioRef.current.src = audioUrl;
    audioRef.current.play().catch(e => console.error("Playback failed:", e));
    
    setActiveId(recording.id);
    setIsPlaying(true);
    setProgress(0);
      
    // Update progress
    audioRef.current.ontimeupdate = () => {
      if (audioRef.current.duration) {
        const prog = (audioRef.current.currentTime / audioRef.current.duration) * 100;
        setProgress(prog);
      }
    };

    audioRef.current.onended = () => {
      setIsPlaying(false);
      setProgress(0);
      setActiveId(null); // Optional: reset active state on finish
    };
  };

  // Helper to format date
  const formatDate = (dateString) => {
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('en-US', options);
  };

  const getMoodClass = (mood) => {
    switch(mood) {
      case 'Positive': return 'mood-positive';
      case 'Neutral': return 'mood-neutral';
      case 'Negative': return 'mood-negative';
      case 'Energetic': return 'mood-energetic';
      case 'Calm': return 'mood-calm';
      default: return 'mood-neutral';
    }
  };

  return (
    <div className="diary-container">
      {/* Main Content Area */}
      <div className={`diary-main ${loading ? 'is-loading' : ''}`}>
        {loading && (
          <div className="loading-overlay">
            <div className="spinner"></div>
            <p>Regenerating Diary...</p>
          </div>
        )}
        <header className="diary-header">
          <h1 className="diary-title">Today's Diary</h1>
          <div className="diary-meta">
            <p className="diary-date">{formatDate(diary_date)}</p>
            {mood && (
              <span className={`diary-mood-badge ${getMoodClass(mood)}`}>
                {mood}
              </span>
            )}
          </div>
        </header>

        <div className="diary-card">
          {content ? (
            <div className="diary-text">
              {content}
            </div>
          ) : (
            <div className="empty-diary-state">
              <div className="empty-icon">
                <Play size={48} strokeWidth={1} />
              </div>
              <h2>Ready to Write?</h2>
              <p>You have recordings for this day. Generate your diary to summarize them.</p>
              <button onClick={onRegenerate} className="generate-btn-large">
                <RotateCw size={20} />
                Generate Diary
              </button>
            </div>
          )}
        </div>

        {actions && actions.length > 0 && (
          <div className="actions-section">
            <h2 className="section-title">Action Items</h2>
            <div className="actions-grid">
              
              {/* Todos */}
              <div className="action-column">
                <h3>Todos</h3>
                {actions.filter(a => a.type === 'todo').map((action, idx) => (
                   <div key={idx} className="action-item">
                     <div className="action-icon" style={{color: '#9ca3af'}}>
                        <Circle size={18} />
                     </div>
                     <span className="action-text">{action.description}</span>
                   </div>
                ))}
                {actions.filter(a => a.type === 'todo').length === 0 && <p style={{color: 'var(--text-tertiary)'}}>No todos.</p>}
              </div>

              {/* Reminders */}
              <div className="action-column">
                <h3>Reminders</h3>
                {actions.filter(a => a.type === 'reminder').map((action, idx) => (
                  <div key={idx} className="action-item">
                    <div className="action-icon" style={{color: 'var(--accent-primary)'}}>
                       <Clock size={18} />
                    </div>
                    <div>
                      <span className="action-text">{action.description}</span>
                      <div className="action-meta">
                         {action.time && <span>{new Date(action.time).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>}
                         {action.location && <span style={{display: 'flex', alignItems: 'center', gap: '4px'}}><MapPin size={10} /> {action.location}</span>}
                      </div>
                    </div>
                  </div>
                ))}
                 {actions.filter(a => a.type === 'reminder').length === 0 && <p style={{color: 'var(--text-tertiary)'}}>No reminders.</p>}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Right Sidebar - Source Recordings */}
      <div className="diary-sidebar">
        <div className="sidebar-section">
          <h3 className="sidebar-title">Source Recordings</h3>
          
          <div className="recording-list">
            {(() => {
              // Logic to resolve recordings from paths or fallback
              let displayList = [];
              if (diary.recording_file_paths && Array.isArray(diary.recording_file_paths) && diary.recording_file_paths.length > 0) {
                 displayList = diary.recording_file_paths.map(path => {
                    // Try to find in full list (normalize slashes for comparison)
                    const found = Array.isArray(recordings) ? recordings.find(r => r.file_path.replace(/\\/g, '/') === path.replace(/\\/g, '/')) : null;
                    if (found) return found;
                    
                    // Fallback: Construct partial object from path
                    // format: .../YYYY-MM-DD/HH-MM-SS.ext
                    const parts = path.split('/');
                    const filename = parts[parts.length - 1] || path;
                    const datePart = parts[parts.length - 2]; 
                    
                    // Try to parse time from filename HH-MM-SS
                    let createdAt = new Date();
                    try {
                        const [h, m, s] = filename.split('.')[0].split('-');
                        if (datePart) createdAt = new Date(datePart);
                        if (h && m && s) createdAt.setHours(h, m, s);
                    } catch (e) {}

                    return {
                        id: path, // Use path as ID for playback key
                        file_path: path,
                        name: "My Rant ",
                        created_at: createdAt.toISOString(),
                        duration: null // Unknown
                    };
                 });
              } else {
                 // If no paths in diary (legacy), fallback to passed recordings if array, else empty
                 displayList = Array.isArray(recordings) ? recordings : [];
              }

              if (displayList.length === 0) {
                 return <div style={{fontStyle: 'italic', color: 'var(--text-tertiary)', fontSize: '0.9rem'}}>No recordings for today.</div>;
              }

              return displayList.map((rec) => (
              <div 
                key={rec.id} 
                className={`recording-card ${activeId === rec.id ? 'is-playing' : ''}`} 
                onClick={() => handlePlay(rec)}
              >
               {activeId === rec.id && (
                  <div className="progress-overlay" style={{width: `${progress}%`}} />
               )}
                <div className="card-icon">
                  {activeId === rec.id && isPlaying ? (
                    <Pause size={20} fill="currentColor" />
                  ) : (
                    <Play size={20} fill="currentColor" />
                  )}
                </div>

                <div className="card-info">
                   <div className="info-row main">
                      <span>{rec.name || "Recording"}</span>
                   </div>
                   <div className="info-row sub">
                      {Number.isFinite(rec.duration) && (
                        <>
                          <span className="duration-badge">
                            <Clock size={12} /> 
                            {Math.floor(rec.duration / 60)}:{(rec.duration % 60).toString().padStart(2, '0')}
                          </span>
                          <span>•</span>
                        </>
                      )}
                      <span>
                        {new Date(rec.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                      </span>
                   </div>
                </div>
              </div>
            ));
            })()}
          </div>

          <button 
            onClick={onRegenerate}
            className="regenerate-btn"
          >
             <RotateCw size={16} />
             Regenerate Diary
          </button>
        </div>
      </div>
    </div>
  );
};

export default DiaryView;
