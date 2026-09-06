/**
 * Diary generation and retrieval.
 *
 * @module services/diary.service
 */

import apiClient from '../lib/apiClient.js';
import { API_ROUTES } from '../api/routes.js';

/**
 * @import { Diary } from '../types/api.js'
 */

export class DiaryService {
  /**
   * Fetch the diary for a day.
   *
   * A day with no diary is a 404 from the backend, which is an expected answer
   * rather than a fault. This returns null for that case and lets every other
   * failure propagate, so callers do not have to inspect status codes.
   *
   * @param {string} [date] ISO date. Defaults to today, backend-side.
   * @param {Object} [options]
   * @param {AbortSignal} [options.signal]
   * @returns {Promise<Diary|null>} Null when no diary exists for that day.
   */
  async getByDate(date, { signal } = {}) {
    const response = await apiClient.get(API_ROUTES.DIARY.GET, {
      signal,
      params: date ? { date } : undefined,
    });
    return response.data ?? null;
  }

  /**
   * Generate or regenerate the diary for a day.
   *
   * Slow by nature: the backend may dispatch transcription jobs and wait on a
   * language model, so callers should show progress rather than assume this
   * returns promptly.
   *
   * @param {string} [date] ISO date. Defaults to today, backend-side.
   * @returns {Promise<Diary>}
   */
  async generate(date) {
    const response = await apiClient.post(API_ROUTES.DIARY.CREATE, null, {
      params: date ? { date } : undefined,
    });
    return response.data;
  }
}

export const diaryService = new DiaryService();
export default diaryService;
