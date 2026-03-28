# =============================================================
# vaultmind — morning_briefing.py
# =============================================================
# Reads notes modified in the last 24 hours and generates a
# structured morning briefing with yesterday's activity,
# pending tasks, and a suggested focus for the day.
#
# Output: Vault/Briefings/YYYY-MM-DD Morning Briefing.md
#
# Schedule with cron to run automatically every morning:
# 0 8 * * * /path/to/venv/bin/python /path/to/morning_briefing.py
# =============================================================

from pathlib import Path
import sys
import json
import datetime
from config import EXCLUDED_FOLDERS, MAX_FILE_SIZE, VAULT_PATH, MAX_NOTE_CHARS, TEMPERATURES, BRIEFING_TITLE_FORMAT, BRIEFING_DIR_NAME
from core.ai_backend import get_backend, call_ai, run_startup_checks

CYAN, GREEN, YELLOW, DIM, BOLD, RESET = "\033[96m", "\033[92m", "\033[93m", "\033[2m", "\033[1m", "\033[0m"

SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

VAULT_PATH  = Path(VAULT_PATH).expanduser().resolve()
BRIEFING_FOLDER = VAULT_PATH / BRIEFING_DIR_NAME
BRIEFING_FOLDER.mkdir(parents=True, exist_ok=True)

# load prompts from prompts.json
PROMPTS_PATH = SCRIPT_DIR / "prompts.json"
with PROMPTS_PATH.open(encoding="utf-8") as f:
    PROMPTS = json.load(f)
    
TEMP_BRIEFING = TEMPERATURES.get("briefing") or TEMPERATURES.get("default") or 0.2

GROUNDING = PROMPTS["grounding"]

def fill_prompt(template: str, **kwargs) -> str:
    """
    Safe placeholder replacement that won't crash on literal { } in the template.
    Uses simple string replacement instead of Python's .format().
    """
    result = template
    for key, value in kwargs.items():
        result = result.replace("{" + key + "}", str(value))
    return result

def collect_notes(days_back: float) -> list[dict]:
    """
    Collect notes modified within the last `days_back` days.

    Args:
        days_back: How many days back to look. Use 0 for today only,
                   1 for yesterday and today.

    Returns:
        List of note dicts with 'name', 'content', and 'mtime' keys.
    """
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days_back)
    notes  = []

    all_files = sorted(
        VAULT_PATH.rglob("*.md"),
        key=lambda p: p.stat().st_mtime if p.exists() else 0,
        reverse=True
    )

    for path_obj in all_files:
        path_str = str(path_obj)
        if any(skip in path_str for skip in EXCLUDED_FOLDERS):
            continue
        
        try:
            stat = path_obj.stat()
            mtime = datetime.datetime.fromtimestamp(stat.st_mtime)
            if mtime >= cutoff:
                if stat.st_size > MAX_FILE_SIZE:
                    continue

                with path_obj.open("r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                notes.append({
                    "name":    path_obj.name,
                    "content": content[:MAX_NOTE_CHARS],
                    "mtime":   mtime,
                })
        except OSError:
            continue

    return notes

def build_notes_block(notes: list[dict]) -> str:
    """
    Format notes into a single string for the prompt.
    Each note includes its filename and last modified time as context.

    Args:
        notes: List of note dicts from collect_notes().

    Returns:
        Formatted string with all notes concatenated.
    """
    return "\n\n---\n\n".join(
        f"### {n['name']} (modified {n['mtime'].strftime('%Y-%m-%d %H:%M')})\n{n['content']}"
        for n in notes
    )

def generate_briefing(yesterday_notes: list[dict], today_notes: list[dict], backend: str) -> str:
    """
    Send the notes to the AI and generate the morning briefing.
    Uses the prompt template from prompts.json so users can customize
    the briefing sections without touching Python code.

    Args:
        yesterday_notes: Notes modified yesterday.
        today_notes:     Notes modified today (may be empty early morning).
        backend:         Which AI backend to use.

    Returns:
        The briefing content as a Markdown string.
    """
    yesterday_block = build_notes_block(yesterday_notes) if yesterday_notes else "No notes modified yesterday."
    today_block     = build_notes_block(today_notes)     if today_notes     else "No notes modified today yet."

    prompt = fill_prompt(
        PROMPTS["morning_briefing"]["prompt"],
        weekday=datetime.datetime.now().strftime("%A"),
        date=datetime.datetime.now().strftime("%Y-%m-%d"),
        grounding=GROUNDING,
        yesterday_block=yesterday_block,
        today_block=today_block,
    )

    return call_ai(prompt, backend, temperature=TEMP_BRIEFING)

def write_briefing(content: str) -> str:
    """
    Write the briefing to the Briefings folder in the vault.
    Creates the folder if it doesn't exist.

    Args:
        content: The briefing Markdown content from generate_briefing().

    Returns:
        The full file path of the saved note.
    """
    BRIEFING_FOLDER.mkdir(parents=True, exist_ok=True)

    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    filename = BRIEFING_TITLE_FORMAT.format(date=date_str)
    filepath = BRIEFING_FOLDER / filename

    fm_lines = [
        "---",
        "creation date: " + date_str,
        "tags:",
        "  - briefing",
        "  - daily",
        "type: briefing",
        "---",
        "",
        "",
    ]

    filepath.write_text("\n".join(fm_lines) + content, encoding="utf-8")

    return filepath


def main():
    backend = get_backend()
    run_startup_checks()

    print(f"\n{CYAN}{BOLD}MORNING BRIEFING{RESET}")
    print(f"{DIM}Vault:   {VAULT_PATH}{RESET}\n")

    print(f"{DIM}• Collecting yesterday's notes...{RESET}", end="\r")
    yesterday_notes = collect_notes(days_back=1)

    print(f"{DIM}• Collecting today's notes...    {RESET}", end="\r")
    today_notes = collect_notes(days_back=0)

    total = len(yesterday_notes)
    
    print(f"{DIM}• Found {total} note(s) modified in the last 24h{' '*10}{RESET}")

    if not yesterday_notes and not today_notes:
        print(f"\n{YELLOW}No recent notes found to brief you on.{RESET}\n")

    print(f"{DIM}• Generating briefing...{RESET}", end="\r")
    content  = generate_briefing(yesterday_notes, today_notes, backend)
    filepath = write_briefing(content)

    print(" " * 50, end="\r")
    print(f"{GREEN}│ Briefing Saved:{RESET} {filepath.name}\n")


if __name__ == "__main__":
    main()