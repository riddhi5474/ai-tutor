"""
LlamaIndex tool router for chat:
- computer algebra
- unit conversion
- Wolfram short answer
- Wikipedia summary
- optional RAG query over indexed course material
"""

from __future__ import annotations

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

    agent = ReActAgent.from_tools(tools=tools, llm=Settings.llm, system_prompt=system_prompt, verbose=False)
    answer = str(agent.chat(question))
    return {"answer": answer, "sources": [], "follow_ups": []}
