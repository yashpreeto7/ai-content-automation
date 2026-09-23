# AI-Powered Content Automation Engine 🎬🤖

An autonomous, end-to-end media automation and video synthesis platform designed to transform topics, headlines, and ideas into fully edited, high-retention short-form (9:16 Shorts/Reels/TikTok) and landscape (16:9) video packages.

---

## ⚡ Core Capabilities

1. **Multimodal Video Reading & Inspection**:
   - Deep inspection of video assets via `ffprobe`: duration, bitrate, resolution, codecs, and framerate.
   - Shot and scene boundary detection.
   - Speech-to-text with word-level timestamps (faster-whisper).

2. **Hook-Driven Scriptwriting**:
   - Psychological viral pacing using the **Hook $\to$ Retain $\to$ Payoff** framework.
   - Timed scene breakdowns with cinematic visual prompts tailored for text-to-video models.

3. **Neural Voiceover & Word Timestamping**:
   - Ultra-realistic, expressive voice narration via `edge-tts` (free, zero-cost, neural) and ElevenLabs.
   - Microsecond-accurate word boundaries extracted for frame-level subtitle synchronization.

4. **Generative Visual Synthesis & Procedural Animation**:
   - Integrations for Gemini Omni Flash (`gemini-omni-flash-preview`), Veo, Runway, and Kling.
   - Built-in dynamic procedural renderer with Ken Burns camera motion (pan/zoom) to ensure 100% offline/local execution capability.

5. **Programmatic Post-Production (FFmpeg)**:
   - Dynamic 9:16 vertical reframing (blurred letterbox padding or smart center-crop).
   - Word-level animated karaoke captions with active word highlighting (`.ass`).
   - Automated sidechain audio ducking (background music volume attenuates -14dB during voiceover).
   - Fast web streaming MP4 encoding (`-movflags +faststart`).

6. **Social Publication Packaging**:
   - Companion metadata package: 3 high-CTR title variations, SEO description with chapter timestamps, trending hashtags, and thumbnail generation prompts.

---

## 🏗️ Directory Layout

```
ai-content-automation/
├── .agents/
│   └── skills/                       # Antigravity Specialized Agent Skills
│       ├── video-reading/            # Ingestion, scene split, OCR, Whisper, metadata
│       ├── video-generation/         # Generative AI video synthesis & B-roll prompts
│       ├── video-processing/         # FFmpeg, 9:16 reframing, animated captions, ducking
│       ├── content-pipeline/         # Autonomous Topic -> Video orchestrator
│       ├── skill-creator/            # Authoring, validating, and publishing agent skills
│       ├── ui-ux-pro-max/            # UI design systems, color tokens, studio layouts
│       ├── impeccable/               # Frontend aesthetic polish & design critique
│       ├── planning-with-files/      # Persistent multi-step task planning
│       └── context-sync/             # Session continuity & handoff tracking
├── src/
│   ├── core/                         # Configuration, models, and directory manager
│   ├── readers/                      # Video inspection and transcription engines
│   ├── generators/                   # Script, neural voice, and video clip generators
│   ├── processors/                   # FFmpeg engine, audio ducking, caption builder
│   └── pipeline/                     # End-to-end automation orchestrator
├── templates/
│   ├── prompts.json                  # Curated visual B-roll prompts across niches
│   └── styles.json                   # Visual themes (Cinematic, Cyberpunk, Minimalist, Documentary)
├── assets/                           # Fonts, background music tracks, and SFX
├── output/                           # Rendered MP4 videos and metadata packages
├── cli.py                            # Unified Rich/Typer command-line interface
├── pyproject.toml                    # Packaging definition
├── requirements.txt                  # Python dependencies
├── .env.example                      # Environment variables template
├── AGENTS.md                         # Master Agent instructions & protocol
└── README.md                         # Documentation
```

---

## 🚀 Quick Start

### 1. Install Dependencies

Ensure Python 3.10+ is installed:

```bash
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)

Copy `.env.example` to `.env` and add your API keys (the engine operates out-of-the-box with free Edge-TTS and local procedural rendering even without external keys):

```bash
cp .env.example .env
```

### 3. CLI Commands

#### End-to-End One-Click Video Generation
```bash
python cli.py auto-short --topic "The Paradox of Choice" --style cinematic
```

#### Generate Viral Script Only
```bash
python cli.py create-script --topic "Why Quantum Computers Change Everything" --style cyberpunk
```

#### Generate Voiceover with Word Timestamps
```bash
python cli.py generate-voice --text "Stop doing this mistake today." --output output/sample_voice.mp3
```

#### Inspect an Existing Video File
```bash
python cli.py analyze-video path/to/video.mp4
```

#### View Visual Styles & Themes
```bash
python cli.py list-styles
```

---

## 🤖 Agent System & Skills

This workspace is fully integrated with **Antigravity AI Agent Protocols**. When interacting with AI assistants in this repository:
- All agents consult `AGENTS.md` as the master directive.
- Specialized workflows are encapsulated as skills in `.agents/skills/`.
- Validate skills anytime using:
  ```bash
  python .agents/skills/skill-creator/scripts/validate_skill.py
  ```

---

## 📄 License

MIT License. Built for modern content creators, automated media workflows, and AI engineering.
