from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from src.core.models import (
    Transcript,
    ContentAnalysis,
    LongFormEditPlan,
    ShortCandidate,
    EditPlan,
    VideoMetadata
)

class AIProvider(ABC):
    """Abstract Base Class for AI Video Understanding and Edit Decision Providers."""

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Verifies API credentials or local service connectivity and model readiness."""
        pass

    @abstractmethod
    async def analyze_content(
        self,
        video_path: str,
        transcript: Transcript,
        keyframes: List[str]
    ) -> ContentAnalysis:
        """
        Analyzes the conversational recording, identifies core narrative topics,
        key insight moments, and flags weak/repetitive sections.
        """
        pass

    @abstractmethod
    async def select_long_form(
        self,
        analysis: ContentAnalysis,
        transcript: Transcript,
        target_duration_seconds: float = 720.0
    ) -> LongFormEditPlan:
        """
        Selects and orders narrative segments to form a cohesive 10-15 min long-form YouTube video.
        """
        pass

    @abstractmethod
    async def select_shorts(
        self,
        analysis: ContentAnalysis,
        transcript: Transcript,
        count: int = 5
    ) -> List[ShortCandidate]:
        """
        Identifies and extracts 4-5 high-performing standalone Shorts/Reels candidates.
        Applies hook optimization heuristics (restructuring punchline into opening hook if needed).
        """
        pass

    @abstractmethod
    async def generate_edit_plan(
        self,
        project_id: str,
        long_form: LongFormEditPlan,
        shorts: List[ShortCandidate],
        transcript: Transcript,
        silence_cuts: Optional[List[Dict[str, float]]] = None
    ) -> EditPlan:
        """
        Synthesizes the complete structured edit plan with cuts, B-roll suggestions,
        captions, and audio ducking specifications.
        """
        pass

    @abstractmethod
    async def generate_metadata(
        self,
        project_name: str,
        transcript: Transcript,
        long_form: LongFormEditPlan,
        shorts: List[ShortCandidate]
    ) -> VideoMetadata:
        """
        Generates authentic Hinglish/English YouTube and Shorts titles, descriptions,
        tags, hashtags, and thumbnail concepts.
        """
        pass
