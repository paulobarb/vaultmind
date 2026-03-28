# =============================================================
# vaultmind — study_recap.py
# =============================================================
# Run this after a study session. It auto-detects notes you
# recently modified, lets you confirm or adjust the list, then
# generates a structured recap with key concepts and review
# questions for spaced repetition.
#
# Output: Vault/Study Recaps/YYYY-MM-DD HH-MM Recap — NoteName.md
# =============================================================

from pathlib import Path
import sys
import json
import datetime
import re

from config import EXCLUDED_FOLDERS, MAX_FILE_SIZE, VAULT_PATH, HOURS_BACK, MAX_NOTE_CHARS, TEMPERATURES, RECAP_TITLE_FORMAT, STUDY_DIR_NAME
from core.ai_backend import get_backend, call_ai, run_startup_checks

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

VAULT_PATH   = Path(VAULT_PATH).expanduser().resolve()
RECAP_FOLDER = VAULT_PATH / STUDY_DIR_NAME
RECAP_FOLDER.mkdir(parents=True, exist_ok=True)

# --- COLORS ---
CYAN, GREEN, YELLOW, DIM, BOLD, RESET = "\033[96m", "\033[92m", "\033[93m", "\033[2m", "\033[1m", "\033[0m"
RED = "\033[31m"

# load all prompts from the shared prompts.json file
PROMPTS_PATH = SCRIPT_DIR / "prompts.json"
with PROMPTS_PATH.open(encoding="utf-8") as f:
    PROMPTS = json.load(f)

TEMP_RECAP = TEMPERATURES.get("recap") or TEMPERATURES.get("default") or 0.2

GROUNDING  = PROMPTS["grounding"]

def format_obsidian_tag(text: str) -> str:
    text = text.lower().replace(" ", "-")
    return re.sub(r'[^a-z0-9_-]', '', text)

def fill_prompt(template: str, **kwargs) -> str:
    result = template
    for key, value in kwargs.items():
        result = result.replace("{" + key + "}", str(value))
    return result

def find_recent_notes(hours: int) -> list[dict]:
    cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)
    found  = []
    all_files = sorted(
        VAULT_PATH.rglob("*.md"),
        key=lambda p: p.stat().st_mtime if p.exists() else 0,
        reverse=True
    )
    
    for path_obj in all_files:
        if any(skip in str(path_obj) for skip in EXCLUDED_FOLDERS):
            continue
        try:
            mtime = datetime.datetime.fromtimestamp(path_obj.stat().st_mtime)
            if mtime >= cutoff:
                found.append({
                    "name":  path_obj.name,
                    "path":  path_obj,
                    "mtime": mtime,
                })
        except OSError:
            continue
    return found

def index_all_notes() -> dict[str, str]:
    notes = {}
    for path_obj in VAULT_PATH.rglob("*.md"):
        try:
            if path_obj.stat().st_size > MAX_FILE_SIZE:
                continue
            content = path_obj.read_text(encoding="utf-8", errors="ignore")[:2000]
            notes[path_obj.stem] = content
        except Exception:
            continue
    return notes

