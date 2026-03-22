# vaultmind

Local AI toolkit for Obsidian. Runs 100% on your machine using [Ollama](https://ollama.com). No cloud, no API costs, no data leaving your computer.

**What it does:** reads your Obsidian vault and generates weekly insight reports, daily morning briefings, study recaps with review questions, and converts any text into structured Obsidian notes.

---

## How it works

Every script follows the same flow:

1. Reads `.md` files from your Obsidian vault
2. Builds a prompt and sends it to a local Ollama model
3. Writes the output back into your vault as a new `.md` note with frontmatter

---

## Requirements

- [Ollama](https://ollama.com) installed and running
- Python 3.10+
- An Obsidian vault

---
## Demo

[![vaultmind demo](https://img.youtube.com/vi/hqVmcqMPpUE/maxresdefault.jpg)](https://www.youtube.com/watch?v=hqVmcqMPpUE)

---

## Installation

**1. Clone the repo**
```bash
git clone https://github.com/yourusername/vaultmind.git
cd vaultmind
```

**2. Create a virtual environment and install dependencies**
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install requests
```

**3. Pull a model**

Vaultmind uses Ollama to run models locally. Pull one before running any script:
```bash
ollama pull llama3.1:8b
```

Recommended models:
| Model | Size | Best for |
|---|---|---|
| `llama3.1:8b` | ~5GB | Best all-around quality |
| `deepseek-r1:8b` | ~5GB | Less hallucination, better reasoning |
| `llama3.2:3b` | ~2GB | Faster, lighter, good for older hardware |

**4. Edit `config.py`**

Open `config.py` and set your vault path and preferred model. Everything else has sensible defaults.

```python
OLLAMA_MODEL = "llama3.1:8b"   # must match what you pulled
VAULT_PATH   = "~/Obsidian"    # path to your vault
```

See the [Configuration](#configuration) section for all options.

**5. Start Ollama**
```bash
# basic
ollama serve

# with parallel requests enabled (recommended for generate_insights.py)
OLLAMA_NUM_PARALLEL=5 ollama serve 2>/dev/null &
```

---

## Scripts

### `generate_insights.py` — Weekly or monthly insight report

Reads all notes modified in the last `DAYS_BACK` days and runs them through 5 analysis lenses in parallel, then writes a synthesis note.

**Lenses:**
- **Therapist** — emotional patterns, mood, stress signals
- **Coach** — productivity, goals, tasks completed or stalled
- **Pattern Detector** — recurring phrases, deferred intentions, cycles
- **Strengths** — wins and growth you may have dismissed
- **Connections** — links between seemingly unrelated notes

```bash
python generate_insights.py
```

Output: `Vault/Insights/YYYY-MM-DD Week Insight.md`

To switch to monthly: set `DAYS_BACK = 30` in `config.py`.

---

### `morning_briefing.py` — Daily briefing

Reads notes modified in the last 24 hours and generates a briefing with:
- What you worked on yesterday
- Pending and unfinished tasks found in your notes
- Suggested focus for today
- List of modified notes as wikilinks

```bash
python morning_briefing.py
```

Output: `Vault/Briefings/YYYY-MM-DD Morning Briefing.md`

Best run automatically every morning via cron, see [Automation](#automation).

---

### `study_recap.py` — Study session recap

After a study session, generates a structured recap with key concepts and review questions for spaced repetition. Also finds connections to other notes in your vault.

```bash
python study_recap.py
```

The script auto-detects notes modified in the last `HOURS_BACK` hours and shows them for confirmation. You can add or remove notes before generating:

```
auto-detected notes (modified in last 4h):
  1. CICD.md (14:32)
  2. GitHub Actions.md (15:01)

commands:
  add filename.md  → add a note
  rm <number>      → remove a note
  done             → start generating

> add BoxdMetrics.md
> rm 2
> done
```

Output: `Vault/Study Recaps/YYYY-MM-DD HH-MM Recap — NoteName.md`

---

### `txt_to_notes.py` — Text to Obsidian notes

Converts any text file into one or more structured Obsidian notes. Works with conversations, meeting notes, articles, braindumps — anything.

```bash
python txt_to_notes.py input.txt
```

**Two-pass process:**
1. First pass analyzes the text and decides how many notes to create, planning titles and tags
2. Second pass writes each note with full content, reusing your existing vault tags and creating wikilinks between notes and to existing vault notes

**Optional instructions block** - add at the top of your `.txt` file to guide the output:
```
---instructions---
This is a technical conversation. Write in first person. Focus on what I built and learned.
---end---

(your content here)
```

Output: `Vault/Captures/title/` all notes from the same dump go into one subfolder.

---

## Configuration

All settings are in `config.py`. You only need to edit this file.

```python
# Model
OLLAMA_MODEL = "llama3.1:8b"        # model name
TEMPERATURE  = 0.2                   # 0.0 = deterministic, 1.0 = creative. Keep low for factual output.

# API
OLLAMA_API_URL = "http://localhost:11434/api/generate"  # change if Ollama runs on a different host
TIMEOUT        = 600                 # seconds to wait per request. Increase for slow hardware.
KEEP_ALIVE     = "10m"              # how long model stays loaded after last request
NUM_CTX        = 8192               # context window in tokens. Higher = more notes fit but uses more RAM.

# Vault
VAULT_PATH     = "~/Obsidian"       # path to your vault

# Behaviour
DAYS_BACK      = 7                  # generate_insights: 7 = weekly, 30 = monthly
HOURS_BACK     = 4                  # study_recap: hours to look back for recent notes
MAX_NOTE_CHARS = 2000               # characters read per note
MAX_NOTES      = 200                # max notes indexed from vault
TOP_N_NOTES    = 15                 # relevant notes injected per query
```

---

## Automation

Run insights weekly and briefing daily using cron:

```bash
crontab -e
```

```
OLLAMA_NUM_PARALLEL=5
PATH=/usr/local/bin:/usr/bin:/bin

# weekly insights — every sunday at 8am
0 8 * * 0 /path/to/vaultmind/venv/bin/python /path/to/vaultmind/generate_insights.py

# morning briefing — every day at 8am
0 8 * * * /path/to/vaultmind/venv/bin/python /path/to/vaultmind/morning_briefing.py
```

Replace `/path/to/vaultmind` with the actual path, e.g. `/home/paulo/vaultmind`.

---

## GPU acceleration

Ollama uses your GPU automatically if available. To verify:
```bash
ollama ps
# look for: PROCESSOR (100% CPU/GPU)
```

If it shows `100% CPU` and you have a GPU:

**AMD (Linux):**
```bash
# Arch
sudo pacman -S rocm-opencl-runtime rocm-hip-runtime

# Ubuntu
sudo apt install rocm-opencl-runtime
```

**NVIDIA:**
```bash
# install CUDA — then restart Ollama
```

With a GPU, generation time drops from ~3 min/call to ~20-30 sec/call.

---

## A note on accuracy

- All prompts use `temperature: 0.2` low randomness, more factual output
- Every prompt includes: *"Only use information explicitly present in the notes. Do not infer or invent."*
- The model can still hallucinate, especially on long or ambiguous notes
- Treat insight reports as starting points for reflection, not as ground truth
- Scripts work best when your notes and your questions are in the same language

---

## Customizing prompts

All prompts are stored in `prompts.json`. You can edit them without touching any Python code.

- Change the insight lens instructions to focus on what matters to you
- Add or remove sections from the morning briefing
- Change the language or tone of any output
- Add new lenses to `insights.lenses` the script picks them up automatically

---

## Project structure

```
vaultmind/
├── config.py              # all settings
├── prompts.json           # all prompts
├── ai_backend.py          # shared Ollama caller used by all scripts
├── generate_insights.py   # weekly/monthly insight report
├── morning_briefing.py    # daily morning briefing
├── study_recap.py         # study session recap with review questions
├── txt_to_notes.py        # converts any text into Obsidian notes
└── README.md
```

---

## License

MIT
