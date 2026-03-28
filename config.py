# =============================================================
# AI & API PROVIDER SETTINGS
# =============================================================

# -- NVIDIA NIM --
USE_NVIDIA_NIM = False # Change to True if you want to use NVIDIA NIM
NVIDIA_API_KEY = "nvapi-xxxxxx" # Your API KEY here
NVIDIA_MODEL   = "meta/llama-3.3-70b-instruct" # Chose your model
                # meta/llama-3.3-70b-instruct was the only model tested

# -- Ollama --
OLLAMA_MODEL   = "llama3.1:8b" # Ollama model   
OLLAMA_API_URL = "http://localhost:11434/api/generate"  
TIMEOUT        = 1000           
KEEP_ALIVE     = "10m"          

# Context Window
# 8192 is safe for almost all local models (Gemma, Llama 3) and standard laptops.
# You can use for example 32768 or 65536 for Llama 3.1, but requires 16GB+ of RAM.
NUM_CTX        = 8192   

# -- Temperature Tuning --
# 0.0-0.3: Rigid/Factual | 0.4-0.7: Balanced | 0.8-1.0: Creative
TEMPERATURES = {
    "default":  0.2,  # Global fallback 

    # Replace 'None' with a float (0.0-1.0) to override "default". 
    "insights": None,  # generate_insights.py
    "briefing": None,  # morning_briefing.py
    "recap":    None,  # study_recap.py
    "txt":      None,  # txt_to_notes.py
    "chat":     None   # chat.py
}


# =============================================================
# VAULT & GLOBAL LIMITS
# =============================================================

VAULT_PATH        = "~/Obsidian" # Path to your Obsidian vault. 
MAX_FILE_SIZE     = 1_000_000    # 1MB max per file, skip larger ones
MAX_NOTE_CHARS    = 8000         # Max characters read per note
MAX_CONTENT_NOTES = 12           # Max files sent to AI per query

# add any folder you want to ignore here 
EXCLUDED_FOLDERS = [
    "Briefings",
    "Insights", 
    "Study Recaps",
    "Captures",
    "MOC",
    "Templates",
    # "Archive",
]


# =============================================================
# SCRIPT SETTINGS
# =============================================================

# -- Vault Chat (chat.py) --
SAVE_CHAT_HISTORY = True         # If True, saves chat to SQLite database
HISTORY_LIMIT     = 12            # Past messages to send for context

# -- Insights Generator (generate_insights.py) --
DAYS_BACK            = 7         # 7 = weekly report, 30 = monthly report
INSIGHT_TITLE_FORMAT = "{date} {period} Insight.md"     # Change here how would you like your title
                                                        # Placeholders: {date}, {period} 

INSIGHTS_DIR_NAME = "Insights"  # Set the folder name for Insights notes

# Words that trigger specific tags 
CANDIDATES = {
    "productivity":  ["productiv", "task", "goal", "work", "focus"],
    "mood":          ["mood", "emotion", "feel", "stress", "anxiet", "happy"],
    "philosophy":    ["meaning", "values", "purpose", "reflect", "life"],
    "habits":        ["habit", "routine", "pattern", "repeat", "daily"],
    "health":        ["health", "sleep", "exercise", "energy", "body"],
    "projects":      ["project", "build", "code", "ship", "launch", "develop"],
    "relationships": ["friend", "family", "partner", "social", "connect"],
    # "finances": ["money", "budget", "spend", "invest", "finance"], 
}


# -- Morning Briefing (morning_briefing.py) --
BRIEFING_TITLE_FORMAT = "{date} Morning Briefing.md"    # Change here how would you like your title
                                                        # Placeholders: {date} 

BRIEFING_DIR_NAME = "Briefings" # Set the folder name for Morning Briefings


# -- Study Recap (study_recap.py) --
HOURS_BACK         = 1          # How many hours back to auto-detect notes
RECAP_TITLE_FORMAT = "{date} ({time}) Study Recap — {subject}.md"   # Change here how would you like your title
                                                                    # Placeholders: {date}, {time}, {subject} 

STUDY_DIR_NAME    = "Study Recaps"  # Set the folder name for Study Recap


# -- TXT to Notes (txt_to_notes.py) --
TXT_TITLE_FORMAT = "{title}.md"     # Change here how would you like your title
                                    # Placeholders: {title} 

CAPTURES_DIR_NAME = "Captures"  # Set the folder name for TXT to Notes


# -- MOC Generator (moc_generator.py) --
MOC_DIR_NAME = "MOC"    # Change here how would you like your title
                        # Placeholders: {title}

MOC_TITLE_FORMAT = "{title} MOC"    # Set the folder name for MOC Generator