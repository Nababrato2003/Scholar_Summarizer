"""
test_parser.py - Verification script for Phase 2 PDF parsing engine.
Generates an in-memory sample academic PDF and verifies text extraction,
title inference, section segmentation, and scanned status detection.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pymupdf
from core.parser import extract_paper_content, PDFParserError


def create_sample_pdf() -> bytes:
    """Creates a realistic 2-page sample academic paper in memory."""
    doc = pymupdf.open()

    # Page 1
    page1 = doc.new_page()
    page1.insert_text(
        (50, 70),
        "Deep Learning for Autonomous Code Review and Verification",
        fontsize=16,
        fontname="helv"
    )
    page1.insert_text((50, 100), "Authors: Jane Doe, John Smith - Stanford University", fontsize=10)
    page1.insert_text(
        (50, 140),
        "Abstract\nIn this paper, we propose an automated deep learning framework for code verification.\n"
        "Our experiments indicate a 94.5% precision on standard benchmark suites.",
        fontsize=11
    )
    page1.insert_text(
        (50, 240),
        "Methodology\nWe train a transformer-based encoder-decoder model on 50,000 open-source repositories.\n"
        "Data was normalized and tokenized using byte-pair encoding with a vocabulary size of 32,000.",
        fontsize=11
    )

    # Page 2
    page2 = doc.new_page()
    page2.insert_text(
        (50, 70),
        "Results\nThe proposed method outperforms baseline models by 12.3% F1 score across 10 evaluation datasets.\n"
        "Ablation studies reveal that attention gating is critical for capturing long-range dependencies.",
        fontsize=11
    )
    page2.insert_text(
        (50, 180),
        "Conclusion\nWe have introduced a reliable, autonomous evaluation system for code.\n"
        "Future work will explore cross-lingual code verification and real-time inference.",
        fontsize=11
    )

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_parser():
    print("Testing PDF Parser with generated academic paper...")
    pdf_bytes = create_sample_pdf()

    result = extract_paper_content(pdf_bytes)

    print("\n--- Extracted Results ---")
    print(f"Title: {result['title']}")
    print(f"Total Pages: {result['total_pages']}")
    print(f"Word Count: {result['word_count']}")
    print(f"Is Scanned: {result['is_scanned']}")
    print(f"Abstract Detected: {bool(result['sections']['abstract'])}")
    print(f"Methodology Detected: {bool(result['sections']['methodology'])}")
    print(f"Results Detected: {bool(result['sections']['results'])}")
    print(f"Conclusion Detected: {bool(result['sections']['conclusion'])}")

    # Assertions
    assert result['total_pages'] == 2, f"Expected 2 pages, got {result['total_pages']}"
    assert "Deep Learning" in result['title'], f"Title inference failed: {result['title']}"
    assert result['word_count'] > 40, f"Word count too low: {result['word_count']}"
    assert not result['is_scanned'], "Document was mistakenly flagged as scanned"
    assert "94.5%" in result['sections']['abstract'], "Abstract content missing"
    assert "transformer-based" in result['sections']['methodology'], "Methodology content missing"
    assert "outperforms baseline" in result['sections']['results'], "Results content missing"
    assert "cross-lingual" in result['sections']['conclusion'], "Conclusion content missing"

    print("\n✅ All PDF Parser assertions passed successfully!")


if __name__ == "__main__":
    test_parser()
