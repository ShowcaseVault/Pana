/**
 * The three-pane swipe surface.
 *
 * Calendar, Record, Diary sit side by side on one horizontal track and the
 * user swipes between them. Record is the middle pane and the one the app
 * opens on: recording is the reason to open Pana, and putting it in the centre
 * makes either neighbour one gesture away.
 *
 * Paging is CSS scroll-snap rather than a gesture library. The browser's own
 * touch scrolling is already momentum-correct and interruptible, which a
 * JS-driven transform is not without a great deal of work.
 *
 * @module screens/Shell
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import CalendarPane from '../panes/CalendarPane.jsx';
import RecordPane from '../panes/RecordPane.jsx';
import DiaryPane from '../panes/DiaryPane.jsx';
import '../styles/shell.css';

const PANES = ['Calendar', 'Record', 'Diary'];
const RECORD_INDEX = 1;
const DIARY_INDEX = 2;

/** Local ISO date (`YYYY-MM-DD`). `toISOString` would shift by the UTC offset. */
function todayIso() {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

export default function Shell() {
  const trackRef = useRef(null);
  const [index, setIndex] = useState(RECORD_INDEX);
  const [diaryDate, setDiaryDate] = useState(todayIso);

  /** Scroll one pane into view. */
  const goTo = useCallback((target, behavior = 'smooth') => {
    const track = trackRef.current;
    if (!track) return;
    track.scrollTo({ left: target * track.clientWidth, behavior });
  }, []);

  // Open on Record. The jump is instant and pre-paint, so the user never sees
  // the calendar slide past.
  useEffect(() => {
    goTo(RECORD_INDEX, 'auto');
  }, [goTo]);

  // Track which pane is settled, for the indicator dots. Reading scroll
  // position beats onScrollEnd, which Safari does not implement.
  const handleScroll = useCallback((event) => {
    const track = event.currentTarget;
    const current = Math.round(track.scrollLeft / track.clientWidth);
    setIndex((previous) => (previous === current ? previous : current));
  }, []);

  /** A calendar day was chosen: show that day's entry and swipe to it. */
  const openDiaryFor = useCallback(
    (isoDate) => {
      setDiaryDate(isoDate);
      goTo(DIARY_INDEX);
    },
    [goTo],
  );

  return (
    <div className="shell">
      <div className="shell__track" ref={trackRef} onScroll={handleScroll}>
        <section className="shell__pane" aria-label="Calendar">
          <CalendarPane selectedDate={diaryDate} onSelectDate={openDiaryFor} />
        </section>
        <section className="shell__pane" aria-label="Record">
          <RecordPane active={index === RECORD_INDEX} />
        </section>
        <section className="shell__pane" aria-label="Diary">
          <DiaryPane date={diaryDate} onChangeDate={setDiaryDate} />
        </section>
      </div>

      <nav className="shell__dots" aria-label="Panes">
        {PANES.map((name, i) => (
          <button
            key={name}
            type="button"
            className={`shell__dot ${i === index ? 'is-active' : ''}`}
            aria-label={name}
            aria-current={i === index}
            onClick={() => goTo(i)}
          />
        ))}
      </nav>
    </div>
  );
}
