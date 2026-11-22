# 🔭 ScholarCritic: Future Scope & Technical Roadmap

> This document outlines the planned future enhancements, experimental features, architectural roadmap, and currently tracked edge cases / known limitations for **ScholarCritic**.

---

## 🧭 Planned Future Enhancements

The feature roadmap is organized by technical priority and implementation complexity:

### 🌟 Priority 1: High-Impact Immediate Enhancements (v1.1)

| Feature | Target Area | Description | Expected Impact |
| :--- | :--- | :--- | :--- |
| **🎙️ Audio Briefing (Text-to-Speech)** | UI / Audio | Adds a 1-click "Listen to Review" player delivering a natural 60-second podcast-style breakdown of the paper's TL;DR and core findings using Web Speech API or `edge-tts`. | High engagement for quick executive reviews and accessibility. |
| **🔗 Direct arXiv / DOI Ingestion** | Ingestion | Allow users to paste an arXiv link (e.g. `https://arxiv.org/abs/1706.03762`) or paper DOI to automatically stream the PDF without manual downloading. | Eliminates friction; users review papers directly from their browsers in seconds. |
| **📋 BibTeX & Multi-Style Citation Exporter** | Documentation | Instant copy buttons for **BibTeX** (`@article{...}`), **APA 7**, and **IEEE** citation formats based on parsed metadata. | High utility for researchers and graduate students drafting literature reviews. |

---

### 🧠 Priority 2: Advanced Document Intelligence (v1.2)

| Feature | Target Area | Description | Expected Impact |
| :--- | :--- | :--- | :--- |
| **💬 "Ask the Paper" (Grounded Q&A)** | Core AI / RAG | An interactive chat panel beneath the scorecard allowing users to query specific details (e.g. *"What learning rate was used in Table 2?"*, *"Explain Equation 4"*). | Transforms static reviews into interactive research assistants. |
| **📜 Saved Reviews & History Dashboard** | Database / Auth | Leverage existing MongoDB Atlas connection to save generated scorecards and summaries to user profiles for later reference. | Creates a persistent personal research library for logged-in users. |
| **⚖️ Overclaim & Hallucination Audit** | Critic Engine | Specialized heuristic check analyzing whether claims made in the Abstract/Conclusion are mathematically and experimentally supported in the Results section. | Directly tackles academic reproducibility and hype detection. |

---

### 🌐 Priority 3: Large-Scale Research Capabilities (v2.0)

| Feature | Target Area | Description | Expected Impact |
| :--- | :--- | :--- | :--- |
| **⚔️ Multi-Paper Comparative Benchmark** | Analysis Engine | Upload 2 to 4 related papers simultaneously (e.g. *Transformer* vs. *Mamba* vs. *RWKV*) to generate a comparative trade-off matrix. | Elite differentiator for survey papers and literature gap analysis. |
| **🔍 Tesseract OCR Pipeline** | Document Engine | Integrated OCR fallback via `pytesseract` or Google Cloud Vision for older scanned historical papers that lack a digital text layer. | Expands ingestion support to legacy and archive documents. |
| **⚡ Celery / Redis Asynchronous Task Queue** | Infrastructure | Offload PDF parsing and LLM inference to asynchronous background workers with real-time WebSocket progress reporting. | Supports high concurrency and multi-user scaling without blocking web workers. |

---

## 🐛 Known Limitations & Edge Cases Watchlist

The following items represent tracked edge cases, current environmental constraints, and planned architectural mitigations:

### 1. Scanned Image PDFs (Non-Digital Text)
- **Current Behavior:** PyMuPDF checks character count; if a PDF contains only scanned raster images with no embedded text stream, `paper_data['is_scanned']` is set to `True`, and an alert prompts the user to upload a digital PDF.
- **Root Cause:** Optical Character Recognition (OCR) is not currently bundled to keep the initial deployment lightweight and dependency-free.
- **Planned Mitigation:** Introduce an optional `pytesseract` or serverless OCR microservice module in v1.2.

### 2. Complex Mathematical Formulas & Nested Tables
- **Current Behavior:** Standard PyMuPDF text extraction flattens complex multi-line mathematical matrices and non-standard symbols into raw Unicode strings.
- **Current Impact:** Gemini still interprets the general mathematical intent accurately, but specific subscript/superscript alignment inside complex equations can occasionally lose formatting.
- **Planned Mitigation:** Implement layout-aware block extraction (bounding box table reconstruction) to preserve Markdown table structure and LaTeX math syntax.

### 3. Extremely Long Monograph Papers (>50 Pages)
- **Current Behavior:** The system enforces a strict **10MB upload limit** and truncates text if the paper exceeds token limits for a single generation call.
- **Current Impact:** Standard conference papers (8–15 pages) parse with 100% fidelity. For 60+ page PhD dissertations or book chapters, only the core sections (Abstract, Intro, Methods, Results, Conclusion) are prioritized.
- **Planned Mitigation:** Implement hierarchical section chunking with embedding-based retrieval (Vector RAG) for unlimited page capacities.

### 4. Flask Development Server on Windows (`watchdog`)
- **Resolved in v1.0.1:** Aggressive file-watcher reloads on Windows severed active client sockets (`WinError 10054`), showing `Failed to fetch`. Disabling the reloader in production/standalone runs resolved this.
- **Best Practice:** Always run with `python app.py` (with `debug=False`) or via production WSGI `gunicorn app:app` on Linux/Render.

### 5. Third-Party SMTP Relays & Rate Limits
- **Current Behavior:** Uses Gmail SMTP (`smtp.gmail.com:587`) with 16-character Google App Passwords.
- **Current Constraint:** Free personal Gmail accounts have a daily sending limit (~500 emails/day).
- **Planned Mitigation:** Provide pluggable email transport support for transactional providers like **SendGrid**, **Resend**, or **AWS SES** for production enterprise deployments.

---

## 📈 Versioning Roadmap

- **v1.0.0 (Current)**: Multi-column PDF parsing, Gemini Flash Critic Engine, Star Scorecards, 2FA MongoDB Atlas Auth + Gmail OTP, Glassmorphic UI.
- **v1.1.0 (Next Target)**: arXiv Link Ingestion, Audio Briefing (TTS), BibTeX Exporters.
- **v1.2.0**: Interactive "Ask the Paper" Chat Panel, Saved User Reviews in MongoDB.
- **v2.0.0**: Multi-Paper Comparison Matrix, OCR Pipeline, Production Cloud Deployment.
