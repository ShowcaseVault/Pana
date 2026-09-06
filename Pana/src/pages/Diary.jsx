import React from 'react';
import { useParams } from 'react-router-dom';
import { toast } from 'sonner';
import CreateDiary from '../components/CreateDiary';
import DiaryView from '../components/Diary/DiaryView';
import { useDiary, useGenerateDiary } from '../hooks/queries/useDiary';
import { useRecordings } from '../hooks/queries/useRecordings';
import '../styles/page.css';

/** Today as an ISO date string, in the user's own timezone. */
const todayIso = () => {
  const now = new Date();
  const offsetMs = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offsetMs).toISOString().split('T')[0];
};

const Diary = () => {
  const { date } = useParams();
  const targetDate = date || todayIso();
  const isToday = targetDate === todayIso();

  const { data: recordingsPage, isPending: loadingRecordings } = useRecordings({
    recordingDate: targetDate,
    pageSize: 100,
  });
  const recordings = recordingsPage?.recordings ?? [];

  const { data: diary, isPending: loadingDiary } = useDiary(targetDate);
  const generateDiary = useGenerateDiary();

  const handleCreateDiary = async () => {
    try {
      await generateDiary.mutateAsync(targetDate);
    } catch (error) {
      toast.error(error.message);
    }
  };

  if (loadingRecordings || loadingDiary) {
    return (
      <div className="page page--single">
        <div className="skeleton" aria-label="Loading diary">
          <div className="skeleton__bar" />
          <div className="skeleton__bar" />
          <div className="skeleton__bar" />
        </div>
      </div>
    );
  }

  const hasEntry = Boolean(diary?.content);
  const hasRecordings = recordings.length > 0;

  // Today with nothing written yet gets the invitation; a past day gets the
  // entry it has, or an explanation of why it has none.
  if (hasEntry) {
    return (
      <DiaryView
        diary={diary}
        recordings={recordings}
        onRegenerate={handleCreateDiary}
        loading={generateDiary.isPending}
      />
    );
  }

  if (hasRecordings) {
    return (
      <CreateDiary
        onCreate={handleCreateDiary}
        loading={generateDiary.isPending}
        count={recordings.length}
        isToday={isToday}
      />
    );
  }

  return (
    <div className="page page--single">
      <h1 className="page__title">{new Date(targetDate).toLocaleDateString(undefined, {
        weekday: 'long', day: 'numeric', month: 'long',
      })}</h1>
      <div className="state">
        <p className="state__line">
          {isToday ? 'Nothing recorded yet today.' : 'Nothing was recorded this day.'}
        </p>
        <p className="state__hint">
          {isToday
            ? 'Pana writes the day up from what you record. Speak for a minute and come back.'
            : 'A diary is written from recordings, and there are none for this date.'}
        </p>
      </div>
    </div>
  );
};

export default Diary;
