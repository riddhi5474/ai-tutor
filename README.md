# AI Tutor (NotebookLM-style)

A modular, local RAG-based AI tutor using **Google Gemini** and **LlamaIndex**. You can use a **Streamlit chat UI** with saved conversations or a **CLI** session over the same course index.

---

## Project structure

```
.
├── app.py                 # Streamlit web UI (chat, uploads, study guide / FAQ)
├── main.py                # CLI entry: parse materials → build index → REPL
├── evaluation.py          # Optional metrics export from SQLite (JSON/CSV)
├── config.py              # Models, paths, chunking, env loading
│
├── core/                  # RAG engine
│   ├── parser.py          # PDF & PPTX → cleaned text
│   └── tutor.py           # Vector index + query
│
├── features/              # Tutor features (guides, FAQ, follow-ups, query)
├── storage/               # SQLite + per-conversation file storage
├── utils/                 # CLI session, export helpers
│
├── course_materials/      # Put PDFs and PPTX here
├── cleaned_text/            # Parsed text (gitignored)
├── output/                  # Exported guides, FAQs, etc. (gitignored)
├── data/                    # Local app DB + uploads (see .gitignore)
│   ├── ai_tutor.db
│   └── storage/             # Per-conversation uploads (gitignored)
│
├── requirements.txt
└── .gitignore
```

---

## Quick start

### 1. Virtual environment

```bash
python -m venv venv
source venv/bin/activate       # macOS / Linux
venv\Scripts\activate          # Windows
```

### 2. Dependencies

```bash
pip install -r requirements.txt
```

**System dependencies** (only for OCR on scanned PDFs):

- macOS: `brew install poppler tesseract`
- Windows: [Poppler](https://github.com/oschwartz10612/poppler-windows) · [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)

### 3. API key

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_key_here
```

`config.py` also accepts `GOOGLE_API_KEY` if you prefer that name.  
Get a key: https://aistudio.google.com/app/apikey

### 4. Add materials

Drop **PDF** or **PPTX** files into `course_materials/`.

### 5. Run the app

**Web UI (recommended):** from the project root,

```bash
streamlit run app.py
```

**CLI:** parses `course_materials/`, builds the index, then starts the interactive session:

```bash
python main.py
```

---

## CLI commands

| Input | Action |
|--------|--------|
| Your question | Answer from indexed materials |
| `guide [topic]` | Study guide |
| `quiz [topic]` | Short quiz |
| `faq [topic]` | FAQ-style document |
| `history` | Conversation history |
| `quit` | Exit |

---

## Configuration

Tunable values live in **`config.py`**:

| Setting | Default | Role |
|---------|---------|------|
| `GEMINI_MODEL` | `models/gemini-2.5-flash` | Generative model |
| `EMBED_MODEL` | `BAAI/bge-small-en-v1.5` | Embeddings |
| `CHUNK_SIZE` | `512` | Chunk size for splitting |
| `CHUNK_OVERLAP` | `50` | Chunk overlap |
| `SIMILARITY_TOP_K` | `5` | Chunks retrieved per query |
| `NUM_FOLLOWUP_QUESTIONS` | `3` | Suggested follow-ups |

Optional: set `CHAT_INPUT_PLACEHOLDER` in `.env` for custom Streamlit input hint text.

---

## Evaluation (optional)

`evaluation.py` reads the Streamlit/CLI conversation database and can emit aggregate metrics (for example grounding-style proxies from stored sources). Example:

```bash
python evaluation.py --db data/ai_tutor.db --out-csv reports/eval.csv
```

Use `--help` for JSON export, label files, and other options.

---

## Extending the project

- **New feature:** add a module under `features/` and wire it from `features/__init__.py` or `app.py` as needed.
- **New CLI command:** extend `utils/session.py`.
- **Save generated text to disk:** use `utils/exporter.save_to_file(content, topic)` (or the paths under `output/` from `config.py`).
