import { useState, useRef, useEffect } from 'react';

export const useAudioRecorder = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const [audioData, setAudioData] = useState(new Uint8Array(0));
  
  const mediaRecorderRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const dataArrayRef = useRef(null);
  const sourceRef = useRef(null);
  const rafIdRef = useRef(null);
  const chunksRef = useRef([]);
  const startTimeRef = useRef(null);

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
      
      source.connect(analyser); // Only connect to analyser, not destination to avoid feedback loop
      
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
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.start();
      startTimeRef.current = Date.now();
      setIsRecording(true);
      
      // Timer
      const interval = setInterval(() => {
        setDuration(Math.floor((Date.now() - startTimeRef.current) / 1000));
      }, 1000);
      
      mediaRecorder.onstop = () => {
        clearInterval(interval);
        cancelAnimationFrame(rafIdRef.current);
        if (sourceRef.current) sourceRef.current.disconnect();
        if (audioContextRef.current) audioContextRef.current.close();
        stream.getTracks().forEach(track => track.stop());
      };

    } catch (err) {
      console.error("Error accessing microphone:", err);
      // You might want to return an error state here
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const getAudioBlob = () => {
    return new Blob(chunksRef.current, { type: 'audio/webm' }); // or 'audio/mp4' depending on browser support
  };

  const resetRecording = () => {
    setDuration(0);
    setAudioData(new Uint8Array(0));
    chunksRef.current = [];
  };

  return {
    isRecording,
    duration,
    audioData,
    startRecording,
    stopRecording,
    getAudioBlob,
    resetRecording
  };
};
