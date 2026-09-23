import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from src.core.models import WordTiming

class CaptionEngine:
    """Generates Roman-Hinglish frame-accurate animated karaoke ASS and SRT subtitles."""

    @classmethod
    def generate_ass(
        cls,
        word_timings: List[WordTiming],
        output_path: str,
        aspect_ratio: str = "9:16",
        style_config: Optional[Dict[str, Any]] = None,
        chunk_size: int = 3
    ) -> str:
        """
        Creates an Advanced SubStation Alpha (.ass) subtitle file with word-by-word
        karaoke highlights and social-media safe-area margins.
        """
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        is_vertical = (aspect_ratio == "9:16")
        res_x = 1080 if is_vertical else 1920
        res_y = 1920 if is_vertical else 1080

        style = style_config or {}
        font_name = style.get("font_family", "Montserrat Black")
        font_size = style.get("font_size", 72 if is_vertical else 54)
        # MarginV: 480px on 9:16 places captions above TikTok/Reels captions but below face
        margin_v = style.get("margin_v", 480 if is_vertical else 90)
        outline = style.get("outline_width", 6)
        shadow = style.get("shadow_depth", 2)

        # Colors in ASS format: &HAABBGGRR
        primary_color = style.get("primary_color", "&H00FFFFFF")     # White
        highlight_color = style.get("highlight_color", "&H0000FFFF") # Neon Yellow / Cyan highlight
        outline_color = style.get("outline_color", "&H00000000")     # Deep Black Outline
        back_color = style.get("back_color", "&H80000000")           # Semi-transparent shadow

        header = f"""[Script Info]
Title: Roman-Hinglish Animated Karaoke Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: {res_x}
PlayResY: {res_y}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,{font_name},{font_size},{primary_color},{highlight_color},{outline_color},{back_color},-1,0,0,0,100,100,0,0,1,{outline},{shadow},2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        dialogue_lines: List[str] = []

        # Group words into 2-3 word chunks for high-retention readability
        for i in range(0, len(word_timings), chunk_size):
            chunk = word_timings[i:i + chunk_size]
            if not chunk:
                continue

            c_start = cls.format_ass_time(chunk[0].start)
            c_end = cls.format_ass_time(chunk[-1].end)

            karaoke_text_parts = []
            for item in chunk:
                # Duration in centiseconds (1/100s)
                duration_cs = max(1, int((item.end - item.start) * 100))
                word = cls._clean_hinglish_word(item.word)
                karaoke_text_parts.append(f"{{\\k{duration_cs}}}{word}")

            line = f"Dialogue: 0,{c_start},{c_end},Karaoke,,0,0,0,,{' '.join(karaoke_text_parts)}"
            dialogue_lines.append(line)

        with open(out_file, "w", encoding="utf-8") as f:
            f.write(header)
            f.write("\n".join(dialogue_lines) + "\n")

        return str(out_file)

    @classmethod
    def generate_srt(cls, word_timings: List[WordTiming], output_path: str, chunk_size: int = 3) -> str:
        """Creates a standard SubRip (.srt) subtitle file."""
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        lines: List[str] = []
        counter = 1

        for i in range(0, len(word_timings), chunk_size):
            chunk = word_timings[i:i + chunk_size]
            if not chunk:
                continue

            start_str = cls.format_srt_time(chunk[0].start)
            end_str = cls.format_srt_time(chunk[-1].end)
            text = " ".join(cls._clean_hinglish_word(item.word) for item in chunk)

            lines.append(f"{counter}")
            lines.append(f"{start_str} --> {end_str}")
            lines.append(f"{text}\n")
            counter += 1

        with open(out_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return str(out_file)

    @staticmethod
    def _clean_hinglish_word(word: str) -> str:
        """Cleans formatting while preserving acronyms and casing."""
        clean = word.replace("{", "").replace("}", "").strip()
        # Common tech acronyms to ensure uppercase
        acronyms = {"ai", "api", "rag", "mcp", "llm", "ui", "ux", "sql", "db", "sdk", "cli", "cpu", "gpu", "ram"}
        if clean.lower() in acronyms:
            return clean.upper()
        return clean

    @staticmethod
    def format_ass_time(seconds: float) -> str:
        """Converts float seconds to ASS format (H:MM:SS.CC)."""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hrs:01d}:{mins:02d}:{secs:05.2f}"

    @staticmethod
    def format_srt_time(seconds: float) -> str:
        """Converts float seconds to SRT format (HH:MM:SS,mmm)."""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int(round((seconds - int(seconds)) * 1000))
        if millis >= 1000:
            millis = 0
            secs += 1
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

