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

@app.command()
def server(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host address"),
    port: int = typer.Option(8765, "--port", "-p", help="Port number"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development")
):
    """
    Launch the local desktop processing backend server.
    """
    import uvicorn
    console.print(f"[bold cyan]Starting AI Content Automation Server on http://{host}:{port}...[/bold cyan]")
    uvicorn.run("src.server.app:app", host=host, port=port, reload=reload)

@app.command()
def list_projects():
    """
    List all local video production projects from SQLite database.
    """
    from src.core.database import db
    projects = db.list_projects()
    if not projects:
        console.print("[yellow]No projects found in database.[/yellow]")
        return

    table = Table(title="Local Production Projects", border_style="cyan")
    table.add_column("Project ID", style="bold cyan")
    table.add_column("Name", style="bold white")
    table.add_column("Provider", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Duration", style="white")

    for p in projects:
        dur = f"{round(p.duration_seconds / 60, 1)}m" if p.duration_seconds else "—"
        table.add_row(p.id, p.name, p.ai_provider.upper(), p.status, dur)

    console.print(table)

@app.command()
def process_video(
    video_path: str = typer.Argument(..., help="Path to raw Hindi/Hinglish recording"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Project name"),
    provider: str = typer.Option("gemini", "--provider", "-p", help="AI provider ('gemini' or 'ollama')"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="AI model identifier")
):
    """
    Run the complete autonomous end-to-end production pipeline on a raw video:
    Inspect -> Transcribe -> AI Curate (10-15m + 4-5 Shorts) -> Render 16:9 & 9:16 -> Metadata.
    """
    import asyncio
    import uuid
    import time
    from src.core.database import db
    from src.providers.factory import get_ai_provider
    from src.processors.caption_engine import CaptionEngine
    from src.processors.ffmpeg_engine import FFmpegEngine
    from src.core.models import WordTiming

    path_obj = Path(video_path).resolve()
    if not path_obj.exists():
        console.print(f"[bold red]Error: Video file not found at {path_obj}[/bold red]")
        raise typer.Exit(code=1)

    proj_name = name or path_obj.stem.replace("_", " ").title()
    proj_id = f"proj_{int(time.time())}_{uuid.uuid4().hex[:6]}"

    console.print(Panel(
        f"[bold cyan]AUTONOMOUS HINGLISH VIDEO PRODUCTION ENGINE[/bold cyan]\n"
        f"[white]Project:[/white] {proj_name}\n"
        f"[white]Source Video:[/white] {path_obj}\n"
        f"[white]AI Provider:[/white] {provider.upper()} ({model or 'default'})",
        expand=False
    ))

    # 1. Inspection
    meta = VideoReader.get_metadata(str(path_obj))
    project = db.create_project(
        project_id=proj_id,
        name=proj_name,
        source_video_path=str(path_obj),
        ai_provider=provider,
        ai_model=model or ("gemini-2.0-flash" if provider == "gemini" else "llama3.2"),
        duration_seconds=meta.get("duration_seconds", 0.0),
        video_width=meta.get("width", 1920),
        video_height=meta.get("height", 1080)
    )

    proj_dir = settings.projects_dir / proj_id

    # 2. Transcription
    console.print("\n[bold yellow]Step 1/5: Transcribing spoken Hinglish via faster-whisper...[/bold yellow]")
    audio_file = proj_dir / "audio" / "extracted.wav"
    VideoReader.extract_audio(str(path_obj), str(audio_file))
    transcript = VideoReader.transcribe(str(audio_file), language="hi")
    db.save_transcript(proj_id, transcript)
    console.print(f"[green]✓ Transcribed {len(transcript.segments)} segments ({len(transcript.full_text.split())} words)[/green]")

    # 3. AI Analysis & Edit Plan
    console.print(f"\n[bold yellow]Step 2/5: Analyzing conversation & curating edit decisions via {provider.upper()}...[/bold yellow]")
    ai_eng = get_ai_provider(provider, model)
    keyframes = VideoReader.extract_keyframes(str(path_obj), str(proj_dir / "previews" / "keyframes"), num_frames=6)
    
    async def run_ai():
        analysis = await ai_eng.analyze_content(str(path_obj), transcript, keyframes)
        db.save_content_analysis(proj_id, analysis)

        long_form = await ai_eng.select_long_form(analysis, transcript, target_duration_seconds=720.0)
        shorts = await ai_eng.select_shorts(analysis, transcript, count=5)
        silence = VideoReader.detect_silence(str(path_obj), min_duration_seconds=0.8)
        edit_plan = await ai_eng.generate_edit_plan(proj_id, long_form, shorts, transcript, silence)
        db.save_edit_plan(proj_id, edit_plan, status="ready_for_review")

        metadata = await ai_eng.generate_metadata(proj_name, transcript, long_form, shorts)
        db.save_metadata(proj_id, metadata)
        return analysis, long_form, shorts, edit_plan, metadata

    analysis, long_form, shorts, edit_plan, metadata = asyncio.run(run_ai())
    console.print(f"[green]✓ Narrative Arc: {long_form.narrative_arc}[/green]")
    console.print(f"[green]✓ Selected {len(long_form.segments)} long-form cuts (~{round(long_form.estimated_duration / 60, 1)} mins)[/green]")
    console.print(f"[green]✓ Discovered {len(shorts)} standalone Shorts/Reels candidates[/green]")

    # 4. Deterministic Long-Form Render
    console.print("\n[bold yellow]Step 3/5: Rendering 16:9 Long-Form Video with audio normalization...[/bold yellow]")
    long_mp4 = proj_dir / "renders" / f"{proj_id}_long_form.mp4"
    FFmpegEngine.render_long_form(
        source_video=str(path_obj),
        segments=long_form.segments,
        output_path=str(long_mp4),
        normalize_audio=True
    )
    console.print(f"[bold green]✓ Long-Form Render Complete:[/bold green] {long_mp4}")

    # 5. Render 4–5 Shorts
    console.print("\n[bold yellow]Step 4/5: Rendering 4–5 Shorts (9:16 vertical, smart face crop & Roman-Hinglish captions)...[/bold yellow]")
    for s in shorts:
        s_dir = proj_dir / "shorts" / s.id
        s_dir.mkdir(parents=True, exist_ok=True)
        s_mp4 = s_dir / f"{s.id}_rendered.mp4"

        # Filter word timings
        words_in_short = []
        for seg in transcript.segments:
            for w in seg.words:
                if s.body_start <= w.start <= s.body_end:
                    words_in_short.append(WordTiming(
                        word=w.word,
                        start=round(w.start - s.body_start, 3),
                        end=round(w.end - s.body_start, 3),
                        confidence=w.confidence
                    ))

        sub_file = None
        if words_in_short:
            ass_path = s_dir / f"{s.id}_captions.ass"
            CaptionEngine.generate_ass(words_in_short, str(ass_path), aspect_ratio="9:16")
            sub_file = str(ass_path)

        FFmpegEngine.render_short(
            source_video=str(path_obj),
            body_start=s.body_start,
            body_end=s.body_end,
            hook_start=s.hook_start,
            hook_end=s.hook_end,
            output_path=str(s_mp4),
            subtitles_file=sub_file,
            use_smart_face_crop=True
        )
        console.print(f"  [green]✓ {s.id} ({s.category}): {s_mp4.name} (★ {s.score})[/green]")

    # 6. Metadata Summary
    console.print("\n[bold yellow]Step 5/5: Packaging SEO & Social Metadata...[/bold yellow]")
    db.update_project_status(proj_id, "completed")

    table = Table(title="Viral Publication Metadata", border_style="cyan")
    table.add_column("Property", style="bold yellow", width=22)
    table.add_column("Details", style="white")

    for i, t in enumerate(metadata.long_form_title_options[:3]):
        table.add_row(f"Title Option {i+1}", t)
    table.add_row("Thumbnail Concept", metadata.long_form_thumbnail_concept[:120] + "...")
    table.add_row("Tags", ", ".join(metadata.long_form_tags[:8]))
    table.add_row("Output Directory", str(proj_dir))

    console.print(table)
    console.print("\n[bold green]🎉 FULL PIPELINE EXECUTION COMPLETED SUCCESSFULLY![/bold green]\n")

if __name__ == "__main__":
    app()

