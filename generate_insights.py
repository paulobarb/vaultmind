# =============================================================
# vaultmind — generate_insights.py
# =============================================================
# Reads notes modified in the last DAYS_BACK days and runs them
# through multiple analysis lenses in parallel. Each lens makes
# a separate AI call focusing on a different aspect of the notes.
# A final synthesis call combines all lens outputs into one note.
#
# Output: Vault/Insights/YYYY-MM-DD Week Insight.md
#
# Schedule with cron to run automatically:
#   0 8 * * 0 /path/to/venv/bin/python /path/to/generate_insights.py
# =============================================================

import os
import sys
import glob
import json
import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# add script directory to path so local modules are found
sys.path.insert(0, os.path.dirname(__file__))
from config import MAX_FILE_SIZE, VAULT_PATH, DAYS_BACK, MAX_NOTE_CHARS, EXCLUDED_FOLDERS
from ai_backend import get_backend, call_ai, backend_label, run_startup_checks

# expand ~ to the full home directory path
VAULT_PATH     = os.path.expanduser(VAULT_PATH)
INSIGHT_FOLDER = os.path.join(VAULT_PATH, "Insights")

# load all prompts from the shared prompts.json file
# users can edit prompts.json without touching this script
with open(os.path.join(os.path.dirname(__file__), "prompts.json"), encoding="utf-8") as f:
    PROMPTS = json.load(f)

GROUNDING = PROMPTS["grounding"]  # injected into every prompt to reduce hallucination
LENSES    = PROMPTS["insights"]["lenses"]  # list of analysis lenses from prompts.json


def fill_prompt(template: str, **kwargs) -> str:
    """
    Safe placeholder replacement that won't crash on literal { } in the template.
    Uses simple string replacement instead of Python's .format() to avoid
    KeyErrors when the prompt contains JSON examples with curly braces.

    Args:
        template: The prompt template string with {placeholder} markers.
        **kwargs: Key-value pairs to substitute into the template.

    Returns:
        The prompt with all placeholders replaced.
    """
    result = template
    for key, value in kwargs.items():
        result = result.replace("{" + key + "}", str(value))
    return result


def get_week_label() -> str:
    """Return the current ISO week number as a string, e.g. 'Week 12'."""
    return f"Week {datetime.datetime.now().isocalendar()[1]}"


