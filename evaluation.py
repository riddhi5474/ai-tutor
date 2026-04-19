"""
evaluation.py
─────────────
Evaluation utilities for the AI Tutor conversation agent (tutoring + RAG).

This script is intentionally dependency-free (stdlib only) and focuses on:
- RAG grounding / citation proxy metrics from `messages.sources_json`
- Conversation quality proxies (turn counts, followups)
- Optional human labels for correctness + user satisfaction (CSAT/helpfulness)

Usage examples:
  python evaluation.py --db data/ai_tutor.db
  python evaluation.py --db data/ai_tutor.db --out-json reports/eval.json --out-csv reports/eval.csv
  python evaluation.py --db data/ai_tutor.db --labels data/labels.jsonl

Labels format (JSONL, one object per line), any of:
  {"conversation_id":"<id>", "assistant_message_id":"<mid>", "correctness":1, "csat":5}
  {"conversation_id":"<id>", "turn_index":3, "correctness":0.5, "csat":4}

Where:
  correctness ∈ {0, 0.5, 1} (fail/partial/success) or any float in [0,1]
  csat ∈ [1..5]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class Message:
    id: str
    conversation_id: str
    role: str
    content: str
    sources: List[dict]
    followups: List[str]
    created_at: str


def _safe_json_loads(s: Optional[str], default: Any) -> Any:
    if not s:
        return default
    try:
        return json.loads(s)
    except Exception:
        return default


def _mean(xs: List[float]) -> Optional[float]:
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return (sum(xs) / len(xs)) if xs else None


def _median(xs: List[float]) -> Optional[float]:
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
    return statistics.median(xs) if xs else None


def _pct(n: int, d: int) -> float:
    return float(n) / float(d) if d else 0.0


def _open_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def load_messages(conn: sqlite3.Connection, conversation_id: Optional[str] = None) -> List[Message]:
    params: Tuple[Any, ...] = tuple()
    where = ""
    if conversation_id:
        where = "WHERE conversation_id = ?"
        params = (conversation_id,)
    rows = conn.execute(
        f"""
        SELECT id, conversation_id, role, content, sources_json, followups_json, created_at
        FROM messages
        {where}
        ORDER BY conversation_id ASC, created_at ASC
        """,
        params,
    ).fetchall()
    out: List[Message] = []
    for r in rows:
        sources = _safe_json_loads(r["sources_json"], default=[])
        followups = _safe_json_loads(r["followups_json"], default=[])
        if not isinstance(sources, list):
            sources = []
        if not isinstance(followups, list):
            followups = []
        out.append(
            Message(
                id=str(r["id"]),
                conversation_id=str(r["conversation_id"]),
                role=str(r["role"]),
                content=str(r["content"] or ""),
                sources=sources,
                followups=followups,
                created_at=str(r["created_at"]),
            )
        )
    return out


def load_conversations(conn: sqlite3.Connection) -> List[dict]:
    rows = conn.execute(
        """
        SELECT id, title, created_at, updated_at, embedding_model, llm_model
        FROM conversations
        ORDER BY updated_at DESC
        """
    ).fetchall()
    return [dict(r) for r in rows]


def _extract_source_scores(sources: List[dict]) -> List[float]:
    scores: List[float] = []
    for s in sources:
        try:
            sc = float(s.get("score", 0.0))
            if math.isfinite(sc):
                scores.append(sc)
        except Exception:
            continue
    return scores


def _extract_source_filenames(sources: List[dict]) -> List[str]:
    names: List[str] = []
    for s in sources:
        md = s.get("metadata") or {}
        if isinstance(md, dict):
            fn = md.get("file_name") or md.get("filename") or md.get("source") or ""
            fn = str(fn).strip()
            if fn:
                names.append(fn)
    return names


def score_conversation(messages: List[Message]) -> dict:
    """
    Computes proxy metrics for one conversation.
    Assumptions:
      - AI turns include RAG sources in sources_json (from `core.tutor.AITutor.query`)
      - followups_json is list[str]
    """
    user_turns = [m for m in messages if m.role == "user"]
    ai_turns = [m for m in messages if m.role == "ai"]

    ai_with_sources = [m for m in ai_turns if len(m.sources or []) > 0]
    ai_with_followups = [m for m in ai_turns if len(m.followups or []) > 0]

    # RAG grounding proxies
    top1_scores: List[float] = []
    mean_scores: List[float] = []
    n_sources_per_ai: List[float] = []
    distinct_files: set[str] = set()
    unknown_file_hits = 0
    for m in ai_turns:
        scores = _extract_source_scores(m.sources or [])
        fns = _extract_source_filenames(m.sources or [])
        for fn in fns:
            distinct_files.add(fn)
            if fn.lower() in {"unknown", "source"}:
                unknown_file_hits += 1
        if m.sources is not None:
            n_sources_per_ai.append(float(len(m.sources)))
        if scores:
            top1_scores.append(max(scores))
            mean_scores.append(sum(scores) / len(scores))

    rag = {
        "ai_messages": len(ai_turns),
        "ai_with_sources": len(ai_with_sources),
        "source_coverage": _pct(len(ai_with_sources), len(ai_turns)),
        "avg_sources_per_ai": _mean(n_sources_per_ai),
        "median_sources_per_ai": _median(n_sources_per_ai),
        "avg_top1_retrieval_score": _mean(top1_scores),
        "avg_mean_retrieval_score": _mean(mean_scores),
        "distinct_source_files": len(distinct_files),
        "unknown_source_file_hits": unknown_file_hits,
    }

    convo = {
        "turns_total": len(messages),
        "turns_user": len(user_turns),
        "turns_ai": len(ai_turns),
        "turn_balance_user_ratio": _pct(len(user_turns), len(messages)),
        "avg_ai_chars": _mean([float(len(m.content or "")) for m in ai_turns]),
        "avg_user_chars": _mean([float(len(m.content or "")) for m in user_turns]),
        "ai_with_followups": len(ai_with_followups),
        "followup_coverage": _pct(len(ai_with_followups), len(ai_turns)),
        "avg_followups_per_ai": _mean([float(len(m.followups or [])) for m in ai_turns]),
    }

    # Simple overall score (0..100) based on correctness/user satisfaction being optional.
    # Here we prioritize grounding + conversational helpfulness proxies.
    grounding_score = 100.0 * (
        0.70 * rag["source_coverage"]
        + 0.20 * min(1.0, (rag["avg_sources_per_ai"] or 0.0) / 3.0)
        + 0.10 * min(1.0, (rag["distinct_source_files"] or 0) / 4.0)
    )
    followup_score = 100.0 * (
        0.70 * convo["followup_coverage"]
        + 0.30 * min(1.0, (convo["avg_followups_per_ai"] or 0.0) / 3.0)
    )
    proxy_overall = 0.70 * grounding_score + 0.30 * followup_score

    return {
        "rag": rag,
        "conversation": convo,
        "proxy_overall_score": proxy_overall,
    }


def _read_jsonl(path: Path) -> List[dict]:
    items: List[dict] = []
    if not path.exists():
        return items
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        items.append(json.loads(line))
    return items


def attach_labels(
    conv_id: str,
    ai_turns: List[Message],
    labels: List[dict],
) -> dict:
    """
    Aggregate labels per conversation.
    Supports labeling by assistant_message_id, or by turn_index within AI turns (0-based).
    """
    by_mid: Dict[str, dict] = {}
    by_ai_index: Dict[int, dict] = {}
    for it in labels:
        if str(it.get("conversation_id", "")) != conv_id:
            continue
        mid = it.get("assistant_message_id")
        if mid:
            by_mid[str(mid)] = it
        if "turn_index" in it:
            try:
                by_ai_index[int(it["turn_index"])] = it
            except Exception:
                pass

    correctness_vals: List[float] = []
    csat_vals: List[float] = []
    matched = 0
    for i, m in enumerate(ai_turns):
        lab = by_mid.get(m.id) or by_ai_index.get(i)
        if not lab:
            continue
        matched += 1
        if "correctness" in lab:
            try:
                v = float(lab["correctness"])
                if math.isfinite(v):
                    correctness_vals.append(max(0.0, min(1.0, v)))
            except Exception:
                pass
        if "csat" in lab:
            try:
                v = float(lab["csat"])
                if math.isfinite(v):
                    csat_vals.append(max(1.0, min(5.0, v)))
            except Exception:
                pass

    return {
        "labels_matched_ai_messages": matched,
        "correctness_mean": _mean(correctness_vals),
        "correctness_success_rate": _pct(sum(1 for v in correctness_vals if v >= 0.999), len(correctness_vals)),
        "csat_mean": _mean(csat_vals),
    }


def evaluate(
    db_path: Path,
    labels_path: Optional[Path] = None,
    conversation_id: Optional[str] = None,
) -> dict:
    with _open_db(db_path) as conn:
        conv_rows = load_conversations(conn)
        messages = load_messages(conn, conversation_id=conversation_id)

    conv_meta_by_id = {c["id"]: c for c in conv_rows}
    labels: List[dict] = _read_jsonl(labels_path) if labels_path else []

    # group messages by conversation
    by_conv: Dict[str, List[Message]] = {}
    for m in messages:
        by_conv.setdefault(m.conversation_id, []).append(m)

    conv_reports: List[dict] = []
    for cid, msgs in by_conv.items():
        base = score_conversation(msgs)
        meta = conv_meta_by_id.get(cid, {"id": cid, "title": "Unknown"})
        ai_turns = [m for m in msgs if m.role == "ai"]
        label_stats = attach_labels(cid, ai_turns, labels) if labels else None
        conv_reports.append(
            {
                "conversation_id": cid,
                "title": meta.get("title"),
                "created_at": meta.get("created_at"),
                "updated_at": meta.get("updated_at"),
                "embedding_model": meta.get("embedding_model"),
                "llm_model": meta.get("llm_model"),
                **base,
                **({"labels": label_stats} if label_stats is not None else {}),
            }
        )

    # overall aggregates
    all_source_coverage = [c["rag"]["source_coverage"] for c in conv_reports]
    all_followup_coverage = [c["conversation"]["followup_coverage"] for c in conv_reports]
    all_proxy = [c["proxy_overall_score"] for c in conv_reports]

    overall: Dict[str, Any] = {
        "conversations": len(conv_reports),
        "avg_source_coverage": _mean(all_source_coverage),
        "avg_followup_coverage": _mean(all_followup_coverage),
        "avg_proxy_overall_score": _mean(all_proxy),
    }

    if labels:
        correctness_means = [
            c.get("labels", {}).get("correctness_mean")
            for c in conv_reports
            if c.get("labels", {}).get("correctness_mean") is not None
        ]
        csat_means = [
            c.get("labels", {}).get("csat_mean")
            for c in conv_reports
            if c.get("labels", {}).get("csat_mean") is not None
        ]
        overall.update(
            {
                "labeled_conversations": sum(
                    1 for c in conv_reports if c.get("labels", {}).get("labels_matched_ai_messages", 0) > 0
                ),
                "avg_correctness_mean": _mean([float(x) for x in correctness_means if x is not None]),
                "avg_csat_mean": _mean([float(x) for x in csat_means if x is not None]),
            }
        )

    return {"overall": overall, "conversations": conv_reports}


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_csv(path: Path, conv_reports: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Flatten a subset of fields for easy spreadsheet use
    fieldnames = [
        "conversation_id",
        "title",
        "turns_total",
        "turns_user",
        "turns_ai",
        "source_coverage",
        "avg_sources_per_ai",
        "avg_top1_retrieval_score",
        "distinct_source_files",
        "followup_coverage",
        "avg_followups_per_ai",
        "proxy_overall_score",
        "labels_matched_ai_messages",
        "correctness_mean",
        "csat_mean",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for c in conv_reports:
            labels = c.get("labels") or {}
            w.writerow(
                {
                    "conversation_id": c.get("conversation_id"),
                    "title": c.get("title"),
                    "turns_total": c.get("conversation", {}).get("turns_total"),
                    "turns_user": c.get("conversation", {}).get("turns_user"),
                    "turns_ai": c.get("conversation", {}).get("turns_ai"),
                    "source_coverage": c.get("rag", {}).get("source_coverage"),
                    "avg_sources_per_ai": c.get("rag", {}).get("avg_sources_per_ai"),
                    "avg_top1_retrieval_score": c.get("rag", {}).get("avg_top1_retrieval_score"),
                    "distinct_source_files": c.get("rag", {}).get("distinct_source_files"),
                    "followup_coverage": c.get("conversation", {}).get("followup_coverage"),
                    "avg_followups_per_ai": c.get("conversation", {}).get("avg_followups_per_ai"),
                    "proxy_overall_score": c.get("proxy_overall_score"),
                    "labels_matched_ai_messages": labels.get("labels_matched_ai_messages"),
                    "correctness_mean": labels.get("correctness_mean"),
                    "csat_mean": labels.get("csat_mean"),
                }
            )


def main() -> int:
    p = argparse.ArgumentParser(description="Evaluate AI Tutor conversations (RAG + tutoring proxies).")
    p.add_argument("--db", type=str, default="data/ai_tutor.db", help="Path to SQLite DB (default: data/ai_tutor.db)")
    p.add_argument("--conversation-id", type=str, default="", help="Evaluate only one conversation id")
    p.add_argument("--labels", type=str, default="", help="Optional JSONL labels file (correctness/csat)")
    p.add_argument("--out-json", type=str, default="", help="Write full JSON report to this path")
    p.add_argument("--out-csv", type=str, default="", help="Write flattened CSV report to this path")
    args = p.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"DB not found: {db_path}")

    labels_path = Path(args.labels) if args.labels else None
    if labels_path and not labels_path.exists():
        raise SystemExit(f"Labels file not found: {labels_path}")

    report = evaluate(
        db_path=db_path,
        labels_path=labels_path,
        conversation_id=(args.conversation_id or None),
    )

    overall = report["overall"]
    print("\n=== AI Tutor Evaluation Summary ===")
    print(f"Conversations: {overall.get('conversations', 0)}")
    print(f"Avg source coverage: {overall.get('avg_source_coverage'):.3f}" if overall.get("avg_source_coverage") is not None else "Avg source coverage: n/a")
    print(f"Avg follow-up coverage: {overall.get('avg_followup_coverage'):.3f}" if overall.get("avg_followup_coverage") is not None else "Avg follow-up coverage: n/a")
    print(f"Avg proxy overall score: {overall.get('avg_proxy_overall_score'):.1f}" if overall.get("avg_proxy_overall_score") is not None else "Avg proxy overall score: n/a")
    if "avg_correctness_mean" in overall:
        print(f"Labeled conversations: {overall.get('labeled_conversations', 0)}")
        print(f"Avg correctness mean: {overall.get('avg_correctness_mean'):.3f}" if overall.get("avg_correctness_mean") is not None else "Avg correctness mean: n/a")
        print(f"Avg CSAT mean: {overall.get('avg_csat_mean'):.3f}" if overall.get("avg_csat_mean") is not None else "Avg CSAT mean: n/a")

    if args.out_json:
        _write_json(Path(args.out_json), report)
        print(f"\nWrote JSON report: {args.out_json}")
    if args.out_csv:
        _write_csv(Path(args.out_csv), report["conversations"])
        print(f"Wrote CSV report: {args.out_csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

