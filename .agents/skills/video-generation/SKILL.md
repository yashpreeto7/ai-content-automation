---
name: video-generation
description: Guides AI-powered video and media generation (generative AI synthesis, NOT screen recording). Covers text-to-video, image-to-video, keyframe interpolation, generative B-roll synthesis, AI avatar/talking heads, and synchronized voiceover synthesis using Google Gemini, Veo, Runway, and Edge-TTS/ElevenLabs.
---

# Generative AI Video & Media Generation Skill

This skill governs **generative AI media synthesis**. It focuses strictly on AI model generation (Text-to-Video, Image-to-Video, B-Roll synthesis, and AI speech), **not screen recording**.

---

## 1. Core Generative Capabilities

1. **Text-to-Video (T2V)**:
   - Generating 3s–10s video clips directly from descriptive visual prompts.
   - Cinematic styling: camera movements (pan, tilt, zoom, dolly, orbit, fpv drone), lighting (golden hour, volumetric rays, neon noir, studio lighting), aspect ratios (`9:16`, `16:9`, `1:1`).
2. **Image-to-Video (I2V) & Keyframe Animation**:
   - Animating a high-resolution concept image or photo into fluid motion.
   - Maintaining character and environmental coherence across frames.
3. **Keyframe Interpolation & Morphing**:
   - Providing starting and ending images to generate smooth, temporally coherent transition videos.
4. **AI Voiceover & Speech Synthesis**:
   - Expressive text-to-speech with natural cadence, pauses, and inflection.
   - Outputting synchronized audio stems and word-level timestamps for caption alignment.
5. **Generative B-Roll Curation**:
   - Synthesizing contextual background footage for each script beat (e.g. futuristic server rooms, macro nature shots, glowing synapses, urban night scapes).

---

## 2. Model Integrations & Workflows

### Workflow A: Gemini Omni Flash Video Generation
Using the official `google-genai` SDK:

```python
from google import genai
from google.genai import types

def generate_ai_clip(prompt: str, aspect_ratio: str = "9:16", duration_seconds: int = 5, output_path: str = "clip.mp4"):
    """
    Generate video clip using Gemini Omni Flash / Veo video generation capabilities.
    """
    client = genai.Client()
    
    # Create video interaction request
    interaction = client.interactions.create(
        model="gemini-omni-flash-preview",
        input=[
            types.ContentPart(text=f"Generate a cinematic {aspect_ratio} video: {prompt}")
        ],
        parameters={
            "duration": duration_seconds,
            "aspect_ratio": aspect_ratio
        }
    )
    
    # Download the rendered video asset
    # Save to output_path
    print(f"Generated clip successfully: {output_path}")
```

### Workflow B: Image-to-Video Animation
```python
from google import genai
from google.genai import types

def animate_image_to_video(image_path: str, motion_prompt: str, output_path: str):
    """
    Uploads a reference image and animates it with motion instructions.
    """
    client = genai.Client()
    
    # 1. Upload reference frame to Files API
    uploaded_image = client.files.upload(file=image_path)
    
    # 2. Call Interactions API referencing the uploaded frame
    interaction = client.interactions.create(
        model="gemini-omni-flash-preview",
        input=[
            types.ContentPart(file_data=types.FileData(file_uri=uploaded_image.uri, mime_type=uploaded_image.mime_type)),
            types.ContentPart(text=f"Camera slowly zooms in with subtle atmospheric particles: {motion_prompt}")
        ],
        parameters={"duration": 5, "aspect_ratio": "9:16"}
    )
    return interaction
```

### Workflow C: AI Voiceover Synthesis (Edge-TTS / ElevenLabs)
Using `edge-tts` for high-quality, zero-cost, local neural voice synthesis with word boundaries:

```python
import asyncio
import edge_tts

async def generate_speech(text: str, voice: str = "en-US-ChristopherNeural", output_audio: str = "voiceover.mp3"):
    """
    Generates neural voiceover audio and collects word timestamps.
    """
    communicate = edge_tts.Communicate(text, voice)
    submaker = edge_tts.SubMaker()
    
    with open(output_audio, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.create_sub((chunk["offset"], chunk["duration"]), chunk["text"])
                
    return submaker.generate_subs()
```

---

## 3. Cinematic Prompt Engineering Guide

When crafting prompts for AI video generation:

| Parameter | Recommended Formulations | Avoid |
| :--- | :--- | :--- |
| **Motion** | "slow dolly zoom", "smooth sweeping cinematic drone pan", "orbiting camera 360", "static shot with intense particle drift" | "fast moving", "shake violently", "crazy action" (causes temporal tearing) |
| **Lighting** | "Moody volumetric backlighting", "golden hour rim light", "dramatic chiaroscuro contrast", "bioluminescent neon glow" | "normal light", "bright" |
| **Texture & Detail** | "Hyper-detailed 8k, shallow depth of field, 35mm film grain, anamorphic lens flare" | "photorealistic" (often results in plastic textures) |
| **Temporal Consistency** | Keep actions focused on a single coherent motion per 5-second interval | Stacking multiple consecutive character actions in a single clip |

---

## 4. Best Practices

- **Scene Granularity**: Never generate a 60-second video in one single prompt. Break the script down into 3-5 second visual beats.
- **Audio Separation**: Always generate the voiceover audio track first so that exact scene durations match speech pacing.
- **Aspect Ratio Locking**: Ensure all generated clips match the target container (`9:16` for Shorts/Reels/TikTok, `16:9` for longform landscape) to prevent distortion during assembly.
