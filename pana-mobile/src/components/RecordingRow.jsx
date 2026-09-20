/**
 * One recording, as a row in the day's list.
 *
 * The web card streams its audio straight from the authenticated media route:
 * an `<audio>` element there carries the session cookie. On a device there is
 * no cookie and an element cannot be given an `Authorization` header, so the
 * file is fetched with one and handed to the element as a blob URL instead.
 *
 * @module components/RecordingRow
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Play, Pause, Trash2, Loader2 } from 'lucide-react';
import { API_ROUTES } from '../lib/routes.js';
import { getAccessToken } from '../lib/tokenStore.js';
import '../styles/recording-row.css';

/** Clock time of a recording, e.g. "9:14 AM". */
const formatClock = (iso) =>
  new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });

/** Duration as m:ss. */
const formatDuration = (seconds = 0) => {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${String(secs).padStart(2, '0')}`;
};

export default function RecordingRow({ recording, onDelete }) {
  const [playing, setPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);

  const audioRef = useRef(null);
  const objectUrlRef = useRef(null);

  const status = String(recording.transcription_status || '').toLowerCase();
  const transcribing = status === 'pending' || status === 'processing';

  // A blob URL holds its data until it is revoked, so a list of played
  // recordings would otherwise keep every file in memory.
  useEffect(
    () => () => {
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
      audioRef.current?.pause();
    },
    [],
  );

  /** Fetch the audio once, with the bearer header, and cache the blob URL. */
  const ensureAudio = useCallback(async () => {
    if (audioRef.current) return audioRef.current;

    const base = API_ROUTES.AUDIO_BASE.replace(/\/$/, '');
    const response = await fetch(`${API_ROUTES.ORIGIN}${base}/${recording.file_path}`, {
      headers: { Authorization: `Bearer ${getAccessToken()}` },
    });
    if (!response.ok) throw new Error(`Audio failed: ${response.status}`);

    const url = URL.createObjectURL(await response.blob());
    objectUrlRef.current = url;

    const audio = new Audio(url);
    audio.ontimeupdate = () =>
      setProgress(audio.duration ? (audio.currentTime / audio.duration) * 100 : 0);
    audio.onended = () => {
      setPlaying(false);
      setProgress(0);
    };
    audioRef.current = audio;
    return audio;
  }, [recording.file_path]);

  const togglePlay = async () => {
    if (playing) {
      audioRef.current?.pause();
      setPlaying(false);
      return;
    }

    setLoading(true);
    try {
      const audio = await ensureAudio();
      await audio.play();
      setPlaying(true);
    } catch (error) {
      console.error('Playback failed', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <article className="row">
      <button
        type="button"
        className={`row__play ${playing ? 'is-playing' : ''}`}
        onClick={togglePlay}
        aria-label={playing ? 'Pause' : 'Play'}
        disabled={loading}
      >
        {loading ? (
          <Loader2 size={17} className="row__spin" />
        ) : playing ? (
          <Pause size={17} fill="currentColor" />
        ) : (
          <Play size={17} fill="currentColor" />
        )}
        {progress > 0 && (
          <span className="row__progress" style={{ '--progress': `${progress}%` }} />
        )}
      </button>

      <div className="row__body">
        <span className="row__time">{formatClock(recording.recorded_at)}</span>
        <span className="row__meta">
          {formatDuration(recording.duration_seconds)}
          {transcribing && (
            <>
              <span className="row__dot" aria-hidden="true" />
              <span className="row__transcribing">
                <span className="row__pulse" aria-hidden="true" />
                Transcribing
              </span>
            </>
          )}
        </span>
      </div>

      {onDelete && (
        <button
          type="button"
          className="row__delete"
          onClick={() => onDelete(recording.id)}
          aria-label="Delete recording"
        >
          <Trash2 size={16} />
        </button>
      )}
    </article>
  );
}
