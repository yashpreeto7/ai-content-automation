import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional
from PIL import Image, ImageDraw, ImageFont
from src.core.config import settings
from src.core.models import Scene

class VideoGenerator:
    """Generates visual scene clips via AI models or cinematic procedural canvas rendering."""

    @classmethod
    def generate_scenes(
        cls,
        scenes: List[Scene],
        aspect_ratio: str = "9:16",
        output_dir: Optional[str] = None
    ) -> List[str]:
        """Generates video clip files for each scene in the script."""
        out_dir = Path(output_dir or (settings.output_dir / "scenes"))
        out_dir.mkdir(parents=True, exist_ok=True)

        clip_paths: List[str] = []

        for scene in scenes:
            clip_name = f"scene_{scene.scene_index:02d}.mp4"
            clip_path = out_dir / clip_name

            # Check if Gemini Omni Flash / Veo is available
            gemini_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
            generated = False

            if gemini_key:
                try:
                    generated = cls._generate_with_gemini_video(scene, str(clip_path), aspect_ratio)
                except Exception as e:
                    print(f"[VideoGenerator] AI video API generation skipped ({e}). Using procedural visualizer.")

            if not generated:
                # Render high-aesthetic visual scene with dynamic motion (Ken Burns zoom)
                cls._render_procedural_clip(scene, str(clip_path), aspect_ratio)

            clip_paths.append(str(clip_path))

        return clip_paths

    @classmethod
    def _generate_with_gemini_video(cls, scene: Scene, output_path: str, aspect_ratio: str) -> bool:
        """Invokes Gemini Omni Flash video generation if configured."""
        from google import genai
        from google.genai import types

        client = genai.Client()
        prompt = f"Cinematic {aspect_ratio} shot: {scene.visual_prompt}"
        
        # Interactions API call
        interaction = client.interactions.create(
            model="gemini-omni-flash-preview",
            input=[types.ContentPart(text=prompt)],
            parameters={
                "duration": int(scene.duration_seconds),
                "aspect_ratio": aspect_ratio
            }
        )
        # If media bytes are returned, write to output_path
        if hasattr(interaction, "media") and interaction.media:
            with open(output_path, "wb") as f:
                f.write(interaction.media.data)
            return True
        return False

    @classmethod
    def _render_procedural_clip(cls, scene: Scene, output_path: str, aspect_ratio: str = "9:16") -> str:
        """
        Creates a cinematic moving clip using PIL gradient graphics and FFmpeg zoompan filter.
        Ensures 100% reliable offline/local execution.
        """
        width = 1080 if aspect_ratio == "9:16" else 1920
        height = 1920 if aspect_ratio == "9:16" else 1080

        # Create base frame image
        frame_dir = Path(output_path).parent / "frames"
        frame_dir.mkdir(parents=True, exist_ok=True)
        img_path = frame_dir / f"still_{scene.scene_index:02d}.png"

        img = Image.new("RGB", (width, height), color=(10, 14, 23))
        draw = ImageDraw.Draw(img)

        # Draw aesthetic atmospheric gradient lines
        color_palettes = [
            [(16, 24, 48), (28, 56, 120), (56, 189, 248)],  # Deep cyan/blue
            [(30, 10, 40), (80, 20, 100), (236, 72, 153)],  # Neon magenta
            [(10, 30, 25), (20, 80, 60), (52, 211, 153)],   # Emerald glow
            [(35, 20, 10), (100, 60, 20), (251, 191, 36)],  # Amber gold
            [(20, 20, 25), (45, 45, 60), (167, 139, 250)],  # Cyber violet
        ]
        palette = color_palettes[(scene.scene_index - 1) % len(color_palettes)]

        # Background gradient blocks
        for y in range(height):
            ratio = y / height
            r = int(palette[0][0] * (1 - ratio) + palette[1][0] * ratio)
            g = int(palette[0][1] * (1 - ratio) + palette[1][1] * ratio)
            b = int(palette[0][2] * (1 - ratio) + palette[1][2] * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Geometric accent glow rings
        accent = palette[2]
        center_x, center_y = width // 2, height // 2
        for r_step in range(120, 420, 60):
            draw.ellipse(
                [(center_x - r_step, center_y - r_step), (center_x + r_step, center_y + r_step)],
                outline=accent,
                width=2
            )

        # Watermark/indicator
        draw.text((60, 120), f"SCENE {scene.scene_index:02d} // AI AUTOMATION", fill=(200, 210, 230))
        img.save(str(img_path))

        # Generate animated MP4 using FFmpeg zoompan filter (slow cinematic push-in)
        from src.processors.ffmpeg_engine import FFmpegEngine
        ffmpeg = FFmpegEngine.get_ffmpeg_binary()
        fps = 30
        total_frames = int(scene.duration_seconds * fps)

        cmd = [
            ffmpeg, "-y",
            "-loop", "1",
            "-i", str(img_path),
            "-filter_complex",
            f"zoompan=z='min(zoom+0.0008,1.25)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={width}x{height}:fps={fps}",
            "-t", str(scene.duration_seconds),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "ultrafast",
            output_path
        ]

        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception as e:
            print(f"[VideoGenerator] Error generating video clip for scene {scene.scene_index}: {e}")

        return output_path
