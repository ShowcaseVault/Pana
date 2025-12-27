import React from 'react';
import { Mic, Square, Pause, Play } from 'lucide-react';
import { useAudioRecorder } from '../hooks/useAudioRecorder';
import FluidWaveVisualizer from './FluidWaveVisualizer';
import { toast } from 'sonner';

const encodeWav = (audioBuffer) => {
  const numChannels = audioBuffer.numberOfChannels;
  const sampleRate = audioBuffer.sampleRate;
  const numFrames = audioBuffer.length;
  const bitsPerSample = 16;

  const bytesPerSample = bitsPerSample / 8;
  const blockAlign = numChannels * bytesPerSample;
  const byteRate = sampleRate * blockAlign;
  const dataSize = numFrames * blockAlign;

  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  let offset = 0;
  const writeString = (s) => {
    for (let i = 0; i < s.length; i += 1) {
      view.setUint8(offset + i, s.charCodeAt(i));
    }
    offset += s.length;
  };

  writeString('RIFF');
  view.setUint32(offset, 36 + dataSize, true);
  offset += 4;
  writeString('WAVE');
  writeString('fmt ');
  view.setUint32(offset, 16, true);
  offset += 4;
  view.setUint16(offset, 1, true);
  offset += 2;
  view.setUint16(offset, numChannels, true);
  offset += 2;
  view.setUint32(offset, sampleRate, true);
  offset += 4;
  view.setUint32(offset, byteRate, true);
  offset += 4;
  view.setUint16(offset, blockAlign, true);
  offset += 2;
  view.setUint16(offset, bitsPerSample, true);
  offset += 2;
  writeString('data');
  view.setUint32(offset, dataSize, true);
  offset += 4;

  const channels = [];
  for (let c = 0; c < numChannels; c += 1) {
    channels.push(audioBuffer.getChannelData(c));
  }

  let dataOffset = offset;
  for (let i = 0; i < numFrames; i += 1) {
    for (let c = 0; c < numChannels; c += 1) {
      let sample = channels[c][i];
      sample = Math.max(-1, Math.min(1, sample));
      view.setInt16(dataOffset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
      dataOffset += 2;
    }
  }

  return new Blob([buffer], { type: 'audio/wav' });
};

const blobToWavBlob = async (blob) => {
  const audioContext = new (window.AudioContext || window.webkitAudioContext)();
  try {
    const arrayBuffer = await blob.arrayBuffer();
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
    return encodeWav(audioBuffer);
  } finally {
    await audioContext.close();
  }
};

const AudioRecorder = ({ onRecordingComplete }) => {
  const { 
    isRecording, 
    isPaused,
    duration, 
    audioData, 
    mimeType,
    startRecording, 
    pauseRecording,
    resumeRecording,
    stopRecording, 
    getAudioBlob, 
    resetRecording 
  } = useAudioRecorder();
  
  const [isProcessing, setIsProcessing] = React.useState(false);

  const handleStart = async () => {
    await startRecording();
  };

  const handlePauseResume = () => {
    if (isPaused) {
      resumeRecording();
    } else {
      pauseRecording();
    }
  };

  const handleStop = async () => {
    if (duration < 10) {
      toast.error("Recording must be at least 10 seconds long.");
      stopRecording();
      resetRecording(); // Reset timer when too short
      return;
    }
    
    stopRecording();
    setIsProcessing(true);
    
    setTimeout(async () => {
      const blob = getAudioBlob();
      let file;
      if ((mimeType || blob.type || '').toLowerCase().startsWith('audio/mp4')) {
        file = new File([blob], `recording_${Date.now()}.m4a`, { type: mimeType || blob.type || 'audio/mp4' });
      } else {
        const wavBlob = await blobToWavBlob(blob);
        file = new File([wavBlob], `recording_${Date.now()}.wav`, { type: 'audio/wav' });
      }
      try {
        await onRecordingComplete(file, duration);
        resetRecording();
        toast.success("Recording saved successfully!");
      } catch (e) {
        console.error(e);
        toast.error("Failed to upload recording.");
      } finally {
        setIsProcessing(false);
      }
    }, 500);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="audio-recorder-premium">
      {/* Large Timer */}
      <div className="timer-display">
        {formatTime(duration)}
      </div>

      {/* 3D Wave Visualizer */}
      <div className="visualizer-container">
        <FluidWaveVisualizer audioData={audioData} isRecording={isRecording && !isPaused} />
      </div>

      {/* Controls */}
      <div className="controls-container">
        {!isRecording ? (
          <button className="control-btn start-btn" onClick={handleStart}>
            <Mic size={32} />
          </button>
        ) : (
          <>
            <button 
              className="control-btn pause-btn" 
              onClick={handlePauseResume}
              disabled={isProcessing}
            >
              {isPaused ? <Play size={28} /> : <Pause size={28} />}
            </button>
            
            <button 
              className="control-btn stop-btn" 
              onClick={handleStop}
              disabled={isProcessing}
            >
              <Square size={28} fill="currentColor" />
            </button>
          </>
        )}
      </div>

      {/* Status Text */}
      <div className="status-text">
        {isProcessing ? "Processing..." : 
         isPaused ? "Paused" :
         isRecording ? "Listening..." : 
         "Tap to Record"}
      </div>

      <style>{`
        .audio-recorder-premium {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          padding: 1rem 2rem;
          max-width: 700px;
          margin: 0 auto;
          gap: 0;
        }

        .timer-display {
          font-size: 7rem;
          font-weight: 100;
          color: var(--text-tertiary);
          letter-spacing: 0.15em;
          margin-bottom: -1rem;
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }

        .visualizer-container {
          width: 100%;
          max-width: 600px;
          margin: 0;
        }

        .controls-container {
          display: flex;
          gap: 1.25rem;
          margin-bottom: 0.75rem;
        }

        .control-btn {
          width: 72px;
          height: 72px;
          border-radius: 50%;
          border: none;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
          position: relative;
        }

        .control-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .start-btn {
          background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
          color: white;
          box-shadow: 0 8px 24px rgba(79, 209, 197, 0.3);
        }

        .start-btn:hover:not(:disabled) {
          transform: scale(1.1);
          box-shadow: 0 12px 32px rgba(79, 209, 197, 0.4);
        }

        .pause-btn {
          background: linear-gradient(135deg, #e2e8f0, #cbd5e0);
          color: #4a5568;
          box-shadow: var(--shadow-md);
        }

        .pause-btn:hover:not(:disabled) {
          transform: scale(1.05);
          box-shadow: var(--shadow-lg);
        }

        .stop-btn {
          background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
          color: white;
          box-shadow: 0 8px 24px rgba(79, 209, 197, 0.3);
        }

        .stop-btn:hover:not(:disabled) {
          transform: scale(1.05);
          box-shadow: 0 12px 32px rgba(79, 209, 197, 0.4);
        }

        .status-text {
          color: var(--text-secondary);
          font-size: 1.1rem;
          font-weight: 300;
          letter-spacing: 0.05em;
        }
      `}</style>
    </div>
  );
};

export default AudioRecorder;
