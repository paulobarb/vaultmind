# =============================================================
# vaultmind — generate_insights.py
# =============================================================
# Reads notes modified in the last DAYS_BACK days and runs them
# through multiple analysis lenses in parallel. Each lens makes
# a separate AI call focusing on a different aspect of the notes.
# A final synthesis call combines all lens outputs into one note.
#
# Persistent Memory: AI_State.md is read at startup and updated
# after each run, giving the AI long-term context across weeks.
#
# Output: Vault/Insights/YYYY-MM-DD Week Insight.md
#
# Schedule with cron to run automatically:
#   0 8 * * 0 /path/to/venv/bin/python /path/to/generate_insights.py
# =============================================================

import sys
import json
import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from config import MAX_FILE_SIZE, VAULT_PATH, DAYS_BACK, MAX_NOTE_CHARS, EXCLUDED_FOLDERS
from ai_backend import get_backend, call_ai, backend_label, run_startup_checks

VAULT_PATH     = Path(VAULT_PATH).expanduser().resolve()
INSIGHT_FOLDER = VAULT_PATH / "Insights"
STATE_FILE     = INSIGHT_FOLDER / "AI_State.md"

# load all prompts from the shared prompts.json file
PROMPTS_PATH = SCRIPT_DIR / "prompts.json"
with PROMPTS_PATH.open(encoding="utf-8") as f:
    PROMPTS = json.load(f)

GROUNDING = PROMPTS["grounding"]
LENSES    = PROMPTS["insights"]["lenses"]

def fill_prompt(template: str, **kwargs) -> str:
    """
    Safe placeholder replacement that won't crash on literal { } in the template.
    Uses simple string replacement instead of Python's .format() to avoid
    KeyErrors when the prompt contains JSON examples with curly braces.
    """
    result = template
    for key, value in kwargs.items():
        result = result.replace("{" + key + "}", str(value))
    return result

def get_week_label() -> str:
    """Return the current ISO week number as a string, e.g. 'Week 12'."""
    return f"Week {datetime.datetime.now().isocalendar()[1]}"


# --- PERSISTENT STATE ---

def load_state() -> str:
    """
    Load AI_State.md which contains compressed historical context
    from previous weeks. Returns empty string on first run.

    Returns:
        Historical context string or empty string.
    """
    if STATE_FILE.exists():
        return STATE_FILE.read_text(encoding="utf-8").strip()
    return ""


def save_state(content: str):
    """
    Save the updated compressed state back to AI_State.md.
    This file grows smarter each week as the AI compresses
    long-term patterns into it.

    Args:
        content: The new compressed state text from the AI.
    """
    INSIGHT_FOLDER.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(content, encoding="utf-8")
    print("   AI_State.md updated")


def extract_state_from_synthesis(synthesis: str) -> tuple:
    """
    Extract the updated state block from the synthesis output.
    The AI appends the state update after a separator line.

    Args:
        synthesis: Full synthesis text from the AI.

    Returns:
        Tuple of (clean_synthesis, new_state).
    """
    separator = "---STATE_UPDATE---"
    if separator in synthesis:
        parts     = synthesis.split(separator, 1)
        clean     = parts[0].strip()
        new_state = parts[1].strip()
        return clean, new_state
    # if model didn't follow format, use full synthesis as state
    return synthesis, synthesis


# --- VAULT ---

