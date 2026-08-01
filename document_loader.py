"""Structured PDF extraction and page-aware chunking.

The ingestion pipeline keeps page, section, and OCR provenance all the way to
the vector-store boundary.  Legacy string helpers remain available for older
callers, but production ingestion uses :func:`load_pdf_chunks`.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import unicodedata
from dataclasses import dataclass, replace
from pathlib import Path

import fitz

from config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    OCR_DPI,
    OCR_ENABLED,
    OCR_LANGUAGES,
    OCR_MIN_TEXT_CHARS,
)

logger = logging.getLogger(__name__)

PARSER_VERSION = "pymupdf-blocks-ocr-v3"
CHUNKER_VERSION = "page-block-section-v2"

_HYPHENATED_LINE_BREAK = re.compile(r"(\w)-\s*\n\s*(\w)")
_WHITESPACE = re.compile(r"[^\S\n]+")
_SECTION_PREFIX = re.compile(
    r"^(?:section\s+)?(?:\d+(?:\.\d+)*|[ivxlcdm]+)[.)]?\s+\S",
    flags=re.IGNORECASE,
)
_CJK = re.compile(r"[\u3400-\u9fff]")
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?。！？；;])(?:\s+|(?=\S))")
_QUARTER_TABLE_CELL = re.compile(
    r"^(?:q[1-4]|[1-4]q)(?:[-_/ ]?(?:fy)?\d{2,4})?$",
    flags=re.IGNORECASE,
)
_DATE_TABLE_CELL = re.compile(
    r"^(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
    r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|"
    r"nov(?:ember)?|dec(?:ember)?)\s+\d{1,2},?$",
    flags=re.IGNORECASE,
)
_KNOWN_SINGLE_WORD_HEADINGS = {
    "conclusion",
    "financials",
    "liquidity",
    "operations",
    "outlook",
    "overview",
    "results",
    "revenue",
    "risks",
    "strategy",
}
_MIN_MERGED_CHUNK_CHARS = 80
_MIN_INDEXABLE_CHUNK_CHARS = 40
_OCR_LONG_BLOCK_CHARS = 40
_OCR_STRICT_LONG_BLOCK_CHARS = 200
_OCR_MIN_ALNUM_RATIO = 0.65
_OCR_MAX_SINGLE_TOKEN_RATIO = 0.40
_OCR_MIN_USEFUL_ALNUM_RATIO = 0.85
_OCR_STRICT_MAX_SINGLE_TOKEN_RATIO = 0.25
_OCR_STRICT_MIN_USEFUL_ALNUM_RATIO = 0.90
_OCR_CJK_TEXT_RATIO = 0.20
_OCR_MAX_DOMINANT_CHAR_RATIO = 0.60
_OCR_BAD_UNICODE_CATEGORIES = frozenset({"Cc", "Cf", "Cs", "Co", "Cn"})


class DocumentProcessingError(ValueError):
    """Raised when a PDF cannot be converted into indexable content."""


@dataclass(frozen=True, slots=True)
class ParsedBlock:
    """One sorted text block extracted from a PDF page."""

    text: str
    page: int
    section: str
    ocr_used: bool
    is_heading: bool = False


@dataclass(frozen=True, slots=True)
class ParsedPage:
    """Structured content and extraction provenance for one PDF page."""

    number: int
    blocks: tuple[ParsedBlock, ...]
    ocr_used: bool


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    """A PDF represented as page-scoped, reading-order text blocks."""

    filename: str
    pages: tuple[ParsedPage, ...]
    parser_version: str = PARSER_VERSION


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    """An indexable chunk with source provenance."""

    text: str
    page: int
    section: str
    ocr_used: bool
    chunk_index: int
    parser_version: str = PARSER_VERSION
    chunker_version: str = CHUNKER_VERSION


def get_company(filename: str) -> str:
    normalized = filename.casefold()
    if "apple" in normalized:
        return "Apple"
    if "nvidia" in normalized:
        return "NVIDIA"
    if "tesla" in normalized:
        return "Tesla"
    return "Unknown"


def get_quarter(filename: str) -> str:
    match = re.search(r"(Q\d.*)\.pdf", filename, flags=re.IGNORECASE)
    return match.group(1) if match else "Unknown"


def clean_text(text: str) -> str:
    """Normalize a single text unit without joining separate PDF blocks."""

    normalized = _HYPHENATED_LINE_BREAK.sub(r"\1\2", text)
    normalized = _WHITESPACE.sub(" ", normalized)
    normalized = re.sub(r"\s*\n\s*", " ", normalized)
    return normalized.strip()


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Backward-compatible boundary-aware string chunking helper."""

    _validate_chunk_settings(chunk_size, overlap)
    normalized = clean_text(text)
    if not normalized:
        return []
    return _split_long_text(normalized, chunk_size, overlap)


