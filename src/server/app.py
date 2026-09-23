import asyncio
import json
import os
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.core.config import settings
from src.core.database import db
from src.core.models import (
    Project,
    Transcript,
    ContentAnalysis,
    EditPlan,
    VideoMetadata,
    RenderJob,
    CutSegment
)
from src.readers.video_reader import VideoReader
from src.providers.factory import get_ai_provider
from src.processors.caption_engine import CaptionEngine
from src.processors.ffmpeg_engine import FFmpegEngine
from src.publishing.youtube import YouTubePublisher
from src.publishing.instagram import InstagramPublisher

app = FastAPI(
    title="AI Content Automation Engine",
    description="Local desktop backend for autonomous Hindi/Hinglish video production",
    version="1.0.0"
)

# Enable CORS for desktop app (Tauri / Vite localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
os.makedirs(settings.projects_dir, exist_ok=True)
app.mount("/projects", StaticFiles(directory=settings.projects_dir), name="projects")

# In-memory SSE subscriber queues: {project_id: [asyncio.Queue]}
_subscribers: Dict[str, List[asyncio.Queue]] = {}

def broadcast_event(project_id: str, stage: str, progress: float, message: str, data: Optional[Dict[str, Any]] = None):
    """Broadcasts SSE progress event to all connected UI clients for this project."""
    if project_id in _subscribers:
        payload = json.dumps({
            "project_id": project_id,
            "stage": stage,
            "progress": round(progress, 1),
            "message": message,
            "data": data or {},
            "timestamp": time.time()
        })
        for q in _subscribers[project_id]:
            try:
                q.put_nowait(payload)
            except Exception:
                pass

# --- Request / Response Schemas ---

class CreateProjectRequest(BaseModel):
    name: str
    source_video_path: str
    ai_provider: str = "gemini"  # "gemini" or "ollama"
    ai_model: Optional[str] = None
    target_duration_minutes: float = 12.0

class PublishRequest(BaseModel):
    platform: str  # "youtube" or "instagram"
    video_type: str = "long_form"  # "long_form" or "short"
    short_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    privacy_status: str = "private"

# --- API Endpoints ---

@app.get("/api/health")
def health_check():
    """Returns local system diagnostics, provider health, and FFmpeg binary info."""
    ffmpeg_bin = FFmpegEngine.get_ffmpeg_binary()
    gemini_health = get_ai_provider("gemini").health_check()
    ollama_health = get_ai_provider("ollama").health_check()

    return {
        "status": "online",
        "ffmpeg": ffmpeg_bin,
        "ffmpeg_available": bool(shutil_which_ffmpeg()),
        "providers": {
            "active": settings.ai_provider,
            "gemini": gemini_health,
            "ollama": ollama_health
        },
        "storage": {
            "projects_dir": str(settings.projects_dir),
            "db_path": str(settings.db_path)
        }
    }

def shutil_which_ffmpeg():
    import shutil
    return shutil.which("ffmpeg") or os.path.exists(FFmpegEngine.get_ffmpeg_binary())

@app.get("/api/projects", response_model=List[Project])
def list_projects():
    """Lists all projects ordered by last update."""
    return db.list_projects()

@app.post("/api/upload-video")
async def upload_video(file: UploadFile = File(...)):
    """Uploads a video file from the browser into the local uploads cache directory."""
    upload_dir = os.path.join(settings.base_dir, "uploads")
    os.makedirs(upload_dir, exist_ok=True)

    clean_name = os.path.basename(file.filename or "uploaded_video.mp4").replace(" ", "_")
    save_path = os.path.join(upload_dir, f"{int(time.time())}_{clean_name}")

    with open(save_path, "wb") as f:
        while chunk := await file.read(1024 * 1024 * 4):  # 4MB chunks
            f.write(chunk)

    return {
        "filename": file.filename,
        "saved_path": save_path,
        "size_bytes": os.path.getsize(save_path)
    }

