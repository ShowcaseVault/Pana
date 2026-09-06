import React from 'react';
import { Mic, Square, Pause, Play } from 'lucide-react';
import { useAudioRecorder } from '../hooks/useAudioRecorder';
import Waveform from './Waveform';
import { toast } from 'sonner';
import '../styles/recorder.css';

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
        toast.success("Recording saved");
      } catch (e) {
        console.error(e);
        toast.error("Could not save the recording. Try again.");
      } finally {
        setIsProcessing(false);
      }
    }, 500);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  const status = isProcessing
    ? 'Saving'
    : isPaused
      ? 'Paused'
      : isRecording
        ? 'Listening'
        : 'Ready when you are';

  return (
    <div className="recorder">
      <div className={`recorder__timer${isRecording ? ' recorder__timer--live' : ''}`}>
        {formatTime(duration)}
      </div>

      <Waveform audioData={audioData} isRecording={isRecording} isPaused={isPaused} />

      <div className="recorder__controls">
        {!isRecording ? (
          <button
            type="button"
            className="recorder__record"
            onClick={handleStart}
            aria-label="Start recording"
          >
            <Mic size={26} />
          </button>
        ) : (
          <>
            <button
              type="button"
              className="recorder__button"
              onClick={handlePauseResume}
              disabled={isProcessing}
              aria-label={isPaused ? 'Resume recording' : 'Pause recording'}
            >
              {isPaused ? <Play size={20} /> : <Pause size={20} />}
            </button>

            <button
              type="button"
              className="recorder__button recorder__button--stop"
              onClick={handleStop}
              disabled={isProcessing}
              aria-label="Stop and save recording"
            >
              <Square size={18} fill="currentColor" />
            </button>
          </>
        )}
      </div>

      <p className="recorder__status" aria-live="polite">
        {status}
      </p>
    </div>
  );
};

export default AudioRecorder;
