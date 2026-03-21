# =============================================================
# vaultmind — txt_to_notes.py
# =============================================================
# Converts any text file into one or more structured Obsidian
# notes. Works with conversations, meeting notes, articles,
# braindumps — anything you can paste into a .txt file.
#
# Two-pass process:
#   Pass 1: AI reads the text and decides how many notes to create,
#           planning titles, types, and tags.
#   Pass 2: AI writes each note with full content, reusing existing
#           vault tags and creating wikilinks between notes.
#
# Optional instructions block at the top of your .txt file:
#   ---instructions---
#   Write in first person. Focus on what I built.
#   ---end---
#
# Output: Vault/Captures/YYYY-MM-DD title/
# =============================================================

import os
import sys
import json
import glob
import re
import datetime

sys.path.insert(0, os.path.dirname(__file__))
from config import MAX_FILE_SIZE, VAULT_PATH
from ai_backend import get_backend, call_ai, backend_label, run_startup_checks

VAULT_PATH  = os.path.expanduser(VAULT_PATH)
OUTPUT_BASE = "Captures"

with open(os.path.join(os.path.dirname(__file__), "prompts.json"), encoding="utf-8") as f:
    PROMPTS = json.load(f)

GROUNDING = PROMPTS["grounding"]

R      = "\033[0m"
DIM    = "\033[2m"
BOLD   = "\033[1m"
PURPLE = "\033[35m"
CYAN   = "\033[36m"
GREEN  = "\033[32m"
RED    = "\033[31m"


def fill_prompt(template: str, **kwargs) -> str:
    """
    Safe placeholder replacement that won't crash on literal { } in the template.
    Uses simple string replacement instead of Python's .format().
    """
    result = template
    for key, value in kwargs.items():
        result = result.replace("{" + key + "}", str(value))
    return result


