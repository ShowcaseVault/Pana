/**
 * Calendar history: which days of a month hold diaries or recordings.
 *
 * @module services/history.service
 */

import apiClient from '../lib/apiClient.js';
import { API_ROUTES } from '../api/routes.js';

/**
 * @import { HistoryCalendar } from '../types/api.js'
 */

export class HistoryService {
  /**
   * @param {number} year
   * @param {number} month 1-indexed, matching the API. `Date#getMonth()` is
   *   0-indexed, so callers converting from a `Date` must add one.
   * @param {Object} [options]
   * @param {AbortSignal} [options.signal]
   * @returns {Promise<HistoryCalendar>}
   */
  async getCalendar(year, month, { signal } = {}) {
    const response = await apiClient.get(API_ROUTES.HISTORY.CALENDAR(year, month), { signal });
    return response.data;
  }
}

export const historyService = new HistoryService();
export default historyService;
