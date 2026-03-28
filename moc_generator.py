# =============================================================
# vaultmind — moc_generator.py
# =============================================================
# Multi-Strategy Map of Content (MOC) Generator.
# Organizes notes via Tags, Anchor Links, or Folder Structures.
# =============================================================

import sys
import re
import json
import datetime
from pathlib import Path
from config import VAULT_PATH, EXCLUDED_FOLDERS, MOC_DIR_NAME, MOC_TITLE_FORMAT
from core.ai_backend import get_backend, call_ai, run_startup_checks

# --- SETUP & PATHS ---
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

# --- LOAD PROMPTS ---
PROMPTS_PATH = SCRIPT_DIR / "prompts.json"
with PROMPTS_PATH.open(encoding="utf-8") as f:
    PROMPTS = json.load(f)

# --- COLORS & CONSTANTS ---
CYAN, GREEN, YELLOW, DIM, BOLD, RESET = "\033[96m", "\033[92m", "\033[93m", "\033[2m", "\033[1m", "\033[0m"
RED = "\033[31m"

VAULT = Path(VAULT_PATH).expanduser().resolve()
MOC_FOLDER = VAULT / MOC_DIR_NAME

# =============================================================
# SEARCH STRATEGIES
# =============================================================

def get_all_notes() -> list[Path]:
    notes = []
    for path in VAULT.rglob("*.md"):
        path_str = str(path)
        if any(skip in path_str for skip in EXCLUDED_FOLDERS):
            continue
        if MOC_DIR_NAME in path.parts:
            continue
        notes.append(path)
    return notes

def find_by_tag(topic: str) -> list[dict]:
    relevant = []
    search_term = topic.replace("#", "").lower()
    for path in get_all_notes():
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            if search_term in content.lower() or search_term in path.name.lower():
                relevant.append({"title": path.stem, "snippet": content[:400]})
        except Exception:
            continue
    return relevant

def find_by_anchor(anchor_title: str) -> list[dict]:
    relevant = []
    anchor_title_clean = anchor_title.replace(".md", "")
    link_pattern = re.compile(r"\[\[([^|\]]+).*?\]\]")
    outgoing_links = set()

    anchor_found = False
    for path in get_all_notes():
        if path.stem.lower() == anchor_title_clean.lower():
            anchor_found = True
            content = path.read_text(encoding="utf-8", errors="ignore")
            matches = link_pattern.findall(content)
            outgoing_links.update([m.strip() for m in matches])
            break

    if not anchor_found:
        print(f"{RED}Could not find an anchor note named '{anchor_title_clean}'.{RESET}")
        return []

    for path in get_all_notes():
        if path.stem.lower() == anchor_title_clean.lower():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            is_incoming = f"[[{anchor_title_clean}]]" in content or f"[[{anchor_title_clean}|" in content
            is_outgoing = path.stem in outgoing_links

            if is_incoming or is_outgoing:
                relevant.append({"title": path.stem, "snippet": content[:400]})
        except Exception:
            continue
    return relevant

def find_by_folder(folder_rel_path: str) -> list[dict]:
    relevant = []
    target_folder = VAULT / folder_rel_path
    if not target_folder.exists() or not target_folder.is_dir():
        print(f"{RED}Folder not found: {target_folder}{RESET}")
        return []

    for path in target_folder.rglob("*.md"):
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            relevant.append({"title": path.stem, "snippet": content[:400]})
        except Exception:
            continue
    return relevant

# =============================================================
# AI GENERATION
# =============================================================

def generate_moc_content(topic: str, context_type: str, notes: list, backend: str) -> str:
    notes_data = "\n".join([f"TITLE: {n['title']} | SNIPPET: {n['snippet']}" for n in notes])

    if context_type == "anchor":
        context_prompt = "These notes are part of a localized graph cluster connected to the anchor note."
    elif context_type == "folder":
        context_prompt = "These notes reside in the same directory. Create a structured index for this folder."
    else:
        context_prompt = "These notes share a common theme or tag."

    template = PROMPTS["moc_generator"]["prompt"]
    prompt = template.format(
        topic=topic,
        context_prompt=context_prompt,
        notes_data=notes_data
    )

    return call_ai(prompt, backend, temperature=0.1)

# =============================================================
# MAIN INTERFACE
# =============================================================

def main():
    backend = get_backend()
    run_startup_checks()

    print(f"\n{CYAN}{BOLD}VAULT MOC ARCHITECT{RESET}")
    print(f"{DIM}1. Search by Tag/Keyword (e.g., #productivity){RESET}")
    print(f"{DIM}2. Anchor Note Graph (e.g., Docker Overview){RESET}")
    print(f"{DIM}3. Folder Index (e.g., Projects/BoxdMetrics){RESET}")

    choice = input(f"\n{YELLOW}Select strategy (1/2/3) > {RESET}").strip()

    if choice == '1':
        topic = input(f"{YELLOW}Enter Keyword/Tag > {RESET}").strip()
        print(f"{DIM}• Scanning vault for '{topic}'...{RESET}", end="\r")
        notes = find_by_tag(topic)
        context_type = "tag"
        filename_base = topic.replace('#', '')

    elif choice == '2':
        topic = input(f"{YELLOW}Enter Exact Anchor Note Title > {RESET}").strip()
        print(f"{DIM}• Mapping connections for '[[{topic}]]'...{RESET}", end="\r")
        notes = find_by_anchor(topic)
        context_type = "anchor"
        filename_base = f"{topic} Network"

    elif choice == '3':
        topic = input(f"{YELLOW}Enter Folder Path (relative to Vault) > {RESET}").strip()
        print(f"{DIM}• Reading contents of '{topic}/'...{RESET}", end="\r")
        notes = find_by_folder(topic)
        context_type = "folder"
        filename_base = Path(topic).name

    else:
        print(f"{RED}Invalid choice.{RESET}")
        sys.exit(1)

    if not notes:
        print(f"\n{RED}No notes found for this query.{RESET}\n")
        return

    print(f"{DIM}• Organizing {len(notes)} notes into an MOC...{' '*15}{RESET}")
    moc_body = generate_moc_content(topic, context_type, notes, backend)

    # --- FILENAME GENERATION ---
    MOC_FOLDER.mkdir(parents=True, exist_ok=True)

    # Sanitize and format the title
    clean_title = re.sub(r'[\\/*?:"<>|]', "", filename_base).title()
    final_title = MOC_TITLE_FORMAT.format(title=clean_title)
    filepath = MOC_FOLDER / f"{final_title}.md"

    # --- SAVE ---
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    frontmatter = f"---\ntags:\n  - moc\ncreated: {now}\n---\n\n# {final_title}\n\n"

    filepath.write_text(frontmatter + moc_body, encoding="utf-8")

    print(f"{DIM}{'─'*45}{RESET}")
    print(f"{GREEN}│ Map Created: {final_title}.md{RESET}")
    print(f"{DIM}│ Check the '{MOC_DIR_NAME}' folder.{RESET}\n")


if __name__ == "__main__":
    main()