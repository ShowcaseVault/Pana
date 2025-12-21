import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axiosClient from '../api/axiosClient';
import { API_ROUTES } from '../api/routes';
import '../styles/themes.css';

const Calendar = () => {
  const { year: urlYear, month: urlMonth } = useParams();
  const navigate = useNavigate();
  
  // Initialize date from URL or current date
  const [currentDate, setCurrentDate] = useState(() => {
    if (urlYear && urlMonth) {
      return new Date(parseInt(urlYear), parseInt(urlMonth) - 1, 1);
    }
    return new Date();
  });

  const [diaryDays, setDiaryDays] = useState(new Set());
  const [recordingDays, setRecordingDays] = useState(new Set());

  // Update currentDate when URL params change
  useEffect(() => {
    if (urlYear && urlMonth) {
      const year = parseInt(urlYear);
      const month = parseInt(urlMonth) - 1;
      // Only update if it's actually different from current state to avoid loops
      if (currentDate.getFullYear() !== year || currentDate.getMonth() !== month) {
        setCurrentDate(new Date(year, month, 1));
      }
    }
  }, [urlYear, urlMonth]);

  useEffect(() => {
    fetchCalendarData();
  }, [currentDate]);

  const fetchCalendarData = async () => {
    try {
      const year = currentDate.getFullYear();
      const month = currentDate.getMonth() + 1; // API expects 1-indexed month
      
      const response = await axiosClient.get(API_ROUTES.HISTORY.CALENDAR(year, month));
      
      if (response.data.code === "SUCCESS" && response.data.data) {
        const { diary_days, recording_days } = response.data.data;
        setDiaryDays(new Set(diary_days || []));
        setRecordingDays(new Set(recording_days || []));
      }
    } catch (error) {
      console.error('Failed to fetch calendar data:', error);
    }
  };

  const getDaysInMonth = (date) => {
    const year = date.getFullYear();
    const month = date.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startingDayOfWeek = firstDay.getDay();

    return { daysInMonth, startingDayOfWeek };
  };

  const getBlobType = (day) => {
    // Return 'diary' if day has diary entry, 'recording' if only recordings, null otherwise
    if (diaryDays.has(day)) {
      return 'diary';
    } else if (recordingDays.has(day)) {
      return 'recording';
    }
    return null;
  };

  const goToPreviousMonth = () => {
    const prevDate = new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1);
    navigate(`/calendar/${prevDate.getFullYear()}/${prevDate.getMonth() + 1}`);
  };

  const goToNextMonth = () => {
    const nextDate = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1);
    navigate(`/calendar/${nextDate.getFullYear()}/${nextDate.getMonth() + 1}`);
  };

  const { daysInMonth, startingDayOfWeek } = getDaysInMonth(currentDate);
  const monthName = currentDate.toLocaleString('default', { month: 'long' });
  const year = currentDate.getFullYear();

  const weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const calendarDays = [];

  // Add empty cells for days before the first day of the month
  for (let i = 0; i < startingDayOfWeek; i++) {
    calendarDays.push(null);
  }

  // Add all days of the month
  for (let day = 1; day <= daysInMonth; day++) {
    calendarDays.push(day);
  }

  // Fill remaining cells to make exactly 35 cells (5 rows × 7 columns)
  while (calendarDays.length < 35) {
    calendarDays.push(null);
  }

  return (
    <div className="calendar-container">
      <div className="calendar-header">
        <button onClick={goToPreviousMonth} className="nav-button">
          <svg width="80" height="28" viewBox="0 0 80 28" fill="none" xmlns="http://www.w3.org/2000/svg">
            <line x1="70" y1="14" x2="18" y2="14" stroke="var(--text-secondary)" strokeWidth="1.5" strokeLinecap="round" />
            <path d="M 10 14 L 18 9 L 18 14 L 18 19 Z" fill="var(--text-secondary)" />
          </svg>
        </button>
        <h1 className="month-year">{monthName} {year}</h1>
        <button onClick={goToNextMonth} className="nav-button">
          <svg width="80" height="28" viewBox="0 0 80 28" fill="none" xmlns="http://www.w3.org/2000/svg">
            <line x1="10" y1="14" x2="62" y2="14" stroke="var(--text-secondary)" strokeWidth="1.5" strokeLinecap="round" />
            <path d="M 70 14 L 62 9 L 62 14 L 62 19 Z" fill="var(--text-secondary)" />
          </svg>
        </button>
      </div>

      <div className="calendar-grid">
        <div className="weekday-header">
          {weekDays.map(day => (
            <div key={day} className="weekday-label">{day}</div>
          ))}
        </div>

        <div className="days-grid">
          {calendarDays.map((day, index) => {
            const blobType = day ? getBlobType(day) : null;
            return (
              <div key={index} className="day-cell">
                {day && (
                  <>
                    <span className="day-number">{day}</span>
                    {blobType && (
                      <div className={`recording-blob ${blobType === 'diary' ? 'blob-diary' : 'blob-recording'}`} />
                    )}
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&display=swap');

        .calendar-container {
          width: 100%;
          height: calc(100vh - 10px);
          padding: 1.5rem 2.5rem 1rem 2.5rem;
          background: var(--bg-primary);
          display: flex;
          flex-direction: column;
          box-sizing: border-box;
        }

        .calendar-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 1.5rem;
          flex-shrink: 0;
          position: relative;
        }

        .nav-button {
          background: transparent;
          border: none;
          color: var(--text-secondary);
          cursor: pointer;
          padding: 0.5rem;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all 0.3s ease;
        }

        .nav-button:hover {
          opacity: 0.7;
          transform: scale(1.05);
        }

        .month-year {
          font-size: 2.25rem;
          font-weight: 700;
          color: var(--text-primary);
          margin: 0;
          flex: 1;
          text-align: center;
          font-family: 'Playfair Display', serif;
          letter-spacing: 0.02em;
        }

        .calendar-grid {
          flex: 1;
          display: flex;
          flex-direction: column;
          min-height: 0;
          background: var(--bg-card);
          border-radius: 16px;
          box-shadow: var(--shadow-md);
          overflow: hidden;
          border: 2px solid var(--bg-tertiary);
          padding: 8px;
        }

        .weekday-header {
          display: grid;
          grid-template-columns: repeat(7, 1fr);
          background: var(--bg-card);
          border-bottom: 2px solid var(--bg-tertiary);
        }

        .weekday-label {
          text-align: center;
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--text-secondary);
          text-transform: uppercase;
          letter-spacing: 0.1em;
          padding: 1rem 0;
        }

        .days-grid {
          display: grid;
          grid-template-columns: repeat(7, 1fr);
          grid-template-rows: repeat(5, 1fr);
          flex: 1;
          min-height: 0;
        }

        .day-cell {
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
          background: var(--bg-card);
          border-right: 1px solid var(--bg-tertiary);
          border-bottom: 1px solid var(--bg-tertiary);
          transition: all 0.2s ease;
        }

        .day-cell:nth-child(7n) {
          border-right: none;
        }

        .day-cell:nth-child(n+29) {
          border-bottom: none;
        }

        .day-cell:hover {
          background: rgba(79, 209, 197, 0.05);
          cursor: pointer;
        }

        .day-number {
          font-size: 1.1rem;
          font-weight: 500;
          color: var(--text-primary);
          z-index: 1;
        }

.recording-blob {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 85%;
  height: 85%;
  z-index: 0;
  filter: blur(8px);
}

/* Diary blob - vibrant accent colors */
.recording-blob.blob-diary::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(ellipse at 40% 40%, rgba(79, 209, 197, 0.5) 0%, transparent 70%),
              radial-gradient(ellipse at 60% 60%, rgba(56, 178, 172, 0.45) 0%, transparent 65%),
              radial-gradient(ellipse at 50% 50%, rgba(79, 209, 197, 0.4) 0%, transparent 80%);
  border-radius: 45% 55% 52% 48% / 48% 52% 48% 52%;
  opacity: 0.35;
  animation: watercolorFlow 4s ease-in-out infinite;
}

.recording-blob.blob-diary::after {
  content: '';
  position: absolute;
  top: -5%;
  left: -5%;
  right: -5%;
  bottom: -5%;
  background: radial-gradient(ellipse at 30% 70%, rgba(56, 178, 172, 0.4) 0%, transparent 60%),
              radial-gradient(ellipse at 70% 30%, rgba(79, 209, 197, 0.35) 0%, transparent 55%);
  border-radius: 52% 48% 55% 45% / 45% 55% 52% 48%;
  opacity: 0.25;
  animation: watercolorFlow 5s ease-in-out infinite reverse;
}

/* Recording-only blob - muted gray colors */
.recording-blob.blob-recording::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: radial-gradient(ellipse at 40% 40%, rgba(113, 128, 150, 0.5) 0%, transparent 70%),
              radial-gradient(ellipse at 60% 60%, rgba(113, 128, 150, 0.45) 0%, transparent 65%),
              radial-gradient(ellipse at 50% 50%, rgba(113, 128, 150, 0.4) 0%, transparent 80%);
  border-radius: 45% 55% 52% 48% / 48% 52% 48% 52%;
  opacity: 0.35;
  animation: watercolorFlow 4s ease-in-out infinite;
}

.recording-blob.blob-recording::after {
  content: '';
  position: absolute;
  top: -5%;
  left: -5%;
  right: -5%;
  bottom: -5%;
  background: radial-gradient(ellipse at 30% 70%, rgba(113, 128, 150, 0.4) 0%, transparent 60%),
              radial-gradient(ellipse at 70% 30%, rgba(113, 128, 150, 0.35) 0%, transparent 55%);
  border-radius: 52% 48% 55% 45% / 45% 55% 52% 48%;
  opacity: 0.25;
  animation: watercolorFlow 5s ease-in-out infinite reverse;
}

@keyframes watercolorFlow {
  0%, 100% {
    border-radius: 45% 55% 52% 48% / 48% 52% 48% 52%;
    transform: rotate(0deg) scale(1);
    opacity: 0.3;
  }
  25% {
    border-radius: 52% 48% 45% 55% / 55% 45% 52% 48%;
    transform: rotate(1deg) scale(1.02);
    opacity: 0.35;
  }
  50% {
    border-radius: 48% 52% 55% 45% / 45% 55% 48% 52%;
    transform: rotate(-1deg) scale(0.98);
    opacity: 0.32;
  }
  75% {
    border-radius: 55% 45% 48% 52% / 52% 48% 55% 45%;
    transform: rotate(0.5deg) scale(1.01);
    opacity: 0.37;
  }
}
        @media (max-width: 1024px) {
          .calendar-container {
            padding: 1.5rem;
          }

          .month-year {
            font-size: 1.25rem;
            min-width: 180px;
          }

          .day-number {
            font-size: 0.8rem;
          }
        }

        @media (max-width: 768px) {
          .calendar-container {
            padding: 1rem;
          }

          .month-year {
            font-size: 1.1rem;
            min-width: 150px;
          }

          .day-number {
            font-size: 0.75rem;
          }

          .weekday-label {
            font-size: 0.65rem;
          }

          .calendar-grid {
            gap: 0.5rem;
          }

          .days-grid {
            gap: 0.35rem;
          }
        }
      `}</style>
    </div>
  );
};

export default Calendar;
