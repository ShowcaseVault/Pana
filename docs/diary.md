# Diary

One written entry per user per day, generated from that day's recordings. This
is the product's payoff: the user records moments, the diary turns them into
something to read.

`DiaryService` (`api/services/diary.py`) over four repositories -- diaries,
transcriptions, location lookup, and the LLM.

## Reading a day

`GET /diary?date=YYYY-MM-DD` (defaults to today).

**A day with no diary yet is not a 404.** It comes back empty but with the
day's recording paths listed. The client shows the day either way, and the
listed recordings are what let it offer "generate" instead of an error.

## Generating

`POST /diary?date=` writes or rewrites the day. Regenerating is free and
non-destructive to the recordings, so it is an upsert rather than a create.

Three steps:

**1. Fill the transcription gaps.** Every recording for the day is checked. One
with no transcription row gets one created; one whose row never reached
`completed` is queued again. Their ids go back to the route, which commits and
dispatches them at high priority. Without this a diary would silently omit
audio that was uploaded but never processed -- the worst kind of failure here,
because the entry looks complete.

**2. Build the model's input.** Each usable transcript becomes an event with
its timestamp, text, language, and location. Two filters apply:

- no text, no event;
- **confidence at or below `TRANSCRIPTION_CONFIDENCE_THRESHOLD`, no event.** A
  low-confidence transcript is more likely to mislead the model than to help
  it, so it is left out entirely rather than passed along hedged.

Location is resolved here. `location_text` holds raw `"lat,long"` from the
client; the coordinates are reverse-geocoded to a place name. If the value is
not coordinates, or the lookup fails, whatever the client sent is used -- a
place name it supplied beats nothing. Absent entirely, `"Unknown Location"`.

**3. Ask the model** for mood, content, and actions, and upsert the row.

## When there is nothing to write

Two cases, and neither is an error the user sees.

**No usable events** -- a day with no recordings, or none that transcribed
clearly. The entry is stored with mood `neutral` and a line saying there was
nothing clear to work from. A day with nothing to say is a fact about the day,
not a failure.

**The model failed** -- the generation is caught, logged with a traceback, and
a placeholder is stored with mood `unknown` asking the user to try again in a
moment. **The day is still written.** The recordings are safe and regenerating
costs nothing, so losing the row would be the only real damage available here.