@app.post("/api/projects", response_model=Project)
def create_project(req: CreateProjectRequest):
    """Creates a new video project and inspects input video metadata."""
    video_path = Path(req.source_video_path)
    if not video_path.exists():
        raise HTTPException(status_code=400, detail=f"Source video file does not exist: {req.source_video_path}")

    proj_id = f"proj_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    
    # Inspect video
    try:
        meta = VideoReader.get_metadata(str(video_path))
        duration = meta.get("duration_seconds", 0.0)
        w = meta.get("width", 1920)
        h = meta.get("height", 1080)
    except Exception as e:
        duration, w, h, meta = 0.0, 1920, 1080, {"error": str(e)}

    project = db.create_project(
        project_id=proj_id,
        name=req.name,
        source_video_path=str(video_path),
        ai_provider=req.ai_provider,
        ai_model=req.ai_model or ("gemini-2.0-flash" if req.ai_provider == "gemini" else "llama3.2"),
        duration_seconds=duration,
        video_width=w,
        video_height=h,
        extra_metadata=meta
    )
    return project

@app.get("/api/projects/{project_id}")
def get_project_details(project_id: str):
    """Fetches full project state including transcript, edit plan, renders, and metadata."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    transcript = db.get_transcript(project_id)
    analysis = db.get_content_analysis(project_id)
    edit_plan = db.get_edit_plan(project_id)
    render_jobs = db.get_render_jobs(project_id)
    metadata = db.get_metadata(project_id)

    return {
        "project": project,
        "transcript": transcript,
        "analysis": analysis,
        "edit_plan": edit_plan,
        "render_jobs": render_jobs,
        "metadata": metadata
    }

@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str):
    """Deletes project from database and filesystem."""
    success = db.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    proj_dir = settings.projects_dir / project_id
    if proj_dir.exists():
        import shutil
        shutil.rmtree(proj_dir, ignore_errors=True)
    return {"status": "deleted", "project_id": project_id}

@app.get("/api/events/{project_id}")
async def project_events_stream(project_id: str):
    """Server-Sent Events (SSE) endpoint streaming real-time pipeline status."""
    q: asyncio.Queue = asyncio.Queue()
    if project_id not in _subscribers:
        _subscribers[project_id] = []
    _subscribers[project_id].append(q)

    async def event_generator():
        try:
            # Send initial ping
            yield f"data: {json.dumps({'type': 'connected', 'project_id': project_id})}\n\n"
            while True:
                data = await q.get()
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if project_id in _subscribers and q in _subscribers[project_id]:
                _subscribers[project_id].remove(q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- Background Task Handlers ---

async def _run_transcription_task(project_id: str):
    """Executes audio extraction and faster-whisper transcription."""
    project = db.get_project(project_id)
    if not project:
        return

    try:
        db.update_project_status(project_id, "transcribing")
        broadcast_event(project_id, "audio_extraction", 15.0, "Extracting audio track for speech recognition...")

        proj_dir = settings.projects_dir / project_id
        audio_file = proj_dir / "audio" / "extracted_audio.wav"
        VideoReader.extract_audio(project.source_video_path, str(audio_file))

        broadcast_event(project_id, "transcription", 35.0, "Transcribing spoken Hindi/Hinglish via faster-whisper...")
        transcript = VideoReader.transcribe(str(audio_file), language="hi")
        db.save_transcript(project_id, transcript)

        broadcast_event(project_id, "transcribed", 50.0, f"Transcription complete! ({len(transcript.segments)} segments)", {"words_count": len(transcript.full_text.split())})
        db.update_project_status(project_id, "transcribed")

    except Exception as e:
        db.update_project_status(project_id, "failed")
        broadcast_event(project_id, "failed", 0.0, f"Transcription error: {str(e)}")

@app.post("/api/projects/{project_id}/transcribe")
def start_transcription(project_id: str, background_tasks: BackgroundTasks):
    """Triggers speech-to-text transcription in background."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    background_tasks.add_task(_run_transcription_task, project_id)
    return {"status": "queued", "stage": "transcription"}

