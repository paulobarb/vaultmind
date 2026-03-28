# =============================================================
# vaultmind — tagger_logic.py
# =============================================================
# Shared tagging engine. Centralizes vault tag collection and 
# AI-based tag generation. 
# =============================================================

import re
import json
from pathlib import Path
from config import MAX_FILE_SIZE, VAULT_PATH
from core.ai_backend import call_ai

PROMPTS_PATH = Path(__file__).parent.parent / "prompts.json"

with PROMPTS_PATH.open(encoding="utf-8") as f:
    PROMPTS = json.load(f)

def format_tag(text: str) -> str:
    text = re.sub(r'^(tags?:|here are.*?:|output:)\s*', '', text, flags=re.IGNORECASE)
    
    text = text.lower().replace(" ", "-")
    return re.sub(r'[^\w-]', '', text)

def collect_vault_tags() -> list[str]:
    """Scans the vault to find every tag you've already used."""
    tags = set()
    vault = Path(VAULT_PATH).expanduser().resolve()
    for path_obj in vault.rglob("*.md"):
        try:
            if path_obj.stat().st_size > MAX_FILE_SIZE: 
                continue
            content = path_obj.read_text(encoding="utf-8", errors="ignore")
            
            # Match frontmatter tags
            fm = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if fm:
                for line in fm.group(1).splitlines():
                    m = re.match(r"\s*-\s*(.+)", line)
                    if m: 
                        tags.add(m.group(1).strip().lower())
            
            # Match inline #hashtags
            for t in re.findall(r"#([a-zA-Z][a-zA-Z0-9_/-]+)", content):
                tags.add(t.lower())
        except Exception: 
            continue
            
    return sorted([format_tag(t) for t in tags if format_tag(t)])

def get_ai_tags(content: str, existing_tags: list, backend: str) -> list[str]:
    """Ask the AI for a simple list of 3-4 relevant tags using the JSON prompt."""
    tags_hint = ", ".join(existing_tags[:80])
    
    # Use the JSON template
    template = PROMPTS["auto_tagger"]["prompt"]
    prompt = template.format(content=content[:4000], tags_hint=tags_hint)
    
    raw = call_ai(prompt, backend, temperature=0.0)
    
    # Clean up and split
    raw_list = raw.replace("\n", ",").split(",")
    ai_tags = [format_tag(t.strip()) for t in raw_list if t.strip()]
    
    final_tags = sorted(list(set([t for t in ai_tags if t])))[:4]
    return final_tags if final_tags else ["untagged"]