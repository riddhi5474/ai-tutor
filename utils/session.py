"""
utils/session.py
────────────────
Interactive CLI session — runs until the user types 'quit'.
All command dispatching lives here; feature logic stays in features/.
"""

from core.tutor import AITutor
from features.query       import query_notebooklm_style
from features.study_guide import generate_study_guide
from features.faq         import generate_faq

_SEP = "=" * 70

_HELP = """
📚 Commands:
  [question]        Ask anything from your course materials
  guide [topic]     Generate a structured study guide
  quiz  [topic]     Generate a 5-question multiple choice quiz
  faq   [topic]     Generate an FAQ document
  history           Show conversation history
  help              Show this menu
  quit              Exit
"""


def interactive_tutor_session(tutor: AITutor) -> None:
    """Start an interactive Q&A session in the terminal."""

    print(_SEP)
    print("🎓  AI TUTOR  –  NotebookLM Style")
    print(_SEP)
    print(_HELP)

    history = []   # list of {"question": ..., "answer": ...}

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            cmd = user_input.lower()

            # ── Exit ──────────────────────────────────────────────────────────
            if cmd in {"quit", "exit", "bye"}:
                print(f"\n{_SEP}")
                print("👋 Thanks for using AI Tutor!")
                print(f"📊 Questions answered this session: {len(history)}")
                print(_SEP)
                break

            # ── Help ──────────────────────────────────────────────────────────
            if cmd == "help":
                print(_HELP)
                continue

            # ── History ───────────────────────────────────────────────────────
            if cmd == "history":
                if not history:
                    print("\n  (no questions yet)\n")
                else:
                    print(f"\n📜 Conversation History\n{'-'*70}")
                    for i, item in enumerate(history, 1):
                        print(f"\n  [{i}] Q: {item['question']}")
                        print(f"       A: {item['answer'][:80]}...")
                    print(f"\n{'-'*70}\n")
                continue

            # ── Study Guide ───────────────────────────────────────────────────
            if cmd.startswith("guide "):
                topic = user_input[6:].strip()
                print(f"\n🔄 Generating study guide for: {topic}...\n")
                guide = generate_study_guide(topic, tutor)
                _print_block(f"📖 Study Guide: {topic}", guide)
                continue

            # ── Quiz ──────────────────────────────────────────────────────────
            if cmd.startswith("quiz "):
                topic = user_input[5:].strip()
                print(f"\n🔄 Generating quiz for: {topic}...\n")
                result = tutor.query(
                    f"Create a 5-question multiple choice quiz on: {topic}",
                    response_format="quiz",
                )
                _print_block(f"✏️  Quiz: {topic}", result["response"])
                continue

            # ── FAQ ───────────────────────────────────────────────────────────
            if cmd.startswith("faq "):
                topic = user_input[4:].strip()
                print(f"\n🔄 Generating FAQ for: {topic}...\n")
                faq = generate_faq(topic, tutor, num_questions=5)
                _print_block(f"❓ FAQ: {topic}", faq)
                continue

            # ── Regular question ──────────────────────────────────────────────
            print("\n🤔 Thinking...")
            result = query_notebooklm_style(user_input, tutor)
            history.append({"question": user_input, "answer": result["answer"]})

        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted — type 'quit' to exit.\n")
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


def _print_block(title: str, content: str) -> None:
    print(_SEP)
    print(title)
    print(_SEP)
    print(content)
    print(f"\n{_SEP}\n")
