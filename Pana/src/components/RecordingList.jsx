import React, { useEffect, useState } from "react";
import axiosClient from "../api/axiosClient";
import { API_ROUTES } from "../api/routes";
import { Play, Calendar, Clock, MapPin, Trash2 } from "lucide-react";
import { toast } from "sonner";

const RecordingList = ({ refreshTrigger }) => {
  const [recordings, setRecordings] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    fetchRecordings();
  }, [refreshTrigger]);

  const fetchRecordings = async () => {
    try {
      setLoading(true);
      const res = await axiosClient.get(
        `${API_ROUTES.RECORDINGS.LIST}?limit=50`
      );
      if (res.data.code === "SUCCESS") {
        const records = res.data.data.data ? res.data.data.data : res.data.data;
        setRecordings(records);
      }
    } catch (err) {
      console.error(err);
      toast.error("Failed to load recordings");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await axiosClient.delete(API_ROUTES.RECORDINGS.DELETE(id));
      toast.success("Recording deleted");
      fetchRecordings();
    } catch (e) {
      toast.error("Delete failed");
    }
  };

  if (loading && recordings.length === 0) {
    return <div className="loading-state">Loading recordings...</div>;
  }

  if (recordings.length === 0) {
    return (
      <div className="empty-state">No recordings yet. Start speaking!</div>
    );
  }

  return (
    <div className="recordings-list">
      <h3 className="list-title">Recent Recordings</h3>
      <div className="list-content">
        {recordings.map((rec) => (
          <div key={rec.id} className="recording-card">
            <div
              className={`card-icon ${
                String(rec.transcription_status || "").toLowerCase() ===
                "completed"
                  ? "completed"
                  : ""
              }`}
            >
              <Play size={20} fill="currentColor" />
            </div>

            <div className="card-info">
              <div className="info-row main">
                <span className="date">
                  {new Date(rec.recorded_at).toLocaleDateString()}
                </span>
                <span className="time">
                  {new Date(rec.recorded_at).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
              </div>
              <div className="info-row sub">
                <span className="duration">
                  <Clock size={12} /> {Math.floor(rec.duration_seconds / 60)}:
                  {(rec.duration_seconds % 60).toString().padStart(2, "0")}
                </span>
                {rec.location_text && (
                  <span className="location">
                    <MapPin size={12} /> {rec.location_text}
                  </span>
                )}
              </div>
            </div>

            <button className="delete-btn" onClick={() => handleDelete(rec.id)}>
              <Trash2 size={16} />
            </button>
          </div>
        ))}
      </div>

      <style>{`
        .recordings-list {
            width: 100%;
            max-width: 800px;
            margin: 2rem auto;
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden; /* For scrolling list inside */
        }
        
        .list-title {
            color: var(--text-primary);
            margin-bottom: 1rem;
            font-size: 1.25rem;
        }

        .list-content {
            display: flex;
            flex-direction: column;
            gap: 1rem;
            overflow-y: auto;
            padding-right: 0.5rem;
            padding-bottom: 2rem;
        }

        .recording-card {
            background-color: var(--bg-tertiary);
            border-radius: 16px;
            padding: 1rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            transition: transform 0.2s;
            border: 1px solid transparent;
        }

        .recording-card:hover {
            transform: translateY(-2px);
            border-color: var(--accent-secondary);
        }

        .card-icon {
            width: 42px;
            height: 42px;
            border-radius: 50%;
            background-color: rgba(31, 41, 55, 1);
            color: rgba(209, 213, 219, 1);
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
        }

        .card-icon.completed {
             background-color: rgba(20, 184, 166, 0.15);
             color: rgb(20, 184, 166);
             box-shadow: 0 0 10px rgba(20, 184, 166, 0.25);
        }

        .card-info {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }

        .info-row {
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .info-row.main {
            font-weight: 500;
            color: var(--text-primary);
        }

        .info-row.sub {
            font-size: 0.85rem;
            color: var(--text-secondary);
        }
        
        .duration, .location {
            display: flex;
            align-items: center;
            gap: 0.25rem;
        }

        .delete-btn {
            background: transparent;
            color: var(--text-secondary);
            padding: 8px;
        }
        .delete-btn:hover {
            background-color: rgba(255,255,255,0.05);
            color: #ef4444;
        }

        .loading-state, .empty-state {
            text-align: center;
            color: var(--text-secondary);
            padding: 2rem;
        }
      `}</style>
    </div>
  );
};

export default RecordingList;
