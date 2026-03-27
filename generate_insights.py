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
import re
import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import MAX_FILE_SIZE, VAULT_PATH, DAYS_BACK, MAX_NOTE_CHARS, EXCLUDED_FOLDERS, CANDIDATES, TEMPERATURES, INSIGHT_TITLE_FORMAT
from ai_backend import get_backend, call_ai, run_startup_checks

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

VAULT_PATH     = Path(VAULT_PATH).expanduser().resolve()
INSIGHT_FOLDER = VAULT_PATH / "Insights"
STATE_FILE     = INSIGHT_FOLDER / "AI_State.md"

# --- COLORS ---
CYAN, GREEN, YELLOW, DIM, BOLD, RESET = "\033[96m", "\033[92m", "\033[93m", "\033[2m", "\033[1m", "\033[0m"

# load all prompts from the shared prompts.json file
PROMPTS_PATH = SCRIPT_DIR / "prompts.json"
with PROMPTS_PATH.open(encoding="utf-8") as f:
    PROMPTS = json.load(f)

TEMP_INSIGHTS = TEMPERATURES.get("insights")

GROUNDING = PROMPTS["grounding"]
LENSES    = PROMPTS["insights"]["lenses"]

def format_obsidian_tag(text: str) -> str:
    text = text.lower().replace(" ", "-")
    return re.sub(r'[^a-z0-9_-]', '', text)

def fill_prompt(template: str, **kwargs) -> str:
    result = template
    for key, value in kwargs.items():
        result = result.replace("{" + key + "}", str(value))
    return result

def get_week_label() -> str:
    now = datetime.datetime.now()
    start_of_week = now - datetime.timedelta(days=now.weekday())
    end_of_week = start_of_week + datetime.timedelta(days=6)
    range_str = f"{start_of_week.strftime('%b %d')} – {end_of_week.strftime('%b %d')}"
    week_num = now.isocalendar()[1]
    return f"{range_str} (Week {week_num})"


# --- PERSISTENT STATE ---

def load_state() -> str:
    if STATE_FILE.exists():
        return STATE_FILE.read_text(encoding="utf-8").strip()
    return ""

def save_state(content: str):
    INSIGHT_FOLDER.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(content, encoding="utf-8")
    print(f"{DIM}│ State updated: AI_State.md{RESET}")

def extract_state_from_synthesis(synthesis: str) -> tuple:
    separator = "---STATE_UPDATE---"
    if separator in synthesis:
        parts     = synthesis.split(separator, 1)
        clean     = parts[0].strip()
        new_state = parts[1].strip()
        return clean, new_state
    return synthesis, synthesis


# --- VAULT ---

def collect_recent_notes(days: int) -> list[dict]:
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

        except OSError as e:
            # Only print actual errors, not every single file it tries to open
            print(f"{YELLOW}│ Error reading {path_obj.name}: {e}{RESET}")
            continue

    return notes

def build_notes_block(notes: list[dict]) -> str:
    return "\n\n---\n\n".join(
        f"### {n['file']}\n{n['content'][:MAX_NOTE_CHARS]}" for n in notes
    )


# --- LENSES ---

def run_lens(lens: dict, notes_block: str, period: str, backend: str) -> dict:
    prompt = fill_prompt(
        PROMPTS["insights"]["lens_prompt"],
        period=period,
        name=lens["name"],
        instruction=lens["instruction"],
        grounding=GROUNDING,
        notes_block=notes_block,
    )
    print(f"{DIM}  │ Analyzing:{RESET} {lens['name']}")
    return {"name": lens["name"], "result": call_ai(prompt, backend, temperature=TEMP_INSIGHTS)}


def run_synthesis(lens_results: list[dict], period: str, state: str, backend: str) -> tuple:
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

    print(f"\n{DIM}• Generating final synthesis...{RESET}", end="\r")
    raw = call_ai(prompt, backend, temperature=TEMP_INSIGHTS)
    return extract_state_from_synthesis(raw)


# --- TAGS ---

def extract_tags(lens_results: list[dict], synthesis: str) -> list[str]:
    base_tags = ["insights"]
    text = synthesis.lower() + " ".join(r["result"].lower() for r in lens_results)

    for tag, keywords in CANDIDATES.items():
        if any(kw in text for kw in keywords):
            base_tags.append(tag)

    final_tags = []
    for tag in base_tags:
        cleaned = format_obsidian_tag(tag)
        if cleaned:
            final_tags.append(cleaned)

    return final_tags[:6]


# --- OUTPUT ---

def write_insight_note(lens_results: list[dict], synthesis: str, note_count: int):
    now = datetime.datetime.now()
    date_str     = datetime.datetime.now().strftime("%Y-%m-%d")

    is_month     = DAYS_BACK > 7
    period_label = "Week" if DAYS_BACK <= 7 else "Monthly"
    filename     = INSIGHT_TITLE_FORMAT.format(date=date_str, period=period_label)

    if is_month:
        time_property = "month: " + now.strftime("%B %Y")
    else:
        time_property = "week: " + get_week_label()
    
    INSIGHT_FOLDER.mkdir(parents=True, exist_ok=True)
    filepath = INSIGHT_FOLDER / filename
    tags = extract_tags(lens_results, synthesis)

    fm_lines = [
        "---", 
        f"creation date: {date_str}",
        "tags:"
        ] + [f"  - {t}" for t in tags] + [
            time_property, 
            "content: insights", 
            "---", 
            "", ""
        ]

    lines = ["## 🔮 Synthesis", "", synthesis, "", "---", ""]
    for r in lens_results:
        lines += [f"## 🔍 {r['name']}", "", r["result"], ""]

    filepath.write_text("\n".join(fm_lines) + "\n".join(lines), encoding="utf-8")
    return filepath


# --- MAIN ---

if __name__ == "__main__":
    backend = get_backend()
    run_startup_checks()
    period  = "week" if DAYS_BACK <= 7 else "month"

    print(f"\n{CYAN}{BOLD}VAULT INSIGHTS{RESET}")
    print(f"{DIM}Period:  Last {DAYS_BACK} days{RESET}\n")

    state = load_state()
    if state:
        print(f"{DIM}• Historical context loaded (AI_State.md){RESET}")
    else:
        print(f"{DIM}• No historical context (First run){RESET}")

    print(f"{DIM}• Scanning vault for recent notes...{RESET}", end="\r")
    notes = collect_recent_notes(DAYS_BACK)
    
    if not notes:
        print(f"{YELLOW}• No recent notes found. Nothing to analyze.{RESET}\n")
        sys.exit(0)

    print(f"{DIM}• Found {len(notes)} notes. Running {len(LENSES)} lenses in parallel...{' '*10}{RESET}")
    
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
    print(" " * 50, end="\r")
    
    save_state(new_state)
    filepath = write_insight_note(lens_results, synthesis, len(notes))
    
    print(f"{GREEN}│ Insight Saved:{RESET} {filepath.name}\n")