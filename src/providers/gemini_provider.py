import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from src.core.config import settings
from src.core.models import (
    Transcript,
    ContentAnalysis,
    KeyMoment,
    WeakSection,
    LongFormEditPlan,
    CutSegment,
    ShortCandidate,
    BRollItem,
    EditPlan,
    VideoMetadata,
    ShortMetadata
)
from src.providers.base import AIProvider

HINGLISH_SYSTEM_PROMPT = """
You are an expert AI Video Editor and Content Strategist specializing in tech/business video content for a creator who speaks natural conversational Hindi/Hinglish.

CRITICAL LINGUISTIC RULES:
1. NEVER translate spoken Hinglish into formal English.
2. NEVER convert spoken Hinglish into formal or Devanagari Hindi.
3. PRESERVE standard Hinglish code-switching (e.g. "Basically agar aap ek AI agent bana rahe ho toh aapko state management ka dhyan rakhna padega.").
4. PRESERVE all technical English terminology verbatim: AI, API, backend, frontend, React, Python, JavaScript, Docker, Kubernetes, LangGraph, RAG, embeddings, vector database, Git, GitHub, FastAPI, LLM, cache, latency, throughput, MCP, agents.
5. All generated titles, captions, and descriptions must sound like an authentic tech creator speaking conversational Hinglish and English.
6. Return ONLY strictly valid JSON matching the requested schema. No markdown formatting, no conversational preamble.
"""

class GeminiProvider(AIProvider):
    """Google Gemini AI implementation for multimodal video analysis and structured edit decisions."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or settings.gemini_model or "gemini-2.0-flash"

    def _get_client(self):
        if not self.api_key:
            raise ValueError(
                "Gemini API key is missing. Set GEMINI_API_KEY in your .env file or UI settings."
            )
        from google import genai
        return genai.Client(api_key=self.api_key)

    def health_check(self) -> Dict[str, Any]:
        """Checks if Gemini API key is valid and responsive."""
        if not self.api_key:
            return {"status": "unconfigured", "error": "GEMINI_API_KEY not set"}
        try:
            client = self._get_client()
            resp = client.models.generate_content(
                model=self.model,
                contents="ping",
            )
            return {"status": "healthy", "model": self.model, "response": resp.text.strip()[:20]}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def analyze_content(
        self,
        video_path: str,
        transcript: Transcript,
        keyframes: List[str]
    ) -> ContentAnalysis:
        client = self._get_client()
        from google.genai import types

        # Build compact transcript digest with timestamps
        transcript_lines = [
            f"[{s.start:.1f}s - {s.end:.1f}s]: {s.text}"
            for s in transcript.segments[:300]
        ]
        digest = "\n".join(transcript_lines)

        prompt = f"""
Analyze this raw conversational Hindi/Hinglish recording transcript ({transcript.duration:.1f} total seconds).
Identify:
1. Core central topic and key themes.
2. High-retention key insight moments (timestamp, description, importance 1-10, category).
3. Weak, repetitive, rambling, or setup sections that should be removed from the final cut.
4. Pacing summary.

Transcript Excerpt:
{digest}

Return JSON with this exact schema:
{{
  "topic": "Central topic of the conversation in Hinglish/English",
  "core_themes": ["Theme 1", "Theme 2", "Theme 3"],
  "pacing_summary": "Evaluation of conversational rhythm and high-energy segments",
  "key_moments": [
    {{"timestamp": 45.2, "description": "Key technical explanation", "importance": 9.2, "category": "insight"}}
  ],
  "weak_sections": [
    {{"start": 0.0, "end": 28.5, "reason": "Pre-talk microphone check and repetitive greeting"}}
  ],
  "estimated_raw_duration": {transcript.duration}
}}
"""
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=HINGLISH_SYSTEM_PROMPT,
                response_mime_type="application/json"
            )
        )

        data = json.loads(response.text)
        return ContentAnalysis(
            topic=data.get("topic", "Tech Discussion"),
            core_themes=data.get("core_themes", []),
            pacing_summary=data.get("pacing_summary", ""),
            key_moments=[KeyMoment(**km) for km in data.get("key_moments", [])],
            weak_sections=[WeakSection(**ws) for ws in data.get("weak_sections", [])],
            estimated_raw_duration=float(data.get("estimated_raw_duration", transcript.duration))
        )

    async def select_long_form(
        self,
        analysis: ContentAnalysis,
        transcript: Transcript,
        target_duration_seconds: float = 720.0
    ) -> LongFormEditPlan:
        client = self._get_client()
        from google.genai import types

        prompt = f"""
