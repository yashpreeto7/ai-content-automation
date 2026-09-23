---
name: video-processing
description: Programmatic video editing, FFmpeg post-processing, 9:16 vertical reframing, animated karaoke subtitle generation, audio ducking, and transition effects. Use when assembling video clips, burning captions, mixing audio, and rendering final social media videos.
---

# Video Processing & Post-Production Skill

This skill provides comprehensive standards, FFmpeg commands, and Python code patterns for programmatic video editing, audio mixing, subtitle styling, and rendering high-retention short-form and long-form video content.

---

## 1. Core Post-Production Capabilities

1. **Aspect Ratio Conversion & Vertical 9:16 Reframing**:
   - Smart center cropping (`crop=ih*9/16:ih`).
   - Blurred background letterboxing (stacking blurred zoomed background with original 16:9 foreground for cinematic aesthetic).
   - Pan-and-scan camera motion across wide shots.

2. **Animated Karaoke Captions (ASS / SRT)**:
   - Generation of Advanced SubStation Alpha (`.ass`) subtitle files with word-by-word highlight colors.
   - High-contrast typography (Montserrat Black, Anton, The Bold Font) with thick outline strokes and subtle drop-shadows.
   - Dynamic popup/scale micro-animations per spoken word.

3. **Audio Mixing & Sidechain Ducking**:
   - Voiceover normalization (EBU R128 loudness normalization to `-16 LUFS` for Shorts/Reels, `-14 LUFS` for YouTube).
   - Dynamic sidechain audio ducking: lowering background music by 12–15dB when narration is present, smoothly ramping back up during silence (attack: 50ms, release: 300ms).
   - Sound effect (SFX) synchronization (whooshes, pops, risers at visual cuts).

4. **Visual Effects & Pacing Hooks**:
   - Subtle Ken Burns pan/zoom effect on static frames.
   - Quick cross-dissolves, dip-to-black, and whip transitions between scenes.
   - Colored progress bars and engagement overlays.

5. **Encoding Optimization**:
   - Fast encoding with H.264 (`libx264`), High profile, YUV420p pixel format.
   - Web streaming optimization with `-movflags +faststart`.
   - Hardware acceleration options (`h264_nvenc` for NVIDIA GPUs, `h264_qsv` for Intel, `h264_amf` for AMD).

---

## 2. Production FFmpeg Recipes

### Recipe A: 16:9 to 9:16 Blurred Background (Letterbox)
Places the original video centered, with a heavily blurred, zoomed version of itself in the background to fill the 1080x1920 vertical canvas:

```bash
ffmpeg -i input.mp4 -lavfi "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=20[bg];[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2" -c:v libx264 -crf 19 -preset fast -c:a copy output_916.mp4
```

### Recipe B: Audio Sidechain Ducking
Lowers background music (`music.mp3`) whenever narration voiceover (`voice.mp3`) speaks:

```bash
ffmpeg -i voice.mp3 -i music.mp3 -filter_complex "[1:a]volume=0.25[music_low];[0:a][music_low]sidechaincompress=threshold=0.08:ratio=5:attack=50:release=300[ducked_music];[0:a][ducked_music]amix=inputs=2:duration=first:dropout_transition=2" -c:a aac -b:a 192k mixed_audio.mp3
```

### Recipe C: Burning Word-Level Animated ASS Captions
```bash
ffmpeg -i video.mp4 -vf "ass=captions.ass" -c:v libx264 -crf 18 -preset medium -c:a copy output_with_captions.mp4
```

### Recipe D: Concatenating Multiple Scene Clips
Using a text file list of clips with same resolution and frame rate:
```bash
# filelist.txt contains:
# file 'scene_001.mp4'
# file 'scene_002.mp4'
ffmpeg -f concat -safe 0 -i filelist.txt -c copy assembled.mp4
```

---

## 3. Python Automation Code Patterns

### Dynamic ASS Karaoke Generator
```python
def generate_karaoke_ass(word_timings: list[dict], output_ass: str):
    """
    Creates an ASS subtitle file where each spoken word highlights in yellow (#00FFFF in BGR).
    word_timings format: [{'word': 'Hello', 'start': 0.12, 'end': 0.45}, ...]
    """
    header = """[Script Info]
Title: Animated Karaoke Captions
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,Montserrat Black,72,&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,2,2,40,40,480,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # Group words into 3-word chunks
    chunks = [word_timings[i:i+3] for i in range(0, len(word_timings), 3)]
    events = []
    
    for chunk in chunks:
        if not chunk:
            continue
        c_start = format_ass_time(chunk[0]['start'])
        c_end = format_ass_time(chunk[-1]['end'])
        
        # Build karaoke timing tags: \k<duration_in_centiseconds>
        k_text = ""
        for w in chunk:
            duration_cs = max(1, int((w['end'] - w['start']) * 100))
            k_text += f"{{\\k{duration_cs}}}{w['word']} "
        
        events.append(f"Dialogue: 0,{c_start},{c_end},Karaoke,,0,0,0,,{k_text.strip()}")
        
    with open(output_ass, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events))

def format_ass_time(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hrs:01d}:{mins:02d}:{secs:05.2f}"
```

### Full Video Assembly Pipeline in Python
```python
import subprocess
import shutil

def render_final_video(scene_clips: list[str], voiceover: str, music: str, ass_subtitles: str, output_path: str):
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    
    # 1. Write concat list
    with open("scenes.txt", "w") as f:
        for clip in scene_clips:
            f.write(f"file '{clip}'\n")
            
    # 2. Concat video, mix voiceover + ducked music, burn subtitles
    cmd = [
        ffmpeg, "-y",
        "-f", "concat", "-safe", "0", "-i", "scenes.txt",
        "-i", voiceover,
        "-i", music,
        "-filter_complex",
        "[2:a]volume=0.2[bgm];"
        "[1:a][bgm]amix=inputs=2:duration=first:dropout_transition=1[aout];"
        f"[0:v]ass='{ass_subtitles}'[vout]",
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "19",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        output_path
    ]
    subprocess.run(cmd, check=True)
```

---

## 4. Best Practices Checklist

- **Font Licensing**: Use open-source, punchy sans-serif fonts (Montserrat, Inter, Anton, Oswald).
- **Safe Zones**: In 9:16 vertical videos, keep captions between vertical margins `Y=35%` to `Y=70%` to prevent UI overlap with TikTok/Reels usernames, like buttons, and seek bars.
- **Audio Levels**: Voice should peak at `-1.0 dBFS`. Music during speech should sit at `-22 dBFS` to `-26 dBFS`.
- **FastStart Flag**: Always append `-movflags +faststart` to MP4 renders so online video players can stream instantly without downloading the entire file.
