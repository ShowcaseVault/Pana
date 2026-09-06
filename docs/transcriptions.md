# Transcriptions

One transcription per recording, created automatically at upload and filled in
by a Celery worker. The user never asks for it; they wait for it.

`TranscriptionService` serves the API side. `TranscriptionJob`
(`api/services/transcription_job.py`) is the worker side.

## Lifecycle

```
pending ──▶ processing ──▶ completed
                  └──────▶ failed
```

The row exists in `pending` from the moment the recording is uploaded, so a
client always has something to poll or display. The worker moves it to
`processing`, then to `completed` with text, language, confidence, and word
timings -- or to `failed`.

The stored row keeps all of that; the response returns a narrower slice. A
client gets the id, the recording id, the text, the word timings, and the
status. `language`, `confidence` and `model_name` describe how the text was
produced rather than what it says, and no screen shows them -- confidence is
read on the server, by [the diary](diary.md#generating), which is the only
thing that acts on it.

## The worker

`TranscriptionJob.run()` **never raises.** A failure is a state the row records
and the client is told about, not an exception for Celery to retry blindly --
corrupt audio would fail identically on every attempt, so retrying only burns
the queue.

The audio goes to Groq (`TRANSCRIPTION_MODEL`) with word and segment
granularity. Confidence is computed per segment from the model's own signals --
`avg_logprob` weighted 0.7, `1 - no_speech_prob` weighted 0.3 -- and averaged.
That single number is what the diary later uses to decide whether a transcript
is worth reading.

The Celery task itself stays a thin entry point: open a session, call the job.
The logic lives in the service so it can be read and tested without a worker.

## Live updates

`GET /transcription-events` -- server-sent events, one stream per user.

When a job finishes, the worker publishes to a Redis channel keyed by user id.
The route subscribes to that one channel, so Redis delivers only the caller's
events rather than the route filtering a firehose -- and a listener never learns
that anyone else is using the system.

**Failures are announced too.** A broken job that stayed silent would look
exactly like a slow one, and the client would wait forever.

Two details keep the connection alive: a `: keep-alive` comment every 25
seconds, because proxies close a connection that goes quiet, and
`X-Accel-Buffering: no`, because proxies otherwise buffer a stream into
uselessness.

A browser's `EventSource` cannot set headers, so web clients authenticate here
with the access cookie; native clients use the bearer header as usual.

## Endpoints

| Endpoint | Does |
|---|---|
| `POST /transcriptions` | Queue one manually for a recording |
| `GET /transcriptions` | Paged list, filterable by `status` |
| `GET /transcriptions/{id}` | One transcription with its text |
| `PATCH /transcriptions/{id}` | Correct the stored text or fields |
| `DELETE /transcriptions/{id}` | Soft-delete, leaving the recording |

`POST` is for the case where the automatic job was lost or a recording predates
it. The recording is looked up through the repository rather than trusted from
the request, so someone else's recording id is a 404, not a transcription of
their audio. A second request for a recording that already has one is a **409**
-- the column is unique, and a clear conflict beats the integrity error the
insert would otherwise raise.

Deleting a transcription leaves its recording alone; the reverse is not true
(see [Recordings](recordings.md#reading-updating-deleting)).
