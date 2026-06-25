import io
import os
import tempfile
from typing import Protocol

from google import genai
from pypdf import PdfReader, PdfWriter

DEFAULT_MODEL = "gemini-2.5-pro"
# Gemini rejects a single document request once the PDF gets large (empirically a
# ~70 MB scan fails with 400 INVALID_ARGUMENT while ~47 MB succeeds). Documents
# above this are split into page-range chunks, each transcribed separately.
MAX_CHUNK_BYTES = 30 * 1024 * 1024
TRANSCRIBE_PROMPT = (
    "Transcribe this scanned document to clean GitHub-flavored Markdown. "
    "Preserve the author's exact words, paragraph breaks, and any headings or "
    "lists. Do not summarise, correct, modernise, or add commentary. Mark any "
    "illustrations or diagrams as [diagram]. If a word is illegible, write "
    "[illegible]."
)


class Transcriber(Protocol):
    def transcribe(self, pdf_bytes: bytes) -> str: ...


class FakeTranscriber:
    def __init__(self, text: str) -> None:
        self._text = text
        self.last_pdf_bytes: bytes | None = None

    def transcribe(self, pdf_bytes: bytes) -> str:
        self.last_pdf_bytes = pdf_bytes
        return self._text


def _split_pdf(pdf_bytes: bytes, max_chunk_bytes: int) -> list[bytes]:
    """Split a PDF into consecutive page-range chunks, each roughly under
    max_chunk_bytes. Returns the input unchanged (single chunk) when already small."""
    if len(pdf_bytes) <= max_chunk_bytes:
        return [pdf_bytes]
    reader = PdfReader(io.BytesIO(pdf_bytes))
    n_pages = len(reader.pages)
    pages_per_chunk = max(1, (max_chunk_bytes * n_pages) // len(pdf_bytes))
    chunks: list[bytes] = []
    for start in range(0, n_pages, pages_per_chunk):
        writer = PdfWriter()
        for i in range(start, min(start + pages_per_chunk, n_pages)):
            writer.add_page(reader.pages[i])
        buf = io.BytesIO()
        writer.write(buf)
        chunks.append(buf.getvalue())
    return chunks


class GeminiTranscriber:
    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        client=None,
        max_chunk_bytes: int = MAX_CHUNK_BYTES,
    ) -> None:
        self._model = model
        self._client = client or genai.Client()
        self._max_chunk_bytes = max_chunk_bytes

    def _transcribe_chunk(self, pdf_bytes: bytes) -> str:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            path = tmp.name
        try:
            uploaded = self._client.files.upload(file=path)
            response = self._client.models.generate_content(
                model=self._model,
                contents=[TRANSCRIBE_PROMPT, uploaded],
            )
            return response.text or ""
        finally:
            os.unlink(path)

    def transcribe(self, pdf_bytes: bytes) -> str:
        chunks = _split_pdf(pdf_bytes, self._max_chunk_bytes)
        return "\n\n".join(self._transcribe_chunk(chunk) for chunk in chunks)
