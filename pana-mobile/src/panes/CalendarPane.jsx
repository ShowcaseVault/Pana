/**
 * The left pane: a month at a glance.
 *
 * The same reading as the web calendar, at thumb scale. A day that holds
 * something carries a soft blob washed behind the date -- teal once it has
 * been written up, grey while it is only recorded. A day with nothing carries
 * no standing mark: red appears only in answer to a press, and fades, because
 * most days in most months are quiet and a month showing red throughout is
 * tiring to look at.
 *
 * The grid always ends on a complete week, so the card's bottom edge stays
 * straight, and it is centred in the pane rather than pinned to the top --
 * there is nothing else on this screen, so the month is the screen.
 *
 * @module panes/CalendarPane
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useCalendar } from '@app/hooks/queries/useCalendar.js';
import '../styles/calendar-pane.css';

const WEEKDAYS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

/** How long the red answer to an empty day stays on screen. */
const REJECT_MS = 600;

/** Local ISO date, without the UTC shift `toISOString` would add. */
const isoFor = (year, month, day) =>
  `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

/**
 * A long, thin arrow.
 *
 * Matches the web calendar: a drawn line with a small head, the gesture of
 * turning a page rather than a button glyph. A chevron at this size reads as a
 * control, which is the wrong note for moving through months.
 */
const LongArrow = ({ direction }) => (
  <svg
    width="38"
    height="14"
    viewBox="0 0 60 20"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.6"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
    focusable="false"
    style={direction === 'left' ? { transform: 'scaleX(-1)' } : undefined}
  >
    <line x1="2" y1="10" x2="56" y2="10" />
    <polyline points="47,3 56,10 47,17" />
  </svg>
);

export default function CalendarPane({ selectedDate, onSelectDate }) {
  const today = useMemo(() => new Date(), []);
  const [view, setView] = useState({ year: today.getFullYear(), month: today.getMonth() + 1 });

  // The day that answered a press with nothing. Held here rather than derived,
  // since it is a moment rather than a state of the data.
  const [rejected, setRejected] = useState(null);
  const rejectTimer = useRef(null);

  useEffect(() => () => window.clearTimeout(rejectTimer.current), []);

  const { data } = useCalendar(view.year, view.month);
  const diaryDays = data?.diaryDays ?? new Set();
  const recordingDays = data?.recordingDays ?? new Set();

  // Leading blanks put the first of the month under its weekday; trailing
  // blanks complete the final week, so the card never ends ragged.
  const cells = useMemo(() => {
    const startWeekday = new Date(view.year, view.month - 1, 1).getDay();
    const daysInMonth = new Date(view.year, view.month, 0).getDate();
    const trailing = (7 - ((startWeekday + daysInMonth) % 7)) % 7;

    return [
      ...Array.from({ length: startWeekday }, () => null),
      ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
      ...Array.from({ length: trailing }, () => null),
    ];
  }, [view]);

  const step = (delta) => {
    setView(({ year, month }) => {
      const next = month + delta;
      if (next < 1) return { year: year - 1, month: 12 };
      if (next > 12) return { year: year + 1, month: 1 };
      return { year, month: next };
    });
  };

  const reject = useCallback((day) => {
    setRejected(day);
    window.clearTimeout(rejectTimer.current);
    rejectTimer.current = window.setTimeout(
      () => setRejected((current) => (current === day ? null : current)),
      REJECT_MS,
    );
  }, []);

  const isCurrentMonth =
    today.getFullYear() === view.year && today.getMonth() + 1 === view.month;

  const monthName = new Date(view.year, view.month - 1, 1).toLocaleString(undefined, {
    month: 'long',
  });

  return (
    <div className="pane calendar">
      <h1 className="pane__title calendar__title">Calendar</h1>

      <header className="calendar__head">
        <button
          type="button"
          className="calendar__arrow"
          onClick={() => step(-1)}
          aria-label="Previous month"
        >
          <LongArrow direction="left" />
        </button>

        <h2 className="calendar__month">
          {monthName} <span className="calendar__year">{view.year}</span>
        </h2>

        <button
          type="button"
          className="calendar__arrow"
          onClick={() => step(1)}
          aria-label="Next month"
        >
          <LongArrow direction="right" />
        </button>
      </header>

      <div className="calendar__grid">
        {WEEKDAYS.map((day, i) => (
          <div key={i} className="calendar__weekday">
            {day}
          </div>
        ))}

        {cells.map((day, i) => {
          if (day === null) return <div key={`pad-${i}`} className="calendar__day is-empty" />;

          const written = diaryDays.has(day);
          const recorded = recordingDays.has(day);
          const filled = written || recorded;
          const iso = isoFor(view.year, view.month, day);
          const isToday = isCurrentMonth && today.getDate() === day;
          const isRejected = rejected === day;

          const label = written
            ? `${day}: diary written`
            : recorded
              ? `${day}: recordings, no diary yet`
              : `${day}: nothing recorded`;

          return (
            <button
              key={iso}
              type="button"
              className={[
                'calendar__day',
                filled ? 'is-filled' : 'is-bare',
                isToday && 'is-today',
                iso === selectedDate && 'is-selected',
              ]
                .filter(Boolean)
                .join(' ')}
              aria-label={label}
              aria-current={isToday ? 'date' : undefined}
              onClick={() => (filled ? onSelectDate(iso) : reject(day))}
            >
              {filled && (
                <span
                  className={`calendar__blob calendar__blob--${written ? 'diary' : 'recording'}`}
                  aria-hidden="true"
                />
              )}
              {isRejected && (
                <span className="calendar__blob calendar__blob--missed" aria-hidden="true" />
              )}
              <span className="calendar__num">{day}</span>
            </button>
          );
        })}
      </div>

      <div className="calendar__key">
        <span className="calendar__key-item">
          <span className="calendar__swatch calendar__swatch--diary" />
          Written
        </span>
        <span className="calendar__key-item">
          <span className="calendar__swatch calendar__swatch--recording" />
          Recorded
        </span>
      </div>
    </div>
  );
}
