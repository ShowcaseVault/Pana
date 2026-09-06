/**
 * Calendar history query.
 *
 * @module hooks/queries/useCalendar
 */

import { useQuery } from '@tanstack/react-query';
import historyService from '../../services/history.service.js';
import { queryKeys } from '../../lib/queryClient.js';

/**
 * Which days of a month hold diaries or recordings.
 *
 * Returns `Set`s rather than arrays because the calendar grid asks "does this
 * day have content?" once per cell, and a set answers in constant time.
 *
 * @param {number} year
 * @param {number} month 1-indexed. `Date#getMonth()` is 0-indexed; add one.
 * @returns {import('@tanstack/react-query').UseQueryResult<{diaryDays: Set<number>, recordingDays: Set<number>}>}
 */
export function useCalendar(year, month) {
  return useQuery({
    queryKey: queryKeys.history.calendar(year, month),
    queryFn: async ({ signal }) => {
      const calendar = await historyService.getCalendar(year, month, { signal });
      return {
        diaryDays: new Set(calendar.diary_days ?? []),
        recordingDays: new Set(calendar.recording_days ?? []),
      };
    },
  });
}
