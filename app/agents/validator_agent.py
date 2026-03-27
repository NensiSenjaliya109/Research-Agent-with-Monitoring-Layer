"""
agents/validator_agent.py
─────────────────────────────────────────────────────────────────
STEP 8c — Validator Agent

WHAT:  The final quality gate. It checks whether the generated
       answer actually answers the original question well.
         1. Scores relevance (0.0 – 1.0)
         2. Checks completeness
         3. Provides improvement feedback

WHY:   Without validation, the pipeline blindly trusts the LLM.
       In production, a validator:
         • Catches hallucinations or off-topic answers
         • Gives users a confidence signal
         • Creates a feedback loop for improvement

DESIGN:  We use Gemini itself as the validator (LLM-as-a-Judge).
         This is standard practice in production RAG systems.
         The score is a structured JSON output from the model.

PRODUCTION TIP:
  Use a DIFFERENT or stricter prompt for the validator vs the
  summarizer — you want adversarial scrutiny, not agreement.
"""

import json
import logging
import re

from app.utils.gemini_client import generate_text
from app.monitoring.tracker import MetricsTracker

logger = logging.getLogger(__name__)

_VALIDATOR_PROMPT = """You are a strict quality evaluator for AI-generated research answers.

Evaluate the following:

ORIGINAL QUERY: {query}

GENERATED ANSWER:
{answer}

Evaluate the answer on these criteria and respond with ONLY a JSON object (no markdown):

{{
  "relevance_score": <float 0.0 to 1.0>,
  "completeness_score": <float 0.0 to 1.0>,
  "accuracy_confidence": <float 0.0 to 1.0>,
  "overall_score": <float 0.0 to 1.0>,
  "is_acceptable": <true or false>,
  "issues": [<list of specific issues found, empty list if none>],
  "improvement_suggestions": <one sentence suggestion or "None">
}}

Scoring guide:
- relevance_score: Does the answer directly address the query?
- completeness_score: Does it cover the key aspects of the topic?
- accuracy_confidence: Based on reasoning coherence, does it appear factually sound?
- overall_score: Weighted average (relevance 40%, completeness 30%, accuracy 30%)
- is_acceptable: true if overall_score >= 0.6"""


class ValidatorAgent:
    """
    LLM-as-a-Judge validator. Scores and critiques the generated answer.
    """

    def run(self, query: str, answer: str, tracker: MetricsTracker) -> dict:
        """
        Validate the generated answer.

        Returns:
          {
            "overall_score"          : float,   ← 0.0 to 1.0
            "relevance_score"        : float,
            "completeness_score"     : float,
            "accuracy_confidence"    : float,
            "is_acceptable"          : bool,
            "issues"                 : List[str],
            "improvement_suggestions": str,
            "input_tokens"           : int,
            "output_tokens"          : int,
          }
        """
        logger.info(f"[ValidatorAgent] Validating answer for: '{query}'")

        tracker.start_step("validation")
        prompt = _VALIDATOR_PROMPT.format(query=query, answer=answer)

        gemini_response = generate_text(
            prompt=prompt,
            temperature=0.1,       # Very low — we want consistent scoring
            max_output_tokens=512,
        )
        tracker.end_step("validation")

        raw_text = gemini_response["text"]
        input_tokens = gemini_response["input_tokens"]
        output_tokens = gemini_response["output_tokens"]
        tracker.add_tokens(input_tokens, output_tokens)

        # ── Parse JSON from Gemini response ─────────────────────────────────
        validation_result = _parse_validation_json(raw_text)
        validation_result["input_tokens"] = input_tokens
        validation_result["output_tokens"] = output_tokens

        logger.info(
            f"[ValidatorAgent] overall_score={validation_result['overall_score']:.2f} "
            f"acceptable={validation_result['is_acceptable']}"
        )
        return validation_result


def _parse_validation_json(raw_text: str) -> dict:
    """
    Robustly parse the JSON output from the validator LLM.
    Falls back to defaults if parsing fails.
    """
    try:
        # Strip any markdown code fences the model might add
        cleaned = re.sub(r"```(?:json)?", "", raw_text).strip()
        cleaned = cleaned.strip("`").strip()
        data = json.loads(cleaned)

        return {
            "overall_score": float(data.get("overall_score", 0.5)),
            "relevance_score": float(data.get("relevance_score", 0.5)),
            "completeness_score": float(data.get("completeness_score", 0.5)),
            "accuracy_confidence": float(data.get("accuracy_confidence", 0.5)),
            "is_acceptable": bool(data.get("is_acceptable", True)),
            "issues": data.get("issues", []),
            "improvement_suggestions": data.get("improvement_suggestions", "None"),
        }

    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        logger.warning(f"[ValidatorAgent] JSON parse failed ({e}). Using defaults.")
        return {
            "overall_score": 0.5,
            "relevance_score": 0.5,
            "completeness_score": 0.5,
            "accuracy_confidence": 0.5,
            "is_acceptable": True,
            "issues": ["Validation score unavailable — JSON parse error"],
            "improvement_suggestions": "Review validation prompt.",
        }
