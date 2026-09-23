---
name: video-reading
description: Inspects, analyzes, and extracts multimodal intelligence from video files. Covers ffprobe metadata extraction, scene segmentation/shot boundary detection, speech-to-text transcription with timestamps, OCR on-screen text recognition, and viral hook/retention analytics.
---

# Video Reading & Analysis Skill

This skill provides comprehensive instructions, workflows, and code patterns to inspect, decompose, and extract semantic intelligence from video media.

---

## 1. Core Capabilities

1. **Format & Metadata Inspection**:
   - Resolution, frame rate (`fps`), total frame count, duration, aspect ratio.
   - Video codec (`h264`, `hevc`, `vp9`, `av01`), pixel format, bitrate.
   - Audio tracks, sample rate (`44100Hz`, `48000Hz`), channels (mono/stereo), audio codecs.
2. **Scene & Shot Boundary Detection**:
   - Detection of hard cuts, fades, and dissolves using pixel delta thresholds.
   - Timestamped scene intervals (`start_time`, `end_time`, `duration`).
   - Representative keyframe extraction per scene.
3. **Speech-to-Text (STT) & Audio Intelligence**:
   - Transcription using Whisper / faster-whisper or Gemini multimodal audio.
   - Word-level timestamps (`word`, `start_sec`, `end_sec`, `confidence`).
   - Silent pause detection for pacing and trimming.
4. **Visual Understanding & OCR**:
   - Keyframe OCR extraction for reading on-screen graphics, lower-thirds, watermarks, or slide text.
   - Multimodal video understanding with Gemini (analyzing subject action, mood, camera motion, and object tracking).
5. **Pacing & Retention Analytics**:
   - Words Per Minute (WPM) calculation (ideal viral pacing: 140–180 WPM).
   - Hook strength analysis (first 3 seconds visual density and audio energy).
   - Scene frequency (average cut interval: 2.0s – 3.5s for short-form retention).

---

## 2. Workflows

### Workflow A: Quick Metadata Inspection
```python
import subprocess
import json

def inspect_video_metadata(video_path: str) -> dict:
    """Extract full stream metadata via ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)
```

### Workflow B: Scene Detection & Keyframe Extraction
Use FFmpeg's `select` filter with scene detection score threshold (typically `0.3` to `0.4`):
```bash
# Extract keyframes on scene change > 30%
ffmpeg -i input.mp4 -vf "select='gt(scene,0.3)',showinfo" -vsync vfr output_keyframe_%03d.png
```

Or via OpenCV / PySceneDetect in Python:
```python
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector

def find_scenes(video_path: str, threshold: float = 27.0):
    video_manager = VideoManager([video_path])
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=threshold))
    
    video_manager.start()
    scene_manager.detect_scenes(frame_source=video_manager)
    scene_list = scene_manager.get_scene_list()
    return [(scene[0].get_seconds(), scene[1].get_seconds()) for scene in scene_list]
```

### Workflow C: Audio Transcription with Word Timestamps
```python
from faster_whisper import WhisperModel

def transcribe_video_audio(video_path: str, model_size: str = "base"):
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, info = model.transcribe(video_path, word_timestamps=True)
    
    transcript = []
    for segment in segments:
        for word in segment.words:
            transcript.append({
                "word": word.word.strip(),
                "start": round(word.start, 3),
                "end": round(word.end, 3),
                "probability": round(word.probability, 3)
            })
    return transcript
```

### Workflow D: Multimodal Video Analysis via Gemini
```python
from google import genai
from google.genai import types

def analyze_video_content(video_path: str, prompt: str = "Break down each scene, identify the hook, and evaluate pacing."):
    client = genai.Client()
    video_file = client.files.upload(file=video_path)
    
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[video_file, prompt]
    )
    return response.text
```

---

## 3. Best Practices & Heuristics

- **Resolution Check**: Check if input is landscape (`1920x1080`) or vertical (`1080x1920`). If repurposing for Shorts/Reels/TikTok, flag it for vertical reframing.
- **Hook Scoring**: The first 3 seconds must contain a strong visual change and immediate voice hook. Zero audio in the first second decreases retention by over 40%.
- **Audio Cleanliness**: Check audio peak levels. If audio clips above 0dB, apply a soft limiter.
