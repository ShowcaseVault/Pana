import React, { useState, useEffect, useCallback } from 'react';
import AudioRecorder from '../components/AudioRecorder';
import RecordingCard from '../components/RecordingCard';
import ConfirmDialog from '../components/ConfirmDialog';
import { Toaster, toast } from 'sonner';
import '../styles/themes.css';

import { useTranscriptionSSE } from '../hooks/useTranscriptionSSE';
import {
  useApplyTranscriptionComplete,
  useCreateRecording,
  useDeleteRecording,
  useRecordings,
} from '../hooks/queries/useRecordings';

const Recordings = () => {
  const [activeMenuId, setActiveMenuId] = useState(null);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [recordingToDelete, setRecordingToDelete] = useState(null);

  // The backend already scopes an unfiltered list to today, so this page asks
  // for exactly what it shows rather than fetching everything and filtering.
  const { data, isPending: loading, isError } = useRecordings({ pageSize: 50 });
  const recordings = data?.recordings ?? [];

  const createRecording = useCreateRecording();
  const deleteRecording = useDeleteRecording();
  const applyTranscriptionComplete = useApplyTranscriptionComplete();

  useEffect(() => {
    if (isError) toast.error('Failed to load recordings');
  }, [isError]);

  // Memoised so the SSE connection is not torn down and rebuilt each render.
  const handleTranscriptionComplete = useCallback(
    (recordingId, transcriptionId) => applyTranscriptionComplete(recordingId, transcriptionId),
    [applyTranscriptionComplete],
  );

  useTranscriptionSSE(handleTranscriptionComplete);

  const [locationText, setLocationText] = useState("");

  useEffect(() => {
    fetchLocation();
  }, []);

  const fetchLocation = () => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setLocationText(`${latitude},${longitude}`);
      },
      (error) => console.warn("Geolocation permission denied or error:", error)
    );
  };

  const handleUpload = async (file, duration) => {
    try {
      await createRecording.mutateAsync({
        file,
        durationSeconds: duration,
        locationText: locationText || undefined,
      });
      toast.success('Recording saved');
    } catch (error) {
      toast.error(error.message);
    }
  };

  useEffect(() => {
    const handleClickOutside = () => setActiveMenuId(null);
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

  const handleMenuToggle = (id) => {
    setActiveMenuId(prev => prev === id ? null : id);
  };

  const handleDeleteRequest = (id) => {
    setRecordingToDelete(id);
    setIsConfirmOpen(true);
    setActiveMenuId(null);
  };

  const confirmDelete = async () => {
    if (!recordingToDelete) return;
    try {
      await deleteRecording.mutateAsync(recordingToDelete);
      toast.success('Recording deleted');
    } catch (error) {
      toast.error(error.message);
    } finally {
      setRecordingToDelete(null);
      setIsConfirmOpen(false);
    }
  };

  return (
    <div className="recordings-page">
      {/* Left Panel - Today's Recordings */}
      <div className="recordings-sidebar">
        <h2 className="sidebar-title">Today's Recordings</h2>
        <div className="recordings-list">
          {loading ? (
            <div className="loading-state">Loading...</div>
          ) : recordings.length > 0 ? (
            recordings.map(recording => (
              <RecordingCard 
                key={recording.id} 
                recording={recording}
                onDelete={handleDeleteRequest}
                showMenu={activeMenuId === recording.id}
                onMenuToggle={() => handleMenuToggle(recording.id)}
              />
            ))
          ) : (
            <div className="empty-state">
              <p>No recordings yet today</p>
              <span>Start recording to see them here</span>
            </div>
          )}
        </div>
      </div>

      {/* Right Panel - Recorder */}
      <div className="recorder-panel">
        <AudioRecorder onRecordingComplete={handleUpload} />
      </div>
      
      <ConfirmDialog 
        isOpen={isConfirmOpen}
        onClose={() => setIsConfirmOpen(false)}
        onConfirm={confirmDelete}
        title="Delete Recording"
        message="Are you sure you want to delete this recording? This action cannot be undone."
        confirmLabel="Delete"
        variant="danger"
      />
      
      <Toaster position="top-center" theme="light" />

      <style>{`
        .recordings-page {
          display: flex;
          height: 100vh;
          background: var(--bg-primary);
        }

        .recordings-sidebar {
          width: 32%;
          min-width: 300px;
          max-width: 450px;
          background: transparent;
          padding: 2rem 1.5rem;
          overflow-y: auto;
        }

        .sidebar-title {
          font-size: 1.125rem;
          font-weight: 400;
          color: var(--text-secondary);
          margin-bottom: 1.5rem;
          padding-left: 0.5rem;
        }

        .recordings-list {
          display: flex;
          flex-direction: column;
        }

        .recorder-panel {
          flex: 1;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 2rem;
        }

        .loading-state {
          text-align: center;
          padding: 2rem;
          color: var(--text-secondary);
        }

        .empty-state {
          text-align: center;
          padding: 3rem 1rem;
          color: var(--text-secondary);
        }

        .empty-state p {
          font-size: 1rem;
          margin-bottom: 0.5rem;
          color: var(--text-primary);
        }

        .empty-state span {
          font-size: 0.875rem;
        }

        /* Scrollbar Styling */
        .recordings-sidebar::-webkit-scrollbar {
          width: 6px;
        }

        .recordings-sidebar::-webkit-scrollbar-track {
          background: transparent;
        }

        .recordings-sidebar::-webkit-scrollbar-thumb {
          background: var(--bg-tertiary);
          border-radius: 3px;
        }

        .recordings-sidebar::-webkit-scrollbar-thumb:hover {
          background: var(--text-tertiary);
        }
      `}</style>
    </div>
  );
};

export default Recordings;
