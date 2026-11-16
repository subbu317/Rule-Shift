"""PDF ingestion: embedded text only. Scans are reported, never OCR-guessed."""
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
import pymupdf

PREFIX = re.compile(r"^\s*(?P<id>\d{1,3}(?:\.\d+)*[.)]?|\([a-z]\)|Section\s+\d+(?:\.\d+)*)\s+[\-:]?\s*(?P<body>\S.*)$", re.I)


@dataclass
class ParsedClause:
    ordinal: int
    key: str
    heading: str
    text: str
    page: int


def parse_pdf(data: bytes, max_pages: int = 80) -> tuple[list[ParsedClause], int, list[dict]]:
    if not data.startswith(b"%PDF-"):
        raise ValueError("File is not a PDF")
    try:
        document = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise ValueError("Cannot open this PDF") from exc
    try:
        if document.is_encrypted:
            raise ValueError("Password-protected PDFs are not supported")
        count = len(document)
        if not 1 <= count <= max_pages:
            raise ValueError(f"PDF must have 1–{max_pages} pages")
        if sum(len(page.get_text("text")) for page in document) > 1_500_000:
            raise ValueError("Document contains too much text")
        warnings: list[dict] = []
        clauses: list[ParsedClause] = []
        current: dict | None = None
        for idx, page in enumerate(document):
            raw = page.get_text("text", sort=True)
            if len(raw.strip()) < 30:
                warnings.append({"page": idx + 1, "message": "Little or no embedded text: scanned page may require OCR (not automatically inferred).", "kind": "scan"})
            lines = [re.sub(r"\s+", " ", line).strip() for line in raw.splitlines()]
            for line in lines:
                if not line:
                    continue
                found = PREFIX.match(line)
                # Start a new clause for numbered provisions; exclude bare page numbers.
                if found and len(found.group("body")) >= 5:
                    if current:
                        clauses.append(_finish(current, len(clauses) + 1))
                    current = {"key": found.group("id").strip(".)"), "lines": [line], "page": idx + 1}
                elif current:
                    current["lines"].append(line)
                else:
                    # Unnumbered documents: paragraphs are treated as clauses.
                    if len(line) > 25 and re.search(r"\b(must|shall|may|eligible|required|deadline|income|age|marks)\b", line, re.I):
                        current = {"key": "", "lines": [line], "page": idx + 1}
            # End on page boundary to preserve exact references.
            if current:
                clauses.append(_finish(current, len(clauses) + 1))
                current = None
        if not clauses:
            raise ValueError("No usable policy clauses found. Upload a text-based PDF, not a scanned image.")
        return clauses, count, warnings
    finally:
        document.close()


def _finish(record: dict, ordinal: int) -> ParsedClause:
    full = " ".join(record["lines"]).strip()
    # First fragment before a colon or a short dash is a human-readable title.
    content = PREFIX.sub(lambda m: m.group("body"), full, count=1) if record["key"] else full
    short = re.split(r":\s+|\s+[–-]\s+", content, maxsplit=1)[0]
    heading = (short if len(short) < 72 else " ".join(short.split()[:6])).strip(" .")
    return ParsedClause(ordinal, record["key"], heading[:180], full, record["page"])


def document_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def render_page(path: Path, page_number: int, evidence: str | None = None) -> bytes:
    with pymupdf.open(path) as doc:
        if page_number < 1 or page_number > len(doc):
            raise ValueError("Invalid page number")
        page = doc[page_number - 1]
        if evidence:
            # Search short distinct text fragments; full paragraphs may span lines.
            fragments = re.sub(r"^\s*\d+[.)]\s*", "", evidence).split()
            fragment = " ".join(fragments[:6])
            for rect in page.search_for(fragment, quads=False)[:8]:
                page.draw_rect(rect, color=(0.08, 0.75, 0.57), fill=(0.67, 0.98, 0.84), fill_opacity=0.30, overlay=True)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(1.4, 1.4), alpha=False)
        return pix.tobytes("png")
