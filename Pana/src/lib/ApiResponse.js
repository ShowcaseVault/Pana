/**
 * The backend's response envelope, as classes.
 *
 * Every endpoint answers with the same shape, success and failure alike:
 *
 *     {"success": true,  "message": "...", "data": {...}}
 *     {"success": false, "message": "...", "data": null}
 *
 * Listing endpoints add a `pagination` object as a *sibling* of `data`, not
 * nested inside it.
 *
 * Parsing that envelope in one place is the point of this module. Call sites
 * that reach into `res.data.data` are reproducing knowledge of the wire format;
 * when the backend changed `code` to `success`, every one of them broke
 * silently, because an undefined field compares false rather than throwing.
 * Here the shape is asserted once and a mismatch becomes a loud `ApiError`.
 *
 * @module lib/ApiResponse
 */

/**
 * @import { Pagination } from '../types/api.js'
 */

/**
 * A failed request, in the one form the app handles.
 *
 * Covers three different failures that call sites should not have to tell
 * apart: the server returned an error envelope, the request never reached the
 * server, or the body did not match the contract. Use the static builders
 * rather than the constructor.
 */
export class ApiError extends Error {
  /**
   * @param {string} message      Human-readable reason, safe to surface in a toast.
   * @param {Object} [options]
   * @param {number|null} [options.status] HTTP status, or null if there was no response.
   * @param {unknown} [options.body]       Parsed response body, when there was one.
   * @param {Error} [options.cause]        The underlying error, when re-wrapping.
   */
  constructor(message, { status = null, body = null, cause } = {}) {
    super(message, cause ? { cause } : undefined);
    this.name = 'ApiError';
    /** @type {number|null} */
    this.status = status;
    /** @type {unknown} */
    this.body = body;
  }

  /** The request failed authentication; the caller should send the user to login. */
  get isUnauthorized() {
    return this.status === 401;
  }

  /**
   * The resource does not exist. Distinguished because it is routinely an
   * expected answer rather than a fault -- asking for a diary on a day that has
   * none, for instance.
   */
  get isNotFound() {
    return this.status === 404;
  }

  /** No response at all: offline, DNS failure, CORS, or a cancelled request. */
  get isNetworkError() {
    return this.status === null;
  }

  /**
   * Build from an Axios rejection.
   *
   * Prefers the backend's own `message` over Axios's generic one, since the
   * former is written for a person and the latter says "Request failed with
   * status code 404".
   *
   * @param {any} error An error thrown by Axios.
   * @returns {ApiError}
   */
  static fromAxios(error) {
    const response = error?.response;

    if (!response) {
      return new ApiError(
        'Could not reach the server. Check your connection and try again.',
        { status: null, cause: error },
      );
    }

    const body = response.data;
    const message =
      (body && typeof body === 'object' && typeof body.message === 'string' && body.message) ||
      error.message ||
      'Something went wrong.';

    return new ApiError(message, { status: response.status, body, cause: error });
  }

  /**
   * Build for a body that did not match the envelope contract -- a proxy error
   * page, a gateway timeout served as HTML, or a genuine backend regression.
   *
   * @param {string} detail What was wrong with the body.
   * @param {unknown} body  The body as received.
   * @returns {ApiError}
   */
  static malformed(detail, body) {
    return new ApiError(`Unexpected response from the server: ${detail}`, {
      status: null,
      body,
    });
  }
}

/**
 * A successful envelope, with its payload unwrapped.
 *
 * @template T
 */
export class ApiResponse {
  /**
   * @param {Object} params
   * @param {T} params.data
   * @param {string|null} params.message
   * @param {Pagination|null} [params.pagination]
   */
  constructor({ data, message, pagination = null }) {
    /** @type {T} */
    this.data = data;
    /** @type {string|null} */
    this.message = message;
    /** @type {Pagination|null} */
    this.pagination = pagination;
  }

  /** Whether this response carries page metadata. */
  get isPaginated() {
    return this.pagination !== null;
  }

  /**
   * Whether another page exists after this one. Always false for a response
   * without pagination.
   */
  get hasNextPage() {
    return this.pagination !== null && this.pagination.page < this.pagination.totalPages;
  }

  /**
   * Parse a raw response body into an `ApiResponse`.
   *
   * Throws rather than returning a falsy value on a bad body: a malformed
   * response is a bug worth surfacing, and returning null here is what let the
   * old `code === 'SUCCESS'` checks fail quietly.
   *
   * @template T
   * @param {unknown} body The parsed JSON body.
   * @returns {ApiResponse<T>}
   * @throws {ApiError} If the body is not a well-formed envelope.
   */
  static parse(body) {
    if (body === null || typeof body !== 'object') {
      throw ApiError.malformed('expected a JSON object', body);
    }

    const envelope = /** @type {Record<string, any>} */ (body);

    if (typeof envelope.success !== 'boolean') {
      throw ApiError.malformed('missing a "success" field', body);
    }

    if (!envelope.success) {
      throw new ApiError(envelope.message || 'The request was unsuccessful.', {
        status: null,
        body,
      });
    }

    return new ApiResponse({
      data: envelope.data,
      message: envelope.message ?? null,
      pagination: parsePagination(envelope.pagination),
    });
  }
}

/**
 * Convert the backend's snake_case page metadata to the camelCase the frontend
 * uses. Confined to this module so `page_size` never leaks into components.
 *
 * @param {unknown} raw
 * @returns {Pagination|null}
 */
function parsePagination(raw) {
  if (raw === null || raw === undefined || typeof raw !== 'object') return null;

  const p = /** @type {Record<string, any>} */ (raw);
  if (typeof p.page !== 'number') return null;

  return {
    page: p.page,
    pageSize: p.page_size,
    total: p.total,
    totalPages: p.total_pages,
  };
}