Using the content analysis and transcript for "{analysis.topic}":
Select the strongest, most coherent sequence of segments to produce a polished 10–15 minute long-form YouTube video.
Total Target Duration: ~{int(target_duration_seconds)} seconds ({target_duration_seconds / 60:.1f} minutes).
Do NOT randomly concatenate clips. Maintain narrative flow, conversational progression, and technical depth.
Ensure cuts occur at natural sentence pauses.
All start and end timestamps MUST fall within 0.0 and {transcript.duration:.1f}.

Return JSON with this exact schema:
{{
  "target_duration_seconds": {target_duration_seconds},
  "narrative_arc": "Summary of the 3-act story arc of this long-form edit",
  "segments": [
    {{
      "start": 28.5,
      "end": 210.0,
      "reason": "Hooks the audience with the main problem and establishes architecture context",
      "transcript_snippet": "Opening spoken lines..."
    }}
  ]
}}
"""
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=HINGLISH_SYSTEM_PROMPT,
                response_mime_type="application/json"
            )
        )

        data = json.loads(response.text)
        raw_segments = data.get("segments", [])
        segments = []
        total_dur = 0.0
        for s in raw_segments:
            st = max(0.0, float(s.get("start", 0.0)))
            en = min(transcript.duration, float(s.get("end", st + 60.0)))
            if en > st:
                segments.append(CutSegment(
                    start=round(st, 2),
                    end=round(en, 2),
                    reason=s.get("reason", "Curated narrative segment"),
                    transcript_snippet=s.get("transcript_snippet", "")
                ))
                total_dur += (en - st)

        return LongFormEditPlan(
            target_duration_seconds=target_duration_seconds,
            estimated_duration=round(total_dur, 2),
            narrative_arc=data.get("narrative_arc", "Polished long-form tech deep dive"),
            segments=segments
        )

    async def select_shorts(
        self,
        analysis: ContentAnalysis,
        transcript: Transcript,
        count: int = 5
    ) -> List[ShortCandidate]:
        client = self._get_client()
        from google.genai import types

        prompt = f"""
From the Hindi/Hinglish recording transcript of "{analysis.topic}":
Select exactly {count} standalone, viral, hook-driven Shorts/Reels candidates.
Target duration per Short: 30 to 58 seconds.

Categories to discover across the video:
1. Strong Opinion / Hot Take
2. Technical Breakthrough / Subtle Gotcha
3. Story / Failure / Lesson
4. Contrarian Point
5. Practical Advice / Shortcut

HOOK RESTRUCTURING RULE:
If the strongest, most punchy sentence occurs later in the segment, designate its timestamp as `hook_start` and `hook_end` (first 2-4 seconds), and the rest of the context as `body_start` and `body_end`.
NEVER fabricate speech or words. Only identify existing timestamps.
Provide suggested Roman-Hinglish captions for social media.

