"""BM25-style keyword retriever for Lenny's podcast transcripts.

Uses a pure-Python TF-IDF/BM25 approach requiring no heavy dependencies.
The index is built in-memory from local transcript files.
"""
import json
import math
import os
import re
from pathlib import Path

from loguru import logger

from app.rag.chunker import TextChunk, TextChunker

# Path to the transcript data directory
TRANSCRIPTS_DIR = Path(__file__).parent.parent.parent / "data" / "transcripts"
INDEX_CACHE_PATH = Path(__file__).parent.parent.parent / "data" / "rag_index.json"


class BM25Retriever:
    """BM25 retrieval over Lenny podcast transcript chunks."""

    # BM25 hyperparameters
    K1 = 1.5
    B = 0.75

    def __init__(self) -> None:
        self.chunks: list[TextChunk] = []
        self.inverted_index: dict[str, list[tuple[int, int]]] = {}  # term -> [(chunk_idx, tf)]
        self.chunk_lengths: list[int] = []
        self.avg_length: float = 0.0
        self._is_loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded and len(self.chunks) > 0

    def build_index(self, chunks: list[TextChunk]) -> None:
        """Build BM25 index from chunks."""
        self.chunks = chunks
        self.inverted_index = {}
        self.chunk_lengths = []

        for idx, chunk in enumerate(chunks):
            tokens = self._tokenize(chunk.content)
            self.chunk_lengths.append(len(tokens))

            # Build term frequency per chunk
            tf: dict[str, int] = {}
            for token in tokens:
                tf[token] = tf.get(token, 0) + 1

            # Add to inverted index
            for term, freq in tf.items():
                if term not in self.inverted_index:
                    self.inverted_index[term] = []
                self.inverted_index[term].append((idx, freq))

        self.avg_length = (
            sum(self.chunk_lengths) / len(self.chunk_lengths)
            if self.chunk_lengths
            else 1.0
        )
        self._is_loaded = True
        logger.info(
            f"BM25 index built: {len(chunks)} chunks, "
            f"{len(self.inverted_index)} unique terms, "
            f"avg_length={self.avg_length:.1f}"
        )

    def retrieve(self, query: str, top_k: int = 5) -> list[tuple[TextChunk, float]]:
        """Retrieve top-k chunks for a query using BM25 scoring."""
        if not self.is_loaded:
            logger.warning("BM25 index not loaded - returning empty results")
            return []

        query_tokens = self._tokenize(query)
        n = len(self.chunks)
        scores: dict[int, float] = {}

        for token in query_tokens:
            if token not in self.inverted_index:
                continue

            postings = self.inverted_index[token]
            df = len(postings)
            idf = math.log((n - df + 0.5) / (df + 0.5) + 1)

            for chunk_idx, tf in postings:
                dl = self.chunk_lengths[chunk_idx]
                tf_norm = (tf * (self.K1 + 1)) / (
                    tf + self.K1 * (1 - self.B + self.B * dl / self.avg_length)
                )
                scores[chunk_idx] = scores.get(chunk_idx, 0.0) + idf * tf_norm

        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [(self.chunks[idx], score) for idx, score in ranked[:top_k]]

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization: lowercase, split on non-alphanumeric."""
        text = text.lower()
        tokens = re.findall(r"\b[a-z]{2,}\b", text)
        # Remove common stopwords
        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "is", "it", "this", "that",
            "was", "are", "were", "be", "been", "has", "have", "had", "do",
            "does", "did", "will", "would", "could", "should", "may", "might",
            "i", "we", "you", "he", "she", "they", "them", "their", "there",
            "so", "if", "as", "up", "out", "my", "our", "your", "its",
        }
        return [t for t in tokens if t not in stopwords]

    def save_index(self, path: Path | None = None) -> None:
        """Persist index to JSON for fast reload."""
        save_path = path or INDEX_CACHE_PATH
        save_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "chunks": [
                {
                    "content": c.content,
                    "source": c.source,
                    "chunk_index": c.chunk_index,
                    "char_start": c.char_start,
                    "char_end": c.char_end,
                    "word_count": c.word_count,
                }
                for c in self.chunks
            ],
            "avg_length": self.avg_length,
            "inverted_index": {
                term: postings
                for term, postings in self.inverted_index.items()
            },
            "chunk_lengths": self.chunk_lengths,
        }
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        logger.info(f"RAG index saved to {save_path}")

    def load_index(self, path: Path | None = None) -> bool:
        """Load index from cached JSON."""
        load_path = path or INDEX_CACHE_PATH
        if not load_path.exists():
            return False
        try:
            with open(load_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.chunks = [
                TextChunk(
                    content=c["content"],
                    source=c["source"],
                    chunk_index=c["chunk_index"],
                    char_start=c["char_start"],
                    char_end=c["char_end"],
                    word_count=c["word_count"],
                )
                for c in data["chunks"]
            ]
            self.avg_length = data["avg_length"]
            self.inverted_index = {
                term: [tuple(p) for p in postings]  # type: ignore[misc]
                for term, postings in data["inverted_index"].items()
            }
            self.chunk_lengths = data["chunk_lengths"]
            self._is_loaded = True
            logger.info(f"RAG index loaded: {len(self.chunks)} chunks from {load_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load RAG index: {e}")
            return False


# Singleton retriever instance
_retriever: BM25Retriever | None = None


def get_retriever() -> BM25Retriever:
    """Get or initialize the singleton BM25 retriever."""
    global _retriever
    if _retriever is None:
        _retriever = BM25Retriever()
    return _retriever


def build_retriever_from_files(transcripts_dir: Path | None = None) -> BM25Retriever:
    """Build (or reload cached) retriever from transcript files."""
    retriever = get_retriever()

    # Try loading from cache first
    if retriever.load_index():
        return retriever

    # Build from transcript files
    source_dir = transcripts_dir or TRANSCRIPTS_DIR
    if not source_dir.exists():
        logger.warning(
            f"Transcripts directory not found: {source_dir}. "
            "Run `python -m app.rag.ingest` to download transcripts."
        )
        return retriever

    chunker = TextChunker(chunk_size=800, overlap=150)
    all_chunks: list[TextChunk] = []
    files_processed = 0

    for ext in ("*.txt", "*.md"):
        for filepath in sorted(source_dir.glob(ext)):
            try:
                text = filepath.read_text(encoding="utf-8", errors="ignore")
                source = filepath.stem
                chunks = chunker.chunk_text(text, source)
                all_chunks.extend(chunks)
                files_processed += 1
            except Exception as e:
                logger.error(f"Error reading {filepath}: {e}")

    if all_chunks:
        retriever.build_index(all_chunks)
        retriever.save_index()
        logger.info(
            f"Built RAG index from {files_processed} files → {len(all_chunks)} chunks"
        )
    else:
        logger.warning("No transcript chunks found. RAG will be disabled.")

    return retriever


def format_retrieved_context(
    results: list[tuple[TextChunk, float]],
    max_tokens: int = 2000,
) -> str:
    """Format retrieved chunks into a context string for the LLM."""
    if not results:
        return ""

    context_parts: list[str] = []
    total_chars = 0
    # Approximate: 1 token ≈ 4 chars
    max_chars = max_tokens * 4

    for chunk, score in results:
        if total_chars >= max_chars:
            break
        part = chunk.to_context_string()
        context_parts.append(part)
        total_chars += len(part)

    return "\n\n---\n\n".join(context_parts)
