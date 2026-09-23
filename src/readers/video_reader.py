import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from src.core.models import WordTiming

class VideoReader:
    """Inspects, analyzes, and extracts metadata/transcripts from video assets."""

    @staticmethod
    def get_ffprobe_path() -> str:
        """Locates ffprobe binary on PATH or via imageio_ffmpeg."""
        system_ffprobe = shutil.which("ffprobe")
        if system_ffprobe:
            return system_ffprobe
        # Try imageio_ffmpeg
        try:
            import imageio_ffmpeg
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            ffprobe_candidate = Path(ffmpeg_exe).parent / "ffprobe.exe"
            if ffprobe_candidate.exists():
                return str(ffprobe_candidate)
        except Exception:
            pass
        return "ffprobe"

    @classmethod
    def get_metadata(cls, video_path: str) -> Dict[str, Any]:
        """Extracts container and stream metadata via ffprobe."""
        path_obj = Path(video_path)
        if not path_obj.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        ffprobe = cls.get_ffprobe_path()
        cmd = [
            ffprobe,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(path_obj)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            raw = json.loads(result.stdout)
            video_stream = next((s for s in raw.get("streams", []) if s.get("codec_type") == "video"), None)
            audio_stream = next((s for s in raw.get("streams", []) if s.get("codec_type") == "audio"), None)
            format_info = raw.get("format", {})

            width = int(video_stream.get("width", 0)) if video_stream else 0
            height = int(video_stream.get("height", 0)) if video_stream else 0
            aspect_ratio = "9:16" if height > width else ("16:9" if width > height else "1:1")

            fps = 0.0
            if video_stream and "r_frame_rate" in video_stream:
                try:
                    num, den = video_stream["r_frame_rate"].split("/")
                    fps = round(float(num) / float(den), 2)
                except Exception:
                    fps = 30.0

            duration = float(format_info.get("duration", 0.0))

            return {
                "file_name": path_obj.name,
                "duration_seconds": round(duration, 2),
                "width": width,
                "height": height,
                "aspect_ratio": aspect_ratio,
                "fps": fps,
                "video_codec": video_stream.get("codec_name") if video_stream else None,
                "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
                "audio_sample_rate": audio_stream.get("sample_rate") if audio_stream else None,
                "bitrate_kbps": round(float(format_info.get("bit_rate", 0)) / 1000, 1),
                "is_vertical": height > width,
            }
        except Exception:
            # Fallback: Parse via ffmpeg -i
            return cls._parse_via_ffmpeg(path_obj)

    @classmethod
    def _parse_via_ffmpeg(cls, path_obj: Path) -> Dict[str, Any]:
        """Parses video metadata directly from ffmpeg -i output."""
        import re
        from src.processors.ffmpeg_engine import FFmpegEngine
        ffmpeg = FFmpegEngine.get_ffmpeg_binary()
        cmd = [ffmpeg, "-i", str(path_obj)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        text = res.stderr

        # Duration
        dur_match = re.search(r"Duration:\s*(\d+):(\d+):([\d\.]+)", text)
        duration = 0.0
        if dur_match:
            h, m, s = dur_match.groups()
            duration = int(h) * 3600 + int(m) * 60 + float(s)

        # Bitrate
        bitrate = 0.0
        br_match = re.search(r"bitrate:\s*(\d+)\s*kb/s", text)
        if br_match:
            bitrate = float(br_match.group(1))

        # Video stream: resolution & fps & codec
        width, height, fps, vcodec = 0, 0, 30.0, None
        v_match = re.search(r"Stream #\d+:\d+.*?: Video:\s*([a-zA-Z0-9_-]+).*?,\s*(\d+)x(\d+).*?,\s*([\d\.]+)\s*fps", text)
        if v_match:
            vcodec = v_match.group(1)
            width = int(v_match.group(2))
            height = int(v_match.group(3))
            fps = float(v_match.group(4))
        else:
            # Try looser match for resolution
            res_match = re.search(r"(\d{3,4})x(\d{3,4})", text)
            if res_match:
                width, height = int(res_match.group(1)), int(res_match.group(2))

        # Audio stream codec & sample rate
        acodec, sample_rate = None, None
        a_match = re.search(r"Stream #\d+:\d+.*?: Audio:\s*([a-zA-Z0-9_-]+).*?,\s*(\d+)\s*Hz", text)
        if a_match:
            acodec = a_match.group(1)
            sample_rate = a_match.group(2)

        aspect_ratio = "9:16" if height > width else ("16:9" if width > height else "1:1")

        return {
            "file_name": path_obj.name,
            "duration_seconds": round(duration, 2),
            "width": width,
            "height": height,
            "aspect_ratio": aspect_ratio,
            "fps": fps,
            "video_codec": vcodec,
            "audio_codec": acodec,
            "audio_sample_rate": sample_rate,
            "bitrate_kbps": bitrate,
            "is_vertical": height > width,
        }

    @classmethod
    def extract_keyframes(cls, video_path: str, output_dir: str, num_frames: int = 5) -> List[str]:
        """Extracts evenly spaced keyframe stills from the video."""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        
        meta = cls.get_metadata(video_path)
        duration = meta.get("duration_seconds", 10.0)
        interval = max(0.5, duration / (num_frames + 1))

        ffmpeg_cmd = shutil.which("ffmpeg") or "ffmpeg"
        frame_paths = []

        for i in range(1, num_frames + 1):
            timestamp = i * interval
            frame_file = out_path / f"frame_{i:02d}.jpg"
            cmd = [
                ffmpeg_cmd, "-y",
                "-ss", str(timestamp),
                "-i", video_path,
                "-vframes", "1",
                "-q:v", "2",
                str(frame_file)
            ]
            try:
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                if frame_file.exists():
                    frame_paths.append(str(frame_file))
            except Exception:
                pass

        return frame_paths

    @classmethod
    def transcribe(cls, audio_or_video_path: str, model_size: str = "base") -> List[WordTiming]:
        """Transcribes audio using faster-whisper if available, with word timestamps."""
        try:
            from faster_whisper import WhisperModel
            model = WhisperModel(model_size, device="cpu", compute_type="int8")
            segments, _ = model.transcribe(audio_or_video_path, word_timestamps=True)
            
            words: List[WordTiming] = []
            for segment in segments:
                for w in segment.words:
                    words.append(WordTiming(
                        word=w.word.strip(),
                        start=round(w.start, 3),
                        end=round(w.end, 3),
                        confidence=round(w.probability, 3)
                    ))
            return words
        except ImportError:
            # Fallback if faster-whisper is not yet installed
            return [
                WordTiming(word="[Transcription", start=0.0, end=1.0, confidence=1.0),
                WordTiming(word="requires", start=1.0, end=1.5, confidence=1.0),
                WordTiming(word="faster-whisper]", start=1.5, end=2.5, confidence=1.0),
            ]
