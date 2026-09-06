import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import RecordingCard from '../components/RecordingCard';
import { useRecordings } from '../hooks/queries/useRecordings';
import { useDiary } from '../hooks/queries/useDiary';
import '../styles/page.css';

/** "Good morning" / "Good afternoon" / "Good evening", by local hour. */
const greeting = () => {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
};

const today = () =>
  new Date().toLocaleDateString(undefined, {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  });

/** Today as YYYY-MM-DD in local time, which is how the backend keys a day. */
const todayIso = () => {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(
    now.getDate(),
  ).padStart(2, '0')}`;
};

/** Total minutes across a day's recordings, rounded to whole minutes. */
const totalMinutes = (recordings) =>
  Math.round(recordings.reduce((sum, r) => sum + r.duration_seconds, 0) / 60);

/**
 * Today.
 *
 * The main column is what the person actually said today, in order. The aside
 * carries the day's standing -- how much was recorded, and whether it has been
 * written up yet -- which is the question this screen exists to answer and the
 * one that decides what to do next.
 */
const Home = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  // No filter: the backend scopes an unfiltered list to today, which is
  // exactly this page's subject.
  const { data, isPending } = useRecordings({ pageSize: 50 });
  const recordings = data?.recordings ?? [];

  const iso = todayIso();
  const { data: diary } = useDiary(iso);

  const firstName = user?.name?.split(' ')[0];
  const minutes = totalMinutes(recordings);

  return (
    <div className="page">
      <div className="page__main">
        <h1 className="page__title">
          {greeting()}
          {firstName ? `, ${firstName}` : ''}
        </h1>
        <p className="page__subtitle figure">{today()}</p>

        <section className="page__section">
          <div className="page__section-head">
            <h2 className="page__section-title">Today</h2>
            {recordings.length > 0 && (
              <span className="page__section-note figure">
                {recordings.length} {recordings.length === 1 ? 'recording' : 'recordings'}
              </span>
            )}
          </div>

          {isPending ? (
            <div className="skeleton" aria-label="Loading today's recordings">
              <div className="skeleton__bar" />
              <div className="skeleton__bar" />
              <div className="skeleton__bar" />
            </div>
          ) : recordings.length > 0 ? (
            <>
              <div>
                {recordings.map((recording) => (
                  <RecordingCard key={recording.id} recording={recording} compact />
                ))}
              </div>
              <div className="state__action">
                <button type="button" className="action" onClick={() => navigate('/recordings')}>
                  Record again
                </button>
              </div>
            </>
          ) : (
            <div className="state">
              <p className="state__line">Nothing recorded yet today.</p>
              <p className="state__hint">
                Speak for a minute about what is on your mind. Pana transcribes it and writes the
                day up for you.
              </p>
              <div className="state__action">
                <button type="button" className="action" onClick={() => navigate('/recordings')}>
                  Start recording
                </button>
              </div>
            </div>
          )}
        </section>
      </div>

      <aside className="page__aside">
        <div className="page__aside-block">
          <h2 className="page__aside-title">Captured</h2>
          <div className="page__stat">
            <span className="page__stat-value figure">{recordings.length}</span>
            <span className="page__stat-label">
              {recordings.length === 1 ? 'recording' : 'recordings'}
            </span>
          </div>
          <div className="page__stat">
            <span className="page__stat-value figure">{minutes}</span>
            <span className="page__stat-label">{minutes === 1 ? 'minute' : 'minutes'}</span>
          </div>
        </div>

        <div className="page__aside-block">
          <h2 className="page__aside-title">Diary</h2>
          {diary ? (
            <>
              <p className="page__aside-note">Today has been written up.</p>
              <button
                type="button"
                className="action action--quiet"
                onClick={() => navigate(`/diary/${iso}`)}
              >
                Read it
              </button>
            </>
          ) : recordings.length > 0 ? (
            <>
              <p className="page__aside-note">
                {recordings.length === 1 ? 'One recording is' : `${recordings.length} recordings are`}{' '}
                waiting to be made into an entry.
              </p>
              <button
                type="button"
                className="action action--quiet"
                onClick={() => navigate(`/diary/${iso}`)}
              >
                Write today
              </button>
            </>
          ) : (
            <p className="page__aside-note">
              Record something first — the entry is written from what you say.
            </p>
          )}
        </div>
      </aside>
    </div>
  );
};

export default Home;
