import React, { useState, useEffect } from "react";
import AudioRecorder from "../components/AudioRecorder";
import RecordingCard from "../components/RecordingCard";
import ConfirmDialog from "../components/ConfirmDialog";
import { Toaster, toast } from "sonner";
import {
  useCreateRecording,
  useDeleteRecording,
  useRecordings,
} from "../hooks/queries/useRecordings";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import "../styles/page.css";

/**
 * Record.
 *
 * Two columns, as designed: today's recordings listed down the left, and the
 * recorder itself centred in the space that remains. The recorder is what the
 * screen is for, so it gets the middle of the window and the only bright
 * colour in the interface; the list stays quiet beside it.
 */
const Recordings = () => {
  useDocumentTitle('Record');

  const [activeMenuId, setActiveMenuId] = useState(null);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [recordingToDelete, setRecordingToDelete] = useState(null);
  const [locationText, setLocationText] = useState("");

  // The backend already scopes an unfiltered list to today, so this page asks
  // for exactly what it shows rather than fetching everything and filtering.
  const { data, isPending: loading, isError } = useRecordings({ pageSize: 50 });
  const recordings = data?.recordings ?? [];

  const createRecording = useCreateRecording();
  const deleteRecording = useDeleteRecording();

  useEffect(() => {
    if (isError) toast.error("Could not load today’s recordings.");
  }, [isError]);

  // Location is optional context on a recording; a refusal is not an error.
  useEffect(() => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => setLocationText(`${coords.latitude},${coords.longitude}`),
      (error) => console.warn("Geolocation unavailable:", error),
    );
  }, []);

  useEffect(() => {
    const dismiss = () => setActiveMenuId(null);
    document.addEventListener("click", dismiss);
    return () => document.removeEventListener("click", dismiss);
  }, []);

  // Errors surface in the recorder, which owns the saving state.
  const handleUpload = async (file, duration) => {
    await createRecording.mutateAsync({
      file,
      durationSeconds: duration,
      locationText: locationText || undefined,
    });
  };

  const confirmDelete = async () => {
    if (!recordingToDelete) return;
    try {
      await deleteRecording.mutateAsync(recordingToDelete);
      toast.success("Recording deleted");
    } catch (error) {
      toast.error(error.message);
    } finally {
      setRecordingToDelete(null);
      setIsConfirmOpen(false);
    }
  };

  const totalSeconds = recordings.reduce(
    (sum, r) => sum + r.duration_seconds,
    0,
  );

  return (
    <div className="studio">
      <aside className="studio__list">
        <div className="page__section-head">
          <h2 className="page__section-title">Today&rsquo;s recordings</h2>
          {recordings.length > 0 && (
            <span className="page__section-note figure">
              {Math.round(totalSeconds / 60)} min
            </span>
          )}
        </div>

        {loading ? (
          <div className="skeleton" aria-label="Loading recordings">
            <div className="skeleton__bar" />
            <div className="skeleton__bar" />
          </div>
        ) : recordings.length > 0 ? (
          <div>
            {recordings.map((recording) => (
              <RecordingCard
                key={recording.id}
                recording={recording}
                compact
                onDelete={(id) => {
                  setRecordingToDelete(id);
                  setIsConfirmOpen(true);
                  setActiveMenuId(null);
                }}
                showMenu={activeMenuId === recording.id}
                onMenuToggle={() =>
                  setActiveMenuId((current) =>
                    current === recording.id ? null : recording.id,
                  )
                }
              />
            ))}
          </div>
        ) : (
          <div className="state">
            <p className="state__line">Nothing yet today.</p>
            <p className="state__hint">
              Recordings appear here as soon as you stop.
            </p>
          </div>
        )}

      </aside>

      <main className="studio__stage">
        <AudioRecorder onRecordingComplete={handleUpload} />
      </main>

      <ConfirmDialog
        isOpen={isConfirmOpen}
        onClose={() => setIsConfirmOpen(false)}
        onConfirm={confirmDelete}
        title="Delete this recording?"
        message={
          recordings.length === 1
            ? 'This is the only recording for today, so today\u2019s diary entry will be removed with it. This cannot be undone.'
            : 'The audio and its transcript are removed for good. This cannot be undone.'
        }
        confirmLabel="Delete"
      />

      <Toaster position="bottom-right" />
    </div>
  );
};

export default Recordings;
