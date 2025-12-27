import React, { useState, useEffect } from 'react';
import AudioRecorder from '../components/AudioRecorder';
import RecordingCard from '../components/RecordingCard';
import ConfirmDialog from '../components/ConfirmDialog';
import { Toaster, toast } from 'sonner';
import axiosClient from '../api/axiosClient';
import { API_ROUTES } from '../api/routes';
import '../styles/themes.css';

import { useTranscriptionSSE } from '../hooks/useTranscriptionSSE';

const Recordings = () => {
  const [refreshKey, setRefreshKey] = useState(0);
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeMenuId, setActiveMenuId] = useState(null);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [recordingToDelete, setRecordingToDelete] = useState(null);

  // Define handler for SSE events
  const handleTranscriptionComplete = (recordingId, transcriptionId) => {
    setRecordings(prev => prev.map(rec => {
        if (String(rec.id) === String(recordingId)) {
            return { ...rec, transcription_status: 'completed', transcription_id: transcriptionId };
        }
        return rec;
    }));
  };

  // Activate the listener
  useTranscriptionSSE(handleTranscriptionComplete);

  useEffect(() => {
    fetchRecordings();
  }, [refreshKey]);

  const fetchRecordings = async () => {
    try {
      setLoading(true);
      const res = await axiosClient.get(`${API_ROUTES.RECORDINGS.LIST}?limit=50`); 
      if (res.data.code === 'SUCCESS') {
          const records = res.data.data.data ? res.data.data.data : res.data.data;
          setRecordings(records); 
      }
    } catch (err) {
      console.error(err);
      toast.error("Failed to load recordings");
    } finally {
      setLoading(false);
    }
  };

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
      const formData = new FormData();
      formData.append('file', file);
      formData.append('duration_seconds', duration);
      formData.append('recorded_at', new Date().toISOString());
      if (locationText) formData.append('location_text', locationText);
      
      try {
          const res = await axiosClient.post(API_ROUTES.RECORDINGS.CREATE, formData, {
              headers: { 'Content-Type': 'multipart/form-data' }
          });
          if (res.data.code === 'SUCCESS') {
              setRefreshKey(prev => prev + 1);
          } else {
              toast.error("Failed to save recording.");
          }
      } catch (err) {
          console.error(err);
          toast.error("Upload error. " + (err.response?.data?.detail || err.message));
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
      const res = await axiosClient.delete(API_ROUTES.RECORDINGS.DELETE(recordingToDelete));
      if (res.data.code === 'SUCCESS') {
        setRecordings(prev => prev.filter(rec => rec.id !== recordingToDelete));
        toast.success("Recording deleted");
      } else {
        toast.error("Failed to delete recording");
      }
    } catch (err) {
      console.error(err);
      toast.error("Delete error: " + (err.response?.data?.detail || err.message));
    } finally {
      setRecordingToDelete(null);
      setIsConfirmOpen(false);
    }
  };

  const getTodayRecordings = () => {
    const today = new Date().toDateString();
    return recordings.filter(r => {
      const recordingDate = new Date(r.recorded_at).toDateString();
      return recordingDate === today;
    });
  };

  return (
    <div className="recordings-page">
      {/* Left Panel - Today's Recordings */}
      <div className="recordings-sidebar">
        <h2 className="sidebar-title">Today's Recordings</h2>
        <div className="recordings-list">
          {loading ? (
            <div className="loading-state">Loading...</div>
          ) : getTodayRecordings().length > 0 ? (
            getTodayRecordings().map(recording => (
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