def parse_pdf(
    pdf_path: str | os.PathLike[str],
    *,
    ocr_enabled: bool = OCR_ENABLED,
    ocr_languages: str = OCR_LANGUAGES,
    ocr_dpi: int = OCR_DPI,
    ocr_min_text_chars: int = OCR_MIN_TEXT_CHARS,
) -> ParsedDocument:
    """Extract sorted page blocks and OCR pages with insufficient text."""

    source_path = Path(pdf_path)
    if not source_path.is_file():
        raise DocumentProcessingError(f"PDF file not found: {source_path}")
    if source_path.stat().st_size == 0:
        raise DocumentProcessingError("PDF file is empty")
    if ocr_dpi < 72:
        raise ValueError("OCR_DPI must be at least 72")
    if ocr_min_text_chars < 0:
        raise ValueError("OCR_MIN_TEXT_CHARS must be non-negative")
    if ocr_enabled and not ocr_languages.strip():
        raise ValueError("OCR_LANGUAGES must not be empty when OCR is enabled")

    try:
        with fitz.open(source_path) as pdf:
            if pdf.page_count == 0:
                raise DocumentProcessingError("PDF contains no pages")

            pages: list[ParsedPage] = []
            active_section = ""
            for page_index, page in enumerate(pdf):
                page_number = page_index + 1
                native_blocks = _extract_text_blocks(page)
                raw_blocks = native_blocks
                text_characters = sum(
                    len(re.sub(r"\s+", "", block_text))
                    for block_text in native_blocks
                )
                ocr_used = False

                if ocr_enabled and text_characters < ocr_min_text_chars:
                    ocr_blocks = _extract_ocr_blocks(
                        page,
                        page_number=page_number,
                        languages=ocr_languages,
                        dpi=ocr_dpi,
                    )
                    raw_blocks = _filter_ocr_blocks(ocr_blocks)
                    rejected_blocks = len(ocr_blocks) - len(raw_blocks)
                    logger.info(
                        "OCR quality gate page=%s accepted_blocks=%s "
                        "rejected_blocks=%s",
                        page_number,
                        len(raw_blocks),
                        rejected_blocks,
                    )
                    if raw_blocks:
                        ocr_used = True
                    else:
                        raw_blocks = native_blocks

                parsed_blocks: list[ParsedBlock] = []
                for raw_text in raw_blocks:
                    text = clean_text(raw_text)
                    if not text:
                        continue
                    is_heading = _looks_like_heading(raw_text, text)
                    if is_heading:
                        active_section = text
                    parsed_blocks.append(
                        ParsedBlock(
                            text=text,
                            page=page_number,
                            section=active_section or f"Page {page_number}",
                            ocr_used=ocr_used,
                            is_heading=is_heading,
                        )
                    )

                pages.append(
                    ParsedPage(
                        number=page_number,
                        blocks=tuple(parsed_blocks),
                        ocr_used=ocr_used,
                    )
                )
    except DocumentProcessingError:
        raise
    except Exception as exc:
        raise DocumentProcessingError(f"Unable to parse PDF {source_path.name}: {exc}") from exc

    if not any(page.blocks for page in pages):
        raise DocumentProcessingError("PDF contains no extractable text")

    return ParsedDocument(filename=source_path.name, pages=tuple(pages))


