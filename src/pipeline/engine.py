import json
import time
import uuid
from pathlib import Path
from typing import Optional, Callable
from src.core.config import settings
from src.core.models import ContentRequest, RenderJob, Script
from src.generators.script_generator import ScriptGenerator
from src.generators.voice_generator import VoiceGenerator
from src.generators.video_generator import VideoGenerator
from src.processors.caption_engine import CaptionEngine
from src.processors.ffmpeg_engine import FFmpegEngine

class ContentPipeline:
    """Orchestrates the entire topic-to-rendered-video automation lifecycle."""

    @classmethod
    def run(
        cls,
        request: ContentRequest,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> RenderJob:
        """Executes the full content automation pipeline synchronously."""
        job_id = f"job_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        job = RenderJob(job_id=job_id, status="starting", request=request)

        def update_progress(stage: str, pct: float):
            job.status = stage
            if progress_callback:
                progress_callback(stage, pct)
            else:
                print(f"[{job_id}] [{pct:3.0f}%] {stage}")

        try:
            # 1. Script Generation
            update_progress("generating_script", 10.0)
            script = ScriptGenerator.generate(
                topic=request.topic,
                style=request.style,
                target_duration=request.target_duration
            )
            job.script = script

            # 2. Voiceover & Word Timestamps
            update_progress("synthesizing_voice", 30.0)
            audio_path = str(settings.output_dir / f"voice_{job_id}.mp3")
            audio_file, word_timings = VoiceGenerator.synthesize(
                text=script.full_text,
                voice=request.voice or settings.default_voice,
                output_audio=audio_path
            )
            job.audio_path = audio_file

            # 3. Subtitles Generation
            update_progress("generating_subtitles", 45.0)
            ass_path = str(settings.output_dir / f"captions_{job_id}.ass")
            CaptionEngine.generate_ass(
                word_timings=word_timings,
                output_path=ass_path,
                chunk_size=3
            )
            job.subtitles_path = ass_path

            # 4. Visual Scene Generation
            update_progress("generating_visuals", 60.0)
            scene_dir = str(settings.output_dir / f"scenes_{job_id}")
            scene_clips = VideoGenerator.generate_scenes(
                scenes=script.scenes,
                aspect_ratio=request.aspect_ratio,
                output_dir=scene_dir
            )
            job.scene_clips = scene_clips

            # 5. FFmpeg Assembly & Audio Ducking
            update_progress("assembling_video", 80.0)
            if request.output_path:
                final_output = request.output_path
            else:
                clean_name = "".join(c if c.isalnum() else "_" for c in request.topic)[:32].strip("_")
                final_output = str(settings.output_dir / f"{clean_name}_{job_id}.mp4")

            FFmpegEngine.assemble_final_video(
                clips=scene_clips,
                voiceover_audio=job.audio_path,
                background_music=request.music_track,
                subtitles_file=job.subtitles_path,
                output_file=final_output
            )
            job.output_file = final_output

            # 6. Social Metadata Packaging
            update_progress("packaging_metadata", 95.0)
            social_package = ScriptGenerator.generate_social_package(script)
            job.social_package = social_package

            meta_file = Path(final_output).with_suffix(".json")
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump({
                    "job_id": job.job_id,
                    "topic": request.topic,
                    "style": request.style,
                    "aspect_ratio": request.aspect_ratio,
                    "titles": social_package.title_options,
                    "description": social_package.description,
                    "hashtags": social_package.hashtags,
                    "thumbnail_prompt": social_package.thumbnail_prompt,
                    "script_text": script.full_text,
                    "output_video": str(final_output),
                    "created_at": job.created_at
                }, f, indent=2)

            update_progress("completed", 100.0)
            job.completed_at = time.time()
            return job

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            print(f"[ContentPipeline Error] {e}")
            raise
