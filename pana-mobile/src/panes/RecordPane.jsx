/**
 * The middle pane: record, and today's recordings beneath.
 *
 * This is what the app opens on. The control is the largest thing on screen
 * and sits where a thumb rests, because the whole point of the app is that
 * speaking should cost nothing.
 *
 * @module panes/RecordPane
 */

import { useCallback, useState } from 'react';
import { Mic, Square, Pause, Play } from 'lucide-react';
import { toast } from 'sonner';
import Waveform from '@app/components/Waveform.jsx';
import { useAudioRecorder } from '@app/hooks/useAudioRecorder.js';
import {
  useApplyTranscriptionComplete,
  useCreateRecording,
  useDeleteRecording,
  useRecordings,
} from '@app/hooks/queries/useRecordings.js';
import { useTranscriptionSSE } from '../lib/useTranscriptionSSE.js';
import ConfirmSheet from '../components/ConfirmSheet.jsx';
import RecordingRow from '../components/RecordingRow.jsx';
import '@app/styles/recorder.css';
import '../styles/record-pane.css';

/** Duration as m:ss, for the live timer. */
const formatDuration = (seconds) => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${String(secs).padStart(2, '0')}`;
};

export default function RecordPane() {
  const [saving, setSaving] = useState(false);

  // The recording awaiting confirmation, or null. Deleting is the one
  // irreversible thing in the app, and a row's delete button sits under the
  // thumb while scrolling a list.
  const [pendingDelete, setPendingDelete] = useState(null);

  const {
    isRecording,
    isPaused,
    duration,
    audioData,
    startRecording,
    pauseRecording,
    resumeRecording,
    stopRecording,
    getAudioBlob,
    resetRecording,
  } = useAudioRecorder();

  const { data, isPending } = useRecordings({ pageSize: 50 });
  const createRecording = useCreateRecording();
  const deleteRecording = useDeleteRecording();

  // Live transcription updates. The callback is stable, so the stream is
  // opened once rather than on every render.
  const applyComplete = useApplyTranscriptionComplete();
  useTranscriptionSSE(applyComplete);

  const recordings = data?.recordings ?? [];

  const handleStop = useCallback(async () => {
    stopRecording();

    // MediaRecorder flushes its last chunk asynchronously; reading the blob in
    // the same tick would miss the tail of the recording.
    await new Promise((resolve) => setTimeout(resolve, 250));

    const blob = getAudioBlob();
    if (!blob.size) {
      resetRecording();
      return;
    }

    setSaving(true);
    try {
      await createRecording.mutateAsync({ file: blob, durationSeconds: duration });
      resetRecording();
    } catch (error) {
      console.error('Upload failed', error);
      toast.error('Could not save that recording');
    } finally {
      setSaving(false);
    }
  }, [createRecording, duration, getAudioBlob, resetRecording, stopRecording]);

  const handleConfirmDelete = useCallback(async () => {
    if (pendingDelete === null) return;
    try {
      await deleteRecording.mutateAsync(pendingDelete);
    } catch (error) {
      console.error('Delete failed', error);
      toast.error('Could not delete that recording');
    } finally {
      setPendingDelete(null);
    }
  }, [deleteRecording, pendingDelete]);

  const handleStart = useCallback(async () => {
    try {
      await startRecording();
    } catch (error) {
      console.error('Microphone unavailable', error);
      toast.error('Microphone permission is needed to record');
    }
  }, [startRecording]);

  return (
    <div className="pane record">
      <header className="record__head">
        <h1 className="pane__title">Today</h1>
        <p className="pane__subtitle">
          {isRecording ? formatDuration(duration) : `${recordings.length} recording${recordings.length === 1 ? '' : 's'}`}
        </p>
      </header>

      <div className="record__stage">
        <Waveform audioData={Array.from(audioData)} isRecording={isRecording} isPaused={isPaused} />
      </div>

      <div className="record__controls">
        {isRecording && (
          <button
            type="button"
            className="record__secondary"
            onClick={isPaused ? resumeRecording : pauseRecording}
            aria-label={isPaused ? 'Resume' : 'Pause'}
          >
            {isPaused ? <Play size={20} fill="currentColor" /> : <Pause size={20} fill="currentColor" />}
          </button>
        )}

        <button
          type="button"
          className={`record__button ${isRecording ? 'is-recording' : ''}`}
          onClick={isRecording ? handleStop : handleStart}
          disabled={saving}
          aria-label={isRecording ? 'Stop recording' : 'Start recording'}
        >
          {isRecording ? <Square size={26} fill="currentColor" /> : <Mic size={28} />}
        </button>

        {isRecording && <span className="record__secondary record__secondary--ghost" aria-hidden="true" />}
      </div>

      {saving && <p className="record__saving">Saving…</p>}

      <section className="record__list">
        {isPending && <p className="pane__empty">Loading…</p>}
        {!isPending && recordings.length === 0 && (
          <p className="pane__empty">Nothing yet today. Press the button and talk.</p>
        )}
        {recordings.map((recording) => (
          <RecordingRow
            key={recording.id}
            recording={recording}
            onDelete={(id) => setPendingDelete(id)}
          />
        ))}
      </section>

      <ConfirmSheet
        open={pendingDelete !== null}
        onCancel={() => setPendingDelete(null)}
        onConfirm={handleConfirmDelete}
        title="Delete this recording?"
        message={
          recordings.length === 1
            ? 'This is the only recording for today, so today\u2019s diary entry goes with it. This cannot be undone.'
            : 'The audio and its transcript are removed for good. This cannot be undone.'
        }
      />
    </div>
  );
}
