---
name: hinglish-content-producer
description: Specialized intelligence for processing, transcribing, and editing spoken conversational Hindi/Hinglish tech video content into 10-15 min long-form YouTube videos and 4-5 hook-driven Shorts/Reels with Roman-Hinglish captions.
---

# Hinglish Content Producer Skill

This skill defines the linguistic rules, content curation guidelines, captioning conventions, and hook-restructuring heuristics for conversational Hindi/Hinglish content creators.

---

## 1. Core Language Principles (Strict Hinglish Code-Switching)

### Never Translate to English
Conversational Hindi/Hinglish represents the authentic voice and rapport of the creator. Converting it to English strips its relatability and emotional resonance.
- **Spoken**: *"Agar aap production mein jaa rahe ho toh direct database query mat likho."*
- **Allowed**: Keep exact Hinglish phrasing.
- **Forbidden**: Translating to *"If you are going to production, do not write direct database queries."*

### Never Convert to Formal / Devanagari Hindi
Creators in Indian tech speak naturally code-switched Hindi-English, not Shuddh/Sanskritized Hindi.
- **Forbidden**: *"यदि आप उत्पादन में जा रहे हैं तो प्रत्यक्ष डेटाबेस..."*

### Strictly Preserve Technical Terminology
Never attempt to translate or phonetically garble technical computing terms:
- Common terms to keep verbatim: `AI`, `API`, `backend`, `frontend`, `React`, `Python`, `JavaScript`, `LangGraph`, `RAG`, `embeddings`, `vector database`, `Docker`, `Kubernetes`, `GitHub`, `state management`, `FastAPI`, `microservices`, `LLM`, `cache`, `latency`, `throughput`.

---

## 2. Roman-Hinglish Caption Formatting Rules

When generating subtitles for social media:
1. **Script**: Use Latin/Roman alphabet (Roman-Hinglish), never Devanagari.
2. **Punctuation**: Add clear commas and question marks to demarcate breath groups and conversational clauses.
3. **Capitalization**: Capitalize standard acronyms (`AI`, `API`, `SQL`, `UI`, `UX`) and the start of spoken clauses.
4. **Pacing**: Display 2–4 words per display line. Active word highlighted using karaoke ASS tags (`{\k<duration>}WORD`).
5. **No Clutter**: Remove verbal filler stuttering (*"uhh"*, *"matlab matlab"*) only if it distracts, but retain expressive conversational markers (*"basically"*, *"yaar"*, *"samjhe"*).

---

## 3. Long-Form Content Selection Heuristics (10–15 Minutes)

For raw conversational recordings:
1. **Identify Narrative Anchor**: Find where the speaker transitions from casual preamble to the core technical/business problem.
2. **Filter Redundancies**: Eliminate repetitive back-and-forth, system setup interruptions, or tangential rants that do not contribute to the central topic.
3. **Preserve Conversational Flow**: Ensure cuts between segments feel natural by joining on natural breath pauses rather than mid-word or mid-thought.
4. **Target Duration**: Aim for 10–15 minutes (600–900 seconds) of high-density insights.

---

## 4. 4–5 Standalone Shorts/Reels Selection & Hook Optimization

From the same recording, extract 4–5 viral short candidates (30–58 seconds):
1. **Categories**:
   - **Strong Opinion / Hot Take**: Unpopular truths, industry criticisms.
   - **Technical Breakthrough / Gotcha**: Subtle bugs, architectural pitfalls, best practices.
   - **Story / Personal Failure**: A real incident where something broke or a lesson was learned.
   - **Contrarian Advice**: Counter-intuitive tech recommendations.
   - **Practical Shortcut**: Actionable tips usable immediately.

2. **Hook Inversion Formula**:
   If the speaker explains context first and reveals the punchline later, re-order the Short:
   ```text
   [Punchline / Climax Sentence] (0–3s) ──> Hook
   [Context / Setup] (4–15s)
   [Technical Details / Story] (16–45s)
   [Resolution / CTA] (46–55s)
   ```
   *Strict Rule*: Only rearrange existing recorded sentences. Never fabricate spoken audio or words.

---

## 5. B-Roll & Visual Callout Protocols

When the speaker describes abstract technical concepts:
- Tag scene intervals with `broll_suggestion`.
- Mark as `B-ROLL REQUIRED` if no local asset is present.
- Suggested visuals:
  - Architecture diagrams (vector search flow, RAG pipeline, client-server sync).
  - Code snippets or terminal commands.
  - Interface screencasts or documentation references.
