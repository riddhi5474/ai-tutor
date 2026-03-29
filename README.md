# 🎓 AI Tutor – NotebookLM Style

A modular, local RAG-based AI tutor built with **Gemini** + **LlamaIndex**.

---

## 📁 Project Structure

```
ai_tutor/
│
├── main.py                  # ← Entry point (run this)
├── config.py                # ← All settings: models, paths, chunking
│
├── core/                    # RAG engine
│   ├── parser.py            #   PDF & PPTX → clean text
│   └── tutor.py             #   LlamaIndex vector index + query
│
├── features/                # NotebookLM-style features
│   ├── followup.py          #   Suggest follow-up questions
│   ├── study_guide.py       #   Generate structured study guide
│   ├── faq.py               #   Generate FAQ document
│   └── query.py             #   Full query: answer + sources + followups
│
├── utils/                   # CLI & I/O helpers
│   ├── session.py           #   Interactive terminal session
│   └── exporter.py          #   Save outputs to output/
│
├── course_materials/        # ← Drop your PDFs & PPTX files here
├── cleaned_text/            #   Auto-generated parsed text (git-ignored)
├── output/                  #   Saved guides, FAQs, quizzes (git-ignored)
│
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## ⚡ Quick Start

### 1. Open the folder in VS Code

### 2. Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate      # Mac/Linux
venv\Scripts\activate         # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

> **System dependencies** (only needed for OCR on scanned PDFs):
> - macOS: `brew install poppler tesseract`
> - Windows: [Poppler](https://github.com/oschwartz10612/poppler-windows) · [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)

### 4. Set your API key
```bash
cp .env.example .env
# Edit .env — paste your Gemini API key
```
Get a free key at: https://aistudio.google.com/app/apikey

### 5. Add your course materials
Drop **PDF** or **PPTX** files into `course_materials/`.

### 6. Run
```bash
python main.py
```

---

## 💬 Interactive Commands

| Command | What it does |
|---|---|
| `[your question]` | Ask anything from your materials |
| `guide [topic]` | Generate a full study guide |
| `quiz [topic]` | Generate a 5-question quiz |
| `faq [topic]` | Generate an FAQ document |
| `history` | View conversation history |
| `quit` | Exit |

---

## 🔧 Customisation

All tunable settings live in **`config.py`**:

| Setting | Default | What it controls |
|---|---|---|
| `GEMINI_MODEL` | `gemini-2.5-flash` | LLM used for answers |
| `EMBED_MODEL` | `BAAI/bge-small-en-v1.5` | Embedding model |
| `CHUNK_SIZE` | `512` | Token chunk size for splitting |
| `CHUNK_OVERLAP` | `50` | Overlap between chunks |
| `SIMILARITY_TOP_K` | `5` | Source chunks retrieved per query |
| `NUM_FOLLOWUP_QUESTIONS` | `3` | Follow-up questions suggested |

---

## ➕ Extending the Project

- **New feature?** Add a file in `features/` and export it from `features/__init__.py`
- **New command?** Add a branch in `utils/session.py`
- **Save output automatically?** Use `utils/exporter.save_to_file(content, topic)`
