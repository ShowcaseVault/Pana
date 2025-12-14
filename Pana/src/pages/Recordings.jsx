import React, { useState } from 'react';
import AudioRecorder from '../components/AudioRecorder';
import RecordingList from '../components/RecordingList';
import { Toaster, toast } from 'sonner';
import axiosClient from '../api/axiosClient';
import { API_ROUTES } from '../api/routes';

const Recordings = () => {
  const [refreshKey, setRefreshKey] = useState(0);

  const handleUpload = async (file, duration) => {
      // Prepare form data
      const formData = new FormData();
      formData.append('file', file);
      formData.append('duration_seconds', duration);
      formData.append('recorded_at', new Date().toISOString());
      
      // Optional: Get location if needed (mocked for now or use Geolocation API)
      // formData.append('location_text', 'Home Studio');

      // The backend expects specific fields. 
      // Based on schema: duration_seconds (int), recorded_at (datetime), location_text (str)
      
      try {
          const res = await axiosClient.post(API_ROUTES.RECORDINGS.CREATE, formData, {
              headers: { 'Content-Type': 'multipart/form-data' }
          });
          
          if (res.data.code === 'SUCCESS') {
              toast.success("Recording saved successfully!");
              setRefreshKey(prev => prev + 1); // Refresh list
          } else {
              toast.error("Failed to save recording.");
          }
      } catch (err) {
          console.error(err);
          toast.error("Upload error. " + (err.response?.data?.detail || err.message));
      }
  };

  return (
    <div className="page-container">
      <header className="page-header">
         <h2>Recordings</h2>
         <p>Capture your thoughts and ideas.</p>
      </header>

      <section className="recorder-section">
         <AudioRecorder onRecordingComplete={handleUpload} />
      </section>

      <section className="list-section">
         <RecordingList refreshTrigger={refreshKey} />
      </section>
      
      <Toaster position="top-center" theme="dark" />

      <style>{`
        .page-container {
            padding: 2rem 3rem;
            height: 100%;
            display: flex;
            flex-direction: column;
            max-width: 1200px;
            margin: 0 auto;
        }

        .page-header {
            margin-bottom: 2rem;
        }
        .page-header h2 {
            font-size: 2rem;
            font-weight: 700;
            margin: 0 0 0.5rem 0;
            color: var(--text-primary);
        }
        .page-header p {
            color: var(--text-secondary);
            margin: 0;
        }

        .recorder-section {
            margin-bottom: 2rem;
        }
        
        .list-section {
            flex: 1;
            display: flex;
            overflow: hidden;
        }
      `}</style>
    </div>
  );
};

export default Recordings;
