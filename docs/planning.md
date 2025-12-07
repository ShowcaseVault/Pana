📄 Pana – AI-Powered Voice Journal Project Report

Project Vision:
Pana is a personal voice-based journaling app that turns everyday voice recordings into meaningful, emotionally rich diary entries. Its goal is to make journaling effortless, story-like, and reflective, using AI to generate a structured daily diary with insights, highlights, emotions, and optional location context.

### 1. Core Features (MVP)

These are must-have features for the initial working version.

| Feature                 | Description                                                               | Priority | Status  |
| ----------------------- | ------------------------------------------------------------------------- | -------- | ------- |
| Voice Recording         | Record multiple short clips per day                                       | High     | Planned |
| Recordings Tab          | View, play, and delete recordings                                         | High     | Planned |
| MyDiary Tab             | Generate a clean daily diary from recordings                              | High     | Planned |
| Generate Diary Workflow | Upload recordings to backend → transcribe → summarize → return diary      | High     | Planned |
| Backend URL Setting     | Configure server URL in settings                                          | High     | Planned |
| Audio File Storage      | Save files locally by date/timestamp (recordings/YYYY-MM-DD/timestamp.m4a) | High     | Planned |

### 2. Backend Features

| Feature                       | Description                                                                 | Priority | Status  |
| ----------------------------- | --------------------------------------------------------------------------- | -------- | ------- |
| Upload Endpoint               | Upload recordings with metadata (date, timestamp)                           | High     | Planned |
| Transcription                 | Transcribe audio using Whisper or similar                                   | High     | Planned |
| Journal Generation Endpoint   | Generate structured diary with story, highlights, todos, emotions, reflections | High     | Planned |
| Optional Database Storage     | Save transcripts and journals for personalization                           | Medium   | Planned |
| PostgreSQL Schema             | Tables: users, recordings, journals                                         | High     | Planned |
| Location Support              | Save location (lat/long + place name) with recordings                       | Medium   | Planned |

### 3. AI & Diary Features

| Feature                    | Description                                           | Priority | Status  |
| -------------------------- | ----------------------------------------------------- | -------- | ------- |
| Narrative Generation       | AI writes story from transcripts                      | High     | Planned |
| Key Moments / Highlights   | Extract important events                              | High     | Planned |
| TODO Extraction            | Detect tasks and reminders                            | High     | Planned |
| Emotion Summary            | Summarize expressed emotions                          | Medium   | Planned |
| Reflection / Insight       | AI adds reflective commentary                         | Medium   | Planned |
| Location Integration       | AI incorporates where recordings occurred             | Medium   | Planned |
| Location Categories        | Gym, Home, Work, School, etc. for richer diary        | Low      | Future  |
| Story Formatting           | Clean, readable text with natural flow                | High     | Planned |

### 4. Future Features / Enhancements

| Feature                       | Description                                       | Priority | Status |
| ----------------------------- | ------------------------------------------------- | -------- | ------ |
| Auto-Generate Daily Journal   | Cron job to automatically generate diary at night | Medium   | Future |
| Weekly Summary                | Summarize past 7 days (trends, emotions, todos)   | Medium   | Future |
| Search Memories               | Search past transcripts/journals by keywords      | Low      | Future |
| Emotion Trend Graphs          | Show weekly emotion charts                        | Low      | Future |
| Moments Auto-Highlighting     | Detect memorable or repeated moments              | Low      | Future |
| Voice Emotion Capture         | Track tone, energy, or stress from voice          | Low      | Future |
| Raw Recording Backup          | Store audio files on backend                      | Low      | Future |
| Daily Question Prompt         | Gentle questions to guide reflection              | Low      | Future |
| “Revisit This Day” Feature    | See diary from previous year / day                | Low      | Future |
| Location Timeline / Map       | Visual map of day’s recordings                    | Low      | Future |

### 5. Suggested Development Prioritization

#### MVP Development
- Voice recording and storage
- Recordings tab + playback
- Backend API endpoints (upload + generate journal)
- Basic AI journal generation (story + highlights + todos)

#### Enhanced AI Features
- Emotion summary
- Reflection / insight
- Location integration

#### Database & Personalization
- PostgreSQL integration
- Save transcripts & journals
- Basic analytics (weekly summary)

#### User Experience Enhancements
- Settings for backend URL
- Auto-generate diary
- Search & revisit features

#### Optional / Future Features
- Emotion graphs
- Moments auto-highlight
- Voice emotion capture
- Location timeline/map

### 6. Technical Notes

- **Frontend**: Flutter or React Native (3-tab interface: Recordings / Record / MyDiary)
- **Backend**: FastAPI (Python) + PostgreSQL
- **Storage**:
  - Audio: local device (date/timestamp folder structure)
  - Transcripts + journals: server database
- **AI**:
  - Whisper for transcription
  - LLM for diary generation (OpenAI API or self-hosted model)
  - Prompt includes transcripts, optional location, optional timestamps

### 7. Next Steps
- Scaffold the frontend tabs (recording, recordings list, diary)
- Build backend API (upload + generate diary)
- Integrate PostgreSQL database
- Implement Whisper transcription + LLM diary generation
- Add location capture for recordings
- Improve AI diary with story, highlights, todos, emotions, reflections