import asyncio
import os
from pathlib import Path
from typing import List, Tuple
from src.core.config import settings
from src.core.models import WordTiming

class VoiceGenerator:
    """Synthesizes high-fidelity neural voiceover audio and extracts word-level timestamps."""

    @classmethod
    def synthesize(cls, text: str, voice: str = None, output_audio: str = None) -> Tuple[str, List[WordTiming]]:
        """Synchronous wrapper for synthesizing speech."""
        return asyncio.run(cls.synthesize_async(text, voice, output_audio))

    @classmethod
    async def synthesize_async(cls, text: str, voice: str = None, output_audio: str = None) -> Tuple[str, List[WordTiming]]:
        """Synthesizes speech via edge-tts with precise word-level offsets."""
        voice = voice or settings.default_voice
        if not output_audio:
            output_dir = Path(settings.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            output_audio = str(output_dir / "voiceover.mp3")

        word_timings: List[WordTiming] = []

        try:
            import edge_tts

            communicate = edge_tts.Communicate(text, voice)
            submaker = edge_tts.SubMaker()

            with open(output_audio, "wb") as file:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        file.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        # offset and duration are in microseconds or 100ns units in edge-tts
                        # edge_tts chunk has: offset (int in 100ns units), duration (int), text (str)
                        offset_sec = chunk["offset"] / 10_000_000.0
                        duration_sec = chunk["duration"] / 10_000_000.0
                        word_timings.append(WordTiming(
                            word=chunk["text"].strip(),
                            start=round(offset_sec, 3),
                            end=round(offset_sec + duration_sec, 3),
                            confidence=1.0
                        ))

            if word_timings:
                return output_audio, word_timings

        except Exception as e:
            print(f"[VoiceGenerator] edge-tts error ({e}). Generating fallback audio timing.")

        # Fallback: Estimate word timings based on standard speaking rate (~150 WPM)
        words = text.split()
        current_time = 0.3
        for w in words:
            # Word duration proportional to length: ~0.25s to 0.6s
            word_dur = max(0.22, min(0.65, len(w) * 0.055))
            word_timings.append(WordTiming(
                word=w,
                start=round(current_time, 3),
                end=round(current_time + word_dur, 3),
                confidence=0.9
            ))
            current_time += word_dur + 0.05

        # If audio file wasn't created by edge_tts, generate a simple sine/silence tone via FFmpeg
        if not Path(output_audio).exists():
            cls._create_silent_audio(output_audio, duration=current_time + 1.0)

        return output_audio, word_timings

    @staticmethod
    def _create_silent_audio(output_path: str, duration: float) -> None:
        """Generates a blank audio stream of the given duration using FFmpeg."""
        import shutil
        import subprocess
        from src.processors.ffmpeg_engine import FFmpegEngine
        ffmpeg = FFmpegEngine.get_ffmpeg_binary()
        cmd = [
            ffmpeg, "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=stereo",
            "-t", str(duration),
            "-q:a", "9",
            "-acodec", "libmp3lame",
            output_path
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception:
            pass
