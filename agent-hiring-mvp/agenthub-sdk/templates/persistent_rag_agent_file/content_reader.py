import os
import tempfile
from typing import Optional

# Detection
import filetype
import mimetypes


# Loaders
from langchain_community.document_loaders import (
    PyPDFLoader,
    CSVLoader,
    JSONLoader,
    TextLoader,
)

# Universal extractor
from docling.document_converter import DocumentConverter


class FileContentReader:
    """
    Detects file type from bytes, then extracts readable content.
    Order of attempts:
      1) Detect MIME via libmagic (+ light heuristics)
      2) Use specialized loaders for PDF / JSON / CSV / text
      3) Docling universal extractor for PDFs, Office, images (OCR), HTML, etc.
      4) Final fallback: read as UTF-8 text
    Returns: str (Markdown for Docling, plain text otherwise)
    """

    def __init__(self):
        # Single, reusable converter instance
        self._docling = DocumentConverter()

    # ------------------------ Public API ------------------------

    def read_text(self, file_content: bytes, filename: str = "", hint_mime: Optional[str] = None) -> str:
        """
        Extract text/markdown from file bytes.
        """
        suffix = self._get_file_extension(filename)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
            tf.write(file_content)
            temp_path = tf.name

        try:
            mime = self._detect_mime(file_content, filename, hint_mime)

            # Specialized loaders first (fast/precise)
            if "pdf" in mime:
                return self._read_via_langchain(PyPDFLoader(temp_path))

            if "json" in mime:
                # jq_schema='.' keeps entire JSON; text_content=False keeps structure
                try:
                    return self._read_via_langchain(JSONLoader(temp_path, jq_schema=".", text_content=False))
                except Exception:
                    # Some "JSON" are JSONL or near-JSON text
                    return self._read_via_langchain(TextLoader(temp_path, encoding="utf-8"))

            if "csv" in mime:
                try:
                    return self._read_via_langchain(CSVLoader(temp_path, encoding="utf-8"))
                except Exception:
                    return self._read_via_langchain(TextLoader(temp_path, encoding="utf-8"))

            if mime.startswith("text/"):
                # Heuristic: CSV-like?
                preview = self._safe_text_preview(temp_path)
                if self._is_probably_csv(preview):
                    try:
                        return self._read_via_langchain(CSVLoader(temp_path, encoding="utf-8"))
                    except Exception:
                        pass
                return self._read_via_langchain(TextLoader(temp_path, encoding="utf-8"))

            # Docling for everything complex/binary (OOXML, images, HTML, EPUB, etc.)
            docling_text = self._try_docling(temp_path)
            if docling_text is not None:
                return docling_text

            # Unknown: try heuristics; else raw text
            preview = self._safe_text_preview(temp_path)
            if preview.strip().startswith(("{", "[")):
                try:
                    return self._read_via_langchain(JSONLoader(temp_path, jq_schema=".", text_content=False))
                except Exception:
                    return preview
            if self._is_probably_csv(preview):
                try:
                    return self._read_via_langchain(CSVLoader(temp_path, encoding="utf-8"))
                except Exception:
                    return preview

            # Final fallback: raw UTF-8
            return self._read_file_as_text(temp_path)

        finally:
            self._safe_unlink(temp_path)

    # ------------------------ Internals ------------------------

    def _detect_mime(self, file_content: bytes, filename: str, hint_mime: str = None) -> str:
        # 1) Try filetype (content sniffing)
        kind = filetype.guess(file_content)
        if kind:
            return kind.mime

        # 2) Fallback: filename extension
        mime, _ = mimetypes.guess_type(filename or "")
        if mime:
            return mime

        # 3) Use user hint if provided
        if hint_mime:
            return hint_mime.lower()

        # 4) Default
        return "application/octet-stream"
    def _read_via_langchain(self, loader) -> str:
        docs = loader.load()
        if not docs:
            return ""
        # For multi-doc returns (CSV/JSON), concatenate
        return "\n\n".join(d.page_content for d in docs if getattr(d, "page_content", None))

    def _try_docling(self, path: str) -> Optional[str]:
        try:
            result = self._docling.convert(path)
            doc = getattr(result, "document", None)
            if doc:
                md = doc.export_to_markdown()  # keep Markdown (tables/layout preserved)
                if md and md.strip():
                    return md
        except Exception as e:
            print(f"Docling conversion error: {e}")
            return None
        return None

    def _safe_text_preview(self, path: str, max_bytes: int = 4096) -> str:
        try:
            with open(path, "rb") as f:
                chunk = f.read(max_bytes)
            return chunk.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _read_file_as_text(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""

    @staticmethod
    def _is_probably_csv(text_sample: str) -> bool:
        if not text_sample:
            return False
        if "," in text_sample or ";" in text_sample or "\t" in text_sample:
            lines = text_sample.splitlines()[:5]
            sep_counts = [max(line.count(","), line.count(";"), line.count("\t")) for line in lines]
            return any(c >= 1 for c in sep_counts)
        return False

    @staticmethod
    def _get_file_extension(filename: str) -> str:
        _, ext = os.path.splitext(filename or "")
        return ext

    @staticmethod
    def _safe_unlink(path: str) -> None:
        try:
            if path and os.path.exists(path):
                os.unlink(path)
        except Exception:
            pass


# ------------------------ Example usage ------------------------

# reader = FileContentReader()
# text = reader.read_text(file_bytes, filename="report.docx")
# print(text[:1000])
