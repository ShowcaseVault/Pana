# Pana - पाना

📜 **The Voice Book That Writes You**

**Pana** is a sophisticated voice journaling assistant that transforms your raw voice notes into structured, meaningful reflections. Inspired by the Nepali word **“पाना (Pana)”**, meaning _page_, this project bridges the gap between spoken thoughts and an organized personal history.

---

## 🚀 Key Features

- **High-Fidelity Audio Capture**
  Record thoughts on the fly with real-time volume visualization and a polished, premium UI.
- **Word-Level Synchronized Transcription**
  Powered by OpenAI Whisper, Pana provides live, word-by-word transcription display during playback, allowing you to "read" your voice.
- **Intelligent Diary Synthesis**
  Pana uses advanced LLMs (Groq) to analyze your day's recordings and automatically generate a cohesive diary entry, complete with:
  - **Mood Analysis**: Detects the emotional tone of your day.
  - **Structured Narrative**: Weaves disparate thoughts into a flowing story.
  - **Action Items**: Automatically extracts Todos and Reminders from your rants.
- **Interactive Calendar**
  A visual history of your life. Browse past days, see your "Streak" (days with recordings/diary), and time-travel to view or regenerate diaries for any specific date.
- **Background Processing**
  Transcriptions and AI generation happen asynchronously via Celery & Redis, keeping the experience buttery smooth.
- **Secure & Private**
  Full control over your data with secure Google Authentication and local-first design principles.

---

## 🛠 Tech Stack

### Frontend

- **Framework**: React.js 19 (Vite)
- **Styling**: Vanilla CSS (Custom Premium Light Theme)
- **State**: React Hooks + Context API
- **Visuals**: Framer Motion (Animations), Lucide React (Icons)
- **API**: Axios with Interceptors

### Backend

- **API Framework**: FastAPI (Python 3.12+)
- **Database**: PostgreSQL (via SQLAlchemy Async)
- **Task Queue**: Celery + Redis
- **AI Services**:
  - **Transcription**: OpenAI Whisper
  - **Synthesis**: Groq (LLM)

---

## 🏗 Architecture

1.  **Capture**: User records audio via the `AudioRecorder` component.
2.  **Upload**: Audio is uploaded to the backend and stored on disk.
3.  **Transcribe**: A Celery worker picks up the job and transcribes audio using Whisper.
4.  **Synthesize**: When requested, the AI engine aggregates the day's transcripts and synthesizes a structured Diary Entry.
5.  **Reflect**: The user views their generated diary, plays back source recordings, and tracks action items on the Dashboard or Calendar.

---

## ⚡ Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker & Docker Compose (for Postgres/Redis)
- Google Cloud Project (for Auth)
- Groq & OpenAI API Keys

### Installation

1.  **Clone the repository**

    ```bash
    git clone https://github.com/ShowcaseVault/Pana.git
    cd Pana
    ```

2.  **Start Infrastructure (DB & Redis)**

    ```bash
    docker-compose up -d
    ```

3.  **Backend Setup**

    ```bash
    # Create virtual environment
    python -m venv venv
    source venv/bin/activate  # or venv\Scripts\activate on Windows

    # Install dependencies
    pip install -r requirements.txt

    # Run Migrations
    alembic upgrade head

    # Start API Server
    python backend.py
    ```

4.  **Frontend Setup** (New Terminal)
  - Remember to add the API_BASE_URL to the .env file
    ```bash
    python frontend.py
    ```

5.  **Access the App**
    Open `http://localhost:5173` in your browser.

---

## 🎯 Current Status

The project is feature-complete for the core MVP. Users can record, transcribe, and generate AI diaries. The Calendar integration allows full historical navigation. Future work will focus on mobile responsiveness and enhanced AI personalization.
