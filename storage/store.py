"""
Local SQLite + on-disk storage for conversations, documents, and chat messages.
Single-user; paths are relative to STORAGE_ROOT / <conversation_id>/.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

from config import DB_PATH, STORAGE_ROOT


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT 'New chat',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                embedding_model TEXT,
                llm_model TEXT,
                study_guide TEXT,
                faq TEXT
            );

            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                original_name TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                file_size INTEGER,
                sha256 TEXT,
                status TEXT NOT NULL DEFAULT 'uploaded',
                error TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                UNIQUE (conversation_id, original_name)
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources_json TEXT,
                followups_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_documents_conv ON documents(conversation_id);
            CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id);
            """
        )


def conversation_paths(conversation_id: str) -> tuple[Path, Path]:
    root = STORAGE_ROOT / conversation_id
    uploads = root / "uploads"
    cleaned = root / "cleaned_text"
    uploads.mkdir(parents=True, exist_ok=True)
    cleaned.mkdir(parents=True, exist_ok=True)
    return uploads, cleaned


def create_conversation(title: str = "New chat") -> str:
    cid = uuid.uuid4().hex
    now = _now_iso()
    conversation_paths(cid)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO conversations (id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (cid, title, now, now),
        )
    return cid


def list_conversations() -> List[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, title, created_at, updated_at
            FROM conversations
            ORDER BY updated_at DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def get_conversation(conversation_id: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
    return dict(row) if row else None


def delete_conversation(conversation_id: str) -> None:
    root = STORAGE_ROOT / conversation_id
    if root.exists():
        import shutil

        shutil.rmtree(root, ignore_errors=True)
    with get_connection() as conn:
        conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))


def touch_conversation(conversation_id: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (_now_iso(), conversation_id),
        )


def update_conversation_extras(
    conversation_id: str,
    *,
    title: Optional[str] = None,
    study_guide: Optional[str] = None,
    faq: Optional[str] = None,
    embedding_model: Optional[str] = None,
    llm_model: Optional[str] = None,
) -> None:
    parts = ["updated_at = ?"]
    vals: List[Any] = [_now_iso()]
    if title is not None:
        parts.append("title = ?")
        vals.append(title)
    if study_guide is not None:
        parts.append("study_guide = ?")
        vals.append(study_guide)
    if faq is not None:
        parts.append("faq = ?")
        vals.append(faq)
    if embedding_model is not None:
        parts.append("embedding_model = ?")
        vals.append(embedding_model)
    if llm_model is not None:
        parts.append("llm_model = ?")
        vals.append(llm_model)
    vals.append(conversation_id)
    sql = f"UPDATE conversations SET {', '.join(parts)} WHERE id = ?"
    with get_connection() as conn:
        conn.execute(sql, vals)


def _delete_document_row(conn: sqlite3.Connection, conversation_id: str, original_name: str) -> None:
    conn.execute(
        "DELETE FROM documents WHERE conversation_id = ? AND original_name = ?",
        (conversation_id, original_name),
    )


def sync_uploaded_files(conversation_id: str, upload_dir: Path, uploaded_files: list) -> None:
    """
    uploaded_files: Streamlit UploadedFile objects with .name and .getvalue().
    Keeps disk + DB aligned with current uploader selection.
    """
    selected = {f.name for f in uploaded_files}
    existing_names = {p.name for p in upload_dir.glob("*") if p.is_file()}

    with get_connection() as conn:
        for name in existing_names - selected:
            p = upload_dir / name
            p.unlink(missing_ok=True)
            _delete_document_row(conn, conversation_id, name)

        for f in uploaded_files:
            data = f.getvalue()
            dest = upload_dir / f.name
            dest.write_bytes(data)
            rel = f"uploads/{f.name}"
            now = _now_iso()
            row = conn.execute(
                """
                SELECT id FROM documents
                WHERE conversation_id = ? AND original_name = ?
                """,
                (conversation_id, f.name),
            ).fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE documents
                    SET file_size = ?, stored_path = ?, status = 'uploaded', error = NULL
                    WHERE conversation_id = ? AND original_name = ?
                    """,
                    (len(data), rel, conversation_id, f.name),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO documents (
                        id, conversation_id, original_name, stored_path,
                        file_size, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, 'uploaded', ?)
                    """,
                    (uuid.uuid4().hex, conversation_id, f.name, rel, len(data), now),
                )

    touch_conversation(conversation_id)


def set_documents_status(
    conversation_id: str,
    status: str,
    error: Optional[str] = None,
) -> None:
    with get_connection() as conn:
        if error is None:
            conn.execute(
                "UPDATE documents SET status = ?, error = NULL WHERE conversation_id = ?",
                (status, conversation_id),
            )
        else:
            conn.execute(
                "UPDATE documents SET status = ?, error = ? WHERE conversation_id = ?",
                (status, error, conversation_id),
            )


def list_document_names(conversation_id: str) -> List[str]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT original_name FROM documents WHERE conversation_id = ? ORDER BY original_name",
            (conversation_id,),
        ).fetchall()
    return [r[0] for r in rows]


def append_message(
    conversation_id: str,
    role: str,
    content: str,
    sources: Optional[List[Any]] = None,
    followups: Optional[List[str]] = None,
) -> None:
    mid = uuid.uuid4().hex
    now = _now_iso()
    src = json.dumps(sources or [], default=str)
    fu = json.dumps(followups or [])
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO messages (id, conversation_id, role, content, sources_json, followups_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (mid, conversation_id, role, content, src, fu, now),
        )
    touch_conversation(conversation_id)


def list_messages_for_ui(conversation_id: str) -> List[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT role, content, sources_json, followups_json
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            """,
            (conversation_id,),
        ).fetchall()
    out = []
    for r in rows:
        sources = json.loads(r["sources_json"] or "[]")
        followups = json.loads(r["followups_json"] or "[]")
        out.append(
            {
                "role": r["role"],
                "content": r["content"],
                "sources": sources,
                "followups": followups,
            }
        )
    return out


def clear_messages(conversation_id: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    touch_conversation(conversation_id)


init_db()
