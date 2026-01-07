# Paraclete

> Mobile-first AI coding platform: Voice-first, model-agnostic, no laptop required.

## Overview

Paraclete is a mobile command center for AI development. Developers delegate to AI agents via voice, review work, and course-correct from anywhere.

**Key Features:**
- 🎤 Voice-first coding with Deepgram STT + ElevenLabs TTS
- 📱 Flutter mobile app with SSH terminal
- 🤖 Multi-agent orchestration via LangGraph
- ☁️ Cloud VM provisioning (Fly.io)
- 🔐 BYOK (Bring Your Own Keys) or managed keys
- 🔄 Desktop session sync (VS Code extension)

## Tech Stack

**Mobile:** Flutter 3.27+ • Dart 3.6+ • Riverpod 3
**Backend:** FastAPI • LangGraph 1.0 • PostgreSQL
**Voice:** Deepgram • ElevenLabs (120ms WebRTC)
**Infrastructure:** Fly.io Machines • Tailscale VPN

## Project Structure

```
Paraclete/
├── backend/          # FastAPI + LangGraph
├── mobile/           # Flutter mobile app
```

## Documentation

See [CLAUDE.md](CLAUDE.md) for complete technical specification.

## License

Proprietary - All rights reserved
