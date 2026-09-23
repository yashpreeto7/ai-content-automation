from pathlib import Path
from typing import List, Dict, Any, Optional
from src.core.models import WordTiming

class CaptionEngine:
    """Generates frame-accurate animated karaoke ASS and SRT subtitle files."""

    @classmethod
    def generate_ass(
        cls,
        word_timings: List[WordTiming],
        output_path: str,
        style_config: Optional[Dict[str, Any]] = None,
        chunk_size: int = 3
    ) -> str:
        """
        Creates an Advanced SubStation Alpha (.ass) subtitle file with word-by-word karaoke highlight tags.
        """
        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        # Style parameters
        style = style_config or {}
        font_name = style.get("font_family", "Montserrat Black")
        font_size = style.get("font_size", 72)
        margin_v = style.get("margin_v", 480)
        outline = style.get("outline_width", 6)
        shadow = style.get("shadow_depth", 2)

        # Color in ASS is &HAABBGGRR
        primary_color = "&H00FFFFFF"   # White
        highlight_color = "&H0000FFFF" # Yellow/Cyan highlight
        outline_color = "&H00000000"   # Black
        back_color = "&H80000000"      # Semi-transparent shadow

        header = f"""[Script Info]
Title: Auto Animated Karaoke Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,{font_name},{font_size},{primary_color},{highlight_color},{outline_color},{back_color},-1,0,0,0,100,100,0,0,1,{outline},{shadow},2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        dialogue_lines: List[str] = []

        # Split words into chunks (e.g. 2-3 words per display screen)
        for i in range(0, len(word_timings), chunk_size):
            chunk = word_timings[i:i + chunk_size]
            if not chunk:
                continue

            c_start = cls.format_ass_time(chunk[0].start)
            c_end = cls.format_ass_time(chunk[-1].end)

            # Build karaoke tags: \k<duration_in_centiseconds>
            karaoke_text = ""
            for item in chunk:
                duration_cs = max(1, int((item.end - item.start) * 100))
                # Clean punctuation for karaoke tag
                clean_word = item.word.replace("{", "").replace("}", "").upper()
                karaoke_text += f"{{\\k{duration_cs}}}{clean_word} "

            line = f"Dialogue: 0,{c_start},{c_end},Karaoke,,0,0,0,,{karaoke_text.strip()}"
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
            text = " ".join(item.word for item in chunk).upper()

            lines.append(f"{counter}")
            lines.append(f"{start_str} --> {end_str}")
            lines.append(f"{text}\n")
            counter += 1

        with open(out_file, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return str(out_file)

    @staticmethod
    def format_ass_time(seconds: float) -> str:
        """Converts seconds float to ASS timestamp format (H:MM:SS.CC)."""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hrs:01d}:{mins:02d}:{secs:05.2f}"

    @staticmethod
    def format_srt_time(seconds: float) -> str:
        """Converts seconds float to SRT timestamp format (HH:MM:SS,mmm)."""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"
