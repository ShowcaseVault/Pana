import { useState, useRef, useEffect } from 'react';

export const useAudioRecorder = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [duration, setDuration] = useState(0);
  const [audioData, setAudioData] = useState(new Uint8Array(0));
  const [mimeType, setMimeType] = useState('audio/webm');
  
  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const dataArrayRef = useRef(null);
  const sourceRef = useRef(null);
  const rafIdRef = useRef(null);
  const chunksRef = useRef([]);
  const startTimeRef = useRef(null);
  const pauseTimeRef = useRef(null);
  const totalPausedTimeRef = useRef(0);
  const intervalRef = useRef(null);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // Audio Context setup for visualizer
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const analyser = audioContext.createAnalyser();
      const source = audioContext.createMediaStreamSource(stream);
      
      analyser.fftSize = 256;
      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      
      source.connect(analyser);
      
      audioContextRef.current = audioContext;
      analyserRef.current = analyser;
      dataArrayRef.current = dataArray;
      sourceRef.current = source;
      
      // Visualization loop
      const updateVisualizer = () => {
        if (!analyserRef.current) return;
        analyserRef.current.getByteFrequencyData(dataArrayRef.current);
        setAudioData(new Uint8Array(dataArrayRef.current));
        rafIdRef.current = requestAnimationFrame(updateVisualizer);
      };
      updateVisualizer();

      // MediaRecorder setup
      const preferredTypes = [
        'audio/mp4;codecs=mp4a.40.2',
        'audio/mp4',
        'audio/webm;codecs=opus',
        'audio/webm'
      ];

      const selectedMimeType = preferredTypes.find((t) => {
        try {
          return typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported(t);
        } catch {
          return false;
        }
      });

      setMimeType(selectedMimeType || 'audio/webm');
      const mediaRecorder = selectedMimeType
        ? new MediaRecorder(stream, { mimeType: selectedMimeType })
        : new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.start();
      startTimeRef.current = Date.now();
      totalPausedTimeRef.current = 0;
      setIsRecording(true);
      setIsPaused(false);
      
      // Timer
      intervalRef.current = setInterval(() => {
        const elapsed = Date.now() - startTimeRef.current - totalPausedTimeRef.current;
        setDuration(Math.floor(elapsed / 1000));
      }, 1000);
      
      mediaRecorder.onstop = () => {
        if (intervalRef.current) clearInterval(intervalRef.current);
        cancelAnimationFrame(rafIdRef.current);
        if (sourceRef.current) sourceRef.current.disconnect();
        if (audioContextRef.current) audioContextRef.current.close();
        stream.getTracks().forEach(track => track.stop());
      };

    } catch (err) {
      console.error("Error accessing microphone:", err);
    }
  };

  const pauseRecording = () => {
    if (mediaRecorderRef.current && isRecording && !isPaused) {
      mediaRecorderRef.current.pause();
      pauseTimeRef.current = Date.now();
      setIsPaused(true);
      if (intervalRef.current) clearInterval(intervalRef.current);
    }
  };

  const resumeRecording = () => {
    if (mediaRecorderRef.current && isRecording && isPaused) {
      mediaRecorderRef.current.resume();
      if (pauseTimeRef.current) {
        totalPausedTimeRef.current += Date.now() - pauseTimeRef.current;
      }
      setIsPaused(false);
      
      // Restart timer
      intervalRef.current = setInterval(() => {
        const elapsed = Date.now() - startTimeRef.current - totalPausedTimeRef.current;
        setDuration(Math.floor(elapsed / 1000));
      }, 1000);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setIsPaused(false);
    }
  };

  const getAudioBlob = () => {
    return new Blob(chunksRef.current, { type: mimeType || 'audio/webm' });
  };

  const resetRecording = () => {
    setDuration(0);
    setAudioData(new Uint8Array(0));
    chunksRef.current = [];
    totalPausedTimeRef.current = 0;
  };

  return {
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
  };
};
