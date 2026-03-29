"""
features/study_guide.py
────────────────────────
Generates a structured study guide for a given topic
using the RAG tutor as the knowledge source.
"""

from core.tutor import AITutor


_TEMPLATE = """Create a comprehensive study guide on: {topic}

Structure:
## Overview
[2-3 sentence overview]

## Key Concepts
- Concept 1: definition and explanation
- Concept 2: definition and explanation

## Important Details
[Formulas, processes, algorithms]

## Common Misconceptions
[What students typically get wrong]

## Practice Questions
[3-4 questions with answers]

## Key Takeaways
[Summary bullets]

Base the guide ENTIRELY on the course materials provided."""


def generate_study_guide(topic: str, tutor: AITutor) -> str:
    """Generate a full study guide for `topic` using the tutor's knowledge base."""
    result = tutor.query(_TEMPLATE.format(topic=topic), response_format="notes")
    return result["response"]
