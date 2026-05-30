"""
synthesis/rag.py — Vector memory (ChromaDB) for the synthesis pipeline.

Stores and retrieves intelligence summaries per company.
Each pipeline run stores its verdict; subsequent runs retrieve
historical context to enable trend detection across runs.

Usage:
    from pipeline.synthesis.rag import store_context, retrieve_context
"""
import os, sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))
load_dotenv()

# Set DISABLE_RAG=true in production (Render) to skip the 79MB ONNX model download.
# ChromaDB data is ephemeral on Render's free tier anyway, so RAG adds latency with no benefit.
_DISABLED   = os.getenv("DISABLE_RAG", "false").lower() == "true"
_AVAILABLE  = False
_collection = None

if not _DISABLED:
    try:
        import chromadb
        _dir = Path(__file__).resolve().parents[2] / "data" / "chroma"
        _dir.mkdir(parents=True, exist_ok=True)
        _client     = chromadb.PersistentClient(path=str(_dir))
        _collection = _client.get_or_create_collection("company_knowledge")
        _AVAILABLE  = True
    except ImportError:
        pass


def retrieve_context(ticker: str, query: str, n: int = 3) -> str:
    """Return up to n relevant historical summaries for a ticker."""
    if not _AVAILABLE or _collection is None:
        return ""
    try:
        results = _collection.query(
            query_texts=[f"{ticker}: {query}"],
            n_results=n,
            where={"ticker": ticker},
        )
        docs = results.get("documents", [[]])[0]
        return "\n---\n".join(docs) if docs else ""
    except Exception:
        return ""


def store_context(ticker: str, doc_id: str, text: str, doc_type: str = "intelligence") -> None:
    """Store a document in the knowledge base for future retrieval."""
    if not _AVAILABLE or _collection is None or not text.strip():
        return
    try:
        _collection.upsert(
            ids=[f"{ticker}_{doc_id}"],
            documents=[text],
            metadatas=[{"ticker": ticker, "type": doc_type}],
        )
    except Exception:
        pass
