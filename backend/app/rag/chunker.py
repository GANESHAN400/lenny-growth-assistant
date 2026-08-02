"""Text chunking strategies for RAG pipeline."""
import re
from dataclasses import dataclass


@dataclass
class TextChunk:
    """A chunk of text with source metadata."""

    content: str
    source: str  # filename/transcript name
    chunk_index: int
    char_start: int
    char_end: int
    word_count: int

    def to_context_string(self) -> str:
        """Format for LLM context injection."""
        return f"[Source: {self.source}]\n{self.content}"


class TextChunker:
    """Splits transcripts into overlapping chunks for retrieval."""

    def __init__(
        self,
        chunk_size: int = 800,
        overlap: int = 150,
        min_chunk_size: int = 100,
    ) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size

    def chunk_text(self, text: str, source: str) -> list[TextChunk]:
        """Split text into overlapping chunks by sentence boundaries."""
        # Clean the text
        text = self._clean_text(text)
        if len(text) < self.min_chunk_size:
            return []

        # Split into sentences
        sentences = self._split_sentences(text)
        chunks: list[TextChunk] = []
        current_chunk: list[str] = []
        current_len = 0
        chunk_index = 0
        char_pos = 0

        for sentence in sentences:
            sentence_len = len(sentence)

            if current_len + sentence_len > self.chunk_size and current_chunk:
                # Emit the current chunk
                chunk_text = " ".join(current_chunk)
                if len(chunk_text) >= self.min_chunk_size:
                    chunks.append(
                        TextChunk(
                            content=chunk_text,
                            source=source,
                            chunk_index=chunk_index,
                            char_start=char_pos - current_len,
                            char_end=char_pos,
                            word_count=len(chunk_text.split()),
                        )
                    )
                    chunk_index += 1

                # Keep overlap by retaining last N sentences
                overlap_sentences: list[str] = []
                overlap_len = 0
                for s in reversed(current_chunk):
                    if overlap_len + len(s) <= self.overlap:
                        overlap_sentences.insert(0, s)
                        overlap_len += len(s)
                    else:
                        break
                current_chunk = overlap_sentences
                current_len = overlap_len

            current_chunk.append(sentence)
            current_len += sentence_len
            char_pos += sentence_len

        # Emit remaining
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(
                    TextChunk(
                        content=chunk_text,
                        source=source,
                        chunk_index=chunk_index,
                        char_start=max(0, char_pos - current_len),
                        char_end=char_pos,
                        word_count=len(chunk_text.split()),
                    )
                )

        return chunks

    def _clean_text(self, text: str) -> str:
        """Clean and normalize transcript text."""
        # Remove excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)
        # Remove timestamps like [00:01:23]
        text = re.sub(r"\[\d{2}:\d{2}:\d{2}\]", "", text)
        # Remove speaker labels like "LENNY:" or "GUEST:"
        text = re.sub(r"^[A-Z][A-Z\s]+:\s*", "", text, flags=re.MULTILINE)
        return text.strip()

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Split on sentence boundaries
        sentence_endings = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")
        sentences = sentence_endings.split(text)
        # Filter empty
        return [s.strip() for s in sentences if s.strip()]
