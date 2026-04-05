"""
AI Tutor - Streamlit UI
Run: streamlit run app.py  (from inside ai_tutor/)
"""

import streamlit as st
import os
import shutil
import uuid
from pathlib import Path
import importlib

from config import EMBED_MODEL, GEMINI_MODEL
from storage import (
    append_message,
    clear_messages,
    conversation_paths,
    create_conversation,
    delete_conversation,
    get_conversation,
    list_conversations,
    list_messages_for_ui,
    set_documents_status,
    sync_uploaded_files,
    update_conversation_extras,
)

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

  :root {
    --bg:      #0d0f14;
    --surface: #13161e;
    --surf2:   #1a1e29;
    --border:  #252b3b;
    --accent:  #5b8dee;
    --purple:  #8b5cf6;
    --green:   #34d399;
    --amber:   #fbbf24;
    --text:    #e2e8f0;
    --muted:   #64748b;
    --r:       12px;
  }

  html, body, [class*="css"] { font-family: 'Sora', sans-serif; }
  .stApp { background: var(--bg); color: var(--text); }

  section[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border);
  }

  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--r);
    padding: 18px 22px;
    margin-bottom: 14px;
  }
  .card-blue   { border-left: 3px solid var(--accent); }
  .card-green  { border-left: 3px solid var(--green);  }
  .card-purple { border-left: 3px solid var(--purple); }

  .msg-user {
    background: linear-gradient(135deg,#1e2d5a,#1a2448);
    border: 1px solid #2d3f7a;
    border-radius: 12px 12px 2px 12px;
    padding: 13px 17px;
    margin: 8px 0 8px 80px;
    font-size: 0.94rem;
    line-height: 1.65;
  }
  .msg-ai {
    background: var(--surf2);
    border: 1px solid var(--border);
    border-radius: 12px 12px 12px 2px;
    padding: 13px 17px;
    margin: 8px 80px 8px 0;
    font-size: 0.94rem;
    line-height: 1.65;
  }
  .msg-label {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 5px;
  }

  .source-chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: #151b2e;
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 3px 11px;
    font-size: 0.71rem;
    color: var(--accent);
    margin: 3px 4px 3px 0;
    font-family: 'JetBrains Mono', monospace;
  }
  .score-dot {
    display: inline-block;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--green);
    flex-shrink: 0;
  }

  .followup-section {
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid var(--border);
  }
  .followup-label {
    font-size: 0.68rem;
    color: var(--muted);
    margin-bottom: 6px;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .fu-pill {
    display: inline-block;
    background: #1a1e29;
    border: 1px solid #252b3b;
    border-radius: 20px;
    padding: 5px 13px;
    font-size: 0.8rem;
    margin: 3px 5px 3px 0;
    color: #94a3b8;
  }

  .badge {
    display: inline-block;
    border-radius: 20px;
    padding: 2px 10px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    margin: 2px 0;
  }
  .badge-green { background:#0d2b1f; color:var(--green);  border:1px solid #1a4a35; }
  .badge-blue  { background:#0d1b3e; color:var(--accent); border:1px solid #1a3070; }
  .badge-amber { background:#2b1d05; color:var(--amber);  border:1px solid #4a3510; }

  .output-box {
    background: var(--surf2);
    border: 1px solid var(--border);
    border-radius: var(--r);
    padding: 20px 22px;
    font-size: 0.88rem;
    line-height: 1.8;
    white-space: pre-wrap;
    max-height: 540px;
    overflow-y: auto;
  }

  .stTextInput > div > div > input,
  .stTextArea textarea {
    background: var(--surf2)  !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 8px !important;
    font-family: 'Sora', sans-serif !important;
  }
  .stTextInput > div > div > input:focus,
  .stTextArea textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(91,141,238,.13) !important;
  }

  .stButton > button {
    background: var(--accent) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-family: 'Sora', sans-serif !important;
    transition: all .18s !important;
  }
  .stButton > button:hover {
    background: #4a7de0 !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 14px rgba(91,141,238,.32) !important;
  }

  .stTabs [data-baseweb="tab-list"] {
    background: var(--surface) !important;
    border-bottom: 1px solid var(--border);
    gap: 4px;
  }
  .stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--muted) !important;
    font-weight: 500 !important;
  }
  .stTabs [aria-selected="true"] {
    background: var(--surf2) !important;
    color: var(--text) !important;
    border-bottom: 2px solid var(--accent) !important;
  }

  hr { border-color: var(--border) !important; }
  .stSelectbox > div > div {
    background: var(--surf2) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
  }
  ::-webkit-scrollbar { width: 5px; }
  ::-webkit-scrollbar-track { background: var(--surface); }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
</style>
""",
    unsafe_allow_html=True,
)


# ── session state ─────────────────────────────────────────────────────────────
_DEFAULTS = {
    "tutor": None,
    "index_ready": False,
    # each entry: {"role":"user"|"ai", "content":str, "sources":list[dict], "followups":list[str]}
    "chat_history": [],
    "study_guide": "",
    "faq": "",
    "api_key_set": False,
    "saved_files": [],
    "active_conversation_id": "",
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

if "_prev_conv_id" not in st.session_state:
    st.session_state._prev_conv_id = None


def _ensure_active_conversation_id() -> str:
    cid = st.session_state.active_conversation_id
    if cid and get_conversation(cid):
        return cid
    convs = list_conversations()
    if convs:
        st.session_state.active_conversation_id = convs[0]["id"]
    else:
        st.session_state.active_conversation_id = create_conversation("Chat 1")
    return st.session_state.active_conversation_id


cid = _ensure_active_conversation_id()
if st.session_state._prev_conv_id != cid:
    st.session_state.chat_history = list_messages_for_ui(cid)
    row = get_conversation(cid)
    st.session_state.study_guide = (row or {}).get("study_guide") or ""
    st.session_state.faq = (row or {}).get("faq") or ""
    st.session_state.tutor = None
    st.session_state.index_ready = False
    st.session_state._prev_conv_id = cid

UPLOAD_DIR, CLEANED_DIR = conversation_paths(cid)


# ── lazy import of project modules ────────────────────────────────────────────
# These must be imported at runtime so Streamlit's module cache picks them up
# correctly after the user has set GOOGLE_API_KEY.
_MODULE_LOAD_ERROR: str | None = None


def _load_modules():
    global _MODULE_LOAD_ERROR
    try:
        from core.parser import SimpleDocParser
        from core.tutor import AITutor
        from features.query import query_notebooklm_style
        from features.study_guide import generate_study_guide
        from features.faq import generate_faq

        _MODULE_LOAD_ERROR = None
        return (
            SimpleDocParser,
            AITutor,
            query_notebooklm_style,
            generate_study_guide,
            generate_faq,
        )
    except Exception as e:
        _MODULE_LOAD_ERROR = f"{type(e).__name__}: {e}"
        return None, None, None, None, None


SimpleDocParser, AITutor, query_notebooklm_style, generate_study_guide, generate_faq = _load_modules()


def _cleaned_corpus_fingerprint(cleaned_dir: Path) -> str:
    files = sorted(cleaned_dir.glob("*.txt"))
    if not files:
        return ""
    parts = [f"{p.name}:{p.stat().st_mtime_ns}" for p in files]
    return f"{len(files)}:" + "|".join(parts)


@st.cache_resource(show_spinner="Loading embedding model & index…")
def _cached_aitutor(cleaned_dir_abs: str, corpus_fp: str):
    """
    AITutor + LlamaIndex are not reliably round-tripped through Streamlit session_state.
    Cache by absolute cleaned_text path + corpus fingerprint so reruns reuse one instance.
    """
    import core.tutor as tutor_mod

    importlib.reload(tutor_mod)
    return tutor_mod.AITutor(course_dir=Path(cleaned_dir_abs))


def _attach_tutor_from_cache(cleaned_dir: Path) -> None:
    if not st.session_state.index_ready or AITutor is None:
        return
    txts = list(cleaned_dir.glob("*.txt"))
    if not txts:
        st.session_state.index_ready = False
        st.session_state.tutor = None
        return
    fp = _cleaned_corpus_fingerprint(cleaned_dir)
    if not fp:
        return
    try:
        st.session_state.tutor = _cached_aitutor(str(cleaned_dir.resolve()), fp)
    except Exception:
        st.session_state.tutor = None
        st.session_state.index_ready = False


_attach_tutor_from_cache(CLEANED_DIR)


# ── source chip renderer ──────────────────────────────────────────────────────
def _sources_html(sources: list) -> str:
    """
    Render source attribution chips.
    sources = list of dicts returned by tutor.query():
      { "metadata": {"file_name": str, ...}, "score": float, "text": str }
    """
    if not sources:
        return ""
    chips = ""
    for src in sources[:4]:
        fname = src.get("metadata", {}).get("file_name", "source")
        score = src.get("score", 0)
        chips += (
            f'<span class="source-chip">'
            f'<span class="score-dot"></span>'
            f"📄 {fname}&nbsp;·&nbsp;{score:.0%}"
            f"</span>"
        )
    return f'<div style="margin-top:10px;">{chips}</div>'


# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(
        """
    <div style="padding:6px 0 22px;">
      <div style="font-size:1.45rem;font-weight:700;color:#e2e8f0;letter-spacing:-0.02em;">
        🎓 AI Tutor
      </div>
      <div style="font-size:0.76rem;color:#64748b;margin-top:3px;">
        NotebookLM-style RAG assistant
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ── API key ───────────────────────────────────────────────────────────────
    st.markdown("#### 🔑 Gemini API Key")
    api_key = st.text_input(
        "key",
        type="password",
        placeholder="AIza…",
        label_visibility="collapsed",
        key="api_key_field",
    )
    if api_key:
        os.environ["GOOGLE_API_KEY"] = api_key
        st.session_state.api_key_set = True
        st.markdown(
            '<span class="badge badge-green">✓ Key saved</span>', unsafe_allow_html=True
        )
    elif st.session_state.api_key_set:
        st.markdown(
            '<span class="badge badge-blue">Key in session</span>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<span class="badge badge-amber">⚠ Key required</span>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── conversations (SQLite + local storage) ────────────────────────────────
    st.markdown("#### 💬 Conversations")
    convs = list_conversations()
    if convs:
        ids = [c["id"] for c in convs]
        try:
            sel_index = ids.index(st.session_state.active_conversation_id)
        except ValueError:
            sel_index = 0
        chosen = st.selectbox(
            "active_conversation",
            options=ids,
            index=sel_index,
            format_func=lambda x: next(c["title"] for c in convs if c["id"] == x),
            label_visibility="collapsed",
            key="conversation_select",
        )
        if chosen != st.session_state.active_conversation_id:
            st.session_state.active_conversation_id = chosen
            st.rerun()
    col_nc, col_del = st.columns(2)
    with col_nc:
        if st.button("➕ New", use_container_width=True):
            n = len(list_conversations()) + 1
            st.session_state.active_conversation_id = create_conversation(f"Chat {n}")
            st.session_state._prev_conv_id = None
            st.rerun()
    with col_del:
        if st.button("🗑 Delete", use_container_width=True) and convs:
            cur = st.session_state.active_conversation_id
            delete_conversation(cur)
            remaining = list_conversations()
            st.session_state.active_conversation_id = (
                remaining[0]["id"] if remaining else create_conversation("Chat 1")
            )
            st.session_state._prev_conv_id = None
            st.rerun()

    st.markdown("---")

    # ── file uploader ─────────────────────────────────────────────────────────
    st.markdown("#### 📂 Course Materials")
    uploads = st.file_uploader(
        "files",
        type=["pdf", "pptx"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    if uploads:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        sync_uploaded_files(cid, UPLOAD_DIR, uploads)
        st.session_state.saved_files = [f.name for f in uploads]
        st.session_state.index_ready = False
        st.session_state.tutor = None

    # show all files currently in this session upload folder
    all_course = []
    if UPLOAD_DIR.exists():
        all_course = list(UPLOAD_DIR.glob("*.pdf")) + list(
            UPLOAD_DIR.glob("*.pptx")
        )
    for p in all_course:
        st.markdown(
            f'<span class="badge badge-green">📄 {p.name}</span>',
            unsafe_allow_html=True,
        )

    st.markdown("")

    # ── build index ───────────────────────────────────────────────────────────
    can_build = (
        st.session_state.api_key_set and bool(all_course) and (AITutor is not None)
    )
    if st.button("⚡ Build Index", use_container_width=True, disabled=not can_build):
        with st.spinner("Parsing documents & building vector index…"):
            try:
                upload_files = list(UPLOAD_DIR.glob("*.pdf")) + list(UPLOAD_DIR.glob("*.pptx"))
                if CLEANED_DIR.exists():
                    shutil.rmtree(CLEANED_DIR)
                CLEANED_DIR.mkdir(parents=True, exist_ok=True)

                parser = SimpleDocParser(input_folder=UPLOAD_DIR, output_folder=CLEANED_DIR)
                parser.process_folder()
                cleaned_files = list(CLEANED_DIR.glob("*.txt"))
                if not cleaned_files:
                    raise RuntimeError(
                        "No readable text could be extracted from the uploaded files. "
                        "Try a text-based PDF/PPTX or ensure OCR dependencies are installed."
                    )
                set_documents_status(cid, "parsed")
                fp = _cleaned_corpus_fingerprint(CLEANED_DIR)
                st.session_state.tutor = _cached_aitutor(str(CLEANED_DIR.resolve()), fp)
                st.session_state.index_ready = True
                set_documents_status(cid, "indexed")
                update_conversation_extras(
                    cid,
                    embedding_model=EMBED_MODEL,
                    llm_model=GEMINI_MODEL,
                )
            except Exception as e:
                set_documents_status(cid, "failed", str(e))
                st.error(
                    f"Index build failed: {e}\n"
                    f"(debug: uploads={len(upload_files)}, parsed_txt={len(list(CLEANED_DIR.glob('*.txt')))}, cleaned_files={[p.name for p in cleaned_files] if 'cleaned_files' in locals() else []})"
                )

    if not st.session_state.api_key_set:
        st.caption("↑ Enter API key to enable")
    elif not all_course:
        st.caption("↑ Upload files to enable")
    elif AITutor is None:
        st.error("Import error — run from ai_tutor/ directory")

    if st.session_state.index_ready:
        st.markdown(
            '<span class="badge badge-green">✓ Index ready</span>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ── settings ──────────────────────────────────────────────────────────────
    st.markdown("#### ⚙️ Settings")
    show_sources = st.toggle("Show source references", value=True)
    show_followups = st.toggle("Show follow-up suggestions", value=True)

    st.markdown("---")
    if st.button("🗑 Clear chat", use_container_width=True):
        clear_messages(cid)
        st.session_state.chat_history = []
        st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# MAIN TABS
# ═════════════════════════════════════════════════════════════════════════════
tab_chat, tab_guide, tab_faq = st.tabs(["💬  Chat", "📖  Study Guide", "❓  FAQ"])


# ── render entire chat history ────────────────────────────────────────────────
def render_chat_history():
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            st.markdown(
                '<div class="msg-label" style="text-align:right;margin-right:6px;">You</div>'
                f'<div class="msg-user">{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            # sources
            src_html = _sources_html(msg.get("sources", [])) if show_sources else ""

            # follow-ups (display-only pills; interactive buttons rendered below input)
            fu_html = ""
            if show_followups and msg.get("followups"):
                pills = "".join(
                    f'<span class="fu-pill">💡 {q}</span>' for q in msg["followups"][:3]
                )
                fu_html = (
                    '<div class="followup-section">'
                    '<div class="followup-label">You might also ask</div>'
                    f"{pills}</div>"
                )

            st.markdown(
                '<div class="msg-label" style="margin-left:6px;">🎓 AI Tutor</div>'
                f'<div class="msg-ai">{msg["content"]}{src_html}{fu_html}</div>',
                unsafe_allow_html=True,
            )


# ════════════════════════════════════════════════════════════════════
# TAB 1 – CHAT
# ════════════════════════════════════════════════════════════════════
with tab_chat:
    if not st.session_state.index_ready:
        st.markdown(
            """
        <div class="card card-blue">
          <div style="font-size:1.05rem;font-weight:600;margin-bottom:10px;">Getting started</div>
          <ol style="color:#94a3b8;font-size:0.88rem;line-height:2.1;margin:0;padding-left:18px;">
            <li>Enter your <strong>Gemini API key</strong> in the sidebar</li>
            <li>Upload <strong>PDF / PPTX</strong> course materials</li>
            <li>Click <strong>⚡ Build Index</strong></li>
            <li>Start asking questions here!</li>
          </ol>
        </div>
        """,
            unsafe_allow_html=True,
        )

    render_chat_history()
    st.markdown("---")

    # ── follow-up quick-send buttons (last AI message) ────────────────────────
    if show_followups and st.session_state.chat_history:
        last_ai = next(
            (m for m in reversed(st.session_state.chat_history) if m["role"] == "ai"),
            None,
        )
        if last_ai and last_ai.get("followups"):
            st.markdown(
                '<div style="font-size:0.72rem;font-weight:600;color:#64748b;'
                'letter-spacing:0.06em;text-transform:uppercase;margin-bottom:6px;">'
                "Suggested follow-ups</div>",
                unsafe_allow_html=True,
            )
            fu_cols = st.columns(min(len(last_ai["followups"][:3]), 3))
            for i, fq in enumerate(last_ai["followups"][:3]):
                with fu_cols[i]:
                    if st.button(f"💡 {fq}", key=f"fu_{i}", use_container_width=True):
                        st.session_state["_pending_q"] = fq

    # ── input row ─────────────────────────────────────────────────────────────
    col_in, col_btn = st.columns([5, 1])
    with col_in:
        # if a follow-up button was clicked, pre-fill the input
        pending = st.session_state.pop("_pending_q", "")
        user_q = st.text_input(
            "question",
            value=pending,
            placeholder="e.g. Explain the three-way handshake in TCP…",
            label_visibility="collapsed",
            key="chat_input",
            disabled=not st.session_state.index_ready,
        )
    with col_btn:
        send = st.button(
            "Send →",
            use_container_width=True,
            disabled=not st.session_state.index_ready,
        )

    # ── handle submit ─────────────────────────────────────────────────────────
    if send and user_q.strip():
        q = user_q.strip()
        append_message(cid, "user", q)
        st.session_state.chat_history.append(
            {"role": "user", "content": q, "sources": [], "followups": []}
        )

        answer, sources, followups = "", [], []

        if not query_notebooklm_style:
            answer = (
                "⚠️ Could not load chat modules. "
                f"{_MODULE_LOAD_ERROR or 'Unknown error'}"
            )
        elif not st.session_state.tutor:
            answer = (
                "⚠️ Tutor is not loaded. Click **⚡ Build Index** again "
                "(or wait for the embedding model to finish loading)."
            )
        else:
            with st.spinner("Thinking…"):
                try:
                    result = query_notebooklm_style(q, st.session_state.tutor)
                    answer = result.get("answer", "")
                    sources = result.get("sources", [])
                    followups = result.get("follow_ups", [])
                except Exception as e:
                    answer = f"⚠️ Error: {e}"

        append_message(cid, "ai", answer, sources=sources, followups=followups)
        st.session_state.chat_history.append(
            {
                "role": "ai",
                "content": answer,
                "sources": sources,
                "followups": followups,
            }
        )
        st.rerun()


# ════════════════════════════════════════════════════════════════════
# TAB 2 – STUDY GUIDE
# ════════════════════════════════════════════════════════════════════
with tab_guide:
    st.markdown(
        """
    <div class="card card-purple">
      <div style="font-size:1rem;font-weight:600;margin-bottom:4px;">📖 Study Guide Generator</div>
      <div style="color:#94a3b8;font-size:0.84rem;">
        Generates a structured, exam-ready study guide from your uploaded materials.
        Enter a topic (e.g. "TCP/IP", "Chapter 3") or leave blank to summarise everything.
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    guide_topic = st.text_input(
        "Topic for study guide",
        placeholder="e.g. Transport Layer, Chapter 2, DNS…",
        key="guide_topic_input",
        disabled=not st.session_state.index_ready,
    )

    col_g1, col_g2 = st.columns([2, 1])
    with col_g1:
        gen_guide = st.button(
            "✨ Generate Study Guide",
            use_container_width=True,
            disabled=not st.session_state.index_ready,
        )
    with col_g2:
        if st.session_state.study_guide:
            st.download_button(
                "⬇ Download .txt",
                data=st.session_state.study_guide,
                file_name="study_guide.txt",
                mime="text/plain",
                use_container_width=True,
            )

    if gen_guide:
        if not generate_study_guide:
            st.error("Module import failed — run from ai_tutor/ directory.")
        elif not st.session_state.tutor:
            st.warning("Build the index first.")
        else:
            topic = guide_topic.strip() or "all course materials"
            with st.spinner(f"Generating study guide for '{topic}'…"):
                try:
                    # ✅ Exact signature: generate_study_guide(topic, tutor)
                    guide = generate_study_guide(topic, st.session_state.tutor)
                    st.session_state.study_guide = guide
                    update_conversation_extras(cid, study_guide=guide)
                    st.success("Study guide saved to this conversation.")
                except Exception as e:
                    st.error(f"Error: {e}")

    if st.session_state.study_guide:
        st.markdown(
            f'<div class="output-box">{st.session_state.study_guide}</div>',
            unsafe_allow_html=True,
        )


# ════════════════════════════════════════════════════════════════════
# TAB 3 – FAQ
# ════════════════════════════════════════════════════════════════════
with tab_faq:
    st.markdown(
        """
    <div class="card card-green">
      <div style="font-size:1rem;font-weight:600;margin-bottom:4px;">❓ FAQ Generator</div>
      <div style="color:#94a3b8;font-size:0.84rem;">
        Auto-generates common Q&amp;A pairs from your course materials.
        Specify a topic and how many questions you'd like.
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    col_fa, col_fb = st.columns([3, 1])
    with col_fa:
        faq_topic = st.text_input(
            "Topic for FAQ",
            placeholder="e.g. Network Layer, Congestion Control…",
            key="faq_topic_input",
            disabled=not st.session_state.index_ready,
        )
    with col_fb:
        faq_n = st.selectbox(
            "# Questions",
            [3, 5, 8, 10],
            index=1,
            disabled=not st.session_state.index_ready,
        )

    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        gen_faq = st.button(
            "✨ Generate FAQ",
            use_container_width=True,
            disabled=not st.session_state.index_ready,
        )
    with col_f2:
        if st.session_state.faq:
            st.download_button(
                "⬇ Download .txt",
                data=st.session_state.faq,
                file_name="faq.txt",
                mime="text/plain",
                use_container_width=True,
            )

    if gen_faq:
        if not generate_faq:
            st.error("Module import failed — run from ai_tutor/ directory.")
        elif not st.session_state.tutor:
            st.warning("Build the index first.")
        else:
            topic = faq_topic.strip() or "all course materials"
            with st.spinner(f"Generating {faq_n} FAQ questions for '{topic}'…"):
                try:
                    # ✅ Exact signature: generate_faq(topic, tutor, num_questions)
                    faq = generate_faq(
                        topic, st.session_state.tutor, num_questions=faq_n
                    )
                    st.session_state.faq = faq
                    update_conversation_extras(cid, faq=faq)
                    st.success("FAQ saved to this conversation.")
                except Exception as e:
                    st.error(f"Error: {e}")

    if st.session_state.faq:
        st.markdown(
            f'<div class="output-box">{st.session_state.faq}</div>',
            unsafe_allow_html=True,
        )
