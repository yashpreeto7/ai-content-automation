import json
import re
from typing import List, Optional, Dict, Any
import httpx
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

HINGLISH_OLLAMA_SYSTEM = """
You are an expert AI Video Editor and Content Strategist for an Indian tech creator who speaks conversational Hindi/Hinglish.
CRITICAL RULES:
1. Never translate to English.
2. Never convert to Devanagari Hindi.
3. Preserve natural Hinglish code-switching and all English tech terms (AI, API, backend, frontend, React, Python, JavaScript, Docker, Kubernetes, LangGraph, RAG, embeddings, etc.).
4. Return ONLY valid JSON matching the exact schema specified. No markdown text, no thought blocks, no preamble.
"""

class OllamaProvider(AIProvider):
    """Local Ollama AI provider for 100% offline, privacy-first content analysis and edit planning."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        vision_model: Optional[str] = None
    ):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model or "llama3.2"
        self.vision_model = vision_model or settings.ollama_vision_model or "llava"

    def health_check(self) -> Dict[str, Any]:
        """Checks if local Ollama daemon is running and what models are installed."""
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m.get("name", "") for m in data.get("models", [])]
                    model_found = any(self.model in m for m in models)
                    return {
                        "status": "healthy" if model_found else "model_missing",
                        "available_models": models,
                        "selected_model": self.model,
                        "base_url": self.base_url
                    }
                return {"status": "error", "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {
                "status": "offline",
                "error": f"Cannot connect to Ollama at {self.base_url}: {e}. Ensure 'ollama serve' is running."
            }

    async def _query_ollama(self, prompt: str, schema_desc: str) -> Dict[str, Any]:
        """Sends query to Ollama with strict JSON formatting instruction."""
        system_instruction = f"{HINGLISH_OLLAMA_SYSTEM}\nYou MUST output valid JSON matching this schema:\n{schema_desc}"
        payload = {
            "model": self.model,
            "prompt": f"{system_instruction}\n\nTask:\n{prompt}",
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.2,
                "num_ctx": 8192
            }
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                if resp.status_code == 200:
                    result = resp.json().get("response", "{}")
                    # Clean any trailing markdown if present
                    clean = re.sub(r"^```json\s*", "", result.strip())
                    clean = re.sub(r"```$", "", clean.strip())
                    return json.loads(clean)
        except Exception as e:
            print(f"[OllamaProvider] Ollama query failed ({e}). Utilizing deterministic heuristic engine.")

        return {}

    async def analyze_content(
        self,
        video_path: str,
        transcript: Transcript,
        keyframes: List[str]
    ) -> ContentAnalysis:
        # Build prompt
        transcript_sample = "\n".join([f"[{s.start:.1f}s]: {s.text}" for s in transcript.segments[:200]])
        prompt = f"Analyze this Hindi/Hinglish recording transcript ({transcript.duration:.1f}s):\n{transcript_sample}"
        schema = '{"topic": "string", "core_themes": ["string"], "pacing_summary": "string", "key_moments": [{"timestamp": 0.0, "description": "string", "importance": 8.5}], "weak_sections": [{"start": 0.0, "end": 10.0, "reason": "string"}]}'

        data = await self._query_ollama(prompt, schema)

        if not data or not data.get("topic"):
            # Deterministic heuristic fallback based on transcript keywords
            words = transcript.full_text.split()
            first_topic = "Tech & AI Architecture Discussion"
            if len(words) > 5:
                first_topic = f"{words[0].capitalize()} {words[1].capitalize()} Tech Conversation"

            return ContentAnalysis(
                topic=first_topic,
                core_themes=["System Design", "Implementation", "Best Practices"],
                pacing_summary="Steady conversational pacing with concentrated technical segments",
                key_moments=[
                    KeyMoment(timestamp=round(min(transcript.duration * 0.2, 45.0), 1), description="Primary concept explanation", importance=9.0),
                    KeyMoment(timestamp=round(min(transcript.duration * 0.5, 120.0), 1), description="Technical gotcha and implementation insight", importance=9.2),
                    KeyMoment(timestamp=round(min(transcript.duration * 0.8, 240.0), 1), description="Conclusion and practical recommendations", importance=8.8),
                ],
                weak_sections=[
                    WeakSection(start=0.0, end=min(transcript.duration * 0.05, 15.0), reason="Conversational preamble and intro setup")
                ],
                estimated_raw_duration=transcript.duration
            )

        return ContentAnalysis(
            topic=data.get("topic", "Tech Discussion"),
            core_themes=data.get("core_themes", []),
            pacing_summary=data.get("pacing_summary", ""),
            key_moments=[KeyMoment(**km) for km in data.get("key_moments", [])],
            weak_sections=[WeakSection(**ws) for ws in data.get("weak_sections", [])],
            estimated_raw_duration=transcript.duration
        )

    async def select_long_form(
        self,
        analysis: ContentAnalysis,
        transcript: Transcript,
        target_duration_seconds: float = 720.0
    ) -> LongFormEditPlan:
        prompt = f"Select cohesive segments totaling ~{target_duration_seconds}s for long-form video on '{analysis.topic}' from duration {transcript.duration}s."
        schema = '{"narrative_arc": "string", "segments": [{"start": 0.0, "end": 100.0, "reason": "string"}]}'

        data = await self._query_ollama(prompt, schema)
        raw_segments = data.get("segments", [])

        if not raw_segments:
            # Deterministic segment curation
            start_offset = 15.0 if transcript.duration > 30.0 else 0.0
            avail_dur = max(10.0, transcript.duration - start_offset)
            target = min(avail_dur, target_duration_seconds)
            chunk_size = min(300.0, target / 3.0)

            curated: List[CutSegment] = []
            curr = start_offset
            reasons = [
                "Introduces core problem statement and context",
                "Deep dive into technical architecture and implementation",
                "Key learnings, gotchas, and conclusions"
            ]
            r_idx = 0
            while curr < (start_offset + target):
                seg_end = min(transcript.duration, curr + chunk_size)
                curated.append(CutSegment(
                    start=round(curr, 2),
                    end=round(seg_end, 2),
                    reason=reasons[r_idx % len(reasons)]
                ))
                curr = seg_end
                r_idx += 1

            return LongFormEditPlan(
                target_duration_seconds=target_duration_seconds,
                estimated_duration=round(target, 2),
                narrative_arc=f"Narrative arc for {analysis.topic} with clear intro, core depth, and payoff",
                segments=curated
            )

        segments = [
            CutSegment(
                start=max(0.0, float(s["start"])),
                end=min(transcript.duration, float(s["end"])),
                reason=s.get("reason", "Curated narrative block")
            )
            for s in raw_segments if float(s.get("end", 0)) > float(s.get("start", 0))
        ]
        return LongFormEditPlan(
            target_duration_seconds=target_duration_seconds,
            estimated_duration=round(sum(s.end - s.start for s in segments), 2),
            narrative_arc=data.get("narrative_arc", "Curated long-form cut"),
            segments=segments
        )

    async def select_shorts(
        self,
        analysis: ContentAnalysis,
        transcript: Transcript,
        count: int = 5
    ) -> List[ShortCandidate]:
        prompt = f"Select {count} standalone Shorts (30-58s) with hooks from '{analysis.topic}'."
        schema = '{"shorts": [{"id": "short_01", "title": "string", "category": "hot_take", "hook": "string", "hook_start": 0.0, "hook_end": 3.0, "body_start": 0.0, "body_end": 45.0, "estimated_duration": 45.0, "score": 9.0, "reason": "string", "suggested_caption": "string"}]}'

        data = await self._query_ollama(prompt, schema)
        raw_shorts = data.get("shorts", [])

        if not raw_shorts or len(raw_shorts) < count:
            # Deterministic Shorts extraction across the timeline
            categories = ["hot_take", "technical_breakthrough", "story", "contrarian", "practical_tip"]
            step = max(45.0, transcript.duration / (count + 1))
            fallback_shorts: List[ShortCandidate] = []

            for i in range(count):
                b_start = min(transcript.duration - 35.0, max(0.0, (i + 0.5) * step))
                b_end = min(transcript.duration, b_start + 45.0)
                h_start = b_start
                h_end = min(transcript.duration, b_start + 4.0)

                # Find spoken words in that interval for authentic hook
                matching_words = [w.word for s in transcript.segments for w in s.words if b_start <= w.start <= h_end]
                hook_text = " ".join(matching_words[:8]) if matching_words else f"Important breakthrough in {analysis.topic}"

                fallback_shorts.append(ShortCandidate(
                    id=f"short_{i+1:02d}",
                    title=f"{analysis.topic}: Key Point #{i+1}",
                    category=categories[i % len(categories)],
                    hook=hook_text,
                    hook_start=round(h_start, 2),
                    hook_end=round(h_end, 2),
                    body_start=round(b_start, 2),
                    body_end=round(b_end, 2),
                    estimated_duration=round(b_end - b_start, 2),
                    score=round(9.0 - (i * 0.2), 1),
                    reason=f"Standalone segment delivering direct value on {analysis.topic}",
                    suggested_caption=f"Yeh point miss mat karna agar aap tech build karte ho! 🚀 #HinglishTech",
                    broll_suggestions=[f"Highlight key architecture of {analysis.topic}"]
                ))
            return fallback_shorts

        return [
            ShortCandidate(
                id=s.get("id", f"short_{i+1:02d}"),
                title=s.get("title", f"Short #{i+1}"),
                category=s.get("category", "technical_breakthrough"),
                hook=s.get("hook", ""),
                hook_start=float(s.get("hook_start", 0.0)),
                hook_end=float(s.get("hook_end", 3.0)),
                body_start=float(s.get("body_start", 0.0)),
                body_end=float(s.get("body_end", 45.0)),
                estimated_duration=float(s.get("estimated_duration", 45.0)),
                score=float(s.get("score", 8.5)),
                reason=s.get("reason", ""),
                suggested_caption=s.get("suggested_caption", ""),
                broll_suggestions=s.get("broll_suggestions", [])
            )
            for i, s in enumerate(raw_shorts[:count])
        ]

    async def generate_edit_plan(
        self,
        project_id: str,
        long_form: LongFormEditPlan,
        shorts: List[ShortCandidate],
        transcript: Transcript,
        silence_cuts: Optional[List[Dict[str, float]]] = None
    ) -> EditPlan:
        broll = [
            BRollItem(
                start=s.body_start,
                end=min(s.body_end, s.body_start + 4.0),
                suggestion=b,
                status="B-ROLL REQUIRED"
            )
            for s in shorts for b in s.broll_suggestions
        ]
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
        prompt = f"Generate Hinglish/English YouTube and Shorts metadata for '{project_name}'."
        schema = '{"long_form_title_options": ["string"], "long_form_description": "string", "long_form_tags": ["string"], "long_form_thumbnail_concept": "string", "shorts_metadata": [{"short_id": "short_01", "title": "string", "caption": "string", "hashtags": ["string"], "thumbnail_timestamp": 0.0}]}'

        data = await self._query_ollama(prompt, schema)

        titles = data.get("long_form_title_options") or [
            f"{project_name} — Complete Architecture Explained",
            f"The Truth About {project_name} in Production 🤯",
            f"Why Everyone is Wrong About {project_name}"
        ]

        desc = data.get("long_form_description") or (
            f"Deep dive into {project_name}. In this video, we break down real-world implementation insights and lessons learned.\n\n"
            f"📌 Chapters:\n0:00 - Introduction\n2:15 - Architecture\n5:40 - Gotchas & Pitfalls\n10:20 - Conclusion\n\n"
            f"#HinglishTech #SystemDesign #SoftwareEngineering #AI"
        )

        shorts_meta = [
            ShortMetadata(
                short_id=s.id,
                title=s.title,
                caption=f"{s.hook} | Watch till the end! 🚀",
                hashtags=["#Shorts", "#HinglishTech", "#Coding", "#Innovation"],
                thumbnail_timestamp=s.hook_start + 1.0,
                thumbnail_concept=f"Speaker reaction with big text: '{s.title[:20]}'"
            )
            for s in shorts
        ]

        return VideoMetadata(
            long_form_title_options=titles,
            long_form_description=desc,
            long_form_tags=data.get("long_form_tags") or ["AI", "HinglishTech", "SoftwareEngineering", "Python"],
            long_form_thumbnail_concept=data.get("long_form_thumbnail_concept") or f"Bold neon typography with key architecture graphic for {project_name}",
            shorts_metadata=shorts_meta
        )
