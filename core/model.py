"""
model.py - Autonomous Research Paper Summarizer & Critic Engine.

Powered by Google Gemini (gemini-3.5-flash) with structured JSON generation.
Extracts deep insights, performs critical evaluation (strengths, weaknesses, bias, reproducibility),
calculates academic scores, and proposes future research directions.
"""

import os
import json
from typing import Dict, Any, Union
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Available candidate models in order of priority
PRIMARY_MODEL = "gemini-3.5-flash"
FALLBACK_MODEL = "gemini-3.8-flash"

SYSTEM_INSTRUCTION = """
You are an expert academic peer-reviewer and research analyst for top-tier venues (NeurIPS, ICML, Nature, Science).
Your task is to analyze the provided research paper content and generate a comprehensive, structured evaluation in strict JSON format.

You must be rigorous, objective, and analytically sharp. Do NOT simply praise the paper; critically inspect:
1. Methodological novelty vs. incremental tweaks.
2. Dataset sufficiency, potential sampling bias, data leakage, and overfitting risks.
3. Clarity and reproducibility (are hyperparameters, proofs, or ablation studies clearly documented?).
4. Real-world applicability vs. purely synthetic benchmark performance.

Return ONLY valid JSON matching this exact structure:
{
  "metadata": {
    "title": "Inferred or explicit title of the paper",
    "authors": ["List of authors or Unknown if not specified"],
    "domain": "Field of research (e.g., Computer Vision, NLP, Bioinformatics)"
  },
  "summary": {
    "tldr": "A sharp, 1-2 sentence executive summary of the entire paper",
    "key_contributions": [
      "Core contribution 1",
      "Core contribution 2",
      "Core contribution 3"
    ],
    "sections": {
      "problem_statement": "What specific challenge does this work solve?",
      "methodology": "How does the proposed solution work technically?",
      "key_findings": "What were the empirical or theoretical findings?",
      "conclusion": "The main takeaway conclusion"
    }
  },
  "critique": {
    "strengths": [
      "Rigorous strength 1",
      "Rigorous strength 2",
      "Rigorous strength 3"
    ],
    "weaknesses": [
      "Specific limitation or flaw 1",
      "Specific limitation or flaw 2",
      "Specific limitation or flaw 3"
    ],
    "methodology_novelty": "In-depth critique of whether the approach is genuinely novel or an incremental combination of existing methods",
    "dataset_and_experiments": {
      "dataset_sufficiency": "Assessment of dataset size, variety, and realism",
      "bias_and_overfitting_risks": "Potential biases, risk of benchmark overfitting, or leakage",
      "validation_rigor": "Are baselines fair and ablated properly?"
    }
  },
  "scores": {
    "novelty": {
      "score": 4,
      "rationale": "Brief justification for novelty score (1-5)"
    },
    "clarity": {
      "score": 5,
      "rationale": "Brief justification for clarity score (1-5)"
    },
    "reproducibility": {
      "score": 3,
      "rationale": "Brief justification for reproducibility score (1-5)"
    },
    "overall": {
      "score": 4.0,
      "verdict": "Accept, Weak Accept, Borderline, or Reject with summary rationale"
    }
  },
  "future_work": {
    "suggested_improvements": [
      "Actionable engineering or theoretical improvement 1",
      "Actionable improvement 2"
    ],
    "alternative_approaches": [
      "Alternative paradigm or model architecture that could tackle this"
    ],
    "real_world_applications": [
      "Immediate or near-term practical use case in industry"
    ]
  }
}
All scores must be integers between 1 and 5 (overall score can be a float from 1.0 to 5.0).
"""


def get_client() -> genai.Client:
    """Returns an initialized Google GenAI client using GEMINI_API_KEY from environment."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment. Please set it in your .env file.")
    return genai.Client(api_key=api_key)


def analyze_paper(paper_data: Union[Dict[str, Any], str]) -> Dict[str, Any]:
    """
    Main entry point for autonomous summarization, peer critique, and paper scoring.

    Args:
        paper_data: Either a dictionary returned by parser.extract_paper_content,
                    or raw paper text string.

    Returns:
        Structured dictionary matching the peer review JSON schema.
    """
    client = get_client()

    # Normalize input
    if isinstance(paper_data, dict):
        full_text = paper_data.get("full_text", "")
        inferred_title = paper_data.get("title", "")
        sections = paper_data.get("sections", {})
        
        # Build prompt payload
        user_prompt = f"TITLE: {inferred_title}\n\n"
        if sections.get("abstract"):
            user_prompt += f"--- ABSTRACT ---\n{sections['abstract']}\n\n"
        if sections.get("methodology"):
            user_prompt += f"--- METHODOLOGY ---\n{sections['methodology']}\n\n"
        if sections.get("results"):
            user_prompt += f"--- RESULTS ---\n{sections['results']}\n\n"
        if sections.get("conclusion"):
            user_prompt += f"--- CONCLUSION ---\n{sections['conclusion']}\n\n"
        
        user_prompt += f"--- FULL PAPER TEXT ---\n{full_text}"
    else:
        user_prompt = f"--- FULL PAPER TEXT ---\n{str(paper_data)}"

    # Configure Gemini with strict JSON mode
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        response_mime_type="application/json",
        temperature=0.2,
    )

    # Attempt with primary model, fallback if needed
    for model_name in [PRIMARY_MODEL, FALLBACK_MODEL]:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=config
            )
            raw_text = response.text.strip()
            parsed_json = json.loads(raw_text)
            return parsed_json
        except Exception as e:
            if model_name == FALLBACK_MODEL:
                raise RuntimeError(f"Critic Engine failed across models: {str(e)}")
            continue

    raise RuntimeError("Critic Engine failed to generate analysis.")


def summarize_text(text: str) -> str:
    """
    Backwards-compatibility helper for legacy callers.
    Returns the executive TL;DR summary string.
    """
    try:
        analysis = analyze_paper(text)
        return analysis.get("summary", {}).get("tldr", "Summary generation completed.")
    except Exception as e:
        return f"Error analyzing paper: {str(e)}"
