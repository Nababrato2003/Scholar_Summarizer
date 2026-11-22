"""
test_e2e.py - Complete End-to-End Test for ScholarCritic.
Simulates a user uploading a multi-page PDF paper, extracts sections,
generates Gemini peer critique + scoring, and verifies the downloadable report.
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.test_parser import create_sample_pdf
from core.parser import extract_paper_content
from core.model import analyze_paper
from app import generate_markdown_report


def test_full_pipeline():
    print("=== STEP 1: Simulating Academic PDF Upload ===")
    pdf_bytes = create_sample_pdf()
    assert len(pdf_bytes) > 0, "PDF generation failed"
    print(f"Generated PDF size: {len(pdf_bytes)} bytes")

    print("\n=== STEP 2: PyMuPDF Section & Text Extraction ===")
    paper_data = extract_paper_content(pdf_bytes)
    print(f"Title: {paper_data['title']}")
    print(f"Total Pages: {paper_data['total_pages']}")
    print(f"Word Count: {paper_data['word_count']}")
    print(f"Is Scanned: {paper_data['is_scanned']}")
    assert paper_data['total_pages'] == 2
    assert not paper_data['is_scanned']

    print("\n=== STEP 3: Gemini Critic Engine & Peer Scoring ===")
    analysis = analyze_paper(paper_data)
    
    tldr = analysis.get("summary", {}).get("tldr", "")
    nov = analysis.get("scores", {}).get("novelty", {}).get("score", 0)
    cla = analysis.get("scores", {}).get("clarity", {}).get("score", 0)
    rep = analysis.get("scores", {}).get("reproducibility", {}).get("score", 0)
    ovr = analysis.get("scores", {}).get("overall", {}).get("score", 0)
    strengths = analysis.get("critique", {}).get("strengths", [])
    weaknesses = analysis.get("critique", {}).get("weaknesses", [])

    print(f"Executive TL;DR: {tldr}")
    print(f"Scores: Novelty={nov}/5, Clarity={cla}/5, Reproducibility={rep}/5, Overall={ovr}/5")
    print(f"Strengths ({len(strengths)}): {strengths[0] if strengths else 'N/A'}")
    print(f"Weaknesses ({len(weaknesses)}): {weaknesses[0] if weaknesses else 'N/A'}")

    assert 1 <= nov <= 5
    assert 1 <= cla <= 5
    assert 1 <= rep <= 5
    assert len(strengths) > 0
    assert len(weaknesses) > 0

    print("\n=== STEP 4: Exportable Report Generation ===")
    report_md = generate_markdown_report(analysis, paper_data)
    assert "# 📄 Academic Peer Review & Critic Report" in report_md
    assert "## 🏆 Scorecard & Evaluation Matrix" in report_md
    assert "## ⚖️ Research Critic Report" in report_md
    print(f"Generated report length: {len(report_md)} characters")

    print("\n🎉 Full End-to-End ScholarCritic Pipeline PASSED!")


if __name__ == "__main__":
    test_full_pipeline()