def collect_recent_notes(days: int) -> list[dict]:
    """
    Scan the vault for .md files modified within the last `days` days.
    Skips the Insights folder to avoid feeding old insight notes back in.

    Args:
        days: Number of days to look back from now.

    Returns:
        List of dicts with 'file' (filename) and 'content' (text) keys.
    """
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    notes  = []

    base_path = Path(VAULT_PATH)

    for path_obj in base_path.rglob("*.md"):
        if any(folder in str(path_obj) for folder in EXCLUDED_FOLDERS):
            continue

        try:
            mtime = datetime.datetime.fromtimestamp(path_obj.stat().st_mtime)

            if mtime >= cutoff:
                if path_obj.stat().st_size > MAX_FILE_SIZE:
                    continue

                print(f"Trying to open: {path_obj}")

                with path_obj.open("r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                notes.append({"file": path_obj.name, "content": content})

        except OSError as e:
            print(f"Error accessing {path_obj}: {e}")
            continue

    return notes


def build_notes_block(notes: list[dict]) -> str:
    """
    Format a list of notes into a single text block for the prompt.
    Each note is separated by '---' and includes its filename as a heading.
    Content is capped at MAX_NOTE_CHARS to keep prompts within context limits.

    Args:
        notes: List of note dicts from collect_recent_notes().

    Returns:
        A formatted string with all notes concatenated.
    """
    return "\n\n---\n\n".join(
        f"### {n['file']}\n{n['content'][:MAX_NOTE_CHARS]}" for n in notes
    )


def run_lens(lens: dict, notes_block: str, period: str, backend: str) -> dict:
    """
    Run a single analysis lens against the notes block.
    Each lens focuses on a different aspect (e.g. emotional, productivity).
    The lens name and instruction come from prompts.json so users can customize them.

    Args:
        lens:        Lens dict with 'name' and 'instruction' from prompts.json.
        notes_block: Formatted string of all notes to analyze.
        period:      'week' or 'month' — used in the prompt.
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
    print(f"   🔍 Running lens: {lens['name']}...")
    return {"name": lens["name"], "result": call_ai(prompt, backend)}


def run_synthesis(lens_results: list[dict], period: str, backend: str) -> str:
    """
    Combine all lens outputs into a single final synthesis.
    Runs after all lenses complete. Extracts the single most important
    insight, one honest challenge, and one concrete action to take.

    Args:
        lens_results: List of dicts with 'name' and 'result' from run_lens().
        period:       'week' or 'month'.
        backend:      Which AI backend to use.

    Returns:
        The synthesis text as a string.
    """
    # join all lens outputs into one block for the synthesis prompt
    combined = "\n\n".join(
        f"### {r['name']}\n{r['result']}" for r in lens_results
    )
    prompt = fill_prompt(
        PROMPTS["insights"]["synthesis_prompt"],
        period=period,
        combined=combined,
        grounding=GROUNDING,
    )
    print("   🧠 Running final synthesis...")
    return call_ai(prompt, backend)


def extract_tags(lens_results: list[dict], synthesis: str) -> list[str]:
    """
    Automatically detect relevant tags from the generated content.
    Scans lens outputs and synthesis for topic keywords and maps them
    to predefined tag names. Always includes 'insights' as a base tag.

    Args:
        lens_results: List of lens output dicts.
        synthesis:    The final synthesis text.

    Returns:
        List of tag strings, capped at 6.
    """
    base_tags = ["insights"]
    # combine all generated text for keyword scanning
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


def write_insight_note(lens_results: list[dict], synthesis: str, note_count: int):
    """
    Write the final insight note to the Insights folder in the vault.
    Creates the folder if it doesn't exist. The note includes:
    - YAML frontmatter with date, tags, week number, and content type
    - A synthesis section at the top
    - One section per lens below

    Args:
        lens_results: List of lens output dicts.
        synthesis:    The final synthesis text.
        note_count:   Number of notes that were analyzed (for reference).
    """
    os.makedirs(INSIGHT_FOLDER, exist_ok=True)

    date_str     = datetime.datetime.now().strftime("%Y-%m-%d")
    period_label = "Week" if DAYS_BACK <= 7 else "Monthly"
    week_label   = get_week_label()
    filename     = f"{date_str} {period_label} Insight.md"
    filepath     = os.path.join(INSIGHT_FOLDER, filename)

    tags = extract_tags(lens_results, synthesis)

    # build frontmatter as a list of lines to avoid f-string issues
    fm_lines = (
        ["---", "creation date: " + date_str, "tags:"]
        + [f"  - {t}" for t in tags]
        + ["week: " + week_label, "content: insights", "---", "", ""]
    )

    # build the note body with synthesis first, then each lens
    lines = ["## 🔮 Synthesis", "", synthesis, "", "---", ""]
    for r in lens_results:
        lines += [f"## 🔍 {r['name']}", "", r["result"], ""]

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(fm_lines) + "\n".join(lines))

    print(f"\n✅ Insight saved: {filepath}")


if __name__ == "__main__":
    backend = get_backend()
    run_startup_checks()
    period  = "week" if DAYS_BACK <= 7 else "month"

    print(f"\n📖 Collecting notes from the last {DAYS_BACK} days...")
    print(f"   Backend: {backend_label(backend)}\n")

    notes = collect_recent_notes(DAYS_BACK)
    if not notes:
        print("No recent notes found. Nothing to analyze.")
        sys.exit(0)

    print(f"   Found {len(notes)} notes. Running {len(LENSES)} lenses in parallel...\n")
    notes_block  = build_notes_block(notes)
    lens_results = [None] * len(LENSES)

    # run all lenses simultaneously using threads
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
            lens_results[i] = result  # preserve original lens order

    # synthesis runs after all lenses complete
    synthesis = run_synthesis(lens_results, period, backend)
    write_insight_note(lens_results, synthesis, len(notes))
