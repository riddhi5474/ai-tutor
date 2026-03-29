"""
features/followup.py
────────────────────
Generates contextual follow-up questions after an answer,
mimicking the NotebookLM "you might also ask" behaviour.
"""

from typing import List

import google.generativeai as genai

from config import GEMINI_API_KEY, NUM_FOLLOWUP_QUESTIONS

genai.configure(api_key=GEMINI_API_KEY)

_FALLBACK = [
    "Can you explain this in more detail?",
    "What are some real-world applications?",
    "How does this relate to other concepts?",
]


def suggest_followup_questions(
    question: str,
    answer: str,
    num: int = NUM_FOLLOWUP_QUESTIONS,
) -> List[str]:
    """Return `num` follow-up questions based on the Q&A pair."""

    prompt = f"""Based on this Q&A:
Q: {question}
A: {answer[:300]}...

Generate {num} natural follow-up questions a student would ask.
Make them specific and educational.
Format: numbered list 1-{num}, questions only."""

    try:
        model    = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)

        questions = []
        for line in response.text.splitlines():
            line = line.strip()
            for prefix in ["1.", "2.", "3.", "4.", "5.", "-", "•", "*"]:
                if line.startswith(prefix):
                    line = line[len(prefix):].strip()
                    break
            if line and "?" in line:
                questions.append(line)

        return questions[:num] or _FALLBACK[:num]

    except Exception:
        return _FALLBACK[:num]
