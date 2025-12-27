import React from 'react';
import { BookOpen } from 'lucide-react';
import './Diary/Diary.css'; // Import the CSS file

const CreateDiary = ({ onCreate, loading }) => {
  return (
    <div className="create-diary-container">
      <div className="create-icon-wrapper">
        <BookOpen size={40} />
      </div>
      <h2 className="create-title">Create Your Daily Diary</h2>
      <p className="create-desc">
        Generate a beautiful summary of your day based on your audio recordings. 
        Captures key moments, action items, and your mood.
      </p>
      
      <button
        onClick={onCreate}
        disabled={loading}
        className="create-btn"
      >
        {loading ? (
           <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
             <div className="spinner"></div>
             <span>Generating...</span>
           </div>
        ) : (
          'Generate Diary'
        )}
      </button>
    </div>
  );
};

export default CreateDiary;
