import pytest
from pathlib import Path
from src.core.models import WordTiming
from src.processors.caption_engine import CaptionEngine
from src.processors.face_tracker import FaceTracker
from src.processors.ffmpeg_engine import FFmpegEngine

def test_caption_engine_ass_generation(tmp_path):
    words = [
        WordTiming(word="Basically", start=0.0, end=0.5),
        WordTiming(word="agar", start=0.6, end=0.9),
        WordTiming(word="aap", start=1.0, end=1.2),
        WordTiming(word="ek", start=1.3, end=1.5),
        WordTiming(word="AI", start=1.6, end=1.9),
        WordTiming(word="agent", start=2.0, end=2.4),
        WordTiming(word="bana", start=2.5, end=2.8),
        WordTiming(word="rahe", start=2.9, end=3.1),
        WordTiming(word="ho", start=3.2, end=3.5)
    ]
    ass_path = tmp_path / "test_captions.ass"
    result = CaptionEngine.generate_ass(words, str(ass_path), aspect_ratio="9:16")

    assert Path(result).exists()
    content = Path(result).read_text(encoding="utf-8")
    assert "PlayResX: 1080" in content
    assert "PlayResY: 1920" in content
    assert "Style: Karaoke" in content
    assert r"{\k" in content  # Contains karaoke timing tags
    assert "AI" in content    # Acronym uppercase preserved

def test_caption_engine_srt_generation(tmp_path):
    words = [
        WordTiming(word="API", start=0.0, end=0.5),
        WordTiming(word="backend", start=0.6, end=1.2)
    ]
    srt_path = tmp_path / "test_captions.srt"
    result = CaptionEngine.generate_srt(words, str(srt_path))

    assert Path(result).exists()
    content = Path(result).read_text(encoding="utf-8")
    assert "00:00:00,000 --> 00:00:01,200" in content
    assert "API backend" in content

def test_face_tracker_fallback_dimensions():
    # Test safe fallback crop calculation for 16:9 input (1920x1080)
    crop = FaceTracker._fallback_center_crop(1920, 1080)
    assert crop["crop_h"] == 1080
    assert crop["crop_w"] == 607  # 1080 * 9 / 16
    assert crop["crop_x"] == (1920 - 607) // 2
    assert "crop=607:1080:" in crop["filter_str"]

def test_ffmpeg_binary_resolution():
    binary = FFmpegEngine.get_ffmpeg_binary()
    assert binary is not None
    assert "ffmpeg" in binary.lower()
