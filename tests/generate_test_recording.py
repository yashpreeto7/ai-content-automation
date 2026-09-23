import asyncio
import os
from pathlib import Path
from PIL import Image, ImageDraw
import edge_tts
from src.processors.ffmpeg_engine import FFmpegEngine

async def create_sample_hinglish_video(output_path: str = "assets/sample_hinglish_tech.mp4") -> str:
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # 1. Synthesize natural spoken Hinglish speech
    hinglish_script = (
        "Basically agar aap ek AI agent bana rahe ho toh aapko state management ka dhyan rakhna padega. "
        "Production environment mein LangGraph aur FastAPI ka architecture bahut powerful hai. "
        "Last year jab humne scale kiya, tab direct LLM calls fail ho rahi thi. "
        "Aur tab hume realize hua ki vector database aur embeddings ke bina context preserve karna impossible hai. "
        "Toh sabse pehle proper schema design karo, phir Docker container banao, aur tab jaake deployment karo."
    )

    audio_temp = out_file.parent / "temp_sample_voice.mp3"
    communicate = edge_tts.Communicate(hinglish_script, voice="hi-IN-MadhurNeural")
    await communicate.save(str(audio_temp))

    # 2. Measure audio duration
    from src.readers.video_reader import VideoReader
    meta = VideoReader.get_metadata(str(audio_temp))
    duration = meta.get("duration_seconds", 25.0)

    # 3. Create a 16:9 1920x1080 frame with speaker visual
    frame_temp = out_file.parent / "temp_speaker_frame.png"
    img = Image.new("RGB", (1920, 1080), color=(15, 23, 42))
    draw = ImageDraw.Draw(img)

    # Draw gradient backdrop
    for y in range(1080):
        ratio = y / 1080.0
        r = int(15 * (1 - ratio) + 30 * ratio)
        g = int(23 * (1 - ratio) + 40 * ratio)
        b = int(42 * (1 - ratio) + 75 * ratio)
        draw.line([(0, y), (1920, y)], fill=(r, g, b))

    # Draw a stylized speaker face representation for face tracking
    head_x, head_y = 960, 480
    head_r = 130
    draw.ellipse([(head_x - head_r, head_y - head_r), (head_x + head_r, head_y + head_r)], fill=(225, 175, 140))
    # Eyes
    draw.ellipse([(head_x - 50, head_y - 30), (head_x - 30, head_y - 10)], fill=(30, 30, 30))
    draw.ellipse([(head_x + 30, head_y - 30), (head_x + 50, head_y - 10)], fill=(30, 30, 30))
    # Smile
    draw.arc([(head_x - 40, head_y + 10), (head_x + 40, head_y + 60)], start=0, end=180, fill=(40, 20, 20), width=6)
    # Shoulders
    draw.polygon([(head_x - 280, 1080), (head_x + 280, 1080), (head_x + 120, 640), (head_x - 120, 640)], fill=(56, 189, 248))

    # Text overlays
    draw.text((80, 80), "RAW HINGLISH TECH RECORDING // 16:9", fill=(0, 240, 255))
    draw.text((80, 120), "Topic: AI Agents, FastAPI & State Management", fill=(200, 210, 230))
    img.save(str(frame_temp))

    # 4. Render 16:9 MP4 with FFmpeg
    ffmpeg = FFmpegEngine.get_ffmpeg_binary()
    cmd = [
        ffmpeg, "-y",
        "-loop", "1",
        "-i", str(frame_temp),
        "-i", str(audio_temp),
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-t", str(duration),
        str(out_file)
    ]
    import subprocess
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    # Cleanup temp
    if audio_temp.exists():
        audio_temp.unlink()
    if frame_temp.exists():
        frame_temp.unlink()

    return str(out_file)

if __name__ == "__main__":
    asyncio.run(create_sample_hinglish_video())
    print("Sample Hinglish video created at assets/sample_hinglish_tech.mp4")
