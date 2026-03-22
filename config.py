# -------------------------------------------------------------
# Model Configuration
# -------------------------------------------------------------
OLLAMA_MODEL = "llama3.1:8b"    # Ollama model to use
                                # Recommended: llama3.1:8b, deepseek-r1:8b, llama3.2:3b

TEMPERATURE  = 0.2              # Controls randomness. Lower = more factual, less hallucination.
                                # Range: 0.0 (deterministic) to 1.0 (creative). Default: 0.2

# -------------------------------------------------------------
# API Configuration
# -------------------------------------------------------------
OLLAMA_API_URL = "http://localhost:11434/api/generate"  # Ollama API endpoint

TIMEOUT        = 1000           # Max seconds to wait for a response per call.
                                # Increase for slow hardware or large prompts. Default: 1000

KEEP_ALIVE     = "10m"          # How long Ollama keeps the model loaded after last request.
                                # Format: "5m", "1h", "0" (unload immediately). Default: "10m"

NUM_CTX        = 8192           # Context window size in tokens.
                                # Higher = more notes fit in prompt but uses more RAM.
                                # Recommended: 4096 (fast) to 16384 (large vaults). Default: 8192

# -------------------------------------------------------------
# Vault Configuration
# -------------------------------------------------------------
VAULT_PATH = "~/Obsidian"       # Path to your Obsidian vault. Supports ~ for home directory.

# -------------------------------------------------------------
# Script Behaviour
# -------------------------------------------------------------
DAYS_BACK      = 7              # generate_insights.py: how many days back to collect notes.
                                # 7 = weekly report, 30 = monthly report.

HOURS_BACK     = 24             # study_recap.py: how many hours back to auto-detect notes.

MAX_NOTE_CHARS = 2000           # Max characters read per note. Higher = more detail but slower.

MAX_FILE_SIZE = 1_000_000  # 1MB max per file, skip larger ones

#--------------------------------------------------------------
# Ignore Folders
#--------------------------------------------------------------
EXCLUDED_FOLDERS = [
    "Briefings",
    "Insights", 
    "Study Recaps",
    "Captures",
    # add any folder you want to exclude here
    # "Templates",
    # "Archive",
]
