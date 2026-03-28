# =============================================================
# vaultmind — chat.py
# =============================================================
# Interactive AI chat interface for your Obsidian Vault.
# Finds relevant notes based on your question and answers
# using your vault as context.
#
# Memory modes (configured in config.py):
#   SAVE_CHAT_HISTORY = True  → persistent memory via SQLite
#   SAVE_CHAT_HISTORY = False → amnesiac mode (no history saved)
#
# Usage:
#   python chat.py
# =============================================================

import sys
import re
import sqlite3
import datetime
from pathlib import Path
from config import (
    VAULT_PATH,
    EXCLUDED_FOLDERS,
    TEMPERATURES,
    MAX_CONTENT_NOTES,
    MAX_NOTE_CHARS,
    SAVE_CHAT_HISTORY,
    HISTORY_LIMIT,
)
from ai_backend import call_ai, get_backend, run_startup_checks

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
DIM    = "\033[2m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

DB_FILE = SCRIPT_DIR / "chat_history.db"

TEMP_CHAT = TEMPERATURES.get("chat") or TEMPERATURES.get("default") or 0.2

# =============================================================
# DATABASE
# =============================================================

def init_db():
    """Create the exchanges table if it doesn't exist."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS exchanges (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_msg  TEXT,
                ai_msg    TEXT,
                timestamp DATETIME
            )
        """)


def add_exchange(user_msg: str, ai_msg: str):
    """Save a user/AI exchange to the database."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT INTO exchanges (user_msg, ai_msg, timestamp) VALUES (?, ?, ?)",
            (user_msg, ai_msg, datetime.datetime.now().isoformat()),
        )


def get_recent_history(limit: int) -> list[dict]:
    """Return the last `limit` exchanges as a message list."""
    with sqlite3.connect(DB_FILE) as conn:
        rows = conn.execute(
            "SELECT user_msg, ai_msg FROM exchanges ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()

    history = []
    for user_msg, ai_msg in reversed(rows):
        history.append({"role": "user",      "content": user_msg})
        history.append({"role": "assistant", "content": ai_msg})
    return history


def forget_exchange(item_id: int) -> bool:
    """Delete a single exchange by ID. Returns True if deleted."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM exchanges WHERE id = ?", (item_id,))
        return conn.total_changes > 0


def clear_all_history():
    """Delete all saved exchanges."""
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("DELETE FROM exchanges")


def print_history():
    """Print all saved exchanges in a readable format."""
    with sqlite3.connect(DB_FILE) as conn:
        rows = conn.execute(
            "SELECT id, user_msg, ai_msg FROM exchanges ORDER BY id ASC"
        ).fetchall()

    if not rows:
        print(f"\n{DIM}Memory bank is empty.{RESET}")
        return

    print(f"\n{CYAN}{BOLD}SAVED EXCHANGES{RESET}")
    print(f"{DIM}{'─' * 50}{RESET}")
    for row_id, user_msg, ai_msg in rows:
        u = (user_msg.replace("\n", " ")[:35] + "...") if len(user_msg) > 35 else user_msg
        a = (ai_msg.replace("\n",  " ")[:35] + "...") if len(ai_msg)  > 35 else ai_msg
        print(f"{CYAN}│{RESET} {DIM}[{row_id}]{RESET} {YELLOW}You:{RESET} {u} {DIM}→{RESET} {GREEN}AI:{RESET} {a}")
    print(f"{DIM}{'─' * 50}{RESET}\n")


# =============================================================
# VAULT
# =============================================================

def index_vault() -> list[Path]:
    """Return all .md paths in the vault, excluding configured folders."""
    vault = Path(VAULT_PATH).expanduser().resolve()
    return [
        p for p in vault.rglob("*.md")
        if not any(skip in str(p) for skip in EXCLUDED_FOLDERS)
    ]


def clean_filename(text: str) -> str:
    """Strip leading numbers, bullets, and whitespace from a filename."""
    return re.sub(r'^[\d\s.\-*]+', '', text).strip()


# =============================================================
# RETRIEVAL
# =============================================================

