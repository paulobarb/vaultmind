# Vaultmind

**Vaultmind** is a local AI tool for Obsidian. It transforms your static notes into an active knowledge base by generating automated insights, daily briefings, and study aids. All powered by [Ollama](https://ollama.com).

[![vaultmind demo](https://img.youtube.com/vi/hqVmcqMPpUE/maxresdefault.jpg)](https://www.youtube.com/watch?v=hqVmcqMPpUE)
---

## Key Features

- **Weekly/Monthly Insights:** Multi-lens analysis (Emotional, Productivity, Patterns) of your recent activity.
- **Daily Morning Briefings:** Summarizes yesterday's progress and extracts pending tasks for today.
- **Intelligent Study Recaps:** Automatically generates spaced-repetition questions and finds connections to older notes.
- **Smart Ingestion:** A two-pass engine that converts raw text dumps and transcripts into structured, tagged Obsidian notes.

---

## Hardware Requirements & Ollama models

Vaultmind performance depends entirely on your local LLM runner (Ollama).

> **Tip:** If you are unsure what your specific hardware can handle, check the [LLM Hardware Requirements Guide](https://onyx.app/llm-hardware-requirements) for a detailed breakdown of parameters vs. VRAM.

While Ollama supports hundreds of models, Vaultmind has been specifically tested with the following:

* **DeepSeek-R1 (8B):** The recommended default. Superior for the `generate_insights.py` script due to its advanced reasoning and low hallucination rate.
* **Llama 3.1 (8B):** Runs a little faster but with a little less accuracy.
* **Llama 3.2 (3B):** Optimized (kinda) for edge devices and systems without dedicated GPUs.

**Disclaimer:** Using models not listed above may result in unexpected output formats, conversational "chatter", or failure to parse the JSON planning phase in `txt_to_notes.py`.

---

## Installation

### 1. Prerequisites

- [Ollama](https://ollama.com) installed and running
- Python 3.10 or higher

### 2. Setup

```bash
# Clone the repository
git clone https://github.com/paulobarb/vaultmind.git
cd vaultmind

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install requests
```

### 3. Initialize Model

Choose a model:

```bash
ollama pull deepseek-r1:latest
```

---

## Configuration

Vaultmind is customizable via `config.py`.

| Setting | Description |
| :--- | :--- |
| `VAULT_PATH` | Absolute path to your Obsidian vault |
| `NUM_CTX` | Context window size — increase for long notes, decrease if you encounter VRAM spillover |
| `TEMPERATURE` | `0.2` for factual briefings, `0.7` for more creative insights |
| `EXCLUDED_FOLDERS` | List of folders the AI should ignore (e.g. Templates, Archive) |

---

## The Toolkit

### ☀️ Morning Briefing (`morning_briefing.py`)

The Daily Momentum Builder

- It categorizes notes into "Yesterday" (execution) and "Today" (planning). It scans for unfinished tasks (empty checkboxes) and unresolved thoughts.
- It provides a "Suggested Focus," acting as a bridge between the work you finished and the work you haven't started yet, ensuring you never wake up with a "cold start" in your vault.

```bash
python generate_insights.py
```

---

### 📊 Weekly Insights (`generate_insights.py`)

It uses a Parallel Processing model to run your notes through multiple "lenses" (like a Therapist or a Pattern Detector) simultaneously to save time.

- It reads a file called AI_State.md at startup. This file contains a compressed history of who you were last week.
- The AI compares your current notes against that state to identify "drift"—checking if you are actually making progress on your goals or just repeating the same cycles. It then updates the state file, making the AI following your journey every time you run it.

```bash
python generate_insights.py
```

---

### 🧠 Study Recap (`study_recap.py`)

This is an Interactive Tool designed to fight the "forgetting curve". Unlike the other scripts, this one waits for your input.

- It auto-detects notes modified in a specific window (e.g., your last 24 hours of studying) and lets you manually refine the list. It then cross-references these with the rest of your vault to find "hidden connections."
- The Result: It generates a dedicated recap note filled with Spaced Repetition questions. It transforms passive reading into active testing.

```bash
python study_recap.py
```

---

### 📥 TXT to Notes (txt_to_notes.py`)

This script handles the "messy" data—transcripts, braindumps, or long articles. It uses a Plan-then-Execute architecture to prevent the AI from getting lost in long texts.

- Pass 1 (Planning): The AI reads the raw text and creates a JSON "blueprint." It decides how many notes are needed, what the titles should be, and which existing tags from your vault to reuse.
- Pass 2 (Writing): Using that blueprint, it writes the actual content, automatically creating [[Wikilinks]] between the new notes and your existing knowledge base.

```bash
python txt_to_notes.py my_transcript.txt
```

---

## Customization

Edit `prompts.json` to change how the AI speaks or what it focuses on.

---

## Automation (Linux / macOS)

Add scripts to your crontab to have briefings waiting every morning (only works if you have your machine 24/7 on):

```bash
# Run morning briefing at 7:00 AM daily
0 7 * * * /path/to/vaultmind/venv/bin/python /path/to/vaultmind/morning_briefing.py

# Run weekly insights every Sunday at 8:00 AM
0 8 * * 0 /path/to/vaultmind/venv/bin/python /path/to/vaultmind/generate_insights.py
```

---

## Limitations & Accuracy

- **Context Limits:** Very long notes may require increasing `NUM_CTX` in `config.py`.
- **Local Speed:** Performance is tied to your hardware. Large-scale analysis is significantly faster with a dedicated GPU.

---

## License

MIT
