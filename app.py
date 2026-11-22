"""
app.py - Autonomous Research Paper Summarizer + Critic
Flask Backend powered by Google Gemini (gemini-3.5-flash), PyMuPDF,
and MongoDB Atlas Authentication with Gmail OTP 2-Factor Verification.
"""

import os
import json
from flask import Flask, render_template, request, jsonify, Response, session
from werkzeug.exceptions import RequestEntityTooLarge
from dotenv import load_dotenv

from parser import extract_paper_content, PDFParserError
from model import analyze_paper
from auth import (
    authenticate_or_register_step1,
    verify_otp_step2,
    resend_otp
)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "scholarcritic-super-secret-key-2026")

# Max upload limit: 10 Megabytes
MAX_FILE_SIZE_MB = 10
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE_MB * 1024 * 1024  # 10 MB in bytes


@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    """Handles upload size exceeding 10MB."""
    return jsonify({
        "error": f"File exceeds the {MAX_FILE_SIZE_MB}MB limit. Please upload a file smaller than {MAX_FILE_SIZE_MB}MB."
    }), 413


@app.route("/")
def home():
    """Renders the main dashboard."""
    api_key_configured = bool(os.getenv("GEMINI_API_KEY"))
    user_email = session.get("user_email")
    return render_template(
        "index.html",
        max_file_size_mb=MAX_FILE_SIZE_MB,
        api_key_configured=api_key_configured,
        user_email=user_email
    )


# --- AUTHENTICATION & OTP ROUTES ---

@app.route("/auth/status", methods=["GET"])
def auth_status():
    """Returns current user session authentication state."""
    user_email = session.get("user_email")
    return jsonify({
        "authenticated": bool(user_email),
        "email": user_email
    })


@app.route("/auth/login", methods=["POST"])
def auth_step1():
    """
    Step 1: Validates credentials (or registers new account), generates OTP,
    and sends it to the user's email address.
    """
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    is_signup = bool(data.get("is_signup", False))

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    success, message = authenticate_or_register_step1(email, password, is_signup)
    if not success:
        return jsonify({"error": message}), 400

    return jsonify({
        "status": "otp_sent",
        "message": message,
        "email": email
    })


@app.route("/auth/verify-otp", methods=["POST"])
def auth_step2():
    """
    Step 2: Verifies entered 6-digit OTP against MongoDB Atlas.
    On success, stores user in session.
    """
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    otp = data.get("otp", "").strip()

    if not email or not otp:
        return jsonify({"error": "Email and OTP code are required."}), 400

    success, message = verify_otp_step2(email, otp)
    if not success:
        return jsonify({"error": message}), 400

    # Authentication completed! Set session
    session["user_email"] = email

    return jsonify({
        "status": "authenticated",
        "message": "Authentication successful!",
        "email": email
    })


@app.route("/auth/resend-otp", methods=["POST"])
def auth_resend():
    """Resends a new 6-digit OTP to the user's email."""
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    if not email:
        return jsonify({"error": "Email is required."}), 400

    success, message = resend_otp(email)
    if not success:
        return jsonify({"error": message}), 400

    return jsonify({"status": "resent", "message": message})


@app.route("/auth/logout", methods=["POST"])
def auth_logout():
    """Logs out the user and clears session."""
    session.pop("user_email", None)
    return jsonify({"status": "logged_out", "message": "Successfully logged out."})


# --- PAPER ANALYSIS & EXPORT ---

