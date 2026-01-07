# Paraclete Backend

FastAPI backend for the Paraclete mobile-first AI coding platform.

## Overview

This backend provides:
- Session management for coding sessions
- WebSocket streaming for real-time agent updates
- Voice transcription and synthesis endpoints
- Authentication via JWT and GitHub OAuth
- PostgreSQL for persistence
- Placeholder agent endpoints (LangGraph integration in Phase 2)

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis (optional, for caching)

### Installation

1. Clone the repository:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run database migrations:
```bash
alembic upgrade head
```

6. Start the development server:
```bash
uvicorn app.main:app --reload --port 8000
```

### Docker Setup

For a complete development environment with PostgreSQL and Redis:

```bash
docker-compose up
```

This will:
- Start PostgreSQL on port 5432
- Start Redis on port 6379
- Run database migrations
- Start the FastAPI server on port 8000

## API Documentation

Once running, visit:
- Interactive API docs: http://localhost:8000/docs
- ReDoc documentation: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── v1/          # API endpoints
│   │   └── websocket.py # WebSocket handlers
│   ├── core/            # Core utilities
│   │   ├── auth.py      # Authentication
│   │   ├── security.py  # JWT, encryption
│   │   └── exceptions.py
│   ├── db/              # Database
│   │   ├── database.py  # Connection setup
│   │   └── models.py    # SQLAlchemy models
│   ├── services/        # Business logic
│   │   ├── session_service.py
│   │   └── notification_service.py
│   ├── config.py        # Settings
│   └── main.py          # FastAPI app
├── alembic/             # Database migrations
├── tests/               # Test suite
├── requirements.txt     # Dependencies
├── Dockerfile           # Container image
└── docker-compose.yml   # Development stack
```

## Key Endpoints

### Sessions
- `POST /v1/sessions` - Create new session
- `GET /v1/sessions` - List user sessions
- `GET /v1/sessions/{id}` - Get session details
- `DELETE /v1/sessions/{id}` - End session
- `POST /v1/sessions/{id}/sync` - Sync from desktop

### Agents (Placeholder)
- `POST /v1/sessions/{id}/invoke` - Invoke agent
- `GET /v1/sessions/{id}/agents` - Get agent statuses
- `POST /v1/sessions/{id}/approve` - Approve action
- `POST /v1/sessions/{id}/cancel` - Cancel task

### Voice
- `POST /v1/voice/transcribe` - Transcribe audio (Deepgram)
- `POST /v1/voice/synthesize` - Generate speech (ElevenLabs)
- `GET /v1/voice/voices` - List available voices

### WebSocket
- `WS /ws/stream?token={jwt}&session_id={id}` - Real-time streaming

## Authentication

The API uses JWT tokens for authentication:

1. Obtain token via GitHub OAuth (to be implemented)
2. Include token in requests: `Authorization: Bearer {token}`
3. WebSocket auth via query parameter: `?token={jwt}`

## Environment Variables

Key configuration variables:

- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT signing key
- `DEEPGRAM_API_KEY` - For speech-to-text
- `ELEVENLABS_API_KEY` - For text-to-speech
- `FIREBASE_PROJECT_ID` - For push notifications

See `.env.example` for full list.

## Testing

Run tests with pytest:

```bash
pytest
pytest --cov=app  # With coverage
```

## Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "Description"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback:
```bash
alembic downgrade -1
```

## Deployment

### Fly.io

Deploy to Fly.io:

```bash
fly launch
fly secrets set DATABASE_URL=...
fly deploy
```

### Docker

Build production image:

```bash
docker build -t paraclete-backend .
docker run -p 8000:8000 paraclete-backend
```

## Phase 2 Implementation

The following will be implemented in Phase 2:
- LangGraph agent orchestration
- MCP proxy for GitHub, Figma, etc.
- Fly.io VM management for compute
- Real agent processing (currently placeholders)

## License

See main repository LICENSE file.