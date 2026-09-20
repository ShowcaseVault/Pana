/**
 * The right pane: the day's entry.
 *
 * The date shown is owned by the shell, so a tap in the calendar lands here on
 * the right day. A day with recordings but no entry offers to write one; the
 * generation is slow, so the button says what it is doing.
 *
 * @module panes/DiaryPane
 */

import { useState } from 'react';
import { ChevronLeft, ChevronRight, Sparkles, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useDiary, useGenerateDiary } from '@app/hooks/queries/useDiary.js';
import { useRecordings } from '@app/hooks/queries/useRecordings.js';
import '../styles/diary-pane.css';

/** Local ISO date, without the UTC shift `toISOString` adds. */
const toIso = (date) => {
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 10);
};

/** "Monday, 3 March" -- the year only when it is not this one. */
const formatDay = (iso) => {
  const date = new Date(`${iso}T00:00:00`);
  const sameYear = date.getFullYear() === new Date().getFullYear();
  return date.toLocaleDateString(undefined, {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    ...(sameYear ? {} : { year: 'numeric' }),
  });
};

export default function DiaryPane({ date, onChangeDate }) {
  const [generating, setGenerating] = useState(false);

  const { data: diary, isPending } = useDiary(date);
  const { data: recordingData } = useRecordings({ recordingDate: date, listAll: true });
  const generate = useGenerateDiary();

  const recordingCount = recordingData?.recordings?.length ?? 0;

  const step = (days) => {
    const next = new Date(`${date}T00:00:00`);
    next.setDate(next.getDate() + days);
    onChangeDate(toIso(next));
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await generate.mutateAsync(date);
    } catch (error) {
      console.error('Diary generation failed', error);
      toast.error('Could not write that entry');
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="pane diary">
      <header className="diary__head">
        <button type="button" onClick={() => step(-1)} aria-label="Previous day">
          <ChevronLeft size={20} />
        </button>
        <h1 className="diary__date">{formatDay(date)}</h1>
        <button
          type="button"
          onClick={() => step(1)}
          aria-label="Next day"
          disabled={date >= toIso(new Date())}
        >
          <ChevronRight size={20} />
        </button>
      </header>

      {isPending && <p className="pane__empty">Loading…</p>}

      {!isPending && diary?.content && (
        <article className="diary__body">
          {diary.content.split('\n\n').map((paragraph, i) => (
            <p key={i}>{paragraph}</p>
          ))}
        </article>
      )}

      {!isPending && !diary?.content && (
        <div className="diary__blank">
          {recordingCount > 0 ? (
            <>
              <p className="pane__empty">
                {recordingCount} recording{recordingCount === 1 ? '' : 's'} from this day, not yet
                written up.
              </p>
              <button
                type="button"
                className="diary__generate"
                onClick={handleGenerate}
                disabled={generating}
              >
                {generating ? <Loader2 size={17} className="diary__spin" /> : <Sparkles size={17} />}
                {generating ? 'Writing…' : 'Write this day'}
              </button>
            </>
          ) : (
            <p className="pane__empty">Nothing recorded on this day.</p>
          )}
        </div>
      )}
    </div>
  );
}