@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Analyzes an uploaded research paper PDF or pasted text.
    Requires user to be authenticated with OTP.
    """
    if not session.get("user_email"):
        return jsonify({
            "error": "Authentication required. Please sign in and verify with your email OTP to use ScholarCritic.",
            "auth_required": True
        }), 401

    if not os.getenv("GEMINI_API_KEY"):
        return jsonify({"error": "Gemini API key is not configured. Please add GEMINI_API_KEY to your .env file."}), 400

    paper_source = None

    # Check for PDF file upload
    if "file" in request.files and request.files["file"].filename != "":
        uploaded_file = request.files["file"]
        
        # Check filename extension
        if not uploaded_file.filename.lower().endswith(".pdf"):
            return jsonify({"error": "Invalid file type. Please upload a valid .pdf file."}), 400

        # Read content and verify size
        file_bytes = uploaded_file.read()
        file_size_mb = len(file_bytes) / (1024 * 1024)
        
        if file_size_mb > MAX_FILE_SIZE_MB:
            return jsonify({
                "error": f"File is too large ({file_size_mb:.1f} MB). Maximum allowed size is {MAX_FILE_SIZE_MB} MB. Please upload a smaller file."
            }), 413

        paper_source = file_bytes

    # Fallback to direct pasted text
    elif "text" in request.form and request.form["text"].strip():
        paper_source = request.form["text"].strip()
    
    if not paper_source:
        return jsonify({"error": "No paper provided. Please upload a PDF or paste text."}), 400

    try:
        # Step 1: Extract structure and sections with PyMuPDF
        paper_data = extract_paper_content(paper_source)

        # Step 2: Run Gemini Critic Engine
        analysis = analyze_paper(paper_data)

        return jsonify({
            "status": "success",
            "paper_data": {
                "title": paper_data.get("title"),
                "total_pages": paper_data.get("total_pages", 1),
                "word_count": paper_data.get("word_count", 0),
                "is_scanned": paper_data.get("is_scanned", False)
            },
            "analysis": analysis
        })

    except PDFParserError as pe:
        return jsonify({"error": f"PDF Parsing Error: {str(pe)}"}), 422
    except Exception as e:
        return jsonify({"error": f"Analysis failed: {str(e)}"}), 500


@app.route("/export", methods=["POST"])
def export_report():
    """Exports formatted Markdown review report for download."""
    data = request.get_json(silent=True) or {}
    analysis = data.get("analysis", {})
    paper_meta = data.get("paper_data", {})

    meta = analysis.get("metadata", {})
    summary = analysis.get("summary", {})
    critique = analysis.get("critique", {})
    scores = analysis.get("scores", {})
    future = analysis.get("future_work", {})

    def format_stars(score):
        clamped = max(1, min(5, int(score or 1)))
        return "★" * clamped + "☆" * (5 - clamped)

    report = f"""# 📄 Academic Peer Review & Critic Report
**Title:** {meta.get('title', paper_meta.get('title', 'Untitled'))}  
**Domain:** {meta.get('domain', 'N/A')}  
**Authors:** {', '.join(meta.get('authors', ['Unknown']))}  
**Pages Analyzed:** {paper_meta.get('total_pages', 1)} | **Word Count:** {paper_meta.get('word_count', 0):,}  

---

## 🏆 Scorecard & Evaluation Matrix
- **Novelty:** {scores.get('novelty', {}).get('score', 0)}/5 ({format_stars(scores.get('novelty', {}).get('score', 0))}) — {scores.get('novelty', {}).get('rationale', '')}
- **Clarity:** {scores.get('clarity', {}).get('score', 0)}/5 ({format_stars(scores.get('clarity', {}).get('score', 0))}) — {scores.get('clarity', {}).get('rationale', '')}
- **Reproducibility:** {scores.get('reproducibility', {}).get('score', 0)}/5 ({format_stars(scores.get('reproducibility', {}).get('score', 0))}) — {scores.get('reproducibility', {}).get('rationale', '')}
- **Overall Verdict:** {scores.get('overall', {}).get('score', 0)}/5 — {scores.get('overall', {}).get('verdict', '')}

---

## 📌 Executive Summary
> **TL;DR:** {summary.get('tldr', 'N/A')}

### Key Contributions
"""
    for c in summary.get("key_contributions", []):
        report += f"- {c}\n"

    sec = summary.get("sections", {})
    report += f"""
### Section Breakdown
- **Problem Statement:** {sec.get('problem_statement', 'N/A')}
- **Methodology Overview:** {sec.get('methodology', 'N/A')}
- **Key Findings:** {sec.get('key_findings', 'N/A')}
- **Conclusion:** {sec.get('conclusion', 'N/A')}

---

## ⚖️ Research Critic Report

### Strengths
"""
    for s in critique.get("strengths", []):
        report += f"- ✅ {s}\n"

    report += "\n### Weaknesses & Limitations\n"
    for w in critique.get("weaknesses", []):
        report += f"- ⚠️ {w}\n"

    dataset_crit = critique.get("dataset_and_experiments", {})
    report += f"""
### Dataset & Validation Analysis
- **Methodology Novelty:** {critique.get('methodology_novelty', 'N/A')}
- **Dataset Sufficiency:** {dataset_crit.get('dataset_sufficiency', 'N/A')}
- **Bias & Overfitting Risks:** {dataset_crit.get('bias_and_overfitting_risks', 'N/A')}
- **Validation Rigor:** {dataset_crit.get('validation_rigor', 'N/A')}

---

## 💡 Future Research Directions
### Recommended Improvements
"""
    for imp in future.get("suggested_improvements", []):
        report += f"- {imp}\n"

    report += "\n### Alternative Approaches\n"
    for alt in future.get("alternative_approaches", []):
        report += f"- {alt}\n"

    report += "\n### Practical Real-World Applications\n"
    for app in future.get("real_world_applications", []):
        report += f"- {app}\n"

    report += "\n---\n*Generated autonomously by ScholarCritic powered by Google Gemini.*"

    return Response(
        report,
        mimetype="text/markdown",
        headers={"Content-Disposition": "attachment;filename=ScholarCritic_Report.md"}
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
