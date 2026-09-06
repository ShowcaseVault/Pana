/**
 * TanStack Query setup: the shared client and the query-key registry.
 *
 * @module lib/queryClient
 */

import { QueryClient } from '@tanstack/react-query';
import { ApiError } from './ApiResponse.js';

/**
 * Every query key in the app, built through one factory.
 *
 * Keys are hierarchical, so a broad key invalidates everything beneath it:
 * invalidating `queryKeys.recordings.all` refreshes every recording list
 * regardless of its filters, without the caller having to know what those
 * filters were. Hand-writing key arrays at call sites is what makes cache
 * invalidation drift out of sync with the queries it is meant to clear.
 */
export const queryKeys = {
  recordings: {
    all: ['recordings'],
    /** @param {Record<string, unknown>} filters */
    list: (filters) => ['recordings', 'list', filters],
    /** @param {number} id */
    detail: (id) => ['recordings', 'detail', id],
  },
  transcriptions: {
    all: ['transcriptions'],
    /** @param {number} id */
    detail: (id) => ['transcriptions', 'detail', id],
  },
  diary: {
    all: ['diary'],
    /** @param {string} [date] */
    byDate: (date) => ['diary', date ?? 'today'],
  },
  history: {
    all: ['history'],
    /**
     * @param {number} year
     * @param {number} month
     */
    calendar: (year, month) => ['history', 'calendar', year, month],
  },
  auth: {
    currentUser: ['auth', 'currentUser'],
  },
};

/**
 * Build the app's query client.
 *
 * A function rather than a module-level singleton so tests can create an
 * isolated client per case instead of inheriting cached state from a previous
 * one.
 *
 * @returns {QueryClient}
 */
export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // The data here is a person's own recordings and diary, which change
        // only when they act. A short staleness window avoids refetching on
        // every remount while keeping cross-tab edits visible.
        staleTime: 30_000,
        gcTime: 5 * 60_000,
        refetchOnWindowFocus: false,

        /**
         * Retry transport failures, never the server's considered answers.
         * Retrying a 401 or a 404 cannot change the outcome and only delays the
         * error the user needs to see.
         *
         * @param {number} failureCount
         * @param {unknown} error
         */
        retry: (failureCount, error) => {
          if (error instanceof ApiError && !error.isNetworkError) return false;
          return failureCount < 2;
        },
      },
      mutations: {
        // A mutation has a side effect, so a blind retry risks performing it
        // twice. Callers that know an operation is idempotent can opt in.
        retry: false,
      },
    },
  });
}
