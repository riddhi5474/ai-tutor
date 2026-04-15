"""
features/query.py
─────────────────
NotebookLM-style query: answer + source attribution + follow-up suggestions.
"""

from typing import Dict, List, Optional

from core.tutor import AITutor
from features.followup import suggest_followup_questions

_SEP = "=" * 70
_DIV = "-" * 70


def query_notebooklm_style(
    question: str,
    tutor: AITutor,
    show_sources: bool = True,
    conversation_history: Optional[List[dict]] = None,
    num_turns: int = 3,
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

    context_block = ""
    if conversation_history:
        # Keep the last N user and last N assistant messages directly, in original order.
        indexed_msgs: List[tuple[int, str, str]] = []
        for i, msg in enumerate(conversation_history):
            role = msg.get("role")
            content = (msg.get("content") or "").strip()
            if role in {"user", "ai"} and content:
                indexed_msgs.append((i, role, content))

        user_indices = [i for i, role, _ in indexed_msgs if role == "user"][-max(0, num_turns):]
        ai_indices = [i for i, role, _ in indexed_msgs if role == "ai"][-max(0, num_turns):]
        keep_indices = set(user_indices + ai_indices)

        selected = [item for item in indexed_msgs if item[0] in keep_indices]
        if selected:
            lines = ["Conversation context (recent messages):"]
            for _, role, content in selected:
                label = "User" if role == "user" else "Tutor"
                # Truncate long prior assistant answers to avoid prompt bloat.
                if role == "ai" and len(content) > 500:
                    content = content[:500].rstrip() + " ...[truncated]"
                lines.append(f"{label}: {content}")
            context_block = "\n".join(lines)

    instruction = (
        "Instruction: Use prior chat for continuity, but prioritize retrieved sources "
        "for factual claims."
    )
    full_query = (
        f"{instruction}\n\nCurrent question: {question}"
        if not context_block
        else f"{instruction}\n\n{context_block}\n\nCurrent question: {question}"
    )
    result = tutor.query(full_query)
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