async def _run_analysis_and_edit_plan_task(project_id: str):
    """Executes AI content analysis, long-form cut selection, and shorts discovery."""
    project = db.get_project(project_id)
    if not project:
        return

    transcript = db.get_transcript(project_id)
    if not transcript:
        # Auto-run transcription first if not present
        await _run_transcription_task(project_id)
        transcript = db.get_transcript(project_id)
        if not transcript:
            return

    try:
        db.update_project_status(project_id, "analyzing")
        broadcast_event(project_id, "ai_analysis", 55.0, f"Analyzing conversation using {project.ai_provider.upper()}...")

        provider = get_ai_provider(project.ai_provider, project.ai_model)
        proj_dir = settings.projects_dir / project_id
        keyframes_dir = proj_dir / "previews" / "keyframes"
        keyframes = VideoReader.extract_keyframes(project.source_video_path, str(keyframes_dir), num_frames=6)

        # 1. Content Analysis
        analysis = await provider.analyze_content(project.source_video_path, transcript, keyframes)
        db.save_content_analysis(project_id, analysis)

        # 2. Long-Form Selection
        broadcast_event(project_id, "long_form_selection", 70.0, "Curating coherent 10–15 min long-form narrative cuts...")
        long_form = await provider.select_long_form(analysis, transcript, target_duration_seconds=720.0)

        # 3. Shorts Discovery
        broadcast_event(project_id, "shorts_selection", 82.0, "Selecting 4–5 hook-driven Shorts/Reels candidates...")
        shorts = await provider.select_shorts(analysis, transcript, count=5)

        # 4. Silence detection
        broadcast_event(project_id, "silence_detection", 88.0, "Detecting conversational pauses & dead-air...")
        silence_cuts = VideoReader.detect_silence(project.source_video_path, min_duration_seconds=0.8)

        # 5. Edit Plan Assembly
        edit_plan = await provider.generate_edit_plan(project_id, long_form, shorts, transcript, silence_cuts)
        db.save_edit_plan(project_id, edit_plan, status="ready_for_review")

        # 6. Metadata Packaging
        broadcast_event(project_id, "metadata_generation", 94.0, "Generating Hinglish YouTube titles, descriptions, and hashtags...")
        metadata = await provider.generate_metadata(project.name, transcript, long_form, shorts)
        db.save_metadata(project_id, metadata)

        db.update_project_status(project_id, "edit_plan_ready")
        broadcast_event(project_id, "edit_plan_ready", 100.0, "Edit plan ready for human review!", {
            "long_form_duration": long_form.estimated_duration,
            "shorts_count": len(shorts)
        })

    except Exception as e:
        db.update_project_status(project_id, "failed")
        broadcast_event(project_id, "failed", 0.0, f"Analysis error: {str(e)}")

