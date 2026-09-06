/**
 * Session queries and mutations.
 *
 * @module hooks/queries/useAuth
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import authService from '../../services/auth.service.js';
import { queryKeys } from '../../lib/queryClient.js';
import { ApiError } from '../../lib/ApiResponse.js';

/**
 * @import { User } from '../../types/api.js'
 */

/**
 * Fetch the signed-in user, or null when there is no session.
 *
 * A 401 becomes null rather than an error: "not signed in" is a state the app
 * routes on, not a failure to report. The client has already tried to refresh
 * by the time this sees a 401, so it means the session is genuinely gone.
 *
 * @returns {import('@tanstack/react-query').UseQueryResult<User|null>}
 */
export function useCurrentUser() {
  return useQuery({
    queryKey: queryKeys.auth.currentUser,
    // The session outlives any single view; refetching it per mount would put a
    // request in front of every navigation.
    staleTime: 5 * 60_000,
    retry: false,
    queryFn: async ({ signal }) => {
      try {
        return await authService.getCurrentUser({ signal });
      } catch (error) {
        if (error instanceof ApiError && error.isUnauthorized) return null;
        throw error;
      }
    },
  });
}

/**
 * Sign out.
 *
 * Clears the cache whether or not the server call succeeds: if the request
 * failed the cookies may still stand, but leaving one user's recordings in
 * memory is worse than an extra login.
 *
 * @returns {import('@tanstack/react-query').UseMutationResult<void, Error, void>}
 */
export function useLogout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => authService.logout(),
    onSettled: () => {
      queryClient.setQueryData(queryKeys.auth.currentUser, null);
      queryClient.clear();
    },
  });
}
