import React from 'react';
import { useParams } from 'react-router-dom';
import { toast } from 'sonner';
import CreateDiary from '../components/CreateDiary';
import DiaryView from '../components/Diary/DiaryView';
import { useDiary, useGenerateDiary } from '../hooks/queries/useDiary';
import { useRecordings } from '../hooks/queries/useRecordings';

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
      <div className="flex items-center justify-center h-full">
         <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  // Check if diary has content - if content is null, treat as not created
  const hasDiaryContent = diary && diary.content !== null;
  const hasRecordings = recordings.length > 0;

  let contentToRender;

  if (hasDiaryContent) {
    contentToRender = (
      <DiaryView 
        diary={diary} 
        recordings={recordings} 
        onRegenerate={handleCreateDiary} 
        loading={generateDiary.isPending} 
      />
    );
  } else if (isToday) {
    // For today, show the specific CreateDiary landing page
    contentToRender = (
      <CreateDiary 
        onCreate={handleCreateDiary} 
        loading={generateDiary.isPending} 
      />
    );
  } else if (hasRecordings) {
    // For past dates with recordings, show DiaryView in "empty" state
    // ensuring we pass a valid object structure so DiaryView doesn't crash
    const placeholderDiary = diary || {
      diary_date: targetDate,
      mood: null,
      content: null,
      actions: []
    };
    
    contentToRender = (
      <DiaryView 
        diary={placeholderDiary} 
        recordings={recordings} 
        onRegenerate={handleCreateDiary} 
        loading={generateDiary.isPending} 
      />
    );
  } else {
    // Past date, no recordings, no diary
    contentToRender = (
      <div className="flex flex-col items-center justify-center h-full text-gray-500">
          <p>No diary entry for this date.</p>
      </div>
    );
  }

  return (
    <div className="p-6 h-full">
      {contentToRender}
    </div>
  );
};

export default Diary;
