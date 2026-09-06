import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { Play, Pause, MoreHorizontal } from 'lucide-react';
import recordingsService from '../services/recordings.service';
import { useTranscription } from '../hooks/queries/useRecordings';
import '../styles/clip.css';

const RING_RADIUS = 17;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

/** Words held on screen at once, as a rolling window over the playing audio. */
const WINDOW_WORDS = 4;

/** Clock time of a recording, e.g. "9:14 AM". */
const formatClock = (iso) =>
  new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });

/** Duration as m:ss. */
const formatDuration = (seconds) => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${String(secs).padStart(2, '0')}`;
};

/**
 * One recording, as a row in the day's thread.
 *
 * Playback is owned here rather than lifted: each row plays its own audio, and
 * the transcript is fetched only once someone presses play.
 */
const RecordingCard = ({
  recording,
  onDelete,
  compact = false,
  showMenu = false,
  onMenuToggle,
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [spokenText, setSpokenText] = useState('');
  const [wantsTranscript, setWantsTranscript] = useState(false);
  const [menuPos, setMenuPos] = useState(null);

  const audioRef = useRef(null);
  const menuBtnRef = useRef(null);

  // isFetching, not isPending: a disabled query reports pending forever, which
  // would leave the loading indicator up for a card that has no transcript.
  const { data: transcription, isFetching: loadingTranscript } = useTranscription(
    recording.transcription_id,
    { enabled: wantsTranscript },
  );

  const isTranscribed = String(recording.transcription_status || '').toLowerCase() === 'completed';

  // Only timed words drive the rolling line. The whole-transcript fallback was
  // dropped deliberately: a single segment spanning the recording would pin
  // the same text on screen for its whole length, which reads as frozen rather
  // than as following along.
  const words = useMemo(() => transcription?.words ?? [], [transcription]);

  /** Create the audio element on first play; the route needs cookies. */
  const getAudio = useCallback(() => {
    if (!audioRef.current) {
      const audio = new Audio();
      audio.crossOrigin = 'use-credentials';
      audio.src = recordingsService.audioUrl(recording.file_path);
      audioRef.current = audio;
    }
    return audioRef.current;
  }, [recording.file_path]);

  useEffect(
    () => () => {
      audioRef.current?.pause();
      audioRef.current = null;
    },
    [],
  );

  // Listeners are attached when playback starts rather than on mount: the
  // element does not exist until then, so an effect that reads audioRef on
  // mount binds to nothing and the progress ring never moves.
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !isPlaying) return undefined;

    const handleTimeUpdate = () => {
      if (!audio.duration) return;
      const time = audio.currentTime;
      setProgress((time / audio.duration) * 100);

      if (!words.length) return;

      // A short rolling window rather than the whole transcript so far: one
      // word at a time is unreadable, and everything-so-far grows without
      // bound and needs a scrollbar. A few words move at about the pace of
      // speech and stay on one line, so the text can be followed while the
      // audio plays without the row changing height.
      const lastSaid = words.findLastIndex((w) => time >= parseFloat(w.start));
      if (lastSaid < 0) {
        setSpokenText('');
        return;
      }

      const recent = words.slice(Math.max(0, lastSaid - WINDOW_WORDS + 1), lastSaid + 1);
      setSpokenText(recent.map((w) => w.text.trim()).join(' '));
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setProgress(0);
      setSpokenText('');
    };

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('ended', handleEnded);
    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('ended', handleEnded);
    };
  }, [isPlaying, words]);

  const togglePlay = (event) => {
    event.stopPropagation();

    if (isPlaying) {
      audioRef.current?.pause();
      setIsPlaying(false);
      return;
    }

    const audio = getAudio();
    if (isTranscribed) setWantsTranscript(true);
    audio.play().then(
      () => setIsPlaying(true),
      (error) => console.error('Playback failed', error),
    );
  };

  useEffect(() => {
    if (showMenu && menuBtnRef.current) {
      const rect = menuBtnRef.current.getBoundingClientRect();
      setMenuPos({ top: rect.bottom + 6, right: window.innerWidth - rect.right });
    } else {
      setMenuPos(null);
    }
  }, [showMenu]);

  const playLabel = `${isPlaying ? 'Pause' : 'Play'} recording from ${formatClock(recording.recorded_at)}`;

  return (
    <div className={`clip${compact ? ' clip--compact' : ''}`}>
      <div className="clip__row">
      <button type="button" className="clip__play" onClick={togglePlay} aria-label={playLabel}>
        <svg className="clip__ring" width="38" height="38" aria-hidden="true">
          <circle
            className="clip__ring-track"
            cx="19"
            cy="19"
            r={RING_RADIUS}
            fill="none"
            strokeWidth="1.5"
          />
          <circle
            className="clip__ring-value"
            cx="19"
            cy="19"
            r={RING_RADIUS}
            fill="none"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeDasharray={RING_CIRCUMFERENCE}
            strokeDashoffset={RING_CIRCUMFERENCE - (progress / 100) * RING_CIRCUMFERENCE}
          />
        </svg>
        <span className="clip__glyph">
          {isPlaying ? (
            <Pause size={12} fill="currentColor" stroke="currentColor" />
          ) : (
            <Play size={12} fill="currentColor" stroke="currentColor" />
          )}
        </span>
      </button>

      <div className="clip__body">
        <div className="clip__time figure">{formatClock(recording.recorded_at)}</div>
        <div className="clip__meta figure">{formatDuration(recording.duration_seconds)}</div>
      </div>

      {onDelete && (
        <>
          <button
            ref={menuBtnRef}
            type="button"
            className={`clip__menu-trigger${showMenu ? ' clip__menu-trigger--open' : ''}`}
            onClick={(event) => {
              event.stopPropagation();
              onMenuToggle?.();
            }}
            aria-label="Recording options"
            aria-expanded={showMenu}
          >
            <MoreHorizontal size={16} />
          </button>

          {showMenu &&
            menuPos &&
            createPortal(
              <div
                className="clip__menu"
                style={{ position: 'fixed', top: menuPos.top, right: menuPos.right, zIndex: 200 }}
                onClick={(event) => event.stopPropagation()}
              >
                <button
                  type="button"
                  className="clip__menu-item clip__menu-item--destructive"
                  onClick={(event) => {
                    event.stopPropagation();
                    onDelete(recording.id);
                  }}
                >
                  Delete
                </button>
              </div>,
              document.body,
            )}
        </>
      )}
      </div>

      {/* What is being said, as it plays. Kept below the row rather than
          beside it so the words get the full width and can wrap -- a
          transcript squeezed into a column and clipped is not readable, which
          is the only thing it is for. */}
      {isPlaying && (
        <p
          className={`clip__transcript${spokenText ? '' : ' clip__transcript--waiting'}`}
          aria-live="polite"
        >
          {spokenText || (loadingTranscript ? '' : 'The words for this one are not ready yet')}
        </p>
      )}
    </div>
  );
};

export default RecordingCard;
