# Task Plan: AI Content Production Desktop Application

## Status Summary
- **Phase 1: Environment & GitHub Repo Setup** — In Progress
- **Phase 2: Core Domain Models & SQLite Storage** — Pending
- **Phase 3: AI Provider Abstraction (Gemini & Ollama)** — Pending
- **Phase 4: Deterministic Video & Audio Processing Engine** — Pending
- **Phase 5: Publishing Services (YouTube & Instagram)** — Pending
- **Phase 6: Local Backend Server (FastAPI + SSE)** — Pending
- **Phase 7: Desktop UI (Tauri v2 + React + TypeScript)** — Pending
- **Phase 8: End-to-End Testing & Verification** — Pending

## Milestones & Tasks

### Phase 1: Environment & GitHub Repo Setup
- [ ] Initialize local git repository
- [ ] Create remote GitHub repository `ai-content-automation` on Yashpreet's account via GitHub MCP
- [ ] Install missing Python dependencies (`fastapi`, `uvicorn`, `google-genai`, `opencv-python-headless`, `faster-whisper`, `moviepy`)
- [ ] Author custom skill `.agents/skills/hinglish-content-producer/SKILL.md`

### Phase 2: Core Models & SQLite Storage
- [ ] Extend `src/core/models.py` with `ContentAnalysis`, `LongFormEditPlan`, `ShortCandidate`, `EditPlan`, `VideoMetadata`, `Project`
- [ ] Implement `src/core/database.py` with SQLite schema and state management
- [ ] Verify database migration and project creation

### Phase 3: AI Provider Abstraction
- [ ] Create `src/providers/base.py` (`AIProvider` ABC)
- [ ] Implement `src/providers/gemini_provider.py` with structured schema & Hinglish prompt directives
- [ ] Implement `src/providers/ollama_provider.py` with local Ollama API, whisper transcript & vision keyframes
- [ ] Implement `src/providers/factory.py` for dynamic provider switching
- [ ] Unit tests for provider abstraction and schema parity

### Phase 4: Deterministic Processing Engine
- [ ] Enhance `src/readers/video_reader.py` with faster-whisper Hinglish transcription and FFmpeg silence detection
- [ ] Implement `src/processors/face_tracker.py` for face-centered 9:16 intelligent cropping
- [ ] Upgrade `src/processors/caption_engine.py` for Roman-Hinglish animated karaoke captions (`\k` highlight, safe margins)
- [ ] Upgrade `src/processors/ffmpeg_engine.py` for deterministic long-form cuts, 9:16 vertical conversion, and audio ducking

### Phase 5: Publishing Services
- [ ] Implement `src/publishing/youtube.py` for YouTube long-form & Shorts
- [ ] Implement `src/publishing/instagram.py` for Instagram Reels

### Phase 6: Local Backend Server
- [ ] Build `src/server/app.py` FastAPI app with REST & SSE endpoints
- [ ] Implement background task runners for video rendering and AI analysis
- [ ] Add static file serving for video previews and assets

### Phase 7: Desktop UI
- [ ] Scaffold Vite + React + TypeScript frontend in `ui/`
- [ ] Integrate modern dark-mode design system with `ui-ux-pro-max` tokens
- [ ] Implement Dashboard, New Project Wizard, Live Processing Progress, Review Studio, and Export/Publish screens
- [ ] Configure Tauri v2 (`src-tauri/`)

### Phase 8: End-to-End Testing & Verification
- [ ] Automated tests (`pytest`)
- [ ] Process real/synthetic Hindi/Hinglish sample video end-to-end
- [ ] Verify rendered long-form video (16:9) and 4-5 Shorts (9:16) with Roman-Hinglish captions
- [ ] Build & package Tauri application
- [ ] Git commit and push all code to GitHub
