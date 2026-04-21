"""
LlamaIndex tool router for chat:
- computer algebra
- unit conversion
- Wolfram short answer
- Wikipedia summary
- optional RAG query over indexed course material
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List


def run_llamaindex_tool_router(
    question: str,
    tutor: Any,
    wolfram_app_id: str,
    run_computer_algebra,
    convert_units,
    wolfram_short_answer,
    wikipedia_summary,
) -> Dict[str, Any]:
    from llama_index.core import Settings
    from llama_index.core.agent import ReActAgent
    from llama_index.core.tools import FunctionTool
    from llama_index.llms.gemini import Gemini

    from config import GEMINI_API_KEY, GEMINI_MODEL, LLM_TEMPERATURE

    if Settings.llm is None:
        Settings.llm = Gemini(
            model=GEMINI_MODEL,
            api_key=GEMINI_API_KEY,
            temperature=LLM_TEMPERATURE,
        )

    def _refine_tool_call(user_question: str) -> Dict[str, Any]:
        """
        LLM-first query refinement for all tools.
        Returns a normalized JSON object, or {} if no confident mapping.
        """
        prompt = (
            "You convert user requests into a single tool call JSON.\n"
            "Return ONLY JSON (no markdown).\n"
            "Schema:\n"
            "{\n"
            '  "tool": "computer_algebra|unit_conversion|wolfram_short_answer|wikipedia_summary|course_rag_lookup|none",\n'
            '  "args": { ... }\n'
            "}\n"
            "Tool args:\n"
            '- computer_algebra: {"operation":"simplify|expand|factor|differentiate|integrate|solve|limit","expression":"...","variable":"x","at_value":0}\n'
            '- unit_conversion: {"value":1.0,"from_unit":"meter","to_unit":"foot"}\n'
            '- wolfram_short_answer: {"query":"..."}\n'
            '- wikipedia_summary: {"query":"...","sentences":8}\n'
            '- course_rag_lookup: {"query":"..."}\n'
            '- none: {}\n'
            "Rules:\n"
            "- Prefer course_rag_lookup for course-material questions.\n"
            "- Prefer computer_algebra for explicit symbolic math operations.\n"
            "- Prefer unit_conversion only for conversion requests.\n"
            "- Prefer wikipedia_summary for general background lookups.\n"
            "- Use wolfram_short_answer for hard computational/factual math/science.\n"
            "- If uncertain, choose none.\n\n"
            f"User request: {user_question}"
        )
        try:
            raw = str(Settings.llm.complete(prompt).text or "").strip()
            if not raw:
                return {}
            cleaned = raw
            if cleaned.startswith("```"):
                cleaned = cleaned.strip("`")
                cleaned = cleaned.replace("json", "", 1).strip()
            obj = json.loads(cleaned)
            if not isinstance(obj, dict):
                return {}
            return obj
        except Exception:
            return {}

    def _try_refined_execution(user_question: str) -> str | None:
        refined = _refine_tool_call(user_question)
        tool = str(refined.get("tool", "")).strip().lower()
        args = refined.get("args") or {}
        if not isinstance(args, dict):
            args = {}

        try:
            if tool == "computer_algebra":
                op = str(args.get("operation", "simplify"))
                expr = str(args.get("expression", "")).strip()
                if not expr:
                    return None
                var = str(args.get("variable", "x"))
                at_raw = args.get("at_value", 0.0)
                at_value = float(at_raw) if at_raw is not None else 0.0
                use_at = at_value if op.strip().lower() == "limit" else None
                return run_computer_algebra(expr, op, variable=var, at_value=use_at).output

            if tool == "unit_conversion":
                value = float(args.get("value", 1.0))
                from_unit = str(args.get("from_unit", "")).strip()
                to_unit = str(args.get("to_unit", "")).strip()
                if not from_unit or not to_unit:
                    return None
                return convert_units(value, from_unit, to_unit)

            if tool == "wolfram_short_answer" and wolfram_app_id.strip():
                query = str(args.get("query", "")).strip()
                if not query:
                    return None
                return wolfram_short_answer(query, wolfram_app_id)

            if tool == "wikipedia_summary":
                query = str(args.get("query", "")).strip()
                if not query:
                    return None
                sentences = int(args.get("sentences", 8))
                sentences = max(1, min(sentences, 12))
                return wikipedia_summary(query, sentences=sentences)

            if tool == "course_rag_lookup" and tutor is not None:
                query = str(args.get("query", user_question)).strip() or user_question
                out = tutor.query(query)
                return out["response"]
        except Exception:
            return None
        return None

    tools: List[Any] = []

    def algebra_tool(operation: str, expression: str, variable: str = "x", at_value: float = 0.0) -> str:
        op = operation.strip().lower()
        use_at = at_value if op == "limit" else None
        res = run_computer_algebra(expression, op, variable=variable, at_value=use_at)
        return res.output

    tools.append(
        FunctionTool.from_defaults(
            fn=algebra_tool,
            name="computer_algebra",
            description=(
                "Do symbolic math. operation must be one of simplify, expand, factor, "
                "differentiate, integrate, solve, limit."
            ),
        )
    )

    tools.append(
        FunctionTool.from_defaults(
            fn=convert_units,
            name="unit_conversion",
            description="Convert units, arguments: value, from_unit, to_unit.",
        )
    )

    if wolfram_app_id.strip():
        def wolfram_tool(query: str) -> str:
            return wolfram_short_answer(query, wolfram_app_id)

        tools.append(
            FunctionTool.from_defaults(
                fn=wolfram_tool,
                name="wolfram_short_answer",
                description="Use for hard computational or factual math/science questions.",
            )
        )

    def wikipedia_tool(query: str, sentences: int = 8) -> str:
        return wikipedia_summary(query, sentences=sentences)

    tools.append(
        FunctionTool.from_defaults(
            fn=wikipedia_tool,
            name="wikipedia_summary",
            description=(
                "Fetch general background context from Wikipedia. "
                "Use sentences argument for depth (default 8)."
            ),
        )
    )

    if tutor is not None:
        def rag_tool(query: str) -> str:
            out = tutor.query(query)
            return out["response"]

        tools.append(
            FunctionTool.from_defaults(
                fn=rag_tool,
                name="course_rag_lookup",
                description="Answer from uploaded course materials whenever course-specific context is needed.",
            )
        )

    system_prompt = (
        "You are an AI tutor with tools. "
        "Prefer course_rag_lookup for course-specific questions when available. "
        "Use computer_algebra or wolfram_short_answer for mathematical computation. "
        "Use unit_conversion only for conversion requests. "
        "Use wikipedia_summary for general background. "
        "Return clear concise answers."
    )

    # LLM-first structured refinement for all tool queries.
    refined_answer = _try_refined_execution(question)
    if refined_answer:
        return {"answer": str(refined_answer), "sources": [], "follow_ups": []}

    # Fallback: ReAct routing with tool descriptions.
    agent = ReActAgent(
        tools=tools,
        llm=Settings.llm,
        system_prompt=system_prompt,
        verbose=False,
    )
    run_out = agent.run(question)
    if hasattr(run_out, "__await__"):
        try:
            run_out = asyncio.run(run_out)
        except RuntimeError:
            # Fallback for environments with an active loop.
            loop = asyncio.new_event_loop()
            try:
                run_out = loop.run_until_complete(run_out)
            finally:
                loop.close()
    answer = str(getattr(run_out, "response", None) or run_out)
    return {"answer": answer, "sources": [], "follow_ups": []}
