"""
features/faq.py
───────────────
Generates a Frequently Asked Questions document for a topic
using the RAG tutor as the knowledge source.
"""

from typing import Any, Dict

from core.tutor import AITutor


_TEMPLATE = """Create an FAQ document about: {topic}

Generate {n} Q&A pairs sourced from the course materials.

Format each pair as:
Q: [Question]
A: [Concise 2-3 sentence answer]

Base answers ONLY on the course materials provided."""


def generate_faq(topic: str, tutor: AITutor, num_questions: int = 5) -> Dict[str, Any]:
    """Generate an FAQ for `topic` with ``num_questions`` entries.

    Returns the same shape as ``AITutor.query`` (``response`` + ``source_nodes``).
    """
    prompt = _TEMPLATE.format(topic=topic, n=num_questions)
    return tutor.query(prompt, response_format="explanation")
