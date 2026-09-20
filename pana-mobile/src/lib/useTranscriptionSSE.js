/**
 * Transcription completions, streamed to a device.
 *
 * Same endpoint and same events as the web client's hook. What differs is how
 * the request is made: `EventSource` cannot set headers, and a device
 * authenticates with a bearer token rather than a cookie, so the stream is read
 * from `fetch` and the `text/event-stream` frames are parsed here.
 *
 * That costs one thing `EventSource` gave away free -- reconnection -- so it is
 * reimplemented below, with a backoff, since a phone loses its connection
 * routinely: a screen lock, a tunnel, a handover between cells.
 *
 * @module lib/useTranscriptionSSE
 */

import { useEffect, useRef } from 'react';
import { API_ROUTES } from './routes.js';
import { getAccessToken } from './tokenStore.js';

/** Backoff between reconnection attempts, in milliseconds. */
const RETRY_MIN = 1000;
const RETRY_MAX = 30000;

/**
 * Subscribe to this user's transcription completions.
 *
 * @param {(recordingId: number|string, transcriptionId: number) => void} onComplete
 *   Must be stable across renders -- `useCallback` -- or the stream reopens on
 *   every render.
 */
export function useTranscriptionSSE(onComplete) {
  // Held in a ref so a changed callback does not tear down the connection.
  const callbackRef = useRef(onComplete);
  callbackRef.current = onComplete;

  useEffect(() => {
    const controller = new AbortController();
    let retryDelay = RETRY_MIN;
    let retryTimer = null;
    let stopped = false;

    /** Dispatch one parsed event. */
    const handleEvent = (payload) => {
      try {
        const data = JSON.parse(payload);
        if (data.status === 'completed' && data.recording_id) {
          callbackRef.current?.(data.recording_id, data.transcription_id);
        }
      } catch {
        // A frame we cannot parse is not worth killing the stream over.
      }
    };

    const connect = async () => {
      const token = getAccessToken();
      if (!token) return; // Not signed in yet; the reconnect below will retry.

      try {
        const response = await fetch(
          `${API_ROUTES.ORIGIN}${API_ROUTES.TRANSCRIPTION_EVENTS}`,
          {
            headers: { Authorization: `Bearer ${token}`, Accept: 'text/event-stream' },
            signal: controller.signal,
          },
        );

        if (!response.ok || !response.body) throw new Error(`SSE failed: ${response.status}`);

        // The connection is good, so a later drop starts its backoff from the
        // bottom rather than from whatever the last failure had reached.
        retryDelay = RETRY_MIN;

        const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
        let buffer = '';

        for (;;) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += value;

          // Frames are separated by a blank line. A chunk can split one
          // anywhere, so only whole frames are taken and the remainder stays
          // in the buffer.
          let split;
          while ((split = buffer.indexOf('\n\n')) !== -1) {
            const frame = buffer.slice(0, split);
            buffer = buffer.slice(split + 2);

            for (const line of frame.split('\n')) {
              // `: keep-alive` is the server's heartbeat; anything that is not
              // a data line carries nothing for us.
              if (line.startsWith('data:')) handleEvent(line.slice(5).trim());
            }
          }
        }
      } catch (error) {
        if (controller.signal.aborted) return;
        console.debug('Transcription stream dropped', error);
      }

      // Reached on a clean end or a failure alike: either way the stream is
      // gone and the client wants it back.
      if (stopped || controller.signal.aborted) return;
      retryTimer = setTimeout(connect, retryDelay);
      retryDelay = Math.min(retryDelay * 2, RETRY_MAX);
    };

    connect();

    return () => {
      stopped = true;
      if (retryTimer) clearTimeout(retryTimer);
      controller.abort();
    };
  }, []);
}

export default useTranscriptionSSE;
