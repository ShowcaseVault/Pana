/**
 * Recording queries and mutations.
 *
 * These are what components import. Each one owns its cache key and its
 * invalidation, so a component asks for data and gets loading, error, and
 * refresh handling without writing any of it.
 *
 * @module hooks/queries/useRecordings
 */

import { useCallback } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import recordingsService from '../../services/recordings.service.js';
import { queryKeys } from '../../lib/queryClient.js';

/**
 * @import { Recording } from '../../types/api.js'
 */

/**
 * List recordings.
 *
 * @param {Object} [params]
 * @param {number} [params.page=1]
 * @param {number} [params.pageSize=50]
 * @param {string} [params.recordingDate] ISO date; narrows to one day.
 * @param {boolean} [params.listAll=false] Required to see anything but today.
 * @param {boolean} [params.enabled=true]
 * @returns {import('@tanstack/react-query').UseQueryResult<{recordings: Recording[], pagination: import('../../types/api.js').Pagination|null}>}
 */
export function useRecordings({
  page = 1,
  pageSize = 50,
  recordingDate,
  listAll = false,
  enabled = true,
} = {}) {
  const filters = { page, pageSize, recordingDate, listAll };

  return useQuery({
    queryKey: queryKeys.recordings.list(filters),
    enabled,
    queryFn: async ({ signal }) => {
      const response = await recordingsService.list({ ...filters, signal });
      // Page metadata is carried alongside the payload rather than dropped, so
      // a caller can add paging controls without changing this hook.
      return { recordings: response.data ?? [], pagination: response.pagination };
    },
  });
}

/**
 * Fetch one transcript, for showing text during playback.
 *
 * @param {number|null|undefined} transcriptionId
 * @param {Object} [options]
 * @param {boolean} [options.enabled=true] Gate fetching until playback starts.
 */
export function useTranscription(transcriptionId, { enabled = true } = {}) {
  return useQuery({
    queryKey: queryKeys.transcriptions.detail(transcriptionId ?? 0),
    enabled: enabled && Boolean(transcriptionId),
    // A finished transcript never changes, so it need not go stale.
    staleTime: Infinity,
    queryFn: ({ signal }) =>
      recordingsService.getTranscription(/** @type {number} */ (transcriptionId), { signal }),
  });
}

/**
 * Upload a recording.
 *
 * @returns {import('@tanstack/react-query').UseMutationResult<Recording, Error, {file: File|Blob, durationSeconds: number, recordedAt?: Date, locationText?: string}>}
 */
export function useCreateRecording() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params) => recordingsService.create(params),
    onSuccess: () => {
      // Broad on purpose: a new recording belongs in every list regardless of
      // filters, and it changes which calendar days have content.
      queryClient.invalidateQueries({ queryKey: queryKeys.recordings.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.history.all });
    },
  });
}

/**
 * Delete a recording.
 *
 * Removes the row from every cached list before the server answers, and puts it
 * back if the request fails, so the UI responds immediately without lying about
 * a delete that did not happen.
 *
 * @returns {import('@tanstack/react-query').UseMutationResult<void, Error, number, {snapshots: [readonly unknown[], unknown][]}>}
 */
export function useDeleteRecording() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id) => recordingsService.remove(id),

    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.recordings.all });

      const snapshots = queryClient.getQueriesData({ queryKey: queryKeys.recordings.all });

      for (const [key, previous] of snapshots) {
        if (!previous || typeof previous !== 'object' || !('recordings' in previous)) continue;
        const page = /** @type {{recordings: Recording[]}} */ (previous);
        queryClient.setQueryData(key, {
          ...page,
          recordings: page.recordings.filter((r) => String(r.id) !== String(id)),
        });
      }

      return { snapshots };
    },

    onError: (_error, _id, context) => {
      for (const [key, previous] of context?.snapshots ?? []) {
        queryClient.setQueryData(key, previous);
      }
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.recordings.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.history.all });

      // A diary is written from a day's recordings, and the backend removes it
      // when the last one goes. Without this the entry stays in the cache and
      // is shown as current while sourced from nothing.
      queryClient.invalidateQueries({ queryKey: queryKeys.diary.all });
    },
  });
}

/**
 * Apply a finished transcription to whatever is already cached.
 *
 * The SSE stream reports completions; patching the cache shows the new status
 * at once, and the invalidation that follows pulls the derived fields the event
 * does not carry, such as confidence.
 *
 * @returns {(recordingId: number|string, transcriptionId: number) => void}
 */
export function useApplyTranscriptionComplete() {
  const queryClient = useQueryClient();

  // Stable across renders: callers pass this to the SSE hook, and a new
  // identity each render would close and reopen the EventSource in a loop.
  return useCallback((recordingId, transcriptionId) => {
    const snapshots = queryClient.getQueriesData({ queryKey: queryKeys.recordings.all });

    for (const [key, previous] of snapshots) {
      if (!previous || typeof previous !== 'object' || !('recordings' in previous)) continue;
      const page = /** @type {{recordings: Recording[]}} */ (previous);
      queryClient.setQueryData(key, {
        ...page,
        recordings: page.recordings.map((r) =>
          String(r.id) === String(recordingId)
            ? { ...r, transcription_status: 'completed', transcription_id: transcriptionId }
            : r,
        ),
      });
    }

    queryClient.invalidateQueries({ queryKey: queryKeys.recordings.all });
  }, [queryClient]);
}