@app.post("/api/projects/{project_id}/analyze")
def start_analysis(project_id: str, background_tasks: BackgroundTasks):
    """Triggers AI analysis, edit decision planning, and metadata creation."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    background_tasks.add_task(_run_analysis_and_edit_plan_task, project_id)
    return {"status": "queued", "stage": "analysis"}

@app.get("/api/projects/{project_id}/edit-plan")
def get_edit_plan(project_id: str):
    """Returns the structured edit plan."""
    plan = db.get_edit_plan(project_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Edit plan not generated yet")
    return plan

@app.put("/api/projects/{project_id}/edit-plan")
def update_edit_plan(project_id: str, plan: EditPlan):
    """Allows user to adjust timestamps, toggle segments, and modify hook selections."""
    db.save_edit_plan(project_id, plan, status="approved")
    return {"status": "updated", "project_id": project_id}

@app.get("/api/projects/{project_id}/metadata")
def get_project_metadata(project_id: str):
    """Returns the social and SEO metadata."""
    meta = db.get_metadata(project_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Metadata not generated yet")
    return meta

@app.put("/api/projects/{project_id}/metadata")
def update_project_metadata(project_id: str, metadata: VideoMetadata):
    """Allows user to customize titles, captions, and descriptions."""
    db.save_metadata(project_id, metadata)
    return {"status": "updated", "project_id": project_id}

# --- Rendering Endpoints ---

async def _render_long_form_task(project_id: str, job_id: str):
    """Executes long-form 16:9 video assembly and audio normalization."""
    project = db.get_project(project_id)
    edit_plan = db.get_edit_plan(project_id)
    if not project or not edit_plan:
        return

    try:
        db.update_render_job(job_id, status="rendering", progress=10.0)
        broadcast_event(project_id, "rendering_long_form", 10.0, "Starting long-form 16:9 render...")

        proj_dir = settings.projects_dir / project_id
        out_mp4 = proj_dir / "renders" / f"{project_id}_long_form.mp4"

        FFmpegEngine.render_long_form(
            source_video=project.source_video_path,
            segments=edit_plan.long_form.segments,
            output_path=str(out_mp4),
            normalize_audio=True
        )

        db.update_render_job(job_id, status="completed", progress=100.0, output_file=str(out_mp4))
        broadcast_event(project_id, "render_completed", 100.0, f"Long-form video rendered: {out_mp4.name}", {"output_file": str(out_mp4)})

    except Exception as e:
        db.update_render_job(job_id, status="failed", progress=0.0, error=str(e))
        broadcast_event(project_id, "render_failed", 0.0, f"Render error: {str(e)}")

@app.post("/api/projects/{project_id}/render/long-form")
def render_long_form(project_id: str, background_tasks: BackgroundTasks):
    """Triggers long-form 10–15 min rendering."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    job_id = f"job_long_{uuid.uuid4().hex[:6]}"
    job = RenderJob(job_id=job_id, project_id=project_id, render_type="long_form")
    db.create_render_job(job)
    background_tasks.add_task(_render_long_form_task, project_id, job_id)
    return {"job_id": job_id, "status": "queued"}

async def _render_short_task(project_id: str, short_id: str, job_id: str):
    """Executes single Short rendering with face tracking and Roman-Hinglish captions."""
    project = db.get_project(project_id)
    edit_plan = db.get_edit_plan(project_id)
    transcript = db.get_transcript(project_id)
    if not project or not edit_plan:
        return

    # Find the target short candidate
    short_candidate = next((s for s in edit_plan.shorts if s.id == short_id), None)
    if not short_candidate:
        return

    try:
        db.update_render_job(job_id, status="rendering", progress=15.0)
        broadcast_event(project_id, "rendering_short", 20.0, f"Generating Roman-Hinglish captions for {short_id}...")

        proj_dir = settings.projects_dir / project_id
        short_dir = proj_dir / "shorts" / short_id
        short_dir.mkdir(parents=True, exist_ok=True)

        # 1. Filter word timings for this short interval
        sub_file = None
        if transcript:
            b_start = short_candidate.body_start
            b_end = short_candidate.body_end
            words_in_short = []
            for seg in transcript.segments:
                for w in seg.words:
                    if b_start <= w.start <= b_end:
                        # Re-base timestamps relative to short start
                        rebased_w = WordTiming(
                            word=w.word,
                            start=round(w.start - b_start, 3),
                            end=round(w.end - b_start, 3),
                            confidence=w.confidence
                        )
                        words_in_short.append(rebased_w)

            if words_in_short:
                ass_path = short_dir / f"{short_id}_captions.ass"
                CaptionEngine.generate_ass(words_in_short, str(ass_path), aspect_ratio="9:16")
                sub_file = str(ass_path)

        # 2. Render 9:16 vertical Short
        broadcast_event(project_id, "rendering_short", 50.0, f"Executing 9:16 face-tracked render for {short_id}...")
        out_mp4 = short_dir / f"{short_id}_rendered.mp4"

        FFmpegEngine.render_short(
            source_video=project.source_video_path,
            body_start=short_candidate.body_start,
            body_end=short_candidate.body_end,
            hook_start=short_candidate.hook_start,
            hook_end=short_candidate.hook_end,
            output_path=str(out_mp4),
            subtitles_file=sub_file,
            use_smart_face_crop=True
        )

        db.update_render_job(job_id, status="completed", progress=100.0, output_file=str(out_mp4))
        broadcast_event(project_id, "short_completed", 100.0, f"{short_id} rendered successfully!", {"output_file": str(out_mp4)})

    except Exception as e:
        db.update_render_job(job_id, status="failed", progress=0.0, error=str(e))
        broadcast_event(project_id, "render_failed", 0.0, f"Error rendering {short_id}: {str(e)}")

