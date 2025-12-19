# Pana - पाना

📜 **The Voice Book That Writes You**

**Pana** is a sophisticated voice journaling assistant that transforms your raw voice notes into structured, meaningful reflections. Inspired by the Nepali word **“पाना (Pana)”**, meaning _page_, this project bridges the gap between spoken thoughts and an organized personal history.

---

## 🚀 Key Features

- **High-Fidelity Audio Capture**
  Record thoughts on the fly with real-time volume visualization and a polished, premium UI.
- **Word-Level Synchronized Transcription**
  Powered by OpenAI Whisper, Pana provides live, word-by-word transcription display during playback, allowing you to "read" your voice.
- **Background Processing with Celery**
  Transcriptions are handled asynchronously in the background, ensuring the UI remains snappy and responsive.
- **Real-Time Status Updates**
  Uses Server-Sent Events (SSE) to notify the frontend as soon as a transcription is processed and ready.
- **Secure Management**
  Full CRUD operations for recordings, including a custom confirmation dialog for deletions and a "soft-delete" pattern in the database.
- **Contextual Meta-Data**
  Automatically captures geolocation and timestamps to provide context for every entry.

---

## 🛠 Tech Stack

### Frontend

- **Framework**: React.js (Vite)
- **Styling**: Vanilla CSS (Premium Light Theme)
- **Icons**: Lucide React
- **State/API**: Axios, Custom Hooks (SSE)
- **Feedback**: Sonner (Toasts), Custom Dialogs

### Backend

- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL (SQLAlchemy Async)
- **Tasks**: Celery + Redis (Task Queue)
- **AI/ML**: OpenAI Whisper (via API)

---

## � Project Architecture

1.  **Capture**: User records audio via the `AudioRecorder` component.
2.  **Upload**: Audio is sent to the FastAPI backend and stored securely.
3.  **Process**: A Celery task is triggered to transcribe the audio using Whisper with word-level granularity.
4.  **Notify**: Once complete, the backend sends an SSE event to the frontend.
5.  **Reflect**: The `RecordingCard` fetches the rich transcription and displays it in sync with audio playback.

---

## 🎯 Current Status

The project core is fully functional, featuring a robust backend-to-frontend pipeline for voice capture and transcription. Future developments will focus on the "Daily Summary" engine to aggregate these notes into cohesive journal pages.

---
