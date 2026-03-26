# -------------------------------------------------------------
# Model Configuration
# -------------------------------------------------------------
OLLAMA_MODEL = "llama3.1:8b"    # Ollama model to use

# Temperature controls the randomness and creativity of the AI.
#   - 0.0 to 0.3: Rigid, factual, analytical (Good for summaries/coding)
#   - 0.4 to 0.7: Balanced, conversational (Good for general writing)
#   - 0.8 to 1.0: Highly creative, unpredictable (Good for brainstorming)
TEMPERATURES = {
    "default":  0.2,  # The global fallback
    
    # Specific script overrides. 
    # Replace 'None' with a float (0.0-1.0) to override.
    "insights": None, 
    "briefing": None, 
    "recap":    None, 
    "txt":      None, 
}

# -------------------------------------------------------------
# Vault Configuration
# -------------------------------------------------------------
VAULT_PATH = "~/Obsidian"       # Path to your Obsidian vault.

# -------------------------------------------------------------
# Script Behaviour
# -------------------------------------------------------------
DAYS_BACK      = 7              
HOURS_BACK     = 24             
MAX_NOTE_CHARS = 2000           
MAX_FILE_SIZE  = 1_000_000  
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
]
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


# -------------------------------------------------------------
# API Configuration
# -------------------------------------------------------------
OLLAMA_API_URL = "http://localhost:11434/api/generate"  
TIMEOUT        = 1000           
KEEP_ALIVE     = "10m"          
NUM_CTX        = 8192           