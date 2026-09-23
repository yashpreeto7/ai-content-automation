import os
import json
from typing import Optional, List
from src.core.config import settings
from src.core.models import Script, Scene, SocialPackage

class ScriptGenerator:
    """Generates viral, high-retention video scripts and visual scene breakdowns."""

    @classmethod
    def generate(cls, topic: str, style: str = "cinematic", target_duration: float = 45.0) -> Script:
        """Generates a complete hook-driven script with timed visual prompts."""
        gemini_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")

        if gemini_key:
            try:
                return cls._generate_with_gemini(topic, style, target_duration, gemini_key)
            except Exception as e:
                print(f"[ScriptGenerator] Gemini API error ({e}). Falling back to heuristic generator.")

        return cls._generate_heuristic_script(topic, style, target_duration)

    @classmethod
    def _generate_with_gemini(cls, topic: str, style: str, target_duration: float, api_key: str) -> Script:
        """Calls Google Gemini model with structured JSON output instructions."""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        target_words = int((target_duration / 60.0) * 155)  # 155 WPM average

        system_instruction = (
            "You are an elite short-form content producer. Create high-retention, "
            "viral video scripts for 9:16 Shorts/Reels/TikTok. Follow this strict formula:\n"
            "1. Hook (0-3s): Irresistible question, counter-intuitive statement, or curiosity gap.\n"
            "2. Retain (4-40s): 3-4 dense, fascinating value points with rapid visual transitions every 3 seconds.\n"
            "3. Payoff & CTA (41-45s): Mind-expanding synthesis and high-converting CTA.\n"
            "Return valid JSON matching the requested schema."
        )

        prompt = f"""
Topic: "{topic}"
Visual Style: {style}
Target Duration: ~{int(target_duration)} seconds (~{target_words} words total).

Return a JSON object with this exact structure:
{{
  "topic": "{topic}",
  "style": "{style}",
  "hook": "Punchy 1-sentence hook that shocks the viewer",
  "body_points": ["First mind-blowing point", "Second fascinating development", "Third surprising fact"],
  "cta": "Engaging final thought and call-to-action",
  "full_text": "The entire narration script written out continuously as spoken speech without timestamps or stage directions.",
  "estimated_duration": {target_duration},
  "scenes": [
    {{
      "scene_index": 1,
      "text_segment": "Spoken words for this 3-4 second cut",
      "visual_prompt": "Cinematic 8k B-roll prompt with lighting, lens angle, and motion vector",
      "duration_seconds": 3.5
    }}
  ]
}}
"""
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json"
            )
        )

        data = json.loads(response.text)
        scenes = [Scene(**s) for s in data.get("scenes", [])]
        return Script(
            topic=data.get("topic", topic),
            style=data.get("style", style),
            hook=data.get("hook", ""),
            body_points=data.get("body_points", []),
            cta=data.get("cta", ""),
            full_text=data.get("full_text", ""),
            scenes=scenes,
            estimated_duration=data.get("estimated_duration", target_duration)
        )

    @classmethod
    def _generate_heuristic_script(cls, topic: str, style: str, target_duration: float) -> Script:
        """Generates a structured viral script without external API dependencies."""
        hook = f"Everything you think you know about {topic} is about to change."
        p1 = f"Deep research reveals that {topic} is accelerating faster than almost anyone anticipated."
        p2 = f"The hidden architecture beneath it operates on principles that defy conventional wisdom."
        p3 = f"Those who master this early will hold an extraordinary strategic advantage over everyone else."
        cta = f"Follow for the next breakthrough in {topic}, and let us know your perspective below."

        full_text = f"{hook} {p1} {p2} {p3} {cta}"

        # Break into 5 timed scenes (~3.5 seconds each)
        scenes = [
            Scene(
                scene_index=1,
                text_segment=hook,
                visual_prompt=f"Cinematic close-up macro visual related to {topic}, pulsing neon lighting, shallow depth of field, 8k resolution, slow push in.",
                duration_seconds=4.0
            ),
            Scene(
                scene_index=2,
                text_segment=p1,
                visual_prompt=f"Epic sweeping panoramic view representing {topic}, atmospheric volumetric haze, anamorphic lens, high contrast color grade.",
                duration_seconds=4.0
            ),
            Scene(
                scene_index=3,
                text_segment=p2,
                visual_prompt=f"Complex geometric data streams and holographic nodes visualizing {topic}, cybernetic aesthetic, dynamic orbiting camera.",
                duration_seconds=4.0
            ),
            Scene(
                scene_index=4,
                text_segment=p3,
                visual_prompt=f"Golden hour dramatic silhouette looking out over a futuristic skyline, representing mastery in {topic}, 35mm film grain.",
                duration_seconds=4.0
            ),
            Scene(
                scene_index=5,
                text_segment=cta,
                visual_prompt=f"High-tech glowing interface seamlessly resolving into an elegant conclusion, minimalist typography, moody lighting.",
                duration_seconds=4.0
            ),
        ]

        return Script(
            topic=topic,
            style=style,
            hook=hook,
            body_points=[p1, p2, p3],
            cta=cta,
            full_text=full_text,
            scenes=scenes,
            estimated_duration=round(sum(s.duration_seconds for s in scenes), 1)
        )

    @classmethod
    def generate_social_package(cls, script: Script) -> SocialPackage:
        """Generates title variations, SEO description, and hashtags."""
        clean_topic = script.topic.replace('"', '').strip()
        titles = [
            f"The Unspoken Truth About {clean_topic} 🤯",
            f"Why {clean_topic} Will Change Everything in 2026",
            f"3 Secrets of {clean_topic} Nobody Told You"
        ]

        tag_topic = "".join(word.capitalize() for word in clean_topic.split() if word.isalnum())[:20]
        hashtags = [
            f"#{tag_topic}", "#Innovation", "#Technology", "#Future", "#Shorts",
            "#MindBlowing", "#DeepDive", "#ViralVideo", "#TechNews", "#DidYouKnow"
        ]

        description = (
            f"Explore the reality behind {clean_topic}. "
            f"In this breakdown, we reveal the core mechanisms and strategic insights shaping the future.\n\n"
            f"📌 Timestamps:\n0:00 - The Hook\n0:05 - The Breakthrough\n0:20 - The Shift\n0:35 - What It Means For You\n\n"
            + " ".join(hashtags)
        )

        thumbnail_prompt = (
            f"Hyper-detailed YouTube thumbnail: Shocking glowing visual concept of {clean_topic}, "
            f"intense facial expression in dramatic lighting, glowing cybernetic accents, bold vibrant colors, 8k octane render."
        )

        return SocialPackage(
            title_options=titles,
            description=description,
            hashtags=hashtags,
            thumbnail_prompt=thumbnail_prompt
        )
