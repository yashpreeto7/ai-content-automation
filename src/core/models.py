import time
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# --- TRANSCRIPTION MODELS ---

class WordTiming(BaseModel):
    word: str
    start: float
    end: float
    confidence: Optional[float] = 1.0

class TranscriptSegment(BaseModel):
    id: int
    start: float
    end: float
    text: str
    words: List[WordTiming] = Field(default_factory=list)

class Transcript(BaseModel):
    language: str = "hi"
    duration: float = 0.0
    full_text: str = ""
    segments: List[TranscriptSegment] = Field(default_factory=list)

# --- CONTENT ANALYSIS & EDITING MODELS ---

class KeyMoment(BaseModel):
    timestamp: float
    description: str
    importance: float = 8.0  # 1.0 - 10.0
    category: str = "insight"

class WeakSection(BaseModel):
    start: float
    end: float
    reason: str

class ContentAnalysis(BaseModel):
    topic: str
    core_themes: List[str] = Field(default_factory=list)
    pacing_summary: str = ""
    key_moments: List[KeyMoment] = Field(default_factory=list)
    weak_sections: List[WeakSection] = Field(default_factory=list)
    estimated_raw_duration: float = 0.0

class CutSegment(BaseModel):
    start: float
    end: float
    reason: str = ""
    transcript_snippet: Optional[str] = None

class LongFormEditPlan(BaseModel):
    target_duration_seconds: float = 720.0  # 10 - 15 minutes default
    estimated_duration: float = 0.0
    narrative_arc: str = ""
    segments: List[CutSegment] = Field(default_factory=list)

class ShortCandidate(BaseModel):
    id: str  # e.g., "short_01"
    title: str
    category: str = "technical_breakthrough"  # "hot_take", "story", "contrarian", "practical_tip", "technical_breakthrough"
    hook: str
    hook_start: float
    hook_end: float
    body_start: float
    body_end: float
    estimated_duration: float = 45.0
    score: float = 8.5
    reason: str = ""
    suggested_caption: str = ""
    broll_suggestions: List[str] = Field(default_factory=list)

class BRollItem(BaseModel):
    start: float
    end: float
    suggestion: str
    status: str = "B-ROLL REQUIRED"  # "B-ROLL REQUIRED" | "INSERTED"
    asset_path: Optional[str] = None

class EditPlan(BaseModel):
    project_id: str
    long_form: LongFormEditPlan
    shorts: List[ShortCandidate] = Field(default_factory=list)
    broll: List[BRollItem] = Field(default_factory=list)
    silence_cuts: List[Dict[str, float]] = Field(default_factory=list)
    ducking_db: float = -12.0

# --- METADATA MODELS ---

class ShortMetadata(BaseModel):
    short_id: str
    title: str
    caption: str
    hashtags: List[str] = Field(default_factory=list)
    thumbnail_timestamp: float = 0.0
    thumbnail_concept: str = ""

class VideoMetadata(BaseModel):
    long_form_title_options: List[str] = Field(default_factory=list)
    long_form_description: str = ""
    long_form_tags: List[str] = Field(default_factory=list)
    long_form_thumbnail_concept: str = ""
    shorts_metadata: List[ShortMetadata] = Field(default_factory=list)

# --- PROJECT & JOB STATE ---

class Project(BaseModel):
    id: str
    name: str
    source_video_path: str
    status: str = "created"  # created, inspecting, transcribed, analyzed, edit_plan_ready, rendering, completed, failed
    ai_provider: str = "gemini"
    ai_model: str = "gemini-2.0-flash"
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    duration_seconds: Optional[float] = None
    video_width: Optional[int] = None
    video_height: Optional[int] = None
    extra_metadata: Dict[str, Any] = Field(default_factory=dict)

class RenderJob(BaseModel):
    job_id: str
    project_id: str
    render_type: str = "short"  # "long_form" or "short"
    short_id: Optional[str] = None
    status: str = "pending"  # pending, rendering, completed, failed
    progress: float = 0.0
    output_file: Optional[str] = None
    error: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    completed_at: Optional[float] = None

# --- LEGACY MODELS FOR CLI BACKWARD COMPATIBILITY ---

class Scene(BaseModel):
    scene_index: int
    text_segment: str
    visual_prompt: str
    duration_seconds: float = 3.5
    image_path: Optional[str] = None
    video_path: Optional[str] = None

class Script(BaseModel):
    topic: str
    style: str = "cinematic"
    hook: str
    body_points: List[str] = Field(default_factory=list)
    cta: str
    full_text: str
    scenes: List[Scene] = Field(default_factory=list)
    estimated_duration: float = 45.0

class SocialPackage(BaseModel):
    title_options: List[str] = Field(default_factory=list)
    description: str
    hashtags: List[str] = Field(default_factory=list)
    thumbnail_prompt: str

class ContentRequest(BaseModel):
    topic: str
    style: str = "cinematic"
    target_duration: float = 45.0
    aspect_ratio: str = "9:16"
    voice: Optional[str] = None
    music_track: Optional[str] = None
    output_path: Optional[str] = None
    use_ai_video: bool = True
