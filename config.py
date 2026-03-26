# -------------------------------------------------------------
# Model Configuration
# -------------------------------------------------------------
OLLAMA_MODEL = "llama3.1:8b"    # Ollama model to use

# Temperature controls the randomness and creativity of the AI.
#   - 0.0 to 0.3: Rigid, factual, analytical (Good for summaries/coding)
#   - 0.4 to 0.7: Balanced, conversational (Good for general writing)
#   - 0.8 to 1.0: Highly creative, unpredictable (Good for brainstorming)
TEMPERATURES = {
    # The global fallback used if a script doesn't have a specific setting.
    "default":  0.2,  
    
    # Specific script overrides. 
    # Replace 'None' with a float to override the default.
    "insights": None, # generate_insights.py
    "briefing": None, # morning_briefing.py
    "recap":    None, # study_recap.py
    "txt":      None, # txt_to_notes.py
}

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

MAX_FILE_SIZE = 1_000_000       # 1MB max per file, skip larger ones

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

#--------------------------------------------------------------
# Tagging System (generate_insights.py)
#--------------------------------------------------------------
CANDIDATES = {
        "productivity":  ["productiv", "task", "goal", "work", "focus"],
        "mood":          ["mood", "emotion", "feel", "stress", "anxiet", "happy"],
        "philosophy":    ["meaning", "values", "purpose", "reflect", "life"],
        "habits":        ["habit", "routine", "pattern", "repeat", "daily"],
        "health":        ["health", "sleep", "exercise", "energy", "body"],
        "projects":      ["project", "build", "code", "ship", "launch", "develop"],
        "relationships": ["friend", "family", "partner", "social", "connect"],
        # "finances":    ["money", "budget", "spend", "invest", "finance"],
        # Words that trigger specific tags
    }

# -------------------------------------------------------------
# FILENAME FORMATS
# -------------------------------------------------------------
# Customize how your generated notes are named.
# Placeholders: {date}, {period}
INSIGHT_TITLE_FORMAT = "{date} {period} Insight.md"

# Placeholders: {date}
BRIEFING_TITLE_FORMAT = "{date} Morning Briefing.md"

# Placeholders: {date}, {time}, {subject}
RECAP_TITLE_FORMAT = "{date} ({time}) Study Recap — {subject}.md"

# Placeholders: {title}
TXT_TITLE_FORMAT = "{title}.md"