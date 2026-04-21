"""
Wikipedia lookup helpers using Wikimedia REST APIs.
"""

from __future__ import annotations

import requests


def wikipedia_summary(query: str, sentences: int = 3) -> str:
    q = (query or "").strip()
    if not q:
        raise ValueError("Wikipedia query is empty.")

    headers = {
        # Wikimedia endpoints can reject generic clients without UA metadata.
        "User-Agent": "ai-tutor/1.0 (educational app; contact: local-app)",
        "Accept": "application/json",
    }

    # Prefer stable MediaWiki API for search + extract.
    search_url = "https://en.wikipedia.org/w/api.php"
    s_resp = requests.get(
        search_url,
        params={
            "action": "query",
            "list": "search",
            "srsearch": q,
            "srlimit": 1,
            "format": "json",
            "utf8": 1,
        },
        headers=headers,
        timeout=10,
    )
    s_resp.raise_for_status()
    search_hits = (s_resp.json().get("query") or {}).get("search") or []
    if not search_hits:
        return f"No Wikipedia article found for '{q}'."
    title = (search_hits[0].get("title") or "").strip()
    if not title:
        return f"No Wikipedia article found for '{q}'."

    extract_resp = requests.get(
        search_url,
        params={
            "action": "query",
            "prop": "extracts",
            "exintro": 1,
            "explaintext": 1,
            "titles": title,
            "format": "json",
            "utf8": 1,
        },
        headers=headers,
        timeout=10,
    )
    extract_resp.raise_for_status()
    pages = ((extract_resp.json().get("query") or {}).get("pages") or {})
    page = next(iter(pages.values()), {}) if pages else {}
    extract = (page.get("extract") or "").strip()

    # Fallback to REST summary if extract API returns empty.
    if not extract:
        summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
        resp = requests.get(summary_url, headers=headers, timeout=10)
        resp.raise_for_status()
        extract = (resp.json().get("extract") or "").strip()
    if not extract:
        return f"No summary available for '{title}'."

    # Keep summary concise for chat use.
    chunks = [s.strip() for s in extract.split(". ") if s.strip()]
    return ". ".join(chunks[: max(1, sentences)]).strip()
