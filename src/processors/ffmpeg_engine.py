import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from src.core.models import CutSegment
from src.processors.face_tracker import FaceTracker

class FFmpegEngine:
    """Manages deterministic FFmpeg cutting, concatenation, 9:16 smart cropping, audio ducking, and rendering."""

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
    def cut_segment(
        cls,
        input_path: str,
        start_time: float,
        end_time: float,
        output_path: str,
        reencode: bool = True
    ) -> str:
        """Cuts a video interval [start_time, end_time] with frame accuracy."""
        duration = max(0.1, end_time - start_time)
        ffmpeg = cls.get_ffmpeg_binary()
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        cmd = [ffmpeg, "-y", "-ss", f"{start_time:.3f}", "-i", str(input_path), "-t", f"{duration:.3f}"]

        if reencode:
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "18",
                "-c:a", "aac",
                "-b:a", "192k",
                "-avoid_negative_ts", "make_zero",
                str(out_file)
            ])
        else:
            cmd.extend([
                "-c", "copy",
                "-avoid_negative_ts", "make_zero",
                str(out_file)
            ])

        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return str(out_file)

    @classmethod
    def concat_videos(cls, clip_paths: List[str], output_path: str) -> str:
        """Concatenates multiple video clips using FFmpeg concat demuxer."""
        if not clip_paths:
            raise ValueError("No clips provided for concatenation")
        if len(clip_paths) == 1:
            shutil.copy(clip_paths[0], output_path)
            return output_path

        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        concat_txt = out_file.parent / f"concat_{uuid.uuid4().hex[:8]}.txt"

        with open(concat_txt, "w", encoding="utf-8") as f:
            for clip in clip_paths:
                clean_path = str(Path(clip).resolve()).replace("\\", "/")
                f.write(f"file '{clean_path}'\n")

        ffmpeg = cls.get_ffmpeg_binary()
        cmd = [
            ffmpeg, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_txt),
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "fast",
            "-c:a", "aac",
            "-b:a", "192k",
            str(out_file)
        ]

        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        finally:
            if concat_txt.exists():
                concat_txt.unlink()

        return str(out_file)

    @classmethod
    def render_long_form(
        cls,
        source_video: str,
        segments: List[CutSegment],
        output_path: str,
        normalize_audio: bool = True
    ) -> str:
        """
        Extracts each curated segment from the raw source video, concatenates them into
        a coherent long-form 16:9 video, and normalizes audio loudness to -14 LUFS.
        """
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        temp_dir = out_file.parent / f"temp_long_{uuid.uuid4().hex[:6]}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        temp_clips: List[str] = []
        try:
            for idx, seg in enumerate(segments):
                seg_clip = temp_dir / f"segment_{idx:03d}.mp4"
                cls.cut_segment(source_video, seg.start, seg.end, str(seg_clip))
                if seg_clip.exists():
                    temp_clips.append(str(seg_clip))

            raw_concatenated = temp_dir / "raw_concat.mp4"
            cls.concat_videos(temp_clips, str(raw_concatenated))

            # Apply loudness normalization if requested
            if normalize_audio:
                ffmpeg = cls.get_ffmpeg_binary()
                cmd = [
                    ffmpeg, "-y",
                    "-i", str(raw_concatenated),
                    "-af", "loudnorm=I=-14:LRA=11:TP=-1.5",
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-movflags", "+faststart",
                    str(out_file)
                ]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            else:
                shutil.copy(str(raw_concatenated), str(out_file))

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        return str(out_file)

    @classmethod
    def render_short(
        cls,
        source_video: str,
        body_start: float,
        body_end: float,
        output_path: str,
        hook_start: Optional[float] = None,
        hook_end: Optional[float] = None,
        subtitles_file: Optional[str] = None,
        background_music: Optional[str] = None,
        music_volume: float = 0.15,
        use_smart_face_crop: bool = True
    ) -> str:
        """
        Renders a polished 9:16 vertical Short/Reel:
        1. Cuts hook & body (supporting hook inversion if hook timestamps differ).
        2. Applies smart face-tracked 9:16 crop.
        3. Burns Roman-Hinglish animated subtitles.
        4. Applies -12dB sidechain audio ducking for background music.
        """
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        temp_dir = out_file.parent / f"temp_short_{uuid.uuid4().hex[:6]}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        ffmpeg = cls.get_ffmpeg_binary()

        try:
            # 1. Prepare raw video clip(s)
            clips_to_join: List[str] = []
            has_separate_hook = (
                hook_start is not None and hook_end is not None and
                hook_end > hook_start and
                not (abs(hook_start - body_start) < 0.5 and abs(hook_end - min(body_end, body_start + 4.0)) < 0.5)
            )

            if has_separate_hook:
                hook_clip = temp_dir / "hook.mp4"
                cls.cut_segment(source_video, hook_start, hook_end, str(hook_clip))
                clips_to_join.append(str(hook_clip))

            body_clip = temp_dir / "body.mp4"
            cls.cut_segment(source_video, body_start, body_end, str(body_clip))
            clips_to_join.append(str(body_clip))

            assembled_source = temp_dir / "assembled.mp4"
            cls.concat_videos(clips_to_join, str(assembled_source))

            # 2. Compute 9:16 Framing Filter
            vf_filters: List[str] = []
            if use_smart_face_crop:
                crop_info = FaceTracker.get_smart_vertical_crop(str(assembled_source))
                vf_filters.append(crop_info["filter_str"])
            else:
                # Blurred background fallback
                vf_filters.append(
                    "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,gblur=sigma=22[bg];"
                    "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
                    "[bg][fg]overlay=(W-w)/2:(H-h)/2"
                )

            # 3. Add Subtitles Filter
            if subtitles_file and Path(subtitles_file).exists():
                sub_escaped = str(Path(subtitles_file).resolve()).replace("\\", "/").replace(":", "\\:")
                vf_filters.append(f"subtitles='{sub_escaped}'")

            video_filter_chain = ",".join(vf_filters)

            # 4. Handle Audio Mixing & Ducking
            inputs = ["-i", str(assembled_source)]
            filter_complex_parts = []
            video_map = "[v_out]"
            audio_map = "[a_out]"

            filter_complex_parts.append(f"[0:v]{video_filter_chain}[v_out]")

            if background_music and Path(background_music).exists():
                inputs.extend(["-i", str(background_music)])
                filter_complex_parts.append(
                    f"[1:a]volume={music_volume}[bgm];"
                    f"[0:a][bgm]sidechaincompress=threshold=0.08:ratio=5:attack=50:release=300[ducked_bgm];"
                    f"[0:a][ducked_bgm]amix=inputs=2:duration=first:dropout_transition=2[a_out]"
                )
            else:
                filter_complex_parts.append("[0:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[a_out]")

            cmd = [ffmpeg, "-y"] + inputs
            cmd.extend([
                "-filter_complex", ";".join(filter_complex_parts),
                "-map", video_map,
                "-map", audio_map,
                "-c:v", "libx264",
                "-crf", "18",
                "-preset", "fast",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                str(out_file)
            ])

            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        return str(out_file)
