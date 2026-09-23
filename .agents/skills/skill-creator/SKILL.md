---
name: skill-creator
description: Comprehensive framework and toolchain for creating, validating, and publishing agent skills in the Antigravity ecosystem. Use when authoring new skills, standardizing SKILL.md frontmatter, adding reference scripts, or packaging workflows into reusable capabilities.
---

# Skill Creator & Standardizer

This skill guides the design, structure, validation, and authoring of new skills for the Antigravity agent system and AI Content Automation workspace.

---

## 1. Skill Architecture Overview

Every skill in `.agents/skills/<skill-name>/` must adhere to the Antigravity skill specification:

```
.agents/skills/<skill-name>/
├── SKILL.md                 # REQUIRED: Main entrypoint with YAML frontmatter & markdown instructions
├── scripts/                 # OPTIONAL: Executable helper scripts (Python, Bash, PowerShell)
├── references/              # OPTIONAL: Detailed documentation, API schemas, design specs
└── examples/                # OPTIONAL: Code samples, test cases, and input/output fixtures
```

### Frontmatter Schema (YAML)
The top of every `SKILL.md` must contain valid YAML frontmatter:

```yaml
---
name: my-skill-name
description: Clear, concise description explaining what this skill does and when the agent should activate it. Include specific triggers and primary capabilities.
user-invocable: true       # Optional: true if user can invoke via /slash command
---
```

**Naming Rules**:
- Lowercase alphanumeric characters and hyphens only (`a-z`, `0-9`, `-`).
- Must match the directory name exactly (e.g. `video-processing/SKILL.md` $\to$ `name: video-processing`).
- Be descriptive and actionable.

**Description Guidelines**:
- Must state **what** the skill provides and **when** an agent should activate it.
- Include trigger keywords (e.g. "Use when assembling video clips, burning captions...").

---

## 2. Standard SKILL.md Structure

A production-grade `SKILL.md` should contain the following standard sections:

1. **Title & Purpose**: High-level explanation of the skill's domain and objective.
2. **Core Capabilities**: Enumerated list of what the skill empowers the agent to do.
3. **Workflows & Code Recipes**: Copy-pasteable, verified CLI commands or Python code patterns.
4. **Best Practices & Guardrails**: Error handling, edge cases, rate limits, performance optimizations.
5. **Verification & Testing**: Commands or criteria to verify the skill's execution.

---

## 3. Step-by-Step Skill Authoring Protocol

### Step 1: Identify the Workflow Need
- Determine the scope, dependencies (libraries, CLI tools, API keys), and trigger conditions.

### Step 2: Create the Directory Structure
```powershell
New-Item -ItemType Directory -Path ".agents/skills/<skill-name>" -Force
New-Item -ItemType Directory -Path ".agents/skills/<skill-name>/scripts" -Force
```

### Step 3: Author the `SKILL.md`
- Draft the frontmatter ensuring valid YAML (`name` and `description`).
- Provide concrete, production-ready code examples with typed signatures and docstrings.

### Step 4: Validate Frontmatter & Syntax
Run the validator script to verify that:
- YAML frontmatter starts with `---` on line 1.
- `name` is present and matches the folder name.
- `description` is non-empty and contains trigger guidance.
- All code blocks have valid language identifiers (`python`, `bash`, `powershell`, `json`, `mermaid`).

### Step 5: Register the Skill
- Add the new skill to the skill catalog table in [AGENTS.md](file:///c:/Users/Yashpreet_o7/Desktop/ai-content-automation/AGENTS.md).
- Reference the new skill in [GEMINI.md](file:///c:/Users/Yashpreet_o7/Desktop/ai-content-automation/GEMINI.md) if applicable.

---

## 4. Automated Skill Validator Script

Save this validator utility in `.agents/skills/skill-creator/scripts/validate_skill.py`:

```python
import os
import sys
import yaml
from pathlib import Path

def validate_skill(skill_dir: Path) -> bool:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        print(f"❌ Missing SKILL.md in {skill_dir}")
        return False
        
    content = skill_md.read_text(encoding="utf-8")
    if not content.startswith("---"):
        print(f"❌ {skill_md}: Frontmatter must start on line 1 with '---'")
        return False
        
    parts = content.split("---", 2)
    if len(parts) < 3:
        print(f"❌ {skill_md}: Frontmatter not properly closed with '---'")
        return False
        
    try:
        meta = yaml.safe_load(parts[1])
    except Exception as e:
        print(f"❌ {skill_md}: Invalid YAML frontmatter: {e}")
        return False
        
    name = meta.get("name")
    desc = meta.get("description")
    
    if not name or name != skill_dir.name:
        print(f"❌ {skill_md}: 'name' ({name}) must match folder name ({skill_dir.name})")
        return False
        
    if not desc or len(desc.strip()) < 20:
        print(f"❌ {skill_md}: 'description' is missing or too short")
        return False
        
    print(f"✅ Skill '{name}' is valid.")
    return True

if __name__ == "__main__":
    skills_root = Path(".agents/skills")
    success = True
    for item in skills_root.iterdir():
        if item.is_dir():
            if not validate_skill(item):
                success = False
    sys.exit(0 if success else 1)
```
