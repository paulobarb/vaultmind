# =============================================================
# vaultmind — auto_tagger.py
# =============================================================
# Scans the vault for notes missing structural tags (no frontmatter, 
# missing 'tags' key, or empty tags list) and automatically 
# generates them using AI based on the note's content.
# =============================================================

import sys
import re
import yaml
from pathlib import Path
from config import VAULT_PATH, EXCLUDED_FOLDERS
from core.ai_backend import get_backend, run_startup_checks
from core.tagger_logic import collect_vault_tags, get_ai_tags

# --- SETUP & PATHS ---
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

# --- COLORS ---
CYAN, GREEN, YELLOW, DIM, BOLD, RESET = "\033[96m", "\033[92m", "\033[93m", "\033[2m", "\033[1m", "\033[0m"
RED = "\033[31m"

def has_no_tags(content: str) -> bool:
    """
    Checks if a note is missing tags structurally.
    Returns True if:
    1. No frontmatter exists.
    2. Frontmatter exists but has no 'tags' key.
    3. Frontmatter has 'tags' but it's empty.
    """
    fm_match = re.match(r'^---(.*?)---', content, re.DOTALL)
    if not fm_match:
        return True
        
    try:
        data = yaml.safe_load(fm_match.group(1))
        if not data or 'tags' not in data:
            return True
        if not data['tags'] or len(data['tags']) == 0:
            return True
        return False
    except Exception:
        return True # If YAML is broken, consider it "untagged"

def process_note(path: Path, existing_tags: list, backend: str):
    """Adds tags while preserving existing non-tag properties (word, link, etc)."""
    content = path.read_text(encoding="utf-8", errors="ignore")
    
    # Separate Frontmatter and Body
    fm_match = re.match(r'^---(.*?)---', content, re.DOTALL)
    if fm_match:
        try:
            metadata = yaml.safe_load(fm_match.group(1)) or {}
        except:
            metadata = {}
        body = content[fm_match.end():].strip()
    else:
        metadata = {}
        body = content.strip()

    # Get AI Tags
    print(f"    {DIM}· Consulting AI...{RESET}", end="\r")
    ai_suggestions = get_ai_tags(body, existing_tags, backend)
    
    # Filter out technical loop-terms
    final_tags = [t for t in ai_suggestions if t.lower() != "untagged"]
    if not final_tags: final_tags = ["needs-review"]

    # Update Metadata
    metadata['tags'] = final_tags
    
    # Rebuild File
    new_fm = yaml.dump(metadata, sort_keys=False, allow_unicode=True).strip()
    new_content = f"---\n{new_fm}\n---\n\n{body}"
    
    path.write_text(new_content, encoding="utf-8")
    print(f"    {GREEN}· Applied: {BOLD}{', '.join(final_tags)}{RESET}")

def main():
    backend = get_backend()
    run_startup_checks()
    vault = Path(VAULT_PATH).expanduser().resolve()

    print(f"\n{CYAN}{BOLD}VAULT TAG MANAGER{RESET}")
    print(f"{DIM}1. Auto-tag all notes missing properties/tags{RESET}")
    print(f"{DIM}2. Tag a specific note by name{RESET}")
    
    choice = input(f"\n{YELLOW}Select > {RESET}").strip()
    existing_tags = collect_vault_tags()

    if choice == '1':
        targets = []
        for p in vault.rglob("*.md"):
            if any(skip in str(p) for skip in EXCLUDED_FOLDERS): continue
            content = p.read_text(encoding="utf-8", errors="ignore")
            
            if has_no_tags(content):
                targets.append(p)

        if not targets:
            print(f"{GREEN}All notes are properly tagged!{RESET}\n"); return

        print(f"{DIM}• Found {len(targets)} note(s) missing tags. Processing...{RESET}")
        for i, path in enumerate(targets):
            print(f"  {CYAN}[{i+1}/{len(targets)}]{RESET} {BOLD}{path.name}{RESET}")
            process_note(path, existing_tags, backend)
            
        print(f"\n{GREEN}Vault tagging complete.{RESET}\n")

    elif choice == '2':
        query = input(f"{YELLOW}Enter filename > {RESET}").strip()
        clean_query = query[:-3].lower() if query.lower().endswith(".md") else query.lower()
        target_path = next((p for p in vault.rglob("*.md") if p.stem.lower() == clean_query), None)
        
        if target_path:
            process_note(target_path, existing_tags, backend)
        else:
            print(f"{RED}File not found.{RESET}")

if __name__ == "__main__":
    main()