/**
 * Diary queries and mutations.
 *
 * @module hooks/queries/useDiary
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import diaryService from '../../services/diary.service.js';
import { queryKeys } from '../../lib/queryClient.js';
import { ApiError } from '../../lib/ApiResponse.js';

/**
 * @import { Diary } from '../../types/api.js'
 */

/**
 * Fetch the diary for a day.
 *
 * Resolves to null when the day has none, which is the ordinary case for a day
 * the user has not written up yet -- so `isError` means a real failure and the
 * UI can show the create prompt on a null instead.
 *
 * @param {string} [date] ISO date. Defaults to today.
 * @returns {import('@tanstack/react-query').UseQueryResult<Diary|null>}
 */
export function useDiary(date) {
  return useQuery({
    queryKey: queryKeys.diary.byDate(date),
    queryFn: async ({ signal }) => {
      try {
        return await diaryService.getByDate(date, { signal });
      } catch (error) {
        if (error instanceof ApiError && error.isNotFound) return null;
        throw error;
      }
    },
  });
}

/**
 * Generate or regenerate a diary.
 *
 * @returns {import('@tanstack/react-query').UseMutationResult<Diary, Error, string|undefined>}
 */
export function useGenerateDiary() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (date) => diaryService.generate(date),
    onSuccess: (diary, date) => {
      // Seed the cache with what the server just returned rather than
      // invalidating: generation is slow, so a refetch would blank the view the
      // user is already looking at.
      queryClient.setQueryData(queryKeys.diary.byDate(date), diary);
      // A new diary changes which calendar days are marked.
      queryClient.invalidateQueries({ queryKey: queryKeys.history.all });
    },
  });
}
