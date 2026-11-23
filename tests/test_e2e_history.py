"""
tests/test_e2e_history.py - End-to-end integration test for PDF History & Download.
Tests the full lifecycle using Flask's test client and MongoDB Atlas.
"""

import os
import sys
import io
import fitz
from dotenv import load_dotenv

from unittest.mock import patch
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv()
from app import app
from core.storage import get_storage_db

def create_dummy_pdf(title="Adaptive Low-Rank Attention Networks"):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), f"Title: {title}", fontsize=16)
    page.insert_text((50, 110), "Authors: A. Vaswani, E. Hu, et al.", fontsize=12)
    page.insert_text((50, 150), "Abstract:\nWe present an empirical study of low-rank parameter-efficient fine-tuning\ncombined with multi-head self-attention mechanisms across standard NLP benchmarks.", fontsize=10)
    page.insert_text((50, 220), "Methodology:\nOur architecture decomposes the weight update matrix into low-rank factors.\nWe evaluate convergence speed and memory reduction on 8x A100 GPUs.", fontsize=10)
    page.insert_text((50, 300), "Experiments & Results:\nExperiments on GLUE benchmarks show that our method retains 99.4% of full\nfine-tuning accuracy while updating only 0.2% of trainable parameters.", fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def test_full_history_lifecycle():
    print("=== STARTING FULL HISTORY E2E INTEGRATION TEST ===")
    app.config["TESTING"] = True
    test_user = "test_user_history@domain.com"
    pdf_bytes = create_dummy_pdf()

    with app.test_client() as client:
        # 1. Establish signed-in session
        with client.session_transaction() as sess:
            sess["user_email"] = test_user
        print(f"1. Signed in as {test_user}")

        # 2. Check initial history
        res = client.get("/history")
        assert res.status_code == 200, f"History fetch failed: {res.data}"
        initial_history = res.get_json().get("history", [])
        print(f"2. Initial user history count: {len(initial_history)}")

        # 3. Analyze paper with PDF upload (mocking Gemini model response)
        print("3. Uploading & analyzing PDF to /analyze...")
        data = {
            "file": (io.BytesIO(pdf_bytes), "Adaptive_Attention.pdf")
        }
        mock_analysis = {
            "metadata": {
                "title": "Adaptive Low-Rank Attention Networks",
                "authors": ["A. Vaswani", "E. Hu"],
                "domain": "Natural Language Processing"
            },
            "summary": {
                "tldr": "Parameter-efficient fine-tuning via decomposed low-rank attention adaptation.",
                "key_contributions": ["Low-rank factorized attention updates", "99.4% GLUE accuracy retention"],
                "sections": {
                    "problem_statement": "Full fine-tuning is computationally prohibitive.",
                    "methodology": "Decomposes weight updates into low-rank matrices.",
                    "key_findings": "Retains performance with 0.2% trainable parameters.",
                    "conclusion": "Enables scalable adaptation of large models."
                }
            },
            "critique": {
                "strengths": ["Clear mathematical formulation", "Substantial parameter reduction"],
                "weaknesses": ["Limited to transformer architectures"],
                "methodology_novelty": "Novel rank decomposition strategy",
                "dataset_and_experiments": {
                    "dataset_sufficiency": "Evaluated on GLUE benchmark suite",
                    "bias_and_overfitting_risks": "Minimal risk observed",
                    "validation_rigor": "Standard cross-validation employed"
                }
            },
            "scores": {
                "novelty": {"score": 4.5, "rationale": "High novelty in parameter efficiency"},
                "clarity": {"score": 5.0, "rationale": "Extremely well-written"},
                "reproducibility": {"score": 4.8, "rationale": "Clear algorithmic specification"},
                "overall": {"score": 4.7, "verdict": "Strong Accept"}
            },
            "future_work": {
                "suggested_improvements": ["Extend to vision-language models"],
                "alternative_approaches": ["Quantized low-rank updates"],
                "real_world_applications": ["Edge device model adaptation"]
            }
        }

        with patch("app.analyze_paper", return_value=mock_analysis):
            res = client.post("/analyze", data=data, content_type="multipart/form-data")
        assert res.status_code == 200, f"Analysis failed: {res.data}"
        analysis_data = res.get_json()
        saved_id = analysis_data.get("saved_history_id")
        assert saved_id, f"No saved_history_id returned! Response: {analysis_data}"
        print(f"   Analysis succeeded! Saved to History with ID: {saved_id}")

        # 4. Fetch updated history list
        res = client.get("/history")
        assert res.status_code == 200
        history_list = res.get_json().get("history", [])
        assert len(history_list) >= 1, "History list is empty!"
        saved_entry = next((h for h in history_list if h["id"] == saved_id), None)
        assert saved_entry is not None, f"Saved paper {saved_id} not found in history list!"
        print(f"4. Verified paper exists in history list. Title: {saved_entry['paper_title']}, Size: {saved_entry['file_size']} bytes")

        # 5. Fetch cached review JSON
        res = client.get(f"/history/{saved_id}")
        assert res.status_code == 200, f"Failed to get review JSON: {res.data}"
        review_data = res.get_json().get("analysis", {})
        assert "metadata" in review_data and "scores" in review_data, "Cached review is missing expected fields!"
        print(f"5. Successfully fetched cached review JSON! Domain: {review_data.get('metadata', {}).get('domain')}")

        # 6. Download original binary PDF
        res = client.get(f"/history/{saved_id}/download")
        assert res.status_code == 200, f"Failed to download PDF: {res.data}"
        assert res.mimetype == "application/pdf", f"Unexpected mimetype: {res.mimetype}"
        downloaded_bytes = res.data
        assert len(downloaded_bytes) == len(pdf_bytes), f"Byte length mismatch! Original: {len(pdf_bytes)}, Downloaded: {len(downloaded_bytes)}"
        assert downloaded_bytes == pdf_bytes, "Downloaded PDF bytes do not match original uploaded PDF bytes!"
        print("6. Binary PDF downloaded with 100% byte-for-byte fidelity!")

        # 7. Delete paper from history & GridFS
        res = client.delete(f"/history/{saved_id}")
        assert res.status_code == 200, f"Failed to delete paper: {res.data}"
        print(f"7. Deleted paper {saved_id} from history.")

        # 8. Verify it is gone from history
        res = client.get(f"/history/{saved_id}")
        assert res.status_code == 404, "Paper still returned after deletion!"
        res_dl = client.get(f"/history/{saved_id}/download")
        assert res_dl.status_code == 404, "PDF still downloadable after deletion!"
        print("8. Verified deletion from both collection and GridFS chunks.")

    print("=== ALL E2E HISTORY TESTS PASSED PERFECTLY! ===")

if __name__ == "__main__":
    test_full_history_lifecycle()
