"""
features/query.py
─────────────────
NotebookLM-style query: answer + source attribution + follow-up suggestions.
"""

from typing import Dict

from core.tutor import AITutor
from features.followup import suggest_followup_questions

_SEP = "=" * 70
_DIV = "-" * 70


def query_notebooklm_style(
    question: str,
    tutor: AITutor,
    show_sources: bool = True,
) -> Dict:
    """
    Query the tutor and display:
      • The answer
      • Top-3 source attributions with relevance scores
      • Suggested follow-up questions
    """
    print(f"\n{_SEP}")
    print(f"❓ {question}")
    print(_SEP)

    result   = tutor.query(question)
    answer   = result["response"]
    sources  = result["source_nodes"]
    followups = suggest_followup_questions(question, answer)

    print(f"\n📝 Answer:\n")
    print(answer)

    if show_sources and sources:
        print(f"\n📚 Sources:\n{_DIV}")
        for i, src in enumerate(sources[:3], 1):
            fname = src["metadata"].get("file_name", "Unknown")
            print(f"  [{i}] {fname}  ({src['score']:.0%} relevance)")
            print(f"      \"{src['text'][:100]}...\"")

    print(f"\n💭 You might also ask:\n{_DIV}")
    for i, q in enumerate(followups, 1):
        print(f"  {i}. {q}")

    print(f"\n{_SEP}\n")

    return {"answer": answer, "sources": sources, "follow_ups": followups}
