from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import time

class WordTiming(BaseModel):
    word: str
    start: float
    end: float
    confidence: Optional[float] = 1.0

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

class RenderJob(BaseModel):
    job_id: str
    status: str = "pending"  # pending, generating_script, synthesizing_voice, rendering_visuals, assembling, completed, failed
    request: ContentRequest
    script: Optional[Script] = None
    audio_path: Optional[str] = None
    subtitles_path: Optional[str] = None
    scene_clips: List[str] = Field(default_factory=list)
    output_file: Optional[str] = None
    social_package: Optional[SocialPackage] = None
    error: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    completed_at: Optional[float] = None
