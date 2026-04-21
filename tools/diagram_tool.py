"""
Diagram generation helpers:
- Draft Mermaid syntax from topic/text using Gemini
- Render Mermaid via Kroki as SVG/PNG
"""

from __future__ import annotations

import requests
import google.generativeai as genai
import re


def _normalize_mermaid_text(text: str) -> str:
    t = (text or "").strip()
    t = t.replace("```mermaid", "").replace("```", "").strip()
    if t.lower().startswith("mermaid"):
        t = t.split("\n", 1)[1].strip() if "\n" in t else ""
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = t.replace("\t", "    ")
    t = t.replace("“", '"').replace("”", '"').replace("’", "'")
    # Mermaid flowcharts don't need semicolons; they can trigger parse issues.
    t = re.sub(r";\s*$", "", t, flags=re.MULTILINE)
    return t.strip()


def _quote_problematic_flowchart_labels(code: str) -> str:
    """
    Convert node labels like A[log2(cl+1)] -> A["log2(cl+1)"] when they contain
    characters Mermaid often misparses in plain [] labels.
    """
    def repl(match: re.Match) -> str:
        node = match.group(1)
        label = match.group(2).strip()
        # Already quoted label
        if label.startswith('"') and label.endswith('"'):
            return match.group(0)
        if re.search(r"[()+*/=<>{};]", label):
            safe = label.replace('"', '\\"')
            return f'{node}["{safe}"]'
        return match.group(0)

    # Match simple square labels only (A[...], node_1[...])
    out = re.sub(r"\b([A-Za-z0-9_]+)\[([^\]]+)\]", repl, code)

    # Convert parenthesis-style nodes to safe square-quoted labels when complex:
    #   A(Some text (with parens)) --> B
    # becomes:
    #   A["Some text (with parens)"] --> B
    def round_repl(match: re.Match) -> str:
        node = match.group(1)
        label = match.group(2).strip()
        safe = label.replace('"', '\\"')
        return f'{node}["{safe}"]'

    out = re.sub(
        r"\b([A-Za-z0-9_]+)\((.+?)\)(?=\s*(?:-->|---|==>|-.->|--\s|$))",
        round_repl,
        out,
        flags=re.MULTILINE,
    )
    return out


def generate_mermaid_diagram(
    topic: str,
    source_text: str,
    api_key: str,
    model_name: str,
    diagram_type: str = "flowchart",
) -> str:
    if not api_key.strip():
        raise ValueError("Gemini API key is required.")

    ctx = (source_text or "").strip()[:6000]
    if not ctx:
        ctx = topic.strip()
    if not ctx:
        raise ValueError("Provide a topic or source text.")

    genai.configure(api_key=api_key.strip())
    model = genai.GenerativeModel(model_name)
    prompt = f"""
Create a Mermaid {diagram_type} diagram for study notes.
Output only valid Mermaid code, no markdown fences, no explanations.
Prefer concise node labels and meaningful flow.

Topic: {topic or "study topic"}
Source:
{ctx}
"""
    resp = model.generate_content(prompt)
    text = _normalize_mermaid_text(getattr(resp, "text", "") or "")

    # Enforce a diagram header when model forgets it.
    if not any(text.startswith(h) for h in ("flowchart", "graph", "sequenceDiagram", "classDiagram", "stateDiagram")):
        text = "flowchart TD\n" + text
    return text


def repair_mermaid_diagram(mermaid_code: str, api_key: str, model_name: str) -> str:
    if not api_key.strip():
        raise ValueError("Gemini API key is required for Mermaid repair.")
    bad = _normalize_mermaid_text(mermaid_code)
    if not bad:
        raise ValueError("Mermaid code is empty.")

    genai.configure(api_key=api_key.strip())
    model = genai.GenerativeModel(model_name)
    prompt = f"""
Fix this Mermaid diagram so it is valid and renderable.
Return ONLY Mermaid code, no markdown fences and no explanation.
Keep the same meaning with minimal edits.

{bad}
"""
    resp = model.generate_content(prompt)
    fixed = _normalize_mermaid_text(getattr(resp, "text", "") or "")
    if not any(fixed.startswith(h) for h in ("flowchart", "graph", "sequenceDiagram", "classDiagram", "stateDiagram")):
        fixed = "flowchart TD\n" + fixed
    return fixed


def render_mermaid_with_kroki(mermaid_code: str, output_format: str = "svg") -> bytes:
    fmt = output_format.strip().lower()
    if fmt not in {"svg", "png"}:
        raise ValueError("output_format must be svg or png")
    cleaned = _normalize_mermaid_text(mermaid_code)
    cleaned = _quote_problematic_flowchart_labels(cleaned)
    if not cleaned:
        raise ValueError("Mermaid code is empty.")

    url = f"https://kroki.io/mermaid/{fmt}"
    resp = requests.post(url, data=cleaned.encode("utf-8"), timeout=20)
    if resp.status_code >= 400:
        detail = (resp.text or "").strip()
        if len(detail) > 500:
            detail = detail[:500] + "..."
        raise ValueError(f"Kroki render failed ({resp.status_code}). Mermaid syntax may be invalid. {detail}")
    return resp.content
