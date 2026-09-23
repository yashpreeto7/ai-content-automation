import json
import os
import sys
from pathlib import Path
from typing import Optional

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

# Force UTF-8 on Windows console to prevent charmap encoding errors
if sys.platform == "win32":
    import io
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from src.core.config import settings
from src.core.models import ContentRequest
from src.pipeline.engine import ContentPipeline
from src.generators.script_generator import ScriptGenerator
from src.generators.voice_generator import VoiceGenerator
from src.readers.video_reader import VideoReader

app = typer.Typer(
    name="content-engine",
    help="Autonomous AI-Powered Content Creation & Media Automation Engine",
    add_completion=False
)
console = Console()

@app.command()
def auto_short(
    topic: str = typer.Option(..., "--topic", "-t", help="Topic or headline for the short-form video"),
    style: str = typer.Option("cinematic", "--style", "-s", help="Visual style preset (cinematic, cyberpunk, minimalist, documentary)"),
    duration: float = typer.Option(45.0, "--duration", "-d", help="Target duration in seconds"),
    aspect_ratio: str = typer.Option("9:16", "--aspect-ratio", "-a", help="Aspect ratio (9:16 or 16:9)"),
    voice: Optional[str] = typer.Option(None, "--voice", "-v", help="Edge-TTS voice (e.g. en-US-ChristopherNeural)"),
    music: Optional[str] = typer.Option(None, "--music", "-m", help="Path to background music audio file"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output MP4 file path")
):
    """
    Generate an end-to-end viral video from a single topic (Script -> Voice -> Visuals -> Captions -> Render).
    """
    console.print(Panel(f"[bold cyan]AI CONTENT AUTOMATION ENGINE[/bold cyan]\n[white]Topic:[/white] {topic}\n[white]Style:[/white] {style} | [white]Aspect:[/white] {aspect_ratio}", expand=False))

    request = ContentRequest(
        topic=topic,
        style=style,
        target_duration=duration,
        aspect_ratio=aspect_ratio,
        voice=voice,
        music_track=music,
        output_path=output
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Processing pipeline...", total=100)

        def on_progress(stage: str, pct: float):
            stage_names = {
                "generating_script": "[yellow]Crafting viral hook & script...",
                "synthesizing_voice": "[blue]Synthesizing neural voiceover...",
                "generating_subtitles": "[magenta]Building animated karaoke captions...",
                "generating_visuals": "[cyan]Generating cinematic scene clips...",
                "assembling_video": "[green]FFmpeg assembly & audio ducking...",
                "packaging_metadata": "[white]Generating SEO tags & thumbnail prompt...",
                "completed": "[bold green]Render complete!"
            }
            desc = stage_names.get(stage, f"[cyan]{stage}...")
            progress.update(task, completed=pct, description=desc)

        job = ContentPipeline.run(request, progress_callback=on_progress)

    console.print("\n[bold green][SUCCESS] VIDEO GENERATION COMPLETE![/bold green]")
    console.print(f"[bold white]Output Video:[/bold white] [underline cyan]{job.output_file}[/underline cyan]")

    if job.social_package:
        table = Table(title="Viral Publication Package", border_style="cyan")
        table.add_column("Property", style="bold yellow", width=18)
        table.add_column("Details", style="white")

        table.add_row("Hook Title 1", job.social_package.title_options[0] if job.social_package.title_options else "")
        table.add_row("Hook Title 2", job.social_package.title_options[1] if len(job.social_package.title_options) > 1 else "")
        table.add_row("Hashtags", " ".join(job.social_package.hashtags[:8]))
        table.add_row("Thumbnail Prompt", job.social_package.thumbnail_prompt[:120] + "...")

        console.print(table)

@app.command()
def create_script(
    topic: str = typer.Option(..., "--topic", "-t", help="Topic for the script"),
    style: str = typer.Option("cinematic", "--style", "-s", help="Visual style preset"),
    duration: float = typer.Option(45.0, "--duration", "-d", help="Target duration in seconds")
):
    """
    Generate a hook-driven viral script with scene visual prompts.
    """
    console.print(f"[cyan]Generating script for topic: '{topic}'...[/cyan]")
    script = ScriptGenerator.generate(topic, style=style, target_duration=duration)

    console.print(Panel(f"[bold yellow]HOOK:[/bold yellow] {script.hook}\n\n[bold green]CTA:[/bold green] {script.cta}", title=f"Viral Script: {topic}", expand=False))
    console.print(f"\n[bold white]Full Narration:[/bold white]\n{script.full_text}\n")

    table = Table(title="Scene Visual Breakdown", border_style="dim")
    table.add_column("#", width=4)
    table.add_column("Spoken Text", width=36)
    table.add_column("Visual Prompt", width=50)

    for s in script.scenes:
        table.add_row(str(s.scene_index), s.text_segment, s.visual_prompt)

    console.print(table)

@app.command()
def generate_voice(
    text: str = typer.Option(..., "--text", "-t", help="Script narration text"),
    voice: str = typer.Option("en-US-ChristopherNeural", "--voice", "-v", help="Voice model ID"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output audio file path")
):
    """
    Synthesize neural voiceover audio and print word-level timestamp offsets.
    """
    console.print(f"[cyan]Synthesizing speech via {voice}...[/cyan]")
    audio_path, word_timings = VoiceGenerator.synthesize(text, voice=voice, output_audio=output)
    console.print(f"[green][SUCCESS] Audio saved to: {audio_path}[/green]")
    console.print(f"Total words timed: [bold cyan]{len(word_timings)}[/bold cyan]")
    if word_timings:
        console.print(f"First 5 words: {[w.word for w in word_timings[:5]]}")

@app.command()
def analyze_video(
    video_path: str = typer.Argument(..., help="Path to video file to analyze")
):
    """
    Inspect an existing video file's codecs, resolution, aspect ratio, and pacing.
    """
    console.print(f"[cyan]Analyzing video: {video_path}...[/cyan]")
    meta = VideoReader.get_metadata(video_path)

    table = Table(title=f"Video Analysis: {meta.get('file_name', video_path)}", border_style="cyan")
    table.add_column("Parameter", style="bold yellow")
    table.add_column("Value", style="white")

    for k, v in meta.items():
        table.add_row(str(k), str(v))

    console.print(table)

@app.command()
def list_styles():
    """
    Display all available visual styling presets from templates/styles.json.
    """
    styles_file = settings.templates_dir / "styles.json"
    if not styles_file.exists():
        console.print("[red]styles.json not found.[/red]")
        return

    with open(styles_file, "r", encoding="utf-8") as f:
        styles = json.load(f)

    table = Table(title="Available Visual Themes & Styles", border_style="magenta")
    table.add_column("Key", style="bold cyan")
    table.add_column("Name", style="bold yellow")
    table.add_column("Pacing (WPM)", style="green")
    table.add_column("Description", style="white")

    for key, data in styles.items():
        table.add_row(key, data.get("name", ""), str(data.get("pacing_wpm", "")), data.get("description", ""))

    console.print(table)

if __name__ == "__main__":
    app()
