import { useEffect } from 'react';
import { API_ROUTES, BASE_URL } from '../api/routes';
import { toast } from 'sonner';

export const useTranscriptionSSE = (onTranscriptionComplete) => {
  useEffect(() => {
    const eventSource = new EventSource(`${BASE_URL}${API_ROUTES.TRANSCRIPTION_EVENTS}/`);

    eventSource.onopen = () => {
      // Connection opened
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.status === "completed" && data.recording_id) {
          
          if (onTranscriptionComplete) {
            onTranscriptionComplete(data.recording_id);
          }
          
          toast.success("Transcription completed!");
        }
      } catch (e) {
        // quiet failure
      }
    };

    eventSource.onerror = (err) => {
        // Quietly fail or log debug info. 
    };

    return () => {
      eventSource.close();
    };
  }, [onTranscriptionComplete]);
};
