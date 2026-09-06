import React from 'react';
import '../styles/page.css';

/**
 * The invitation to write a day up.
 *
 * Shown when a day has recordings but no entry yet. It says what will happen
 * and what it will be made from, rather than describing the feature.
 */
const CreateDiary = ({ onCreate, loading, count = 0, isToday = true }) => (
  <div className="page page--single">
    <h1 className="page__title">{isToday ? 'Today, unwritten' : 'This day, unwritten'}</h1>

    <div className="state">
      <p className="state__line">
        {count} {count === 1 ? 'recording is' : 'recordings are'} waiting to be read back.
      </p>
      <p className="state__hint">
        Pana listens through {count === 1 ? 'it' : 'them'} and writes the day as prose, with
        anything you said you would do gathered at the end.
      </p>

      <div className="state__action">
        <button type="button" className="action" onClick={onCreate} disabled={loading}>
          {loading ? 'Writing' : 'Write this day'}
        </button>
      </div>
    </div>
  </div>
);

export default CreateDiary;
