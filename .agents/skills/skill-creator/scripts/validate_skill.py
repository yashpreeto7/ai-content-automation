import os
import sys
from pathlib import Path

def validate_skill(skill_dir: Path) -> bool:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        print(f"[FAIL] Missing SKILL.md in {skill_dir}")
        return False
        
    content = skill_md.read_text(encoding="utf-8")
    if not content.startswith("---"):
        print(f"[FAIL] {skill_md}: Frontmatter must start on line 1 with '---'")
        return False
        
    parts = content.split("---", 2)
    if len(parts) < 3:
        print(f"[FAIL] {skill_md}: Frontmatter not properly closed with '---'")
        return False
        
    # Parse simple yaml key-value without extra deps
    frontmatter_text = parts[1]
    name = None
    desc = None
    for line in frontmatter_text.splitlines():
        line = line.strip()
        if line.startswith("name:"):
            name = line.split("name:", 1)[1].strip().strip('"').strip("'")
        elif line.startswith("description:"):
            desc = line.split("description:", 1)[1].strip().strip('"').strip("'")
            
    if not name or name != skill_dir.name:
        print(f"[FAIL] {skill_md}: 'name' ({name}) must match folder name ({skill_dir.name})")
        return False
        
    if not desc or len(desc.strip()) < 15:
        print(f"[FAIL] {skill_md}: 'description' is missing or too short")
        return False
        
    print(f"[OK] Skill '{name}' is valid.")
    return True

if __name__ == "__main__":
    current_dir = Path(__file__).resolve().parent
    # scripts -> skill-creator -> skills -> .agents -> workspace_root
    workspace_root = current_dir.parents[3]
    skills_root = workspace_root / ".agents" / "skills"
    
    if not skills_root.exists():
        print(f"Skills root not found: {skills_root}")
        sys.exit(1)
        
    print(f"Validating skills in: {skills_root}")
    all_ok = True
    for item in sorted(skills_root.iterdir()):
        if item.is_dir():
            if not validate_skill(item):
                all_ok = False
                
    if all_ok:
        print("\n[SUCCESS] All skills passed validation!")
        sys.exit(0)
    else:
        print("\n[WARNING] Some skills failed validation.")
        sys.exit(1)