def retrieve_context(query: str, all_paths: list[Path], backend: str) -> tuple:
    """
    Two-step retrieval:
      1. Keyword force  — exact filename matches for query words
      2. Librarian      — AI ranks the full file list and picks top 10
    Then reads the content of matched files.

    Returns:
        Tuple of (context_blocks, matched_filenames)
    """
    query_words = [w for w in re.findall(r'\w+', query.lower()) if len(w) > 3]
    forced = [p for p in all_paths if any(w in p.name.lower() for w in query_words)]

    print(f"{DIM}  ranking files...{RESET}", end="\r")
    file_list = "\n".join(p.name for p in all_paths)
    librarian_prompt = (
        f"QUESTION: {query}\n"
        f"FILES:\n{file_list}\n"
        f"Return ONLY the top 10 most relevant filenames, one per line."
    )
    raw = call_ai(librarian_prompt, backend, temperature=0.0)
    suggested = [clean_filename(line) for line in raw.splitlines() if line.strip()]

    context_blocks, matched_names = [], []
    seen = set()

    for name in [p.name for p in forced] + suggested:
        if name in seen:
            continue
        match = next((p for p in all_paths if p.name.lower() == name.lower()), None)
        if not match:
            continue
        try:
            content = match.read_text(errors="ignore")[:MAX_NOTE_CHARS]
            context_blocks.append(f"### {match.name}\n{content}")
            matched_names.append(match.name)
            seen.add(name)
        except OSError:
            continue
        if len(matched_names) >= MAX_CONTENT_NOTES:
            break

    return context_blocks, matched_names


# =============================================================
# COMMANDS
# =============================================================

def handle_command(query: str) -> bool:
    """
    Handle slash commands. Returns True if a command was handled
    (so the main loop skips AI generation).
    """
    cmd = query.lower()

    if not SAVE_CHAT_HISTORY:
        print(f"{DIM}  memory commands are disabled (SAVE_CHAT_HISTORY = False){RESET}")
        return True

    if cmd == "/clear":
        clear_all_history()
        print(f"{DIM}  history cleared{RESET}")

    elif cmd in ("/memories", "/history"):
        print_history()

    elif cmd.startswith("/forget"):
        parts = query.split()
        if len(parts) == 2 and parts[1].isdigit():
            if forget_exchange(int(parts[1])):
                print(f"{DIM}  deleted{RESET}")
            else:
                print(f"{DIM}  id not found{RESET}")
        else:
            print(f"{DIM}  usage: /forget <id>{RESET}")

    else:
        print(f"{DIM}  unknown command{RESET}")

    return True


# =============================================================
# OUTPUT
# =============================================================

def print_response(content: str, sources: list[str]):
    """Print the AI response in a clean box with source files."""
    source_str = ", ".join(sources[:4])
    if len(sources) > 4:
        source_str += f" +{len(sources) - 4} more"

    print(f"\n{GREEN}{BOLD}AI{RESET} {DIM}· {source_str}{RESET}")
    print(f"{GREEN}│{RESET}")
    for line in content.split("\n"):
        print(f"{GREEN}│{RESET} {line}")
    print()


# =============================================================
# MAIN
# =============================================================

def main():
    backend    = get_backend()
    all_paths  = index_vault()

    run_startup_checks()

    if SAVE_CHAT_HISTORY:
        init_db()
        mem_label = f"{GREEN}on{RESET}"
        cmd_hint  = "/memories  /forget <id>  /clear  /exit"
    else:
        mem_label = f"{YELLOW}off{RESET}"
        cmd_hint  = "/exit"

    print(f"\n{CYAN}{BOLD}  vault chat{RESET}")
    print(f"{DIM}  {len(all_paths)} notes indexed  ·  memory: {mem_label}  ·  temp: {TEMP_CHAT}{RESET}")
    print(f"{DIM}  {cmd_hint}{RESET}\n")

    while True:
        try:
            query = input(f"{YELLOW}{BOLD}you > {RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{DIM}bye{RESET}\n")
            break

        if not query:
            continue

        if query.lower() in ("/exit", "/quit"):
            print(f"\n{DIM}bye{RESET}\n")
            break

        if query.lower() in ("exit", "quit"):
            print(f"{DIM}  use /exit to leave{RESET}")
            continue

        if query.startswith("/"):
            handle_command(query)
            continue

        # retrieve relevant notes
        context_blocks, matched = retrieve_context(query, all_paths, backend)

        if not context_blocks:
            print(f"{DIM}  no relevant notes found{RESET}\n")
            continue

        # build prompt
        print(f"{DIM}  generating...{RESET}", end="\r")

        if SAVE_CHAT_HISTORY:
            history     = get_recent_history(HISTORY_LIMIT)
            history_str = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history)
            prompt      = f"HISTORY:\n{history_str}\n\nVAULT NOTES:\n{' '.join(context_blocks)}\n\nQUESTION: {query}"
        else:
            prompt = f"VAULT NOTES:\n{' '.join(context_blocks)}\n\nQUESTION: {query}"

        answer = call_ai(prompt, backend, temperature=TEMP_CHAT)

        if SAVE_CHAT_HISTORY:
            add_exchange(query, answer)

        print(" " * 40, end="\r")
        print_response(answer, matched)


if __name__ == "__main__":
    main()