Return JSON with this schema:
{{
  "shorts": [
    {{
      "id": "short_01",
      "title": "Punchy Hinglish Short Title",
      "category": "hot_take",
      "hook": "The exact opening spoken sentence that hooks the viewer",
      "hook_start": 142.0,
      "hook_end": 146.5,
      "body_start": 120.0,
      "body_end": 165.0,
      "estimated_duration": 48.0,
      "score": 9.4,
      "reason": "High retention potential due to counter-intuitive claim about AI agents",
      "suggested_caption": "Wait till the end agar aap bhi AI agents build kar rahe ho 🤯👇",
      "broll_suggestions": ["Show visual of agent state loop", "Highlight Python code snippet"]
    }}
  ]
}}
"""
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=HINGLISH_SYSTEM_PROMPT,
                response_mime_type="application/json"
            )
        )

        data = json.loads(response.text)
        shorts = []
        for idx, s in enumerate(data.get("shorts", [])):
            short_id = s.get("id") or f"short_{idx+1:02d}"
            shorts.append(ShortCandidate(
                id=short_id,
                title=s.get("title", f"Insight #{idx+1}"),
                category=s.get("category", "technical_breakthrough"),
                hook=s.get("hook", ""),
                hook_start=round(float(s.get("hook_start", 0.0)), 2),
                hook_end=round(float(s.get("hook_end", 3.0)), 2),
                body_start=round(float(s.get("body_start", 0.0)), 2),
                body_end=round(float(s.get("body_end", 45.0)), 2),
                estimated_duration=round(float(s.get("estimated_duration", 45.0)), 2),
                score=round(float(s.get("score", 8.5)), 1),
                reason=s.get("reason", ""),
                suggested_caption=s.get("suggested_caption", ""),
                broll_suggestions=s.get("broll_suggestions", [])
            ))
        return shorts

    async def generate_edit_plan(
        self,
        project_id: str,
        long_form: LongFormEditPlan,
        shorts: List[ShortCandidate],
        transcript: Transcript,
        silence_cuts: Optional[List[Dict[str, float]]] = None
    ) -> EditPlan:
        # Assemble B-roll suggestions from shorts and key segments
        broll: List[BRollItem] = []
        for s in shorts:
            for b_text in s.broll_suggestions:
                broll.append(BRollItem(
                    start=s.body_start,
                    end=min(s.body_end, s.body_start + 4.0),
                    suggestion=b_text,
                    status="B-ROLL REQUIRED"
                ))

        return EditPlan(
            project_id=project_id,
            long_form=long_form,
            shorts=shorts,
            broll=broll,
            silence_cuts=silence_cuts or [],
            ducking_db=settings.ducking_db
        )

    async def generate_metadata(
        self,
        project_name: str,
        transcript: Transcript,
        long_form: LongFormEditPlan,
        shorts: List[ShortCandidate]
    ) -> VideoMetadata:
        client = self._get_client()
        from google.genai import types

        shorts_summary = "\n".join([f"- {s.id}: {s.title} (Hook: {s.hook})" for s in shorts])
        prompt = f"""
Generate full viral publication metadata for the project "{project_name}".
Long-form edit arc: {long_form.narrative_arc}
Available Shorts:
{shorts_summary}

Requirements:
1. Long-form: 3 high-CTR title variations in Hinglish/English, comprehensive SEO description with chapter timestamps, 12-15 relevant tags, and a YouTube thumbnail concept with overlay text.
2. For EACH Short: punchy title, social caption in conversational Roman Hinglish, 8-10 hashtags, and recommended thumbnail timestamp.

Return JSON with this schema:
{{
  "long_form_title_options": [
    "Title 1 in punchy Hinglish",
    "Title 2 focused on curiosity gap",
    "Title 3 high technical authority"
  ],
  "long_form_description": "Full YouTube description with chapters and hashtags",
  "long_form_tags": ["AI", "Hinglish", "Tech", "Python"],
  "long_form_thumbnail_concept": "Description of thumbnail layout, facial expression, and big 3-word bold text overlay",
  "shorts_metadata": [
    {{
      "short_id": "short_01",
      "title": "Short title",
      "caption": "Short caption in Roman Hinglish with call to action",
      "hashtags": ["#Shorts", "#AI", "#HinglishTech", "#Coding"],
      "thumbnail_timestamp": 143.5,
      "thumbnail_concept": "Expressive face with reaction overlay"
    }}
  ]
}}
"""
        response = client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=HINGLISH_SYSTEM_PROMPT,
                response_mime_type="application/json"
            )
        )

        data = json.loads(response.text)
        shorts_meta = [
            ShortMetadata(
                short_id=sm.get("short_id", f"short_{i+1:02d}"),
                title=sm.get("title", ""),
                caption=sm.get("caption", ""),
                hashtags=sm.get("hashtags", []),
                thumbnail_timestamp=float(sm.get("thumbnail_timestamp", 0.0)),
                thumbnail_concept=sm.get("thumbnail_concept", "")
            )
            for i, sm in enumerate(data.get("shorts_metadata", []))
        ]

        return VideoMetadata(
            long_form_title_options=data.get("long_form_title_options", [project_name]),
            long_form_description=data.get("long_form_description", ""),
            long_form_tags=data.get("long_form_tags", ["AI", "Tech"]),
            long_form_thumbnail_concept=data.get("long_form_thumbnail_concept", ""),
            shorts_metadata=shorts_meta
        )
