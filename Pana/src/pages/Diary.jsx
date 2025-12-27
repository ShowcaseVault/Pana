import React, { useState, useEffect } from 'react';
import axiosClient from '../api/axiosClient';
import { API_ROUTES } from '../api/routes';
import CreateDiary from '../components/CreateDiary';
import DiaryView from '../components/Diary/DiaryView';

const Diary = () => {
  const [diary, setDiary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [recordings, setRecordings] = useState([]);
  const [loadingRecordings, setLoadingRecordings] = useState(true);

  // Helper for today's date in YYYY-MM-DD
  const getTodayDateString = () => {
    return new Date().toISOString().split('T')[0];
  };

  const fetchRecordings = async () => {
    try {
      const today = getTodayDateString();
      const response = await axiosClient.get(API_ROUTES.RECORDINGS.LIST, {
        params: { recording_date: today }
      });
      if (response.data && response.data.code === 'SUCCESS') {
        setRecordings(response.data.data || []);
      }
    } catch (error) {
      console.error("Failed to fetch recordings:", error);
    } finally {
      setLoadingRecordings(false);
    }
  };

  const checkExistingDiary = async () => {
    try {
      const response = await axiosClient.get(API_ROUTES.DIARY.GET);
      if (response.data && response.data.code === 'SUCCESS') {
        setDiary(response.data.data);
      }
    } catch (error) {
      // 404 is expected if diary doesn't exist, just ignore
      if (error.response && error.response.status !== 404) {
          console.error("Failed to fetch diary:", error);
      }
    }
  };

  const handleCreateDiary = async () => {
    setLoading(true);
    try {
      const response = await axiosClient.post(API_ROUTES.DIARY.CREATE);
      if (response.data && response.data.code === 'SUCCESS') {
        setDiary(response.data.data);
      } else {
        // Handle failure message if needed
        console.error("Diary generation failed:", response.data.message);
      }
    } catch (error) {
      console.error("Error generating diary:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Load both recordings and diary status in parallel
    const init = async () => {
        setLoadingRecordings(true);
        await Promise.all([
            fetchRecordings(),
            checkExistingDiary()
        ]);
        setLoadingRecordings(false);
    };
    init();
  }, []);

  if (loadingRecordings) {
    return (
      <div className="flex items-center justify-center h-full">
         <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  return (
    <div className="p-6 h-full">
      {diary ? (
        <DiaryView 
          diary={diary} 
          recordings={recordings} 
          onRegenerate={handleCreateDiary} 
          loading={loading}
        />
      ) : (
        <CreateDiary 
          onCreate={handleCreateDiary} 
          loading={loading} 
        />
      )}
    </div>
  );
};

export default Diary;
