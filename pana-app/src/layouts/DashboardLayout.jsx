import React, { useCallback } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import { useTranscriptionSSE } from '../hooks/useTranscriptionSSE';
import { useApplyTranscriptionComplete } from '../hooks/queries/useRecordings';
import '../styles/shell.css';

/**
 * The shell around every authenticated page.
 *
 * The transcription stream is subscribed here rather than on the page that
 * happens to start a recording. Transcription finishes in the background,
 * often a minute after the user has moved on -- so a subscription that lives
 * on one page means every other screen shows stale rows until it is reloaded.
 * One connection for the whole session, opened where the session lives.
 */
const DashboardLayout = () => {
  const applyTranscriptionComplete = useApplyTranscriptionComplete();

  const handleTranscriptionComplete = useCallback(
    (recordingId, transcriptionId) => applyTranscriptionComplete(recordingId, transcriptionId),
    [applyTranscriptionComplete],
  );

  useTranscriptionSSE(handleTranscriptionComplete);

  return (
    <div className="shell">
      <Sidebar />
      <main className="shell__main">
        <Outlet />
      </main>
    </div>
  );
};

export default DashboardLayout;
