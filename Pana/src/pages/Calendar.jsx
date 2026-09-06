import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useCalendar } from '../hooks/queries/useCalendar';
import '../styles/calendar.css';

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

/** ISO date for a day in the shown month, without crossing a timezone. */
const isoFor = (date, day) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

/**
 * A long, thin arrow.
 *
 * Lucide's chevrons are short and blunt at this size. The reference draws a
 * drawn line with a small head -- the gesture of turning a page rather than a
 * button glyph -- which is a shaft long enough to read as a stroke.
 */
const LongArrow = ({ direction }) => (
  <svg
    width="60"
    height="20"
    viewBox="0 0 60 20"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.4"
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

/**
 * A month, marked by what each day holds.
 *
 * The URL is the single source of truth for which month is shown. Mirroring it
 * into state means two things to keep in sync, and the effect that did so was
 * one comparison away from an update loop.
 */
const Calendar = () => {
  const { year: urlYear, month: urlMonth } = useParams();
  const navigate = useNavigate();

  // A day with nothing in it answers a press instead of ignoring it: it
  // flashes red for a moment. Silence would leave you unsure the click landed.
  const [rejected, setRejected] = useState(null);

  const currentDate =
    urlYear && urlMonth
      ? new Date(parseInt(urlYear, 10), parseInt(urlMonth, 10) - 1, 1)
      : new Date();

  const { data } = useCalendar(
    currentDate.getFullYear(),
    currentDate.getMonth() + 1,
  );
  const diaryDays = data?.diaryDays ?? new Set();
  const recordingDays = data?.recordingDays ?? new Set();

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const startWeekday = new Date(year, month, 1).getDay();

  const today = new Date();
  const isCurrentMonth =
    today.getFullYear() === year && today.getMonth() === month;

  const step = (delta) => {
    const target = new Date(year, month + delta, 1);
    navigate(`/calendar/${target.getFullYear()}/${target.getMonth() + 1}`);
  };

  // Leading blanks before the first, and trailing blanks after the last, so
  // the grid always ends on a complete week. A ragged final row leaves the
  // card's bottom edge broken.
  const leading = Array.from({ length: startWeekday }, () => null);
  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1);
  const trailing = Array.from(
    { length: (7 - ((startWeekday + daysInMonth) % 7)) % 7 },
    () => null,
  );
  const cells = [...leading, ...days, ...trailing];

  return (
    <div className="cal">
      <header className="cal__head">
        <button
          type="button"
          className="cal__arrow"
          onClick={() => step(-1)}
          aria-label="Previous month"
        >
          <LongArrow direction="left" />
        </button>

        <h1 className="cal__month">
          {currentDate.toLocaleString(undefined, { month: 'long' })} {year}
        </h1>

        <button
          type="button"
          className="cal__arrow"
          onClick={() => step(1)}
          aria-label="Next month"
        >
          <LongArrow direction="right" />
        </button>
      </header>

      <div className="cal__grid">
        {WEEKDAYS.map((day) => (
          <div key={day} className="cal__weekday">
            {day}
          </div>
        ))}

        {cells.map((day, i) => {
          if (day === null)
            return (
              <div key={`pad-${i}`} className="cal__day cal__day--empty" />
            );

          const written = diaryDays.has(day);
          const recorded = recordingDays.has(day);
          const filled = written || recorded;
          const isToday = isCurrentMonth && today.getDate() === day;

          // Teal for a day written up, grey for one only recorded. A day with
          // nothing carries no standing mark -- red on every quiet day makes
          // the month tiring to look at, so it appears only in answer to a
          // press.
          const mark = written ? 'diary' : 'recording';
          const isRejected = rejected === day;
          const label = written
            ? `${day}: diary written`
            : recorded
              ? `${day}: recordings, no diary yet`
              : `${day}: nothing recorded`;

          return (
            <button
              key={day}
              type="button"
              className={`cal__day ${filled ? 'cal__day--filled' : 'cal__day--bare'}${
                isToday ? ' cal__day--today' : ''
              }${isRejected ? ' cal__day--rejected' : ''}`}
              aria-label={label}
              onClick={() => {
                if (filled) {
                  navigate(`/diary/${isoFor(currentDate, day)}`);
                  return;
                }
                setRejected(day);
                window.setTimeout(
                  () => setRejected((d) => (d === day ? null : d)),
                  600,
                );
              }}
            >
              {filled && (
                <span className={`cal__blob cal__blob--${mark}`} aria-hidden="true" />
              )}
              {isRejected && <span className="cal__blob cal__blob--missed" aria-hidden="true" />}
              <span className="cal__num">{day}</span>
            </button>
          );
        })}
      </div>

      <div className="cal__key">
        <span className="cal__key-item">
          <span className="cal__swatch cal__swatch--diary" />
          Diary written
        </span>
        <span className="cal__key-item">
          <span className="cal__swatch cal__swatch--recording" />
          Recorded, not yet written
        </span>

      </div>
    </div>
  );
};

export default Calendar;
