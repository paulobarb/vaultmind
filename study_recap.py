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

from config import EXCLUDED_FOLDERS, MAX_FILE_SIZE, VAULT_PATH, HOURS_BACK, MAX_NOTE_CHARS
from ai_backend import get_backend, call_ai, backend_label, run_startup_checks

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

VAULT_PATH  = Path(VAULT_PATH).expanduser().resolve()
RECAP_FOLDER = VAULT_PATH / "Study Recaps"

PROMPTS_PATH = SCRIPT_DIR / "prompts.json"
with PROMPTS_PATH.open(encoding="utf-8") as f:
    PROMPTS = json.load(f)

GROUNDING = PROMPTS["grounding"]

R      = "\033[0m"
DIM    = "\033[2m"
BOLD   = "\033[1m"
CYAN   = "\033[36m"
PURPLE = "\033[35m"
GREEN  = "\033[32m"
RED    = "\033[31m"
YELLOW = "\033[33m"

def format_obsidian_tag(text: str) -> str:
    """
    Limpa uma string para ser uma tag válida no Obsidian.
    - Transforma em minúsculas
    - Substitui espaços por hifens
    - Remove tudo que não for letra, número, '-' ou '_'
    """

    text = text.lower().replace(" ", "-")

    return re.sub(r'[^a-z0-9_-]', '', text)


def fill_prompt(template: str, **kwargs) -> str:
    """
    Safe placeholder replacement that won't crash on literal { } in the template.
    Uses simple string replacement instead of Python's .format().
    """
    result = template
    for key, value in kwargs.items():
        result = result.replace("{" + key + "}", str(value))
    return result


def find_recent_notes(hours: int) -> list[dict]:
    """
    Find notes modified within the last `hours` hours.
    Skips folders listed in EXCLUDED_FOLDERS from config.py.

    Args:
        hours: How many hours back to look.

    Returns:
        List of note dicts with 'name', 'path', and 'mtime' keys.
    """
    cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)
    found  = []

    base_path = Path(VAULT_PATH).expanduser().resolve()

    all_files = sorted(
        base_path.rglob("*.md"),
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
    """
    Build an index of all notes in the vault for connection finding.
    Only reads the first 500 chars of each note to keep memory usage low.
    """
    notes = {}
    for path_obj in VAULT_PATH.rglob("*.md"):
        try:
            if path_obj.stat().st_size > MAX_FILE_SIZE:
                continue
            content = path_obj.read_text(encoding="utf-8", errors="ignore")[:500]
            notes[path_obj.stem] = content
        except Exception:
            continue
    return notes


def select_notes_interactively(auto_detected: list[dict]) -> list[dict]:
    """
    Show auto-detected notes and let the user confirm, add, or remove them.

    Commands:
        add filename.md  — add a note
        rm <number>      — remove a note
        done             — proceed
    """
    print(f"\n{BOLD}auto-detected notes (modified in last {HOURS_BACK}h):{R}")
    selected = list(auto_detected)

    if not selected:
        print(f"  {DIM}none found{R}")
    else:
        for i, n in enumerate(selected):
            print(f"  {GREEN}{i+1}.{R} {n['name']} {DIM}({n['mtime'].strftime('%H:%M')}){R}")

    print(f"\n{DIM}commands:{R}")
    print(f"  {DIM}add filename.md  → add a note{R}")
    print(f"  {DIM}rm <number>      → remove a note{R}")
    print(f"  {DIM}done             → start generating{R}\n")

    vault_index = {path.name.lower(): path for path in VAULT_PATH.rglob("*.md")}

    while True:
        try:
            cmd = input(f"{CYAN}> {R}").strip()
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
                note  = {"name": real_filename, "path": path_obj, "mtime": mtime}
                if real_filename not in [n["name"] for n in selected]:
                    selected.append(note)
                    print(f"  {GREEN}added: {real_filename}{R}")
                else:
                    print(f"  {DIM}already in list{R}")
            else:
                print(f"  {RED}not found: {target_filename}{R}")
        elif cmd.startswith("rm "):
            try:
                idx     = int(cmd[3:].strip()) - 1
                removed = selected.pop(idx)
                print(f"  {YELLOW}removed: {removed['name']}{R}")
                for i, n in enumerate(selected):
                    print(f"  {GREEN}{i+1}.{R} {n['name']}")
            except (ValueError, IndexError):
                print(f"  {RED}invalid number{R}")
        else:
            print(f"  {DIM}unknown command. use add, rm or done{R}")

    return selected


def generate_recap(notes_data: list[dict], all_notes: dict, backend: str) -> str:
    """Send studied notes to AI and generate the recap."""
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
    return call_ai(prompt, backend, timeout=600)


def write_recap(content: str, note_names: list[str]) -> str:
    """Write the recap note to the Study Recaps folder."""
    RECAP_FOLDER.mkdir(parents=True, exist_ok=True)

    date_str  = datetime.datetime.now().strftime("%Y-%m-%d")
    time_str  = datetime.datetime.now().strftime("%H-%M")

    base_name = Path(note_names[0]).stem if note_names else "Session"
    if len(note_names) > 1:
        base_name += f" +{len(note_names)-1} more"

    filename   = f"{date_str} {time_str} Recap - {base_name}.md"
    filepath   = RECAP_FOLDER / filename

    tags_lines = [
        f"  - {format_obsidian_tag(Path(n).stem)}"
        for n in note_names[:5]
    ]

    fm_lines = (
        ["---", "creation date: " + date_str, "tags:", "  - study-recap", "  - review"]
        + tags_lines
        + ["---", "", ""]
    )

    filepath.write_text("\n".join(fm_lines) + content, encoding="utf-8")
    return filepath


def main():
    backend = get_backend()
    run_startup_checks()

    print(f"\n{BOLD}{PURPLE}  study recap{R}{DIM}  spaced repetition generator{R}")
    print(f"{DIM}  backend : {backend_label(backend)}{R}")
    print(f"{DIM}  vault   : {VAULT_PATH}{R}")

    auto_detected = find_recent_notes(HOURS_BACK)
    selected      = select_notes_interactively(auto_detected)

    if not selected:
        print(f"\n{RED}  no notes selected. exiting.{R}\n")
        sys.exit(0)

    print(f"\n{DIM}  loading {len(selected)} note(s)...{R}")
    notes_data = []
    for n in selected:
        content = n["path"].read_text(encoding="utf-8", errors="ignore")

        notes_data.append({
            "name":    n["name"],
            "content": content[:MAX_NOTE_CHARS],
        })

    print(f"{DIM}  indexing vault for connections...{R}")
    all_notes = index_all_notes()

    print(f"{DIM}  generating recap...{R}\n")
    content  = generate_recap(notes_data, all_notes, backend)
    filepath = write_recap(content, [n["name"] for n in selected])

    print(f"\n{GREEN}✅ recap saved: {filepath}{R}\n")


if __name__ == "__main__":
    main()