import pytest
from src.core.models import (
    Transcript,
    TranscriptSegment,
    WordTiming,
    ContentAnalysis,
    LongFormEditPlan,
    ShortCandidate,
    EditPlan,
    VideoMetadata
)
from src.providers.factory import get_ai_provider
from src.providers.ollama_provider import OllamaProvider
from src.providers.gemini_provider import GeminiProvider

@pytest.fixture
def sample_transcript():
    words1 = [
        WordTiming(word="Basically", start=0.0, end=0.6),
        WordTiming(word="agar", start=0.7, end=1.0),
        WordTiming(word="aap", start=1.1, end=1.3),
        WordTiming(word="ek", start=1.4, end=1.6),
        WordTiming(word="AI", start=1.7, end=2.0),
        WordTiming(word="agent", start=2.1, end=2.5),
        WordTiming(word="bana", start=2.6, end=2.9),
        WordTiming(word="rahe", start=3.0, end=3.2),
        WordTiming(word="ho", start=3.3, end=3.5),
    ]
    words2 = [
        WordTiming(word="toh", start=3.6, end=3.8),
        WordTiming(word="state", start=3.9, end=4.3),
        WordTiming(word="management", start=4.4, end=5.0),
        WordTiming(word="ka", start=5.1, end=5.3),
        WordTiming(word="dhyan", start=5.4, end=5.8),
        WordTiming(word="rakhna", start=5.9, end=6.3),
        WordTiming(word="padega.", start=6.4, end=7.0),
    ]
    seg1 = TranscriptSegment(id=1, start=0.0, end=3.5, text="Basically agar aap ek AI agent bana rahe ho", words=words1)
    seg2 = TranscriptSegment(id=2, start=3.6, end=7.0, text="toh state management ka dhyan rakhna padega.", words=words2)
    return Transcript(
        language="hi",
        duration=120.0,
        full_text="Basically agar aap ek AI agent bana rahe ho toh state management ka dhyan rakhna padega.",
        segments=[seg1, seg2]
    )

def test_provider_factory():
    gemini = get_ai_provider("gemini")
    assert isinstance(gemini, GeminiProvider)
    ollama = get_ai_provider("ollama")
    assert isinstance(ollama, OllamaProvider)

@pytest.mark.asyncio
async def test_ollama_provider_schema_parity(sample_transcript):
    provider = OllamaProvider()
    
    # 1. Content Analysis
    analysis = await provider.analyze_content("dummy_path.mp4", sample_transcript, [])
    assert isinstance(analysis, ContentAnalysis)
    assert len(analysis.core_themes) > 0
    assert analysis.estimated_raw_duration == sample_transcript.duration

    # 2. Long-Form Selection
    long_form = await provider.select_long_form(analysis, sample_transcript, target_duration_seconds=60.0)
    assert isinstance(long_form, LongFormEditPlan)
    assert len(long_form.segments) > 0
    for seg in long_form.segments:
        assert seg.start >= 0.0
        assert seg.end <= sample_transcript.duration
        assert seg.end > seg.start

    # 3. Shorts Selection
    shorts = await provider.select_shorts(analysis, sample_transcript, count=4)
    assert isinstance(shorts, list)
    assert len(shorts) == 4
    for s in shorts:
        assert isinstance(s, ShortCandidate)
        assert s.hook_end >= s.hook_start
        assert s.body_end >= s.body_start
        assert s.score >= 1.0

    # 4. Edit Plan Synthesis
    edit_plan = await provider.generate_edit_plan("test_proj", long_form, shorts, sample_transcript)
    assert isinstance(edit_plan, EditPlan)
    assert edit_plan.project_id == "test_proj"

    # 5. Metadata
    metadata = await provider.generate_metadata("AI Agents Deep Dive", sample_transcript, long_form, shorts)
    assert isinstance(metadata, VideoMetadata)
    assert len(metadata.long_form_title_options) > 0
    assert len(metadata.shorts_metadata) == 4
