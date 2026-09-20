/**
 * The left pane: a month at a glance.
 *
 * A day is marked when it holds something. Tapping one opens its entry, which
 * means swiping right to the diary pane -- the calendar is a way into the
 * writing, not a destination.
 *
 * @module panes/CalendarPane
 */

import { useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useCalendar } from '@app/hooks/queries/useCalendar.js';
import '../styles/calendar-pane.css';

const WEEKDAYS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

/** Local ISO date for a year/month/day, without the UTC shift `toISOString` adds. */
const isoFor = (year, month, day) =>
  `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

export default function CalendarPane({ selectedDate, onSelectDate }) {
  const today = new Date();
  const [view, setView] = useState({ year: today.getFullYear(), month: today.getMonth() + 1 });

  const { data } = useCalendar(view.year, view.month);
  const diaryDays = data?.diaryDays ?? new Set();
  const recordingDays = data?.recordingDays ?? new Set();

  // Leading blanks align the first of the month under its weekday.
  const cells = useMemo(() => {
    const firstWeekday = new Date(view.year, view.month - 1, 1).getDay();
    const daysInMonth = new Date(view.year, view.month, 0).getDate();
    return [
      ...Array.from({ length: firstWeekday }, () => null),
      ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
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

  const todayIso = isoFor(today.getFullYear(), today.getMonth() + 1, today.getDate());

  return (
    <div className="pane calendar">
      <header className="calendar__head">
        <button type="button" onClick={() => step(-1)} aria-label="Previous month">
          <ChevronLeft size={20} />
        </button>
        <h1 className="calendar__month">
          {MONTHS[view.month - 1]} <span>{view.year}</span>
        </h1>
        <button type="button" onClick={() => step(1)} aria-label="Next month">
          <ChevronRight size={20} />
        </button>
      </header>

      <div className="calendar__weekdays" aria-hidden="true">
        {WEEKDAYS.map((day, i) => (
          <span key={i}>{day}</span>
        ))}
      </div>

      <div className="calendar__grid">
        {cells.map((day, i) => {
          if (day === null) return <span key={`blank-${i}`} className="calendar__blank" />;

          const iso = isoFor(view.year, view.month, day);
          const classes = [
            'calendar__day',
            diaryDays.has(day) && 'has-diary',
            recordingDays.has(day) && 'has-recording',
            iso === selectedDate && 'is-selected',
            iso === todayIso && 'is-today',
          ]
            .filter(Boolean)
            .join(' ');

          return (
            <button
              key={iso}
              type="button"
              className={classes}
              onClick={() => onSelectDate(iso)}
              aria-current={iso === todayIso ? 'date' : undefined}
            >
              {day}
              {(diaryDays.has(day) || recordingDays.has(day)) && (
                <span className="calendar__mark" aria-hidden="true" />
              )}
            </button>
          );
        })}
      </div>

      <p className="calendar__legend">Tap a marked day to read its entry.</p>
    </div>
  );
}
