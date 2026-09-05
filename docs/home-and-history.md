# Home and history

Two small read-only features behind the app's navigation.

## Home

`GET /home` returns the signed-in user's profile -- what the home screen needs
to greet them.

`HomeService` resolves the JWT's `sub` claim to a user row. **A valid token
whose user is gone is a 404, not a 401.** The caller is authenticated; the row
just is not there. Returning 401 would tell a legitimate client to re-login,
which would succeed and land in the same place.

The day's recordings for that screen come from
[`GET /recordings`](recordings.md#listing), which already defaults to today.

## History calendar

`GET /history/calendar/{year}/{month}` returns, for one month:
`days_in_month`, the days that have a diary, and the days that have recordings.
Enough to dot a calendar widget without a request per day.

**An out-of-range or missing year or month falls back to today's** rather than
failing. This backs a calendar widget: a 422 over a stray month number would
blank the screen, where the current month answers the question perfectly well.
Month 13 gives you this month, not an error.
