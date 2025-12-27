import React, { useState, useEffect } from 'react';
import axiosClient from '../api/axiosClient';
import { API_ROUTES } from '../api/routes';
import CreateDiary from '../components/CreateDiary';
import DiaryView from '../components/Diary/DiaryView';
import { useParams } from 'react-router-dom';

const Diary = () => {
  const { date } = useParams();
  const [diary, setDiary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [recordings, setRecordings] = useState([]);
  const [loadingRecordings, setLoadingRecordings] = useState(true);

  // Helper for today's date in YYYY-MM-DD
  const getTodayDateString = () => {
    return new Date().toISOString().split('T')[0];
  };

  const targetDate = date || getTodayDateString();
  const isToday = targetDate === getTodayDateString();

  const fetchRecordings = async () => {
    try {
      const response = await axiosClient.get(API_ROUTES.RECORDINGS.LIST, {
        params: { recording_date: targetDate }
      });
      if (response.data && response.data.code === 'SUCCESS') {
        const records = response.data.data.data ? response.data.data.data : response.data.data;
        setRecordings(records || []);
      }
    } catch (error) {
      console.error("Failed to fetch recordings:", error);
    } finally {
      setLoadingRecordings(false);
    }
  };

  const checkExistingDiary = async () => {
    try {
      const response = await axiosClient.get(API_ROUTES.DIARY.GET, {
          params: { date: targetDate }
      });
      
      if (response.data && response.data.code === 'SUCCESS') {
        setDiary(response.data.data);
      } else {
        setDiary(null);
      }
    } catch (error) {
      // 404 is expected if diary doesn't exist
      setDiary(null);
    }
  };

  const handleCreateDiary = async () => {
    // We now support creating/regenerating diary for any date supported by backend
    setLoading(true);
    try {
      // Pass the targetDate as a query parameter
      const response = await axiosClient.post(API_ROUTES.DIARY.CREATE, null, {
          params: { date: targetDate }
      });
      if (response.data && response.data.code === 'SUCCESS') {
        setDiary(response.data.data);
      } else {
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
        setDiary(null); // Reset on date change
        await Promise.all([
            fetchRecordings(),
            checkExistingDiary()
        ]);
        setLoadingRecordings(false);
    };
    init();
  }, [targetDate]);

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
        isToday ? (
            <CreateDiary 
            onCreate={handleCreateDiary} 
            loading={loading} 
            />
        ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
                <p>No diary entry for this date.</p>
                {recordings.length > 0 && <p className="text-sm mt-2">({recordings.length} recordings found)</p>}
            </div>
        )
      )}
    </div>
  );
};

export default Diary;
