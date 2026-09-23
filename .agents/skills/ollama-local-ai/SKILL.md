---
name: ollama-local-ai
description: Offline local AI inference engine using Ollama on consumer GPUs (e.g., RTX 4060 8GB VRAM). Manages context window budgeting, transcript chunking, keyframe vision analysis, strict structured JSON prompting, and deterministic heuristic fallback when Ollama is offline.
---

# Ollama Local AI Skill

This skill provides optimization patterns, prompt templates, and execution workflows for running video transcript understanding and edit plan generation entirely on local hardware using Ollama.

---

## 1. Hardware Architecture & Budget (RTX 4060, 8GB VRAM)

When processing video recordings on consumer hardware:
1. **Memory Budgeting**:
   - `faster-whisper` (medium or small) consumes ~1.5GB to 2.5GB VRAM.
   - Ollama LLM (e.g. `llama3.2:3b`, `qwen2.5:7b-instruct-q4_K_M`) consumes 3.5GB to 5.5GB VRAM.
   - Run stages sequentially: unload or release whisper model before starting Ollama inference if VRAM headroom is tight.
2. **Recommended Models**:
   - `llama3.2:3b`: Ultra-fast (80+ tokens/sec on RTX 4060), fits easily into 3GB VRAM, highly competent at JSON structuring.
   - `qwen2.5:7b-instruct-q4_K_M`: Superb multilingual and Indian code-switching capabilities, handles long transcripts up to 32k context.
   - `llava:7b` or `moondream2`: Lightweight vision models for keyframe B-roll and visual hook validation.

---

## 2. Local Video Understanding Pipeline

Because local models cannot directly ingest high-resolution raw video files in one stream:

```text
Raw Video Recording
       │
       ├── FFmpeg Audio Extract (16kHz mono WAV)
       │         │
       │         ▼
       │   faster-whisper (Word-level timestamps & Roman Hinglish)
       │
       └── FFmpeg Keyframe Sample (1 frame every 5s / scene changes)
                 │
                 ▼
       Lightweight Vision Check (Optional)
                 │
                 ▼
       Transcript + Timeline Intervals
                 │
                 ▼
          Ollama LLM
   (Strict System Prompt + JSON Format)
                 │
                 ▼
        Structured Edit Plan
   (Long-form Cuts + 4-5 Standalone Shorts)
```

---

## 3. Strict Structured JSON Generation

Local models need explicit guidance to output valid JSON without conversational conversational preambles:

```python
import json
import httpx

def query_ollama_json(
    prompt: str,
    system_prompt: str,
    model: str = "llama3.2",
    endpoint: str = "http://127.0.0.1:11434"
) -> dict:
    url = f"{endpoint}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system_prompt,
        "format": "json", # Ollama native JSON schema mode
        "stream": False,
        "options": {
            "temperature": 0.2, # Low temperature for deterministic timestamps
            "top_p": 0.9,
            "num_ctx": 16384    # Extended context window for full transcripts
        }
    }
    
    with httpx.Client(timeout=120.0) as client:
        res = client.post(url, json=payload)
        res.raise_for_status()
        data = res.json()
        return json.loads(data["response"])
```

---

## 4. Deterministic Fallback Mode

If Ollama service is not running or the model is downloading, the system must not crash. It activates a deterministic heuristic engine that analyzes speech density, silence intervals, and sentence boundaries to curate the 10–15m long-form cuts and 4–5 Shorts.
