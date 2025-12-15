import React, { useState, useEffect } from 'react';
import AudioRecorder from '../components/AudioRecorder';
import RecordingCard from '../components/RecordingCard';
import { Toaster, toast } from 'sonner';
import axiosClient from '../api/axiosClient';
import { API_ROUTES } from '../api/routes';
import '../styles/themes.css';

const Recordings = () => {
  const [refreshKey, setRefreshKey] = useState(0);
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(true);

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

  const handleUpload = async (file, duration) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('duration_seconds', duration);
      formData.append('recorded_at', new Date().toISOString());
      
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
      
      <Toaster position="top-center" theme="light" />

      <style>{`
        .recordings-page {
          display: flex;
          height: 100vh;
          background: var(--bg-primary);
        }

        .recordings-sidebar {
          width: 28%;
          min-width: 280px;
          max-width: 400px;
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
