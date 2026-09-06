/**
 * Shared shapes of the backend's payloads.
 *
 * These mirror the Pydantic schemas in `api/schemas/`. They exist as JSDoc
 * typedefs rather than runtime code so editors can complete and check field
 * names without adding a build step. When a backend schema changes, change the
 * typedef here first -- it is the one place the frontend states what it expects.
 *
 * @module types/api
 */

/**
 * Page metadata that accompanies a listing response.
 *
 * @typedef {Object} Pagination
 * @property {number} page       Current page, 1-based.
 * @property {number} pageSize   Items per page.
 * @property {number} total      Total items across all pages.
 * @property {number} totalPages Total number of pages.
 */

/**
 * A stored audio recording. Mirrors `RecordingResponse`.
 *
 * @typedef {Object} Recording
 * @property {number} id
 * @property {number} user_id
 * @property {string} file_path
 * @property {number} duration_seconds
 * @property {string} recorded_at              ISO-8601 datetime.
 * @property {string} recording_date           ISO-8601 date.
 * @property {string|null} location_text
 * @property {string} created_at               ISO-8601 datetime.
 * @property {boolean} is_deleted
 * @property {TranscriptionStatus|null} [transcription_status]
 * @property {number|null} [transcription_id]
 * @property {number|null} [transcription_confidence]
 */

/**
 * Lifecycle of a transcription job. Mirrors the backend enum of the same name;
 * the values are the strings the API sends, so compare against these rather
 * than against string literals spelled out at the call site.
 *
 * @typedef {'pending'|'processing'|'completed'|'failed'} TranscriptionStatus
 */

/**
 * One timed segment of a transcript, used to highlight text during playback.
 *
 * @typedef {Object} TranscriptionWord
 * @property {number} start Seconds from the start of the recording.
 * @property {number} end   Seconds from the start of the recording.
 * @property {string} text
 */

/**
 * A transcript. Mirrors `TranscriptionResponse`.
 *
 * @typedef {Object} Transcription
 * @property {number} id
 * @property {number} recording_id
 * @property {string|null} text
 * @property {string|null} language
 * @property {number|null} confidence
 * @property {string|null} model_name
 * @property {TranscriptionStatus} status
 * @property {string} created_at
 * @property {string|null} transcribed_at
 * @property {TranscriptionWord[]|null} [words]
 * @property {boolean} is_deleted
 */

/**
 * A generated diary entry. Mirrors `DiaryResponse`.
 *
 * @typedef {Object} Diary
 * @property {string} diary_date                    ISO-8601 date.
 * @property {string|null} [mood]
 * @property {string|null} [content]
 * @property {Object[]|null} [actions]
 * @property {string[]|null} [recording_file_paths]
 */

/**
 * Which days of a month have content. Mirrors `HistoryCalendar`.
 *
 * @typedef {Object} HistoryCalendar
 * @property {number} year
 * @property {number} month
 * @property {number} days_in_month
 * @property {number[]} diary_days     Day-of-month numbers with a diary entry.
 * @property {number[]} recording_days Day-of-month numbers with recordings.
 */

/**
 * The authenticated user. Mirrors `UserResponse`.
 *
 * @typedef {Object} User
 * @property {number} id
 * @property {string} google_id
 * @property {string} email
 * @property {string|null} [name]
 * @property {string|null} [picture]
 * @property {string|null} [created_at]
 * @property {string|null} [updated_at]
 */

/**
 * A transcription-completed event pushed over SSE.
 *
 * @typedef {Object} TranscriptionEvent
 * @property {number} recording_id
 * @property {number} transcription_id
 * @property {TranscriptionStatus} status
 */

export {};
