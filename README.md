# Paraclete

Mobile-first AI coding platform: Voice-first, model-agnostic and other features.

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

1. **Mobile:** Flutter 3.27+, Dart 3.6+, Riverpod 3
2. **Backend:** FastAPI, LangGraph 1.0, PostgreSQL
3. **Voice:** Deepgram, ElevenLabs (120ms WebRTC)
4. **Infrastructure:** Fly.io Machines, Tailscale VPN

## Project Structure

```
Paraclete/
├── backend/          # FastAPI + LangGraph
├── mobile/           # Flutter mobile app
```

## License

Proprietary - All rights reserved
