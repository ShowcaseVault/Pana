import React from "react";
import { Circle, CheckCircle2, RotateCw } from "lucide-react";
import RecordingCard from "../RecordingCard";
import "./Diary.css";

/** "Tuesday, 4 March 2025" in the reader's locale. */
const formatDate = (value) =>
  new Date(value).toLocaleDateString(undefined, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

/**
 * A day's diary entry.
 *
 * The entry is the subject: it holds the main column at a reading measure.
 * The recordings it was written from sit in the aside, where they are within
 * reach for checking a passage against what was actually said without
 * interrupting the reading.
 */
const DiaryView = ({
  diary,
  recordings = [],
  onRegenerate,
  loading = false,
}) => {
  const { diary_date: diaryDate, mood, content, actions } = diary;

  const todos = actions?.filter((a) => a.type === "todo") ?? [];
  const done = actions?.filter((a) => a.type !== "todo") ?? [];

  return (
    <div className="page">
      <article className="page__main diary">
        <header>
          <h1 className="diary__date">{formatDate(diaryDate)}</h1>
          <div className="diary__meta">
            <span className="figure">
              {recordings.length}{" "}
              {recordings.length === 1 ? "recording" : "recordings"}
            </span>
            {mood && <span className="diary__mood">{mood.toLowerCase()}</span>}
          </div>
        </header>

        {loading ? (
          <div className="diary__writing">
            <p className="diary__writing-line">
              Reading back through the day
              <span className="diary__writing-dots" />
            </p>
          </div>
        ) : (
          <div className="diary__entry">{content}</div>
        )}

        {todos.length > 0 && (
          <section className="diary__section">
            <h2 className="diary__section-title">What the day asked for</h2>
            <div className="diary__actions">
              {todos.map((action, i) => (
                <div key={i} className="diary__action">
                  <Circle className="diary__action-mark" size={15} />
                  <span>{action.description}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        {done.length > 0 && (
          <section className="diary__section">
            <h2 className="diary__section-title">What happened</h2>
            <div className="diary__actions">
              {done.map((action, i) => (
                <div key={i} className="diary__action">
                  <CheckCircle2 className="diary__action-mark" size={15} />
                  <span>{action.description}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        <button
          type="button"
          className="diary__refresh"
          onClick={onRegenerate}
          disabled={loading}
        >
          <RotateCw size={13} />
          {loading ? "Writing" : "Write this day again"}
        </button>
      </article>

      <aside className="page__aside">
        {recordings.length > 0 && (
          <div className="page__aside-block">
            <h2 className="page__aside-title">Written from</h2>
            {recordings.map((recording) => (
              <RecordingCard key={recording.id} recording={recording} compact />
            ))}
          </div>
        )}

        {mood && (
          <div className="page__aside-block">
            <h2 className="page__aside-title">Mood</h2>
            <p className="page__aside-note">{mood.toLowerCase()}</p>
          </div>
        )}
      </aside>
    </div>
  );
};

export default DiaryView;