def select_notes_interactively(auto_detected: list[dict]) -> list[dict]:
    print(f"\n{BOLD}Auto-detected notes (last {HOURS_BACK}h):{RESET}")
    selected = list(auto_detected)

    if not selected:
        print(f"  {DIM}None found.{RESET}")
    else:
        for i, n in enumerate(selected):
            print(f"  {GREEN}{i+1}.{RESET} {n['name']} {DIM}({n['mtime'].strftime('%H:%M')}){RESET}")

    print(f"\n{DIM}Commands: add <file.md>, rm <number>, done{RESET}")

    vault_index = {path.name.lower(): path for path in VAULT_PATH.rglob("*.md")}

    while True:
        try:
            cmd = input(f"{CYAN}Select > {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if cmd.lower() in ("done", ""):
            break
        elif cmd.startswith("add "):
            target_filename = cmd[4:].strip().lower()
            if not target_filename.endswith(".md"): 
                target_filename += ".md"
            if target_filename in vault_index:
                path_obj  = vault_index[target_filename]
                real_filename = path_obj.name
                mtime = datetime.datetime.fromtimestamp(path_obj.stat().st_mtime)
                if real_filename not in [n["name"] for n in selected]:
                    selected.append({"name": real_filename, "path": path_obj, "mtime": mtime})
                    print(f"  {GREEN}Added:{RESET} {real_filename}")
                else:
                    print(f"  {DIM}Already in list.{RESET}")
            else:
                print(f"  {RED}Not found: {target_filename}{RESET}")
        elif cmd.startswith("rm "):
            try:
                idx     = int(cmd[3:].strip()) - 1
                removed = selected.pop(idx)
                print(f"  {YELLOW}Removed:{RESET} {removed['name']}")
                for i, n in enumerate(selected):
                    print(f"  {GREEN}{i+1}.{RESET} {n['name']}")
            except (ValueError, IndexError):
                print(f"  {RED}Invalid number.{RESET}")
        else:
            print(f"{DIM}Unknown command.{RESET}")

    return selected

def generate_recap(notes_data: list[dict], all_notes: dict, backend: str) -> str:
    notes_block = "\n\n---\n\n".join(
        f"### {n['name']}\n{n['content']}" for n in notes_data
    )
    all_titles = ", ".join(list(all_notes.keys())[:100])
    prompt = fill_prompt(
        PROMPTS["study_recap"]["prompt"],
        grounding=GROUNDING,
        notes_block=notes_block,
        all_titles=all_titles,
    )
    return call_ai(prompt, backend, temperature=TEMP_RECAP)

def write_recap(content: str, note_names: list[str]) -> str:
    RECAP_FOLDER.mkdir(parents=True, exist_ok=True)
    date_str  = datetime.datetime.now().strftime("%Y-%m-%d")
    time_str  = datetime.datetime.now().strftime("%Hh%M")
    stems = [Path(n).stem for n in note_names]
    
    if len(stems) == 1: 
        subject = stems[0]
    elif len(stems) == 2: 
        subject = f"{stems[0]} & {stems[1]}"
    else: 
        subject = f"{stems[0]}, {stems[1]} (+{len(stems)-2})"

    safe_subject = re.sub(r'[\\/*?:"<>|]', "", subject)
    filename   = RECAP_TITLE_FORMAT.format(date=date_str, time=time_str, subject=safe_subject)
    filepath   = RECAP_FOLDER / filename

    tags_lines = [f"  - {format_obsidian_tag(s)}" for s in stems[:5]]
    fm_lines = (
        ["---", f"creation date: {date_str}", "tags:", "  - study-recap", "  - review"]
        + tags_lines
        + ["---", "", ""]
    )
    filepath.write_text("\n".join(fm_lines) + content, encoding="utf-8")
    return filepath

def main():
    backend = get_backend()
    run_startup_checks()

    print(f"\n{CYAN}{BOLD}STUDY RECAP{RESET}")
    print(f"{DIM}Vault:   {VAULT_PATH}{RESET}")

    auto_detected = find_recent_notes(HOURS_BACK)
    selected      = select_notes_interactively(auto_detected)

    if not selected:
        print(f"\n{RED}No notes selected. Exiting.{RESET}\n")
        sys.exit(0)

    print(f"{DIM}• Loading selected note(s)...{' '*10}{RESET}", end="\r")
    notes_data = []
    for n in selected:
        content = n["path"].read_text(encoding="utf-8", errors="ignore")
        notes_data.append({"name": n["name"], "content": content[:MAX_NOTE_CHARS]})

    print(f"{DIM}• Indexing vault for connections...{' '*10}{RESET}", end="\r")
    all_notes = index_all_notes()

    print(f"{DIM}• Generating recap...{' '*20}{RESET}", end="\r")
    content  = generate_recap(notes_data, all_notes, backend)
    filepath = write_recap(content, [n["name"] for n in selected])

    print(" " * 50, end="\r")
    print(f"{GREEN}│ Recap Saved:{RESET} {filepath.name}\n")

if __name__ == "__main__":
    main()