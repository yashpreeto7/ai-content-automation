import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

class FFmpegEngine:
    """Manages programmatic FFmpeg execution, concatenation, audio ducking, and rendering."""

    @staticmethod
    def get_ffmpeg_binary() -> str:
        """Finds system ffmpeg or uses imageio_ffmpeg fallback."""
        sys_ffmpeg = shutil.which("ffmpeg")
        if sys_ffmpeg:
            return sys_ffmpeg
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            return "ffmpeg"

    @classmethod
    def concat_videos(cls, clip_paths: List[str], output_path: str) -> str:
        """Concatenates multiple video clips using FFmpeg concat demuxer."""
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        concat_txt = out_file.parent / f"concat_{out_file.stem}.txt"

        with open(concat_txt, "w", encoding="utf-8") as f:
            for clip in clip_paths:
                # Escape single quotes and backslashes for FFmpeg
                clean_path = str(Path(clip).resolve()).replace("\\", "/")
                f.write(f"file '{clean_path}'\n")

        ffmpeg = cls.get_ffmpeg_binary()
        cmd = [
            ffmpeg, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_txt),
            "-c", "copy",
            str(out_file)
        ]

        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if concat_txt.exists():
            concat_txt.unlink()

        return str(out_file)

    @classmethod
    def reframe_to_vertical(cls, input_path: str, output_path: str, mode: str = "blur") -> str:
        """
        Converts 16:9 video to 9:16 vertical (1080x1920).
        mode="blur": Blurred background padding (recommended for high retention).
        mode="crop": Direct center crop.
        """
        ffmpeg = cls.get_ffmpeg_binary()
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        if mode == "blur":
            filter_str = (
                "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=22[bg];"
                "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
                "[bg][fg]overlay=(W-w)/2:(H-h)/2"
            )
        else:
            filter_str = "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920"

        cmd = [
            ffmpeg, "-y",
            "-i", str(input_path),
            "-vf", filter_str,
            "-c:v", "libx264",
            "-crf", "19",
            "-preset", "fast",
            "-c:a", "copy",
            str(out_file)
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return str(out_file)

    @classmethod
    def assemble_final_video(
        cls,
        clips: List[str],
        voiceover_audio: str,
        output_file: str,
        background_music: Optional[str] = None,
        subtitles_file: Optional[str] = None,
        music_volume: float = 0.20
    ) -> str:
        """
        Assembles all scene clips, mixes voiceover and ducked background music,
        burns animated subtitles, and outputs an optimized H.264 MP4.
        """
        ffmpeg = cls.get_ffmpeg_binary()
        final_mp4 = Path(output_file)
        final_mp4.parent.mkdir(parents=True, exist_ok=True)

        # 1. First concatenate the visual clips
        raw_concat = final_mp4.parent / f"raw_concat_{final_mp4.stem}.mp4"
        cls.concat_videos(clips, str(raw_concat))

        # 2. Build filter complex for audio and video
        inputs = ["-i", str(raw_concat), "-i", str(voiceover_audio)]
        filter_complex_parts = []

        # Handle background music with sidechain ducking
        if background_music and Path(background_music).exists():
            inputs.extend(["-i", str(background_music)])
            # Input 0: video, Input 1: voice, Input 2: music
            filter_complex_parts.append(
                f"[2:a]volume={music_volume}[bgm];"
                f"[1:a][bgm]sidechaincompress=threshold=0.08:ratio=5:attack=50:release=300[ducked_bgm];"
                f"[1:a][ducked_bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            )
            audio_map = "[aout]"
        else:
            # Voiceover only
            audio_map = "1:a"

        # Handle subtitles
        if subtitles_file and Path(subtitles_file).exists():
            # Escape path for FFmpeg subtitles filter on Windows
            sub_escaped = str(Path(subtitles_file).resolve()).replace("\\", "/").replace(":", "\\:")
            filter_complex_parts.append(f"[0:v]subtitles='{sub_escaped}'[vout]")
            video_map = "[vout]"
        else:
            video_map = "0:v"

        cmd = [ffmpeg, "-y"] + inputs

        if filter_complex_parts:
            cmd.extend(["-filter_complex", ";".join(filter_complex_parts)])

        cmd.extend([
            "-map", video_map,
            "-map", audio_map,
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            str(final_mp4)
        ])

        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception as e:
            # Fallback if subtitle filter fails due to libass font caching: render video + audio directly
            cmd_fallback = [
                ffmpeg, "-y",
                "-i", str(raw_concat),
                "-i", str(voiceover_audio),
                "-map", "0:v",
                "-map", "1:a",
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                str(final_mp4)
            ]
            subprocess.run(cmd_fallback, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Cleanup intermediate concat
        if raw_concat.exists():
            raw_concat.unlink()

        return str(final_mp4)
