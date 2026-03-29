"""
core/tutor.py
─────────────
Builds and queries the RAG index using LlamaIndex + Gemini.
All model configuration is pulled from config.py.
"""

from pathlib import Path
from typing import Dict, List

import google.generativeai as genai

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    EMBED_MODEL,
    LLM_TEMPERATURE,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    SIMILARITY_TOP_K,
    CLEANED_TEXT_DIR,
)

# Configure Gemini globally once
genai.configure(api_key=GEMINI_API_KEY)


class AITutor:
    """RAG-powered AI Tutor built on LlamaIndex + Gemini."""

    RESPONSE_PROMPTS = {
        "explanation": "Provide a clear, student-friendly explanation.",
        "quiz":        "Generate a 5-question multiple choice quiz with answers.",
        "notes":       "Create concise, well-structured bullet-point notes.",
    }

    def __init__(self, course_dir: Path = CLEANED_TEXT_DIR):
        from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
        from llama_index.core.node_parser import SentenceSplitter
        from llama_index.llms.gemini import Gemini
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding

        print("\n🔧 Configuring models...")
        Settings.llm        = Gemini(model=GEMINI_MODEL, api_key=GEMINI_API_KEY, temperature=LLM_TEMPERATURE)
        Settings.embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL)
        Settings.node_parser = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
        print(f"   LLM        : {GEMINI_MODEL}")
        print(f"   Embeddings : {EMBED_MODEL}")
        print(f"   Chunk size : {CHUNK_SIZE} (overlap {CHUNK_OVERLAP})")

        print(f"\n🔨 Building index from: {course_dir}/")
        docs = SimpleDirectoryReader(input_dir=str(course_dir), filename_as_id=True).load_data()
        print(f"📚 Loaded {len(docs)} document(s)")

        self.index = VectorStoreIndex.from_documents(docs, show_progress=True)
        print("✅ Tutor ready!\n")

    def query(self, question: str, response_format: str = "explanation") -> Dict:
        """Run a RAG query and return the answer + source nodes."""
        suffix = self.RESPONSE_PROMPTS.get(response_format, self.RESPONSE_PROMPTS["explanation"])
        engine   = self.index.as_query_engine(similarity_top_k=SIMILARITY_TOP_K)
        response = engine.query(f"{question}\n\n{suffix}")

        return {
            "question": question,
            "response": str(response),
            "source_nodes": [
                {
                    "text":     node.node.text[:150],
                    "score":    node.score,
                    "metadata": node.node.metadata,
                }
                for node in response.source_nodes
            ],
        }
