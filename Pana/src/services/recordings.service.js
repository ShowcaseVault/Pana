/**
 * Recording and transcription operations.
 *
 * A service owns the contract for one domain: which endpoint, which parameters,
 * and what comes back. Components import the query hooks rather than this class,
 * but the class is what makes the endpoints testable without React and gives a
 * single place to look when the backend changes.
 *
 * @module services/recordings.service
 */

import apiClient from '../lib/apiClient.js';
import { API_ROUTES } from '../api/routes.js';

/**
 * @import { ApiResponse } from '../lib/ApiResponse.js'
 * @import { Recording, Transcription } from '../types/api.js'
 */

/** Matches the backend's `page_size` ceiling; asking for more is a 422. */
export const MAX_PAGE_SIZE = 200;

export class RecordingsService {
  /**
   * List recordings.
   *
   * The backend defaults to *today only*. `listAll` is what widens it to the
   * user's whole history, so a caller showing anything other than today must
   * pass it.
   *
   * @param {Object} [params]
   * @param {number} [params.page=1]
   * @param {number} [params.pageSize=50]
   * @param {string} [params.recordingDate] ISO date; narrows to a single day.
   * @param {boolean} [params.listAll=false]
   * @param {AbortSignal} [params.signal]
   * @returns {Promise<ApiResponse<Recording[]>>} Payload plus page metadata.
   */
  async list({ page = 1, pageSize = 50, recordingDate, listAll = false, signal } = {}) {
    return apiClient.get(API_ROUTES.RECORDINGS.LIST, {
      signal,
      params: {
        page,
        page_size: Math.min(pageSize, MAX_PAGE_SIZE),
        ...(recordingDate ? { recording_date: recordingDate } : {}),
        ...(listAll ? { list_all: true } : {}),
      },
    });
  }

  /**
   * @param {number} id
   * @param {Object} [options]
   * @param {AbortSignal} [options.signal]
   * @returns {Promise<Recording>}
   */
  async getById(id, { signal } = {}) {
    const response = await apiClient.get(API_ROUTES.RECORDINGS.DETAIL(id), { signal });
    return response.data;
  }

  /**
   * Upload a recording. The backend queues transcription itself.
   *
   * @param {Object} params
   * @param {File|Blob} params.file
   * @param {number} params.durationSeconds
   * @param {Date} [params.recordedAt] Defaults to now.
   * @param {string} [params.locationText]
   * @returns {Promise<Recording>}
   */
  async create({ file, durationSeconds, recordedAt = new Date(), locationText }) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('duration_seconds', String(durationSeconds));
    formData.append('recorded_at', recordedAt.toISOString());
    if (locationText) formData.append('location_text', locationText);

    const response = await apiClient.upload(API_ROUTES.RECORDINGS.CREATE, formData);
    return response.data;
  }

  /**
   * @param {number} id
   * @returns {Promise<void>}
   */
  async remove(id) {
    await apiClient.delete(API_ROUTES.RECORDINGS.DELETE(id));
  }

  /**
   * Fetch a transcript.
   *
   * @param {number} transcriptionId
   * @param {Object} [options]
   * @param {AbortSignal} [options.signal]
   * @returns {Promise<Transcription>}
   */
  async getTranscription(transcriptionId, { signal } = {}) {
    const response = await apiClient.get(API_ROUTES.TRANSCRIPTIONS.DETAIL(transcriptionId), {
      signal,
    });
    return response.data;
  }

  /**
   * Absolute URL for a recording's audio.
   *
   * The media route is authenticated, so whatever loads this URL has to send
   * cookies -- an `<audio>` element needs `crossOrigin = 'use-credentials'`.
   *
   * @param {string} filePath The `file_path` from a `Recording`.
   * @returns {string}
   */
  audioUrl(filePath) {
    const base = API_ROUTES.AUDIO_BASE.replace(/\/$/, '');
    return `${API_ROUTES.ORIGIN}${base}/${filePath}`;
  }
}

export const recordingsService = new RecordingsService();
export default recordingsService;
