# -------------------------------------------------------------
# Model Configuration
# -------------------------------------------------------------
OLLAMA_MODEL = "llama3.1:8b"    # Ollama model to use

# --- AI BEHAVIOR ---
# Temperature controls the randomness and creativity of the AI.
#   - 0.0 to 0.3: Rigid, factual, analytical (Good for summaries/coding)
#   - 0.4 to 0.7: Balanced, conversational (Good for general writing)
#   - 0.8 to 1.0: Highly creative, unpredictable (Good for brainstorming)
TEMPERATURES = {
    "default":  0.2,  # The global fallback
    
    # Specific script overrides. Replace 'None' with a float (0.0-1.0) to override.
    "insights": None, 
    "briefing": None, 
    "recap":    None, 
    "txt":      None, 
}

# --- FILENAME FORMATS ---
# Customize how your generated notes are named.
INSIGHT_TITLE_FORMAT  = "{date} {period} Insight.md"
BRIEFING_TITLE_FORMAT = "{date} Morning Briefing.md"
RECAP_TITLE_FORMAT    = "{date} ({time}) Study Recap — {subject}.md"
TXT_TITLE_FORMAT      = "{title}.md"

# --- TAGGING SYSTEM ---
# Words that trigger specific tags during AI synthesis (for generate_insights.py)
CANDIDATES = {
    "productivity":  ["productiv", "task", "goal", "work", "focus"],
    "mood":          ["mood", "emotion", "feel", "stress", "anxiet", "happy"],
    "philosophy":    ["meaning", "values", "purpose", "reflect", "life"],
    "habits":        ["habit", "routine", "pattern", "repeat", "daily"],
    "health":        ["health", "sleep", "exercise", "energy", "body"],
    "projects":      ["project", "build", "code", "ship", "launch", "develop"],
    "relationships": ["friend", "family", "partner", "social", "connect"],
}

# -------------------------------------------------------------
# API Configuration
# -------------------------------------------------------------
OLLAMA_API_URL = "http://localhost:11434/api/generate"  
TIMEOUT        = 1000           
KEEP_ALIVE     = "10m"          
NUM_CTX        = 8192           

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

#--------------------------------------------------------------
# Ignore Folders
#--------------------------------------------------------------
EXCLUDED_FOLDERS = [
    "Briefings",
    "Insights", 
    "Study Recaps",
    "Captures",
]