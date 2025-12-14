import React, { useEffect, useRef } from 'react';
import { Mic, Square, Loader } from 'lucide-react';
import { useAudioRecorder } from '../hooks/useAudioRecorder';
import { motion } from 'framer-motion';
import { toast } from 'sonner';

const bars = 50;

const AudioRecorder = ({ onRecordingComplete }) => {
  const { isRecording, duration, audioData, startRecording, stopRecording, getAudioBlob, resetRecording } = useAudioRecorder();
  const [isProcessing, setIsProcessing] = React.useState(false);

  const handleToggle = async () => {
    if (isRecording) {
      if (duration < 10) {
        toast.error("Recording must be at least 10 seconds long.");
        stopRecording(); // Stop but don't save
        return;
      }
      stopRecording();
      setIsProcessing(true);
      
      // Allow state to settle before getting blob (small macro task delay)
      setTimeout(async () => {
          const blob = getAudioBlob();
          const file = new File([blob], `recording_${Date.now()}.webm`, { type: blob.type });
          try {
            await onRecordingComplete(file, duration);
            resetRecording(); 
          } catch (e) {
            console.error(e);
            toast.error("Failed to upload recording.");
          } finally {
            setIsProcessing(false);
          }
      }, 500);

    } else {
      await startRecording();
    }
  };

  // Calculate average volume for background effect
  const volume = React.useMemo(() => {
    if (audioData.length === 0) return 0;
    const sum = audioData.reduce((a, b) => a + b, 0);
    const avg = sum / audioData.length;
    return Math.min(avg / 128, 1); // Normalize 0-1 (roughly)
  }, [audioData]);

  return (
    <motion.div 
        className="recorder-container"
        animate={{
            boxShadow: `0 8px 32px rgba(139, 92, 246, ${Math.max(0.1, volume * 0.4)})`,
            background: `linear-gradient(145deg, rgba(139, 92, 246, ${Math.max(0.05, volume * 0.2)}) 0%, rgba(20, 20, 20, 1) 100%)`
        }}
        transition={{ type: "tween", ease: "linear", duration: 0.1 }}
    >
      <div className="visualizer-area">
        <div className="bars-container">
           {Array.from({ length: bars }).map((_, i) => {
             // Map audio data to height
             // audioData is 0-255. 
             // We can sample roughly evenly across the frequency spectrum.
             const index = Math.floor((i / bars) * (audioData.length / 2)); // Use lower half of spectrum (bass/mids)
             const value = audioData[index] || 0;
             const height = isRecording ? Math.max(4, (value / 255) * 100) : 4; 
             
             return (
               <motion.div
                 key={i}
                 className="bar"
                 animate={{ height: `${height}%`, opacity: isRecording ? 1 : 0.3 }}
                 transition={{ type: "spring", stiffness: 300, damping: 20 }}
               />
             );
           })}
        </div>
        
        <div className="timer">
           {Math.floor(duration / 60)}:{(duration % 60).toString().padStart(2, '0')}
        </div>
      </div>

      <div className="controls">
        <button 
            className={`record-btn ${isRecording ? 'recording' : ''}`}
            onClick={handleToggle}
            disabled={isProcessing}
        >
          {isProcessing ? (
              <Loader className="animate-spin" size={32} />
          ) : isRecording ? (
            <Square size={28} fill="currentColor" />
          ) : (
            <Mic size={32} />
          )}
        </button>
        <p className="status-text">
            {isProcessing ? "Processing..." : isRecording ? "Listening..." : "Tap to Record"}
        </p>
      </div>

      <style>{`
        .recorder-container {
          /* background is handled by motion.div inline styles for dynamic effect */
          border-radius: 24px;
          padding: 2rem;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 2rem;
          border: 1px solid rgba(255,255,255,0.1);
          backdrop-filter: blur(10px);
          width: 100%;
          max-width: 600px;
          margin: 0 auto;
          /* box-shadow handled by motion.div */
        }

        .visualizer-area {
          width: 100%;
          height: 120px;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 1rem;
          position: relative;
        }

        .bars-container {
           display: flex;
           align-items: center;
           justify-content: center;
           gap: 4px;
           height: 80px;
           width: 100%;
        }

        .bar {
           width: 6px;
           background-color: var(--accent-primary);
           border-radius: 4px;
        }

        .timer {
           font-family: monospace;
           font-size: 1.5rem;
           color: var(--text-secondary);
           font-weight: 600;
        }

        .controls {
           display: flex;
           flex-direction: column;
           align-items: center;
           gap: 1rem;
        }

        .record-btn {
           width: 80px;
           height: 80px;
           border-radius: 50%;
           background: var(--accent-primary);
           border: none;
           color: white;
           display: flex;
           align-items: center;
           justify-content: center;
           cursor: pointer;
           transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
           box-shadow: 0 0 0 0 rgba(139, 92, 246, 0.7);
        }

        .record-btn:hover {
           transform: scale(1.05);
           box-shadow: 0 0 20px rgba(139, 92, 246, 0.4);
        }

        .record-btn.recording {
           background: #ef4444; /* Red for Stop */
           animation: pulse-red 2s infinite;
        }

        @keyframes pulse-red {
            0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
            70% { box-shadow: 0 0 0 20px rgba(239, 68, 68, 0); }
            100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
        }

        .status-text {
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin: 0;
        }
      `}</style>
    </motion.div>
  );
};

export default AudioRecorder;
