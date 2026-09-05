# Documentation

Reference for the parts of the system where the code alone does not explain the
reasoning -- protocol shapes, security trade-offs, the rules a feature enforces,
and the contracts clients depend on.

Start with [architecture.md](architecture.md) for the shape every feature
follows; the rest are one page per thing the app does for a user.

| Document | Covers |
|---|---|
| [architecture.md](architecture.md) | Routes, services, repositories; the response envelope; errors; why background jobs are dispatched after commit |
| [authentication.md](authentication.md) | Google sign-in for browser and native clients, token lifecycle, rotation and revocation, threat model |
| [recordings.md](recordings.md) | Upload and validation, day-based listing, soft delete, authorized audio playback |
| [transcriptions.md](transcriptions.md) | Job lifecycle, the Celery worker and its failure policy, confidence scoring, the SSE stream |
| [diary.md](diary.md) | Daily entry generation, transcript gap-filling and filtering, location resolution, the two empty-day fallbacks |
| [home-and-history.md](home-and-history.md) | Profile endpoint and the calendar month view |

Conventions, layout, and commands live in [../CLAUDE.md](../CLAUDE.md).