def chunk_document(
    document: ParsedDocument,
    *,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[DocumentChunk]:
    """Create page- and section-scoped chunks from parsed PDF blocks."""

    _validate_chunk_settings(chunk_size, overlap)
    chunks: list[DocumentChunk] = []

    for page in document.pages:
        page_chunks: list[DocumentChunk] = []
        group: list[ParsedBlock] = []
        active_section: str | None = None
        for block in page.blocks:
            if group and block.section != active_section:
                page_chunks.extend(
                    _chunk_block_group(
                        group,
                        chunk_size=chunk_size,
                        overlap=overlap,
                        start_index=len(page_chunks),
                    )
                )
                group = []
            active_section = block.section
            group.append(block)

        if group:
            page_chunks.extend(
                _chunk_block_group(
                    group,
                    chunk_size=chunk_size,
                    overlap=overlap,
                    start_index=len(page_chunks),
                )
            )
        chunks.extend(
            _merge_tiny_page_chunks(
                page_chunks,
                minimum_chars=min(_MIN_MERGED_CHUNK_CHARS, chunk_size),
            )
        )

    return [
        replace(chunk, chunk_index=index)
        for index, chunk in enumerate(_deduplicate_chunks(chunks))
    ]


def load_pdf_chunks(
    pdf_path: str | os.PathLike[str],
    *,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
    ocr_enabled: bool = OCR_ENABLED,
    ocr_languages: str = OCR_LANGUAGES,
    ocr_dpi: int = OCR_DPI,
    ocr_min_text_chars: int = OCR_MIN_TEXT_CHARS,
) -> list[DocumentChunk]:
    """Run the canonical parser and chunker for one PDF."""

    document = parse_pdf(
        pdf_path,
        ocr_enabled=ocr_enabled,
        ocr_languages=ocr_languages,
        ocr_dpi=ocr_dpi,
        ocr_min_text_chars=ocr_min_text_chars,
    )
    chunks = chunk_document(
        document,
        chunk_size=chunk_size,
        overlap=overlap,
    )
    if not chunks:
        raise DocumentProcessingError("PDF produced no indexable chunks")
    return chunks


def load_documents(pdf_folder: str | os.PathLike[str]) -> list[dict[str, object]]:
    """Load public/demo PDFs through the same ingestion path as uploads."""

    folder = Path(pdf_folder)
    documents: list[dict[str, object]] = []
    pdf_files = sorted(path for path in folder.iterdir() if path.is_file() and path.suffix.casefold() == ".pdf")

    for pdf_path in pdf_files:
        company = get_company(pdf_path.name)
        quarter = get_quarter(pdf_path.name)
        content_sha256 = _file_sha256(pdf_path)
        document_id = pdf_path.stem.casefold().replace(" ", "_").replace("-", "_")
        for chunk in load_pdf_chunks(pdf_path):
            documents.append(
                {
                    "source": pdf_path.name,
                    "chunk_id": chunk.chunk_index,
                    "company": company,
                    "quarter": quarter,
                    "document_id": document_id,
                    "text": chunk.text,
                    "page": chunk.page,
                    "section": chunk.section,
                    "ocr_used": chunk.ocr_used,
                    "parser_version": chunk.parser_version,
                    "chunker_version": chunk.chunker_version,
                    "content_sha256": content_sha256,
                }
            )

    logger.info(
        "Loaded public knowledge PDFs count=%s chunks=%s",
        len(pdf_files),
        len(documents),
    )
    return documents


def prepare_document(pdf_path: str | os.PathLike[str]) -> list[str]:
    """Compatibility wrapper returning text-only chunks."""

    return [chunk.text for chunk in load_pdf_chunks(pdf_path)]


def show_chunk_preview(chunks: list[dict[str, object]]) -> None:
    """Print a small preview for legacy command-line workflows."""

    print("=" * 60)
    print("DOCUMENT INFORMATION")
    print("=" * 60)
    print(f"Total Chunks: {len(chunks)}")
    for chunk in chunks[:3]:
        print("-" * 60)
        print(f"Source: {chunk['source']}")
        print(f"Chunk ID: {chunk['chunk_id']}")
        print(f"Company: {chunk['company']}")
        print(f"Quarter: {chunk['quarter']}")
        print(str(chunk["text"])[:300])
        print("...")


def _extract_text_blocks(
    page: fitz.Page,
    *,
    textpage: fitz.TextPage | None = None,
) -> list[str]:
    blocks = page.get_text(
        "blocks",
        sort=True,
        textpage=textpage,
    )
    return [str(block[4]) for block in blocks if len(block) >= 7 and block[6] == 0 and str(block[4]).strip()]


def _extract_ocr_blocks(
    page: fitz.Page,
    *,
    page_number: int,
    languages: str,
    dpi: int,
) -> list[str]:
    try:
        textpage = page.get_textpage_ocr(
            language=languages,
            dpi=dpi,
            full=True,
        )
        return _extract_text_blocks(page, textpage=textpage)
    except Exception as exc:
        raise DocumentProcessingError(f"OCR failed on page {page_number} with languages {languages!r}: {exc}") from exc


def _filter_ocr_blocks(blocks: list[str]) -> list[str]:
    """Remove OCR blocks that are mostly image-derived character noise."""

    filtered = [block for block in blocks if _is_usable_ocr_block(block)]
    if filtered and _is_usable_ocr_block("\n".join(filtered)):
        return filtered
    return []


def _is_usable_ocr_block(text: str) -> bool:
    """Apply a Unicode-aware OCR quality gate without using a word list."""

    normalized = unicodedata.normalize("NFKC", text)
    visible = [character for character in normalized if not character.isspace()]
    if not visible:
        return False

    alphanumeric = [character for character in visible if character.isalnum()]
    if not alphanumeric:
        return False

    bad_characters = [
        character
        for character in visible
        if character == "\ufffd"
        or unicodedata.category(character) in _OCR_BAD_UNICODE_CATEGORIES
    ]
    if _has_consecutive_bad_characters(visible):
        return False
    if (
        len(bad_characters) >= 2
        and len(bad_characters) / len(visible) > 0.05
    ):
        return False

    character_counts: dict[str, int] = {}
    for character in visible:
        key = character.casefold()
        character_counts[key] = character_counts.get(key, 0) + 1
    if (
        len(visible) >= 12
        and max(character_counts.values()) / len(visible)
        >= _OCR_MAX_DOMINANT_CHAR_RATIO
    ):
        return False

    if (
        len(visible) >= _OCR_LONG_BLOCK_CHARS
        and len(alphanumeric) / len(visible) < _OCR_MIN_ALNUM_RATIO
    ):
        return False

    tokens = _ocr_alphanumeric_tokens(normalized)
    if len(tokens) < 6:
        return True

    cjk_characters = sum(
        1 for character in alphanumeric if _CJK.fullmatch(character)
    )
    if cjk_characters / len(alphanumeric) >= _OCR_CJK_TEXT_RATIO:
        return True

    single_token_ratio = sum(len(token) == 1 for token in tokens) / len(tokens)
    useful_alphanumeric = sum(len(token) for token in tokens if len(token) >= 2)
    useful_alphanumeric_ratio = useful_alphanumeric / len(alphanumeric)
    if len(visible) >= _OCR_STRICT_LONG_BLOCK_CHARS:
        return (
            single_token_ratio <= _OCR_STRICT_MAX_SINGLE_TOKEN_RATIO
            and useful_alphanumeric_ratio
            >= _OCR_STRICT_MIN_USEFUL_ALNUM_RATIO
        )
    return (
        single_token_ratio <= _OCR_MAX_SINGLE_TOKEN_RATIO
        and useful_alphanumeric_ratio >= _OCR_MIN_USEFUL_ALNUM_RATIO
    )


def _has_consecutive_bad_characters(characters: list[str]) -> bool:
    consecutive = 0
    for character in characters:
        is_bad = (
            character == "\ufffd"
            or unicodedata.category(character) in _OCR_BAD_UNICODE_CATEGORIES
        )
        consecutive = consecutive + 1 if is_bad else 0
        if consecutive >= 3:
            return True
    return False


def _ocr_alphanumeric_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    current_is_cjk: bool | None = None

    for character in text:
        if not character.isalnum():
            if current:
                tokens.append("".join(current))
                current = []
                current_is_cjk = None
            continue

        is_cjk = bool(_CJK.fullmatch(character))
        if current and is_cjk != current_is_cjk:
            tokens.append("".join(current))
            current = []
        current.append(character)
        current_is_cjk = is_cjk

    if current:
        tokens.append("".join(current))
    return tokens


def _looks_like_heading(raw_text: str, normalized_text: str) -> bool:
    if len(normalized_text) > 140:
        return False
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if len(lines) > 2:
        return False
    if normalized_text.endswith(
        (".", "?", "!", "。", "？", "！", ";", "；", ",", "，")
    ):
        return False

    words = normalized_text.split()
    if len(words) > 16:
        return False
    if _SECTION_PREFIX.match(normalized_text):
        return True
    if _looks_like_table_cell(normalized_text):
        return False
    if normalized_text.endswith((":", "：")):
        return True

    letters = "".join(character for character in normalized_text if character.isalpha())
    if (
        letters
        and letters.isupper()
        and not any(character.isdigit() for character in normalized_text)
        and (
            len(letters) >= 6
            or normalized_text.casefold() in _KNOWN_SINGLE_WORD_HEADINGS
        )
    ):
        return True
    if _CJK.search(normalized_text):
        return 4 <= len(normalized_text) <= 30

    title_words = [word for word in words if any(character.isalpha() for character in word)]
    if len(title_words) == 1:
        return False
    return len(title_words) >= 2 and all(word[0].isupper() for word in title_words)


def _looks_like_table_cell(text: str) -> bool:
    compact = text.strip()
    if _QUARTER_TABLE_CELL.fullmatch(compact):
        return True
    if _DATE_TABLE_CELL.fullmatch(compact):
        return True
    if len(compact) <= 40 and any(character.isdigit() for character in compact):
        return True
    return False


def _chunk_block_group(
    blocks: list[ParsedBlock],
    *,
    chunk_size: int,
    overlap: int,
    start_index: int,
) -> list[DocumentChunk]:
    expanded: list[ParsedBlock] = []
    for block in blocks:
        parts = _split_long_text(block.text, chunk_size, overlap)
        expanded.extend(
            ParsedBlock(
                text=part,
                page=block.page,
                section=block.section,
                ocr_used=block.ocr_used,
                is_heading=block.is_heading and index == 0,
            )
            for index, part in enumerate(parts)
        )

    chunks: list[DocumentChunk] = []
    current: list[ParsedBlock] = []
    for block in expanded:
        proposed_length = _joined_length([*current, block])
        if current and proposed_length > chunk_size:
            chunks.append(
                _make_chunk(
                    current,
                    chunk_index=start_index + len(chunks),
                )
            )
            current = _overlap_blocks(current, overlap)
            while current and _joined_length([*current, block]) > chunk_size:
                current.pop(0)
        current.append(block)

    if current:
        chunks.append(
            _make_chunk(
                current,
                chunk_index=start_index + len(chunks),
            )
        )
    return chunks


def _make_chunk(
    blocks: list[ParsedBlock],
    *,
    chunk_index: int,
) -> DocumentChunk:
    return DocumentChunk(
        text="\n\n".join(block.text for block in blocks),
        page=blocks[0].page,
        section=blocks[0].section,
        ocr_used=any(block.ocr_used for block in blocks),
        chunk_index=chunk_index,
    )


def _merge_tiny_page_chunks(
    chunks: list[DocumentChunk],
    *,
    minimum_chars: int,
) -> list[DocumentChunk]:
    """Merge short adjacent chunks without crossing a page boundary."""

    pending = list(chunks)
    index = 0
    while len(pending) > 1 and index < len(pending):
        chunk = pending[index]
        if (
            len(_normalize_content(chunk.text)) >= minimum_chars
            and not _is_heading_only_chunk(chunk)
        ):
            index += 1
            continue

        if index + 1 < len(pending):
            pending[index : index + 2] = [
                _merge_chunks(chunk, pending[index + 1])
            ]
            continue

        pending[index - 1 : index + 1] = [
            _merge_chunks(pending[index - 1], chunk)
        ]
        index = max(index - 1, 0)
    return pending


def _merge_chunks(
    first: DocumentChunk,
    second: DocumentChunk,
) -> DocumentChunk:
    paragraphs: list[str] = []
    seen: set[str] = set()
    for text in (first.text, second.text):
        for paragraph in text.split("\n\n"):
            key = _normalize_content(paragraph)
            if key and key not in seen:
                seen.add(key)
                paragraphs.append(paragraph.strip())
    section = (
        second.section
        if _is_heading_only_chunk(first) and not _is_heading_only_chunk(second)
        else first.section
    )
    return replace(
        first,
        text="\n\n".join(paragraphs),
        section=section,
        ocr_used=first.ocr_used or second.ocr_used,
    )


def _is_heading_only_chunk(chunk: DocumentChunk) -> bool:
    return _normalize_content(chunk.text) == _normalize_content(chunk.section)


def _deduplicate_chunks(
    chunks: list[DocumentChunk],
) -> list[DocumentChunk]:
    deduplicated: list[DocumentChunk] = []
    seen: set[str] = set()
    for chunk in chunks:
        key = _normalize_content(chunk.text)
        if (
            len(key) < _MIN_INDEXABLE_CHUNK_CHARS
            or _is_heading_only_chunk(chunk)
            or key in seen
        ):
            continue
        seen.add(key)
        deduplicated.append(chunk)
    return deduplicated


def _normalize_content(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def _overlap_blocks(
    blocks: list[ParsedBlock],
    overlap: int,
) -> list[ParsedBlock]:
    if overlap == 0:
        return []

    retained: list[ParsedBlock] = []
    retained_length = 0
    for block in reversed(blocks):
        if retained and retained_length + len(block.text) > overlap:
            break
        retained.insert(0, block)
        retained_length += len(block.text)
        if retained_length >= overlap:
            break
    return retained


def _joined_length(blocks: list[ParsedBlock]) -> int:
    if not blocks:
        return 0
    return sum(len(block.text) for block in blocks) + (2 * (len(blocks) - 1))


def _split_long_text(
    text: str,
    chunk_size: int,
    overlap: int,
) -> list[str]:
    if len(text) <= chunk_size:
        return [text]

    sentences = [sentence.strip() for sentence in _SENTENCE_BOUNDARY.split(text) if sentence.strip()]
    if len(sentences) > 1 and all(len(sentence) <= chunk_size for sentence in sentences):
        pieces: list[str] = []
        current = ""
        for sentence in sentences:
            proposed = f"{current} {sentence}".strip()
            if current and len(proposed) > chunk_size:
                pieces.append(current)
                prefix = current[-overlap:].lstrip() if overlap else ""
                current = f"{prefix} {sentence}".strip()
            else:
                current = proposed
        if current:
            pieces.append(current)
        return pieces

    pieces = []
    step = chunk_size - overlap
    for start in range(0, len(text), step):
        piece = text[start : start + chunk_size].strip()
        if piece:
            pieces.append(piece)
        if start + chunk_size >= len(text):
            break
    return pieces


def _validate_chunk_settings(chunk_size: int, overlap: int) -> None:
    if chunk_size < 1:
        raise ValueError("CHUNK_SIZE must be positive")
    if overlap < 0:
        raise ValueError("CHUNK_OVERLAP must be non-negative")
    if overlap >= chunk_size:
        raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
