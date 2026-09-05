# Recordings

A recording is one piece of captured audio: the file on disk, the row that
describes it, and the transcription job that follows automatically.

`RecordingService` (`api/services/recordings.py`) over three repositories --
`RecordingRepository` for the rows, `TranscriptionRepository` for the job row,
`RecordingFileRepository` for the bytes.

## Uploading

`POST /recordings` -- multipart: the `file`, `duration_seconds`, `recorded_at`,
and optionally `location_text`.

Four things happen, in order:

1. **The upload is checked for being audio.** Content type first, file
   extension as a fallback. Browsers and mobile clients disagree about what to
   send, and a real recording arriving as `application/octet-stream` is common
   enough that rejecting on type alone would break uploads. Anything that is
   neither is a 400.
2. **The bytes are written** under `RECORDINGS_DIR`, at
   `<google_sub>/<date>/<HH-MM-SS>.<ext>`.
3. **The row is created**, including `recording_date` derived from
   `recorded_at` -- that derived column is what the day-based listing filters on.
4. **A transcription row is created** and its id returned to the route, which
   commits and then queues the Celery job. See
   [Committing before dispatch](architecture.md#committing-before-dispatch).

The client gets the recording back immediately. Transcription arrives later,
over [the event stream](transcriptions.md#live-updates).

## Listing

`GET /recordings?page=&page_size=&recording_date=&list_all=`

**With neither `recording_date` nor `list_all`, this answers "today."** That is
the home screen's question, and making it the default keeps the common call
parameterless. Pass `recording_date=YYYY-MM-DD` for another day, or
`list_all=true` for the whole history.

Paged: `page` from 1, `page_size` 1-200 (default 100). The count and page come
back together, and the route puts the totals in the envelope's `pagination`
block. Each row carries its transcription's status, id, and confidence inline,
so a list view does not need a second call per recording to know what is ready.

## Reading, updating, deleting

`GET /recordings/{id}` returns one. `PATCH` accepts a partial update of
`duration_seconds`, `recorded_at`, `location_text`. Moving `recorded_at` also
moves `recording_date` -- otherwise the date filter would disagree with the
timestamp it was derived from.

`DELETE` soft-deletes the recording **and its transcription together**, since a
transcript of a deleted recording is not something a user asked to keep. The
audio file stays on disk.

Everything is scoped to the caller. A recording id belonging to someone else is
a 404, not a 403.

## Playing audio back

`GET /recordings/file/{path}` streams the file.

This deliberately replaces a `StaticFiles` mount. Static serving cannot
authorize, and the stored paths are guessable, so every byte goes through
`MediaService`, which checks two things:

- the path belongs to a live recording **owned by the caller**;
- the resolved path is inside `RECORDINGS_DIR`.

The second check happens after resolution, not by inspecting the string, so
`..` segments and symlinks pointing outside are both caught.

**Every failure is the same 404** -- wrong owner, no such row, missing file,
attempted escape. A 403 would confirm the recording exists, and with guessable
paths that is exactly the enumeration this route exists to prevent.

## Operational check

`check_recordings_exist()` (`api/utils/`) compares live rows against the
directory and reports `missing_files` (rows whose audio is gone) and
`orphan_files` (audio no row claims). For after a bad deploy or a restore.
