"""
Wolfram Alpha API helper.
Uses Short Answers API endpoint for easy plain-text responses.
"""

from __future__ import annotations

import requests


def _wolfram_short(query: str, app_id: str, timeout_sec: float) -> str:
    resp = requests.get(
        "https://api.wolframalpha.com/v1/result",
        params={"i": query, "appid": app_id.strip()},
        timeout=timeout_sec,
    )
    if resp.status_code == 200:
        return resp.text.strip()
    if resp.status_code == 501:
        raise ValueError("Wolfram could not interpret that query.")
    if resp.status_code == 403:
        raise ValueError("Invalid Wolfram AppID.")
    raise RuntimeError(f"Wolfram API error: HTTP {resp.status_code} - {resp.text[:200]}")


def _wolfram_full(query: str, app_id: str, timeout_sec: float) -> str:
    resp = requests.get(
        "https://api.wolframalpha.com/v2/query",
        params={
            "input": query,
            "appid": app_id.strip(),
            "output": "JSON",
            "format": "plaintext",
        },
        timeout=timeout_sec,
    )
    if resp.status_code == 403:
        raise ValueError("Invalid Wolfram AppID.")
    resp.raise_for_status()

    data = resp.json().get("queryresult", {})
    if not data.get("success", False):
        raise ValueError("Wolfram could not interpret that query.")

    pods = data.get("pods", []) or []
    lines = []
    for pod in pods[:6]:
        title = (pod.get("title") or "").strip()
        subpods = pod.get("subpods") or []
        texts = []
        for sp in subpods:
            t = (sp.get("plaintext") or "").strip()
            if t:
                texts.append(t)
        if texts:
            if title:
                lines.append(f"{title}:")
            lines.append("\n".join(texts[:2]))
            lines.append("")

    output = "\n".join(lines).strip()
    if not output:
        raise ValueError("Wolfram returned no plaintext result.")
    return output


def wolfram_short_answer(query: str, app_id: str, timeout_sec: float = 12.0) -> str:
    if not query.strip():
        raise ValueError("Query is empty.")
    if not app_id.strip():
        raise ValueError("Wolfram AppID is required.")

    raw_query = query.strip()
    ql = raw_query.lower()
    wants_short = " short" in ql or ql.startswith("short:")
    cleaned_query = (
        raw_query.replace("short:", "", 1).replace(" short answer", "").replace(" short", "").strip()
        if wants_short
        else raw_query
    )

    # Default behavior: full result (pods/plaintext). Explicit "short" switches to v1/result.
    if wants_short:
        return _wolfram_short(cleaned_query, app_id, timeout_sec)

    try:
        return _wolfram_full(cleaned_query, app_id, timeout_sec)
    except Exception:
        # If full parsing fails for a query, fallback to short answer instead of hard-failing.
        return _wolfram_short(cleaned_query, app_id, timeout_sec)
