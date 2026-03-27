from app.utils.gemini_client import call_gemini
from app.utils.text_processor import calculate_cost
from typing import Dict
import re
import time

VALIDATOR_SYSTEM = """You are a strict quality assessor for AI-generated research.
Be objective and critical. Output ONLY valid JSON."""

class ValidatorAgent:
    """
    Responsibility: Score the quality of the summary and return a final answer.
    Catches hallucinations, irrelevance, and incompleteness.
    
    This is your quality gate — nothing low-quality goes to the user.
    """

    def run(self, query: str, summary: str, sources: list) -> Dict:
        start = time.time()

        sources_str = "\n".join(sources) if sources else "None"
        
        prompt = f"""Evaluate this research summary. Return ONLY valid JSON.

Original Query: {query}

Summary to Evaluate:
{summary}

Sources Used: {sources_str}

Return this exact JSON structure:
{{
  "relevance_score": <0.0-1.0, how well does the summary answer the query>,
  "completeness_score": <0.0-1.0, how complete is the information>,
  "confidence_score": <0.0-1.0, how confident are you in the accuracy>,
  "overall_score": <average of above three>,
  "issues": ["list any problems found"],
  "final_answer": "<clean, direct answer to the original query in 2-4 sentences>",
  "recommendation": "PASS" or "FAIL"
}}"""

        result = call_gemini(prompt, system_instruction=VALIDATOR_SYSTEM)
        
        # Parse JSON from Gemini — strip markdown code fences if present
        text = result["text"].strip()
        text = re.sub(r'^```(?:json)?\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
        
        import json
        try:
            validation = json.loads(text)
        except json.JSONDecodeError:
            # Fallback if Gemini adds extra text
            validation = {
                "relevance_score": 0.5,
                "completeness_score": 0.5,
                "confidence_score": 0.5,
                "overall_score": 0.5,
                "issues": ["Could not parse validator response"],
                "final_answer": summary[:500],
                "recommendation": "PASS"
            }

        validation["input_tokens"] = result["input_tokens"]
        validation["output_tokens"] = result["output_tokens"]
        validation["cost"] = calculate_cost(result["input_tokens"], result["output_tokens"])
        validation["latency"] = round(time.time() - start, 3)

        return validation
