import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, MoreHorizontal, Volume2 } from 'lucide-react';
import { API_ROUTES, BASE_URL } from '../api/routes';
import axiosClient from '../api/axiosClient';

const RecordingCard = ({ recording, onPlay, onDelete, compact = false }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [words, setWords] = useState([]);
  const [currentText, setCurrentText] = useState("");
  const [loadingTranscription, setLoadingTranscription] = useState(false);
  const audioRef = useRef(null);

  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  const fetchTranscription = async () => {
    if (words.length > 0 || !recording.transcription_id) {
      console.log("Transcription already fetched or no id:", { wordsLen: words.length, tid: recording.transcription_id });
      return;
    }
    
    try {
      setLoadingTranscription(true);
      console.log("Fetching transcription for id:", recording.transcription_id);
      const res = await axiosClient.get(API_ROUTES.TRANSCRIPTIONS.DETAIL(recording.transcription_id));
      console.log("Transcription response:", res.data);
      if (res.data.code === 'SUCCESS') {
        const data = res.data.data;
        if (data.words && data.words.length > 0) {
          console.log("Setting words:", data.words);
          setWords(data.words);
        } else if (data.text) {
          console.log("No words found, using fallback text:", data.text);
          setWords([{ start: 0, end: recording.duration_seconds || 3600, text: data.text }]);
        }
      }
    } catch (err) {
      console.error("Failed to fetch transcription", err);
    } finally {
      setLoadingTranscription(false);
    }
  };



  useEffect(() => {
    if (!audioRef.current) return;
    
    const audio = audioRef.current;
    
    const handleTimeUpdate = () => {
      if (audio.duration) {
        const time = audio.currentTime;
        setProgress((time / audio.duration) * 100);
        
        // Find active word in NEWEST scope
        if (words.length > 0) {
          const active = words.find(s => {
            const start = parseFloat(s.start);
            const end = parseFloat(s.end);
            return time >= start && time <= end;
          });

          if (active) {
            const cleanText = active.text.trim();
            if (cleanText !== currentText) {
              setCurrentText(cleanText);
            }
          } else if (currentText) {
            setCurrentText("");
          }
        }
      }
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setProgress(0);
      setCurrentText("");
    };

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('ended', handleEnded);
    };
  }, [words, currentText]); // Re-attach when data changes to avoid stale closures

  const togglePlay = (e) => {
    e.stopPropagation(); // Prevent card click

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      if (!audioRef.current) {
        const url = `${BASE_URL}${API_ROUTES.AUDIO_BASE}/${recording.file_path}`;
        audioRef.current = new Audio(url);
      }
      
      if (String(recording.transcription_status || '').toLowerCase() === 'completed') {
        fetchTranscription();
      }

      audioRef.current.play().catch(err => console.error("Playback failed", err));
      setIsPlaying(true);
    }
  };

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
          <div className="compact-title">{recording.name || 'Untitled'}</div>
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
  
  const radius = 16;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  const isTranscriptionCompleted = String(recording.transcription_status || '').toLowerCase() === 'completed';

  return (
    <div className="recording-card-wrapper">
      <div className="recording-card">
        <div className={`play-button-wrapper ${!isTranscriptionCompleted ? 'is-accent' : ''}`} onClick={togglePlay}>
          <svg className="progress-ring" width="36" height="36">
             <circle
               className="progress-ring__circle-bg"
               stroke={!isTranscriptionCompleted ? "rgba(20, 184, 166, 0.15)" : "#f3f4f6"}
               strokeWidth="3.5"
               fill="transparent"
               r={radius}
               cx="18"
               cy="18"
             />
             <circle
               className="progress-ring__circle"
               stroke={!isTranscriptionCompleted ? "var(--accent-primary)" : "#4b5563"}
               strokeWidth="3.5"
               strokeLinecap="round"
               fill="transparent"
               r={radius}
               cx="18"
               cy="18"
               style={{
                   strokeDasharray: `${circumference} ${circumference}`,
                   strokeDashoffset: strokeDashoffset,
                   transform: 'rotate(-90deg)',
                   transformOrigin: '50% 50%',
                   transition: 'stroke-dashoffset 0.1s linear'
               }}
             />
          </svg>
          <div className={`play-icon-center ${!isTranscriptionCompleted ? 'is-accent' : ''}`}>
              {isPlaying ? (
                  <Pause size={13} fill="currentColor" stroke="currentColor" />
              ) : (
                  <Play size={13} fill="currentColor" stroke="currentColor" />
              )}
          </div>
        </div>
        
        <div className="card-content">
          <div className="card-title-row">
            <span className="card-title">{recording.name || 'In My Head'}</span>
            <Volume2 size={14} className="speaker-icon" />
          </div>
          <div className="card-meta">
            {formatTime(recording.recorded_at)} - {formatDuration(recording.duration_seconds)}
          </div>
        </div>

        {/* Live Transcription Section */}
        {isPlaying && (
          <div className="live-text-container">
            {loadingTranscription ? (
              <div className="live-text-loading">•••</div>
            ) : currentText ? (
              <div key={currentText} className="live-text-fade">
                {currentText}
              </div>
            ) : words.length > 0 ? (
               <div className="live-text-waiting">Listening...</div>
            ) : null}
          </div>
        )}
        
        <button className="menu-button">
          <MoreHorizontal size={18} />
        </button>
      </div>

      <style>{`
        .recording-card-wrapper {
          margin-bottom: 0.75rem;
          width: 100%;
        }

        .recording-card {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.875rem 1rem;
          background: var(--bg-card);
          border-radius: 4px;
          box-shadow: var(--shadow-sm);
          transition: all 0.2s ease;
          cursor: pointer;
          position: relative;
          min-height: 72px;
        }
        
        .recording-card:hover {
          box-shadow: var(--shadow-md);
          transform: translateY(-1px);
        }
        
        .play-button-wrapper {
            position: relative;
            width: 36px;
            height: 36px;
            cursor: pointer;
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .play-icon-center {
            position: absolute;
            color: #374151;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
        }

        .play-icon-center.is-accent {
            color: var(--accent-primary);
        }
        
        .card-content {
          flex: 0 1 auto;
          min-width: 0;
          max-width: 180px;
          transition: all 0.3s ease;
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

        /* Live Text Styles on the Right - Shifted Leftward */
        .live-text-container {
          flex: 1;
          padding-left: 0.75rem;
          border-left: 1px solid #f3f4f6;
          margin-left: 0.5rem;
          display: flex;
          align-items: center;
          height: 32px;
          min-width: 0;
        }

        .live-text-fade {
          font-size: 0.875rem;
          line-height: 1.4;
          color: var(--accent-primary);
          font-weight: 500;
          font-style: italic;
          opacity: 1;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          animation: textFadeIn 0.4s ease-out;
        }

        @keyframes textFadeIn {
          from { opacity: 0; transform: translateX(5px); }
          to { opacity: 0.9; transform: translateX(0); }
        }

        .live-text-loading {
          color: var(--accent-primary);
          opacity: 0.5;
          font-size: 0.75rem;
          letter-spacing: 1px;
        }

        .live-text-waiting {
          color: var(--text-tertiary);
          font-size: 0.75rem;
          font-style: italic;
          animation: pulse 1.5s infinite;
        }

        @keyframes pulse {
          0% { opacity: 0.4; }
          50% { opacity: 0.8; }
          100% { opacity: 0.4; }
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
          margin-left: auto;
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
