"""
test_storage.py - Automated verification for core/storage.py
Tests MongoDB GridFS PDF chunking, metadata recording, byte integrity, and deletion.
"""

import os
import sys
import hashlib
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.storage import (
    save_paper_history,
    get_user_history,
    get_paper_review,
    get_paper_pdf,
    delete_paper_history
)
from tests.test_parser import create_sample_pdf


def test_storage_engine():
    test_user = "test_user_storage_verify@scholarcritic.dev"
    test_filename = "Verification_Test_Paper.pdf"
    
    print("1. Generating sample PDF bytes...")
    sample_pdf_bytes = create_sample_pdf()
    original_sha256 = hashlib.sha256(sample_pdf_bytes).hexdigest()
    print(f"Sample PDF size: {len(sample_pdf_bytes)} bytes, SHA256: {original_sha256[:10]}...")

    sample_analysis = {
        "metadata": {
            "title": "Deep Learning for Autonomous Code Review and Verification",
            "authors": ["Jane Doe", "John Smith"],
            "domain": "Computer Science / Software Engineering"
        },
        "scores": {
            "novelty": {"score": 5, "rationale": "High novelty in automated review."},
            "clarity": {"score": 4, "rationale": "Clear and well documented."},
            "reproducibility": {"score": 4, "rationale": "Ablations documented."},
            "overall": {"score": 5, "verdict": "Accept with Distinction"}
        },
        "summary": {
            "tldr": "A deep learning framework for code verification achieving 94.5% precision.",
            "key_contributions": ["Novel architecture", "Empirical validation"]
        }
    }

    print("\n2. Testing save_paper_history (PDF GridFS + Metadata)...")
    paper_id = save_paper_history(test_user, test_filename, sample_pdf_bytes, sample_analysis)
    print(f"Saved paper history record with ID: {paper_id}")
    assert paper_id is not None and len(paper_id) == 24, "Invalid ObjectId returned"

    print("\n3. Testing get_user_history...")
    history = get_user_history(test_user)
    print(f"Found {len(history)} records for test user")
    assert len(history) >= 1, "Expected at least 1 record"
    matched = [h for h in history if h["id"] == paper_id]
    assert len(matched) == 1, "Saved record not found in user history list"
    assert matched[0]["paper_title"] == "Deep Learning for Autonomous Code Review and Verification"
    assert matched[0]["scores"]["novelty"]["score"] == 5

    print("\n4. Testing get_paper_review...")
    review = get_paper_review(paper_id, test_user)
    assert review is not None
    assert review["summary"]["tldr"].startswith("A deep learning framework")
    print("Successfully retrieved review JSON payload!")

    print("\n5. Testing get_paper_pdf (Byte Integrity Check)...")
    retrieved_filename, retrieved_bytes = get_paper_pdf(paper_id, test_user)
    assert retrieved_filename == test_filename
    retrieved_sha256 = hashlib.sha256(retrieved_bytes).hexdigest()
    assert retrieved_sha256 == original_sha256, "PDF bytes corrupted during GridFS store/retrieve!"
    print("PDF byte integrity 100% MATCHED!")

    print("\n6. Testing delete_paper_history...")
    delete_success = delete_paper_history(paper_id, test_user)
    assert delete_success is True, "Failed to delete paper history"

    # Verify gone
    assert get_paper_pdf(paper_id, test_user) is None
    assert get_paper_review(paper_id, test_user) is None
    print("Successfully deleted record and verified cleanup from GridFS!")

    print("\n✅ ALL STORAGE & GRIDFS TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_storage_engine()
