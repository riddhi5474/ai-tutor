"""
utils/exporter.py
─────────────────
Saves generated content (study guides, FAQs, quizzes) to the output/ folder.
"""

from datetime import datetime
from pathlib import Path

from config import OUTPUT_DIR


def save_to_file(content: str, topic: str, content_type: str = "guide") -> Path:
    """
    Save `content` to output/<content_type>_<topic>_<timestamp>.txt

    Args:
        content:      Text to save.
        topic:        Topic name (used in filename).
        content_type: One of 'guide', 'faq', 'quiz', etc.

    Returns:
        Path to the saved file.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = topic.replace(" ", "_").lower()
    filename   = OUTPUT_DIR / f"{content_type}_{safe_topic}_{timestamp}.txt"

    filename.write_text(content, encoding="utf-8")
    print(f"💾 Saved → {filename}")
    return filename
