"""
main.py
───────
Entry point for the AI Tutor.

Usage:
    python main.py

Steps:
  1. Parses all PDFs / PPTX files in course_materials/
  2. Builds a RAG index from the parsed text
  3. Starts an interactive CLI session
"""

from core   import SimpleDocParser, AITutor
from utils  import interactive_tutor_session


def main():
    # ── Step 1: Parse course materials ────────────────────────────────────────
    parser = SimpleDocParser()
    parser.process_folder()

    # ── Step 2: Build the AI tutor ────────────────────────────────────────────
    tutor = AITutor()

    # ── Step 3: Start interactive session ─────────────────────────────────────
    interactive_tutor_session(tutor)


if __name__ == "__main__":
    main()
