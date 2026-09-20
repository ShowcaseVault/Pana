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
import { CalendarDays, Mic, BookOpen } from 'lucide-react';
import CalendarPane from '../panes/CalendarPane.jsx';
import RecordPane from '../panes/RecordPane.jsx';
import DiaryPane from '../panes/DiaryPane.jsx';
import '../styles/shell.css';

/* The indicator names the three panes. An icon says which pane each one is
   far faster than a dot does, without becoming a chrome bar: the swipe is
   still the way you move, and this floats above the content saying where you
   are and offering the jump. */
const PANES = [
  { name: 'Calendar', Icon: CalendarDays },
  { name: 'Record', Icon: Mic },
  { name: 'Diary', Icon: BookOpen },
];

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

  // Where the track actually is, as a fraction of a pane width. Separate from
  // `index` so the marker can be mid-travel while the settled pane is still
  // the one behind it.
  const [offset, setOffset] = useState(RECORD_INDEX);
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

  // Track the scroll position, for the indicator. Reading it directly beats
  // onScrollEnd, which Safari does not implement.
  //
  // Two values, because they answer different questions. `index` is the pane
  // that has settled, which is what the tabs mark as current and what the
  // panes are told about; `offset` is the fractional position, which the
  // marker follows so it travels with the drag instead of waiting for it to
  // finish and then jumping.
  const handleScroll = useCallback((event) => {
    const track = event.currentTarget;
    const position = track.scrollLeft / track.clientWidth;

    setOffset(position);

    const current = Math.round(position);
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

      <nav
        className="shell__dots"
        aria-label="Panes"
        // The marker's geometry, in one place: the button size and the step
        // between buttons are the gap plus that size, and the CSS derives the
        // travel from them rather than repeating the numbers.
        style={{ '--size': '2rem', '--step': 'calc(2rem + 0.25rem)', '--index': offset }}
      >
        <span className="shell__marker" aria-hidden="true" />

        {PANES.map(({ name, Icon }, i) => (
          <button
            key={name}
            type="button"
            className={`shell__dot ${i === index ? 'is-active' : ''}`}
            aria-label={name}
            aria-current={i === index}
            onClick={() => goTo(i)}
          >
            <Icon size={17} aria-hidden="true" />
          </button>
        ))}
      </nav>
    </div>
  );
}
