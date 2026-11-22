"""
parser.py - Research Paper PDF & Text Extraction Engine using PyMuPDF.

Handles extraction of multi-page academic PDFs, detects structural sections
(Title, Abstract, Methodology, Results, Conclusion), and flags scanned/empty documents.
"""

import os
import re
import pymupdf
from typing import Dict, Any, Union, BinaryIO

COMMON_SECTION_PATTERNS = {
    "abstract": re.compile(r"^(?:abstract|summary)\b", re.IGNORECASE),
    "introduction": re.compile(r"^(?:\d+[\.\s]+)?(?:introduction|background)\b", re.IGNORECASE),
    "methodology": re.compile(r"^(?:\d+[\.\s]+)?(?:methodology|methods|proposed\s+method|architecture|approach)\b", re.IGNORECASE),
    "results": re.compile(r"^(?:\d+[\.\s]+)?(?:results|experiments|evaluation|findings)\b", re.IGNORECASE),
    "discussion": re.compile(r"^(?:\d+[\.\s]+)?(?:discussion|limitations)\b", re.IGNORECASE),
    "conclusion": re.compile(r"^(?:\d+[\.\s]+)?(?:conclusion|conclusions|future\s+work)\b", re.IGNORECASE),
    "references": re.compile(r"^(?:\d+[\.\s]+)?(?:references|bibliography)\b", re.IGNORECASE),
}


class PDFParserError(Exception):
    """Custom exception raised when PDF parsing fails."""
    pass


def extract_paper_content(source: Union[str, bytes, BinaryIO]) -> Dict[str, Any]:
    """
    Extracts text, metadata, and detected sections from a PDF or plain text string.

    Args:
        source: File path (str), raw PDF bytes, or file-like object.

    Returns:
        Dict containing:
            - title: Inferred title of the paper
            - full_text: Full extracted text of the paper
            - sections: Dict of detected sections (abstract, methodology, results, etc.)
            - total_pages: Number of pages (1 for raw text)
            - word_count: Total word count
            - is_scanned: True if extracted text is suspiciously short (indicates image-only scan)
    """
    if isinstance(source, str) and not os.path.exists(source):
        # Direct raw text provided (not an existing PDF file path)
        return _process_raw_text(source)

    try:
        if isinstance(source, bytes):
            doc = pymupdf.open(stream=source, filetype="pdf")
        elif hasattr(source, "read"):
            # File-like object (e.g. Flask FileStorage.stream)
            content = source.read()
            doc = pymupdf.open(stream=content, filetype="pdf")
        elif isinstance(source, str):
            doc = pymupdf.open(source)
        else:
            raise PDFParserError(f"Unsupported source type: {type(source)}")
    except Exception as e:
        raise PDFParserError(f"Failed to open PDF document: {str(e)}")

    total_pages = doc.page_count
    if total_pages == 0:
        doc.close()
        raise PDFParserError("The provided PDF file contains 0 pages.")

    pages_text = []
    first_page_blocks = []

    for i in range(total_pages):
        page = doc[i]
        # Get blocks to preserve reading order in multi-column layouts
        text = page.get_text("text")
        pages_text.append(text)
        if i == 0:
            first_page_blocks = page.get_text("blocks")

    doc_metadata = doc.metadata or {}
    doc.close()

    full_text = "\n\n".join(pages_text).strip()
    word_count = len(full_text.split())

    # Detect if document is likely a scanned image PDF
    is_scanned = (total_pages > 0 and (len(full_text) / total_pages) < 50)

    # Infer Title
    title = _infer_title(first_page_blocks, doc_metadata, full_text)

    # Segment into detected sections
    sections = _segment_sections(full_text)

    return {
        "title": title,
        "full_text": full_text,
        "sections": sections,
        "total_pages": total_pages,
        "word_count": word_count,
        "is_scanned": is_scanned
    }


def _infer_title(first_page_blocks: list, doc_metadata: dict, full_text: str) -> str:
    """Infers paper title from metadata or highest prominent block on page 1."""
    meta_title = (doc_metadata.get("title") or "").strip()
    if meta_title and len(meta_title) > 5 and not meta_title.lower().endswith(".pdf"):
        return meta_title

    # Fallback to the first significant text block on page 1
    if first_page_blocks:
        for block in first_page_blocks:
            # block format: (x0, y0, x1, y1, text, block_no, block_type)
            block_text = block[4].strip() if len(block) > 4 else ""
            lines = [l.strip() for l in block_text.splitlines() if l.strip()]
            if lines:
                candidate = " ".join(lines)
                # Skip page numbers, header tags, or tiny text
                if 8 < len(candidate) < 250 and not candidate.lower().startswith("arxiv:"):
                    return candidate

    # Fallback to first non-empty line of full text
    for line in full_text.splitlines():
        line = line.strip()
        if len(line) > 8:
            return line[:150]

    return "Untitled Academic Paper"


def _segment_sections(full_text: str) -> Dict[str, str]:
    """Segments paper text into canonical sections using heading heuristics."""
    sections = {
        "abstract": "",
        "methodology": "",
        "results": "",
        "conclusion": "",
        "other": ""
    }

    lines = full_text.splitlines()
    current_section = "other"
    buffer = {k: [] for k in sections}

    for line in lines:
        cleaned_line = line.strip()
        if not cleaned_line:
            continue

        # Check if line matches a known section header
        matched_section = None
        for sec_name, pattern in COMMON_SECTION_PATTERNS.items():
            if pattern.match(cleaned_line) and len(cleaned_line.split()) <= 6:
                matched_section = sec_name
                break

        if matched_section:
            if matched_section in ("methodology", "introduction"):
                current_section = "methodology" if matched_section == "methodology" else "other"
            elif matched_section in ("results", "discussion"):
                current_section = "results"
            elif matched_section == "conclusion":
                current_section = "conclusion"
            elif matched_section == "abstract":
                current_section = "abstract"
            elif matched_section == "references":
                # Stop parsing main content after references
                current_section = "other"
        else:
            buffer[current_section].append(cleaned_line)

    for k in sections:
        sections[k] = "\n".join(buffer[k]).strip()

    return sections


def _process_raw_text(text: str) -> Dict[str, Any]:
    """Helper for direct raw text input."""
    clean_text = text.strip()
    sections = _segment_sections(clean_text)
    first_line = clean_text.splitlines()[0][:120] if clean_text else "Pasted Text Research Document"
    
    return {
        "title": first_line,
        "full_text": clean_text,
        "sections": sections,
        "total_pages": 1,
        "word_count": len(clean_text.split()),
        "is_scanned": False
    }
