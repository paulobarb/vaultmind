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

* **Llama 3.1 (8B):** The recommended default. Excellent at following the "Note Generator" persona.
* **DeepSeek-R1 (8B):** Superior for the `generate_insights.py` script due to its advanced reasoning and low hallucination rate.
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
ollama pull llama3.1:8b
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

### `morning_briefing.py`

**Frequency:** Daily

Summarizes the last 24 hours of activity. Identifies empty checkboxes and suggests a specific focus for your day.

```bash
python morning_briefing.py
```

---

### `generate_insights.py`

**Frequency:** Weekly or Monthly

Runs your notes through five parallel lenses (Therapist, Coach, Pattern Detector, Strengths, Connections). Provides a deep-dive synthesis of your mental and professional state.

```bash
python generate_insights.py
```

---

### `study_recap.py`

**Frequency:** Post-study

Extracts key concepts and generates review questions from recently modified educational notes to assist in spaced repetition.

```bash
python study_recap.py
```

---

### `txt_to_notes.py`

**Frequency:** As needed

First plans a note structure (tags, titles), then writes the full content and links it to existing notes in your vault.

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