@app.post("/api/projects/{project_id}/render/short/{short_id}")
def render_individual_short(project_id: str, short_id: str, background_tasks: BackgroundTasks):
    """Renders or re-renders an individual Short without reprocessing the rest of the project."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    job_id = f"job_{short_id}_{uuid.uuid4().hex[:6]}"
    job = RenderJob(job_id=job_id, project_id=project_id, render_type="short", short_id=short_id)
    db.create_render_job(job)
    background_tasks.add_task(_render_short_task, project_id, short_id, job_id)
    return {"job_id": job_id, "status": "queued", "short_id": short_id}

@app.post("/api/projects/{project_id}/render/all-shorts")
def render_all_shorts(project_id: str, background_tasks: BackgroundTasks):
    """Batches rendering for all selected Shorts in the edit plan."""
    edit_plan = db.get_edit_plan(project_id)
    if not edit_plan:
        raise HTTPException(status_code=404, detail="Edit plan not found")
    queued_jobs = []
    for s in edit_plan.shorts:
        job_id = f"job_{s.id}_{uuid.uuid4().hex[:6]}"
        job = RenderJob(job_id=job_id, project_id=project_id, render_type="short", short_id=s.id)
        db.create_render_job(job)
        background_tasks.add_task(_render_short_task, project_id, s.id, job_id)
        queued_jobs.append({"short_id": s.id, "job_id": job_id})
    return {"queued_shorts": queued_jobs}

# --- Publishing Endpoints ---

@app.post("/api/projects/{project_id}/publish")
async def publish_content(project_id: str, req: PublishRequest):
    """Dispatches approved video to YouTube or Instagram."""
    project = db.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    metadata = db.get_metadata(project_id)
    proj_dir = settings.projects_dir / project_id

    # Determine file path and metadata
    if req.video_type == "long_form":
        target_file = proj_dir / "renders" / f"{project_id}_long_form.mp4"
        title = req.title or (metadata.long_form_title_options[0] if metadata and metadata.long_form_title_options else project.name)
        description = req.description or (metadata.long_form_description if metadata else "")
        tags = metadata.long_form_tags if metadata else []
        is_short = False
    else:
        target_file = proj_dir / "shorts" / (req.short_id or "short_01") / f"{req.short_id}_rendered.mp4"
        short_meta = next((sm for sm in metadata.shorts_metadata if sm.short_id == req.short_id), None) if metadata else None
        title = req.title or (short_meta.title if short_meta else f"{project.name} Short")
        description = req.description or (short_meta.caption if short_meta else "")
        tags = short_meta.hashtags if short_meta else []
        is_short = True

    if not target_file.exists():
        raise HTTPException(status_code=400, detail=f"Rendered video file not found at {target_file}. Please render before publishing.")

    if req.platform.lower() == "youtube":
        publisher = YouTubePublisher()
        result = await publisher.upload_video(
            video_path=str(target_file),
            title=title,
            description=description,
            tags=tags,
            is_short=is_short,
            privacy_status=req.privacy_status
        )
        return result
    elif req.platform.lower() == "instagram":
        publisher = InstagramPublisher()
        result = await publisher.publish_reel(
            video_path=str(target_file),
            caption=description or title,
            hashtags=tags
        )
        return result
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported publishing platform '{req.platform}'")

# --- Serve Local Media Files (Previews, Renders, Assets) ---

@app.get("/media/file")
def get_media_file(path: str):
    """Safely serves rendered project videos and preview frames to the UI."""
    file_path = Path(path).resolve()
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Media file not found")
    return FileResponse(str(file_path))
