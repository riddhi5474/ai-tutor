"""
config.py
─────────
Central configuration for the AI Tutor.
Edit this file to change models, paths, or chunking settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR          = Path(__file__).parent
COURSE_MATERIALS  = BASE_DIR / "course_materials"   # Drop PDFs/PPTX here
CLEANED_TEXT_DIR  = BASE_DIR / "cleaned_text"       # Parsed text output
OUTPUT_DIR        = BASE_DIR / "output"             # Saved guides, FAQs, etc.

# Local app data (SQLite + per-conversation uploads); gitignored in development
DATA_DIR          = BASE_DIR / "data"
STORAGE_ROOT      = DATA_DIR / "storage"            # data/storage/<conversation_id>/...
DB_PATH           = DATA_DIR / "ai_tutor.db"

for _dir in (COURSE_MATERIALS, CLEANED_TEXT_DIR, OUTPUT_DIR, DATA_DIR, STORAGE_ROOT):
    _dir.mkdir(parents=True, exist_ok=True)

# ── Model Settings ────────────────────────────────────────────────────────────
GEMINI_MODEL      = "models/gemini-2.5-flash"
EMBED_MODEL       = "BAAI/bge-small-en-v1.5"
LLM_TEMPERATURE   = 0.1

# ── RAG / Chunking ────────────────────────────────────────────────────────────
CHUNK_SIZE        = 512
CHUNK_OVERLAP     = 50
SIMILARITY_TOP_K  = 5

# ── Follow-up Suggestions ─────────────────────────────────────────────────────
NUM_FOLLOWUP_QUESTIONS = 3

# ── Chat UI ───────────────────────────────────────────────────────────────────
# Optional: set CHAT_INPUT_PLACEHOLDER in .env (leave unset for no placeholder text)
CHAT_INPUT_PLACEHOLDER = (os.getenv("CHAT_INPUT_PLACEHOLDER") or "").strip()
