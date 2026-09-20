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

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Play, Pause, Trash2, Loader2 } from 'lucide-react';
import { useTranscription } from '@app/hooks/queries/useRecordings.js';
import { API_ROUTES } from '../lib/routes.js';
import { getServerOrigin } from '../lib/serverStore.js';
import { getAccessToken } from '../lib/tokenStore.js';
import '../styles/recording-row.css';

/**
 * Words kept on screen, trailing the one being spoken.
 *
 * The line ends at the current word and never runs ahead of it: a transcript
 * that shows what is coming reads the recording out before it plays. Behind
 * it, enough words to fill two lines at this width, because the phrase
 * leading up to now is what makes the current word mean anything -- a
 * four-word line replaced wholesale gives the eye nothing to hold onto.
 */
const WINDOW_WORDS = 14;

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
  // The words on screen, and which of them is being said now. An object
  // rather than a string: the highlight needs to move through the line
  // without the line itself changing.
  const [spoken, setSpoken] = useState({ words: [], current: -1 });

  // The transcript is only wanted once playback has started: most rows are
  // never played, and fetching every one of them on mount would be a request
  // per row for text nobody is reading.
  const [wantsTranscript, setWantsTranscript] = useState(false);

  const audioRef = useRef(null);
  const objectUrlRef = useRef(null);

  const status = String(recording.transcription_status || '').toLowerCase();
  const transcribing = status === 'pending' || status === 'processing';
  const isTranscribed = status === 'completed';

  // isFetching, not isPending: a disabled query reports pending forever, which
  // would leave the waiting line up for a row that has no transcript.
  const { data: transcription, isFetching: loadingTranscript } = useTranscription(
    recording.transcription_id,
    { enabled: wantsTranscript },
  );

  // Only timed words drive the rolling line. A whole-transcript fallback would
  // pin the same text on screen for the recording's whole length, which reads
  // as frozen rather than as following along.
  const words = useMemo(() => transcription?.words ?? [], [transcription]);

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
    const response = await fetch(`${getServerOrigin()}${base}/${recording.file_path}`, {
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
      setSpoken({ words: [], current: -1 });
    };
    audioRef.current = audio;
    return audio;
  }, [recording.file_path]);

  // The window over the words, recomputed on each tick of the playing audio.
  // Attached only while playing: the element does not exist before the first
  // press, and there is nothing to follow along with once it stops.
  //
  // The window holds its position for several words at a time and the
  // highlight travels through it, rather than the whole line being replaced on
  // every word. Reading is easier when the text stays still.
  useEffect(() => {
    const audio = audioRef.current;
    if (!playing || !audio || words.length === 0) return undefined;

    const handleTimeUpdate = () => {
      const time = audio.currentTime;
      const lastSaid = words.findLastIndex((word) => time >= parseFloat(word.start));
      if (lastSaid < 0) {
        setSpoken({ words: [], current: -1 });
        return;
      }

      // The line ends at the word being said: nothing ahead of it is shown,
      // since a transcript that runs in front of the audio reads the recording
      // out before it plays. It grows up to the window size and then trails
      // it, keeping the phrase that led up to now.
      const start = Math.max(0, lastSaid - WINDOW_WORDS + 1);

      setSpoken({
        words: words.slice(start, lastSaid + 1),
        current: lastSaid - start,
      });
    };

    audio.addEventListener('timeupdate', handleTimeUpdate);
    return () => audio.removeEventListener('timeupdate', handleTimeUpdate);
  }, [playing, words]);

  const togglePlay = async () => {
    if (playing) {
      audioRef.current?.pause();
      setPlaying(false);
      return;
    }

    setLoading(true);
    try {
      const audio = await ensureAudio();
      if (isTranscribed) setWantsTranscript(true);
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
      <div className="row__main">
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
      </div>

      {/* What is being said, as it plays. Below the row rather than beside it
          so the words get the full width and can wrap -- a transcript squeezed
          into a column and clipped is not readable, which is the only thing it
          is for. */}
      {playing && (
        <p
          className={`row__transcript${spoken.words.length ? '' : ' row__transcript--waiting'}`}
          aria-live="polite"
        >
          {spoken.words.length
            ? spoken.words.map((word, i) => (
                <span
                  // The index is the key because the same word recurs in a
                  // sentence and the list is a window, not a collection.
                  key={i}
                  className={`row__word${i === spoken.current ? ' is-current' : ''}`}
                >
                  {word.text.trim()}{' '}
                </span>
              ))
            : loadingTranscript
              ? ''
              : 'The words for this one are not ready yet'}
        </p>
      )}
    </article>
  );
}
