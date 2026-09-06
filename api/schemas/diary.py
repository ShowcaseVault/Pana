from datetime import date

from pydantic import BaseModel, ConfigDict


class DiaryResponse(BaseModel):
    """A day's diary entry.

    `recording_file_paths` is not returned: it is the record of which audio the
    entry was generated from, which the client gets by listing that day's
    recordings. Sending a second, possibly stale copy of the same list invites
    the two to disagree.

    `content` is null when the day has no entry yet. That is the ordinary case
    for a day not written up, not an error, so the day still answers with its
    own shape.
    """

    diary_date: date
    mood: str | None = None
    content: str | None = None
    actions: list[dict] | None = None

    model_config = ConfigDict(from_attributes=True)