def parse_input(raw: str) -> tuple[str, str]:
    """
    Parse the input file for an optional instructions block.

    Format:
        ---instructions---
        your instructions here
        ---end---
        (content below)

    Returns:
        Tuple of (instructions, content).
    """
    match = re.match(r"---instructions---\s*(.*?)\s*---end---\s*", raw, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip(), raw[match.end():].strip()
    return "", raw.strip()


def collect_vault_tags() -> list[str]:
    """
    Scan all notes and collect existing tags from frontmatter and inline #hashtags.
    Passed to the AI so it reuses existing tags instead of inventing new ones.
    """
    tags = set()
    for path in glob.glob(f"{VAULT_PATH}/**/*.md", recursive=True):
        try:
            if os.path.getsize(path) > MAX_FILE_SIZE:
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            fm = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
            if fm:
                for line in fm.group(1).splitlines():
                    m = re.match(r"\s*-\s*(.+)", line)
                    if m:
                        tags.add(m.group(1).strip().lower())
            for t in re.findall(r"#([a-zA-Z][a-zA-Z0-9_/-]+)", content):
                tags.add(t.lower())
        except Exception:
            continue
    return sorted(tags)


def collect_note_titles() -> list[str]:
    """
    Collect all note titles for wikilink generation.
    Strips date prefixes from filenames.
    """
    titles = []
    for path in glob.glob(f"{VAULT_PATH}/**/*.md", recursive=True):
        name  = os.path.splitext(os.path.basename(path))[0]
        clean = re.sub(r"^\d{4}-\d{2}-\d{2}\s+", "", name)
        titles.append(clean)
    return titles


def plan_notes(text, instructions, existing_tags, existing_titles, backend) -> list[dict]:
    """
    Pass 1: Ask the AI to analyze the text and plan how many notes to create.

    Returns:
        List of note plan dicts with title, type, tags, summary, related_existing.

    Raises:
        ValueError: If the model doesn't return valid JSON.
    """
    tags_hint   = ", ".join(existing_tags[:60])   if existing_tags   else "none yet"
    titles_hint = ", ".join(existing_titles[:80]) if existing_titles else "none"
    instr_block = f"\nExtra instructions from the user:\n{instructions}\n" if instructions else ""

    prompt = fill_prompt(
        PROMPTS["txt_to_notes"]["plan_prompt"],
        instructions_block=instr_block,
        grounding=GROUNDING,
        text=text[:12000],
        tags_hint=tags_hint,
        titles_hint=titles_hint,
    )

    raw = call_ai(prompt, backend)
    raw = re.sub(r"```(?:json)?", "", raw).strip()

    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        raise ValueError(f"Model did not return a JSON array.\nRaw output:\n{raw[:500]}")

    try:
        return json.loads(match.group())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from model: {e}\nMatched:\n{match.group()[:500]}")


def write_note_content(text, note_plan, all_titles_in_batch, instructions, existing_tags, backend) -> str:
    """
    Pass 2: Write the full content for a single note.
    The model knows all other notes in this batch so it can cross-link between them.
    """
    tags_hint     = ", ".join(existing_tags[:40]) if existing_tags else "none yet"
    batch_links   = ", ".join(f"[[{t}]]" for t in all_titles_in_batch)
    related_links = ", ".join(f"[[{t}]]" for t in note_plan.get("related_existing", [])) or "none identified"
    instr_block   = f"\nExtra instructions from the user:\n{instructions}\n" if instructions else ""

    prompt = fill_prompt(
        PROMPTS["txt_to_notes"]["write_prompt"],
        instructions_block=instr_block,
        grounding=GROUNDING,
        title=note_plan["title"],
        type=note_plan["type"],
        summary=note_plan["summary"],
        text=text[:12000],
        batch_links=batch_links,
        related_links=related_links,
        tags_hint=tags_hint,
    )
    return call_ai(prompt, backend, timeout=300)


def write_file(note_plan, body, folder_path, date_str) -> str:
    """Write a single note to disk with Obsidian frontmatter."""
    title      = note_plan.get("title", "Untitled")
    tags       = note_plan.get("tags", [])
    safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
    filename   = f"{date_str} {safe_title}.md"
    filepath   = os.path.join(folder_path, filename)

    fm_lines = (
        ["---", "parent: ", "tags:"]
        + [f"  - {t}" for t in tags]
        + ["font: ", "creation date: " + date_str, "---", "", ""]
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(fm_lines) + body)

    return filepath


def main():
    backend = get_backend()
    run_startup_checks()

    args = [a for a in sys.argv[1:] if a != "--api"]
    if not args:
        print(f"{RED}usage: python txt_to_notes.py <file.txt>{R}")
        sys.exit(1)

    source = args[0]
    if not os.path.exists(source):
        print(f"{RED}file not found: {source}{R}")
        sys.exit(1)

    with open(source, "r", encoding="utf-8", errors="ignore") as f:
        raw = f.read()

    instructions, text = parse_input(raw)

    if not text:
        print(f"{RED}file is empty{R}")
        sys.exit(1)

    print(f"\n{BOLD}{PURPLE}  txt_to_notes{R}")
    print(f"{DIM}  source  : {source} ({len(text)} chars){R}")
    print(f"{DIM}  backend : {backend_label(backend)}{R}")
    if instructions:
        print(f"{DIM}  instructions detected{R}")
    print()

    print(f"{DIM}  scanning vault...{R}")
    existing_tags   = collect_vault_tags()
    existing_titles = collect_note_titles()
    print(f"{DIM}  {len(existing_tags)} tags · {len(existing_titles)} note titles{R}\n")

    print(f"{DIM}  pass 1: planning notes...{R}")
    try:
        plan = plan_notes(text, instructions, existing_tags, existing_titles, backend)
    except Exception as e:
        print(f"{RED}  pass 1 failed: {e}{R}")
        sys.exit(1)

    print(f"{CYAN}  {len(plan)} note(s) planned:{R}")
    for n in plan:
        print(f"    {DIM}· {n['title']} [{n['type']}]{R}")
    print()

    date_str    = datetime.datetime.now().strftime("%Y-%m-%d")
    folder_name = re.sub(r'[\\/*?:"<>|]', "", plan[0]["title"]) if plan else "dump"
    folder_path = os.path.join(VAULT_PATH, OUTPUT_BASE, f"{date_str} {folder_name}")
    os.makedirs(folder_path, exist_ok=True)

    all_titles_in_batch = [n["title"] for n in plan]

    print(f"{DIM}  pass 2: writing notes...{R}\n")
    created = []
    for i, note_plan in enumerate(plan):
        title = note_plan["title"]
        print(f"  {CYAN}[{i+1}/{len(plan)}]{R} {BOLD}{title}{R}")
        try:
            body     = write_note_content(text, note_plan, all_titles_in_batch, instructions, existing_tags, backend)
            filepath = write_file(note_plan, body, folder_path, date_str)
            tags     = ", ".join(note_plan.get("tags", []))
            print(f"    {DIM}tags : {tags}{R}")
            print(f"    {DIM}path : {filepath}{R}")
            created.append(filepath)
        except Exception as e:
            print(f"    {RED}failed: {e}{R}")
        print()

    print(f"{GREEN}  done. {len(created)} note(s) saved to:{R}")
    print(f"  {BOLD}{folder_path}{R}\n")


if __name__ == "__main__":
    main()