def collect_recent_notes(days: int) -> list[dict]:
    """
    Scan the vault for .md files modified within the last `days` days.
    Uses pathlib for cross-platform compatibility (Windows + Unicode).

    Args:
        days: Number of days to look back from now.

    Returns:
        List of dicts with 'file' (filename) and 'content' (text) keys.
    """
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    notes  = []

    for path_obj in VAULT_PATH.rglob("*.md"):
        if any(folder in str(path_obj) for folder in EXCLUDED_FOLDERS):
            continue

        try:
            mtime = datetime.datetime.fromtimestamp(path_obj.stat().st_mtime)

            if mtime >= cutoff:
                if path_obj.stat().st_size > MAX_FILE_SIZE:
                    continue

                with path_obj.open("r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                notes.append({"file": path_obj.name, "content": content})

                print(f"Trying to open: {path_obj}")

        except OSError as e:
            print(f"Error accessing {path_obj}: {e}")
            continue

    return notes

def build_notes_block(notes: list[dict]) -> str:
    """
    Format a list of notes into a single text block for the prompt.
    Content is capped at MAX_NOTE_CHARS to keep prompts within context limits.
    """
    return "\n\n---\n\n".join(
        f"### {n['file']}\n{n['content'][:MAX_NOTE_CHARS]}" for n in notes
    )


# --- LENSES ---

def run_lens(lens: dict, notes_block: str, period: str, backend: str) -> dict:
    """
    Run a single analysis lens against the notes block.

    Args:
        lens:        Lens dict with 'name' and 'instruction' from prompts.json.
        notes_block: Formatted string of all notes to analyze.
        period:      'week' or 'month'.
        backend:     Which AI backend to use.

    Returns:
        Dict with 'name' and 'result' keys.
    """
    prompt = fill_prompt(
        PROMPTS["insights"]["lens_prompt"],
        period=period,
        name=lens["name"],
        instruction=lens["instruction"],
        grounding=GROUNDING,
        notes_block=notes_block,
    )
    print(f"   Running lens: {lens['name']}...")
    return {"name": lens["name"], "result": call_ai(prompt, backend)}


def run_synthesis(lens_results: list[dict], period: str, state: str, backend: str) -> tuple:
    """
    Combine all lens outputs into a final synthesis.
    Also asks the AI to produce an updated compressed state for AI_State.md.

    Args:
        lens_results: List of lens output dicts.
        period:       'week' or 'month'.
        state:        Historical context from AI_State.md.
        backend:      Which AI backend to use.

    Returns:
        Tuple of (clean_synthesis, new_state).
    """
    combined = "\n\n".join(
        f"### {r['name']}\n{r['result']}" for r in lens_results
    )

    state_block = f"""HISTORICAL CONTEXT (compressed memory from previous weeks):
{state}

Use this context to identify long-term patterns and evolution over time.
""" if state else "No historical context yet — this is the first run.\n"

    prompt = fill_prompt(
        PROMPTS["insights"]["synthesis_prompt"],
        period=period,
        combined=combined,
        grounding=GROUNDING,
        state_block=state_block,
    )

    print("   Running final synthesis...")
    raw = call_ai(prompt, backend)
    return extract_state_from_synthesis(raw)


# --- TAGS ---

def extract_tags(lens_results: list[dict], synthesis: str) -> list[str]:
    """
    Automatically detect relevant tags from the generated content.
    Always includes 'insights' as a base tag.
    """
    base_tags = ["insights"]
    text = synthesis.lower() + " ".join(r["result"].lower() for r in lens_results)

    candidates = {
        "productivity":  ["productiv", "task", "goal", "work", "focus"],
        "mood":          ["mood", "emotion", "feel", "stress", "anxiet", "happy"],
        "philosophy":    ["meaning", "values", "purpose", "reflect", "life"],
        "habits":        ["habit", "routine", "pattern", "repeat", "daily"],
        "health":        ["health", "sleep", "exercise", "energy", "body"],
        "projects":      ["project", "build", "code", "ship", "launch", "develop"],
        "relationships": ["friend", "family", "partner", "social", "connect"],
    }

    for tag, keywords in candidates.items():
        if any(kw in text for kw in keywords):
            base_tags.append(tag)

    return base_tags[:6]


# --- OUTPUT ---

def write_insight_note(lens_results: list[dict], synthesis: str, note_count: int):
    """
    Write the final insight note to the Insights folder in the vault.
    Creates the folder if it doesn't exist.
    """
    date_str     = datetime.datetime.now().strftime("%Y-%m-%d")
    period_label = "Week" if DAYS_BACK <= 7 else "Monthly"
    week_label   = get_week_label()
    filename     = f"{date_str} {period_label} Insight.md"

    INSIGHT_FOLDER.mkdir(parents=True, exist_ok=True)
    filepath = INSIGHT_FOLDER / filename

    tags = extract_tags(lens_results, synthesis)

    fm_lines = (
        ["---", "creation date: " + date_str, "tags:"]
        + [f"  - {t}" for t in tags]
        + ["week: " + week_label, "content: insights", "---", "", ""]
    )

    lines = ["## 🔮 Synthesis", "", synthesis, "", "---", ""]
    for r in lens_results:
        lines += [f"## 🔍 {r['name']}", "", r["result"], ""]

    filepath.write_text("\n".join(fm_lines) + "\n".join(lines), encoding="utf-8")
    print(f"\n✅ Insight saved: {filepath}")


# --- MAIN ---

if __name__ == "__main__":
    backend = get_backend()
    run_startup_checks()
    period  = "week" if DAYS_BACK <= 7 else "month"

    print(f"\n📖 Collecting notes from the last {DAYS_BACK} days...")
    print(f"   Backend: {backend_label(backend)}\n")

    # load historical state from previous runs
    state = load_state()
    if state:
        print("   📚 Historical context loaded from AI_State.md\n")
    else:
        print("   📚 No historical context yet — first run\n")

    notes = collect_recent_notes(DAYS_BACK)
    if not notes:
        print("No recent notes found. Nothing to analyze.")
        sys.exit(0)

    print(f"   Found {len(notes)} notes. Running {len(LENSES)} lenses in parallel...\n")
    notes_block  = build_notes_block(notes)
    lens_results = [None] * len(LENSES)

    def run_lens_indexed(args):
        i, lens = args
        return i, run_lens(lens, notes_block, period, backend)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(run_lens_indexed, (i, lens)): i
            for i, lens in enumerate(LENSES)
        }
        for future in as_completed(futures):
            i, result = future.result()
            lens_results[i] = result

    synthesis, new_state = run_synthesis(lens_results, period, state, backend)
    save_state(new_state)
    write_insight_note(lens_results, synthesis, len(notes))