"""
test_critic.py - Verification script for Phase 3: Core AI Engine & Critic Logic.
Tests model.analyze_paper with sample academic paper content, verifies
JSON structure, critic engine fields, and numeric scoring.
"""

from parser import extract_paper_content
from test_parser import create_sample_pdf
from model import analyze_paper


def test_critic_engine():
    print("Generating sample research paper PDF...")
    pdf_bytes = create_sample_pdf()
    paper_data = extract_paper_content(pdf_bytes)

    print(f"Extracted Paper: '{paper_data['title']}' ({paper_data['word_count']} words)")
    print("Calling Gemini Critic Engine (analyze_paper)...")

    result = analyze_paper(paper_data)

    print("\n--- Model Response Verification ---")
    print(f"Title: {result.get('metadata', {}).get('title')}")
    print(f"Domain: {result.get('metadata', {}).get('domain')}")
    print(f"TL;DR: {result.get('summary', {}).get('tldr')}")
    
    # Check Key Contributions
    contributions = result.get('summary', {}).get('key_contributions', [])
    print(f"Key Contributions count: {len(contributions)}")

    # Check Critique
    strengths = result.get('critique', {}).get('strengths', [])
    weaknesses = result.get('critique', {}).get('weaknesses', [])
    print(f"Strengths count: {len(strengths)}")
    print(f"Weaknesses count: {len(weaknesses)}")
    print(f"Methodology Novelty: {result.get('critique', {}).get('methodology_novelty')[:100]}...")

    # Check Scores
    scores = result.get('scores', {})
    nov = scores.get('novelty', {}).get('score')
    cla = scores.get('clarity', {}).get('score')
    rep = scores.get('reproducibility', {}).get('score')
    ovr = scores.get('overall', {}).get('score')
    print(f"Scores -> Novelty: {nov}/5, Clarity: {cla}/5, Reproducibility: {rep}/5, Overall: {ovr}/5")

    # Check Future Work
    improvements = result.get('future_work', {}).get('suggested_improvements', [])
    print(f"Future Improvements count: {len(improvements)}")

    # Assertions
    assert "metadata" in result, "Missing 'metadata' section in response"
    assert "summary" in result, "Missing 'summary' section in response"
    assert "critique" in result, "Missing 'critique' section in response"
    assert "scores" in result, "Missing 'scores' section in response"
    assert "future_work" in result, "Missing 'future_work' section in response"

    assert len(strengths) >= 1, "Expected at least 1 strength identified"
    assert len(weaknesses) >= 1, "Expected at least 1 weakness identified"
    assert 1 <= nov <= 5, f"Novelty score out of range: {nov}"
    assert 1 <= cla <= 5, f"Clarity score out of range: {cla}"
    assert 1 <= rep <= 5, f"Reproducibility score out of range: {rep}"

    print("\n✅ Phase 3: Core AI Engine & Critic Logic verified successfully!")


if __name__ == "__main__":
    test_critic_engine()
