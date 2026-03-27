from app.utils.gemini_client import call_gemini
from app.utils.text_processor import calculate_cost
from typing import Dict
import time

SUMMARIZER_SYSTEM = """You are an expert research synthesizer.
Your output must be structured, factual, and concise.
Always organize information under clear headings."""

class SummarizerAgent:
    """
    Responsibility: Transform raw research text into a clean, structured summary.
    Reduces noise and extracts signal for the Validator.
    """
    
    def run(self, query: str, raw_text: str) -> Dict:
        start = time.time()
        
        # Truncate to avoid token overflow (safe limit for Flash)
        max_chars = 8000
        if len(raw_text) > max_chars:
            raw_text = raw_text[:max_chars] + "\n...[truncated]"

        prompt = f"""Research Query: {query}

Raw Research Data:
{raw_text}

Create a structured summary with these sections:
1. **Key Findings** (3-5 bullet points)
2. **Important Details** (relevant facts and data)
3. **Gaps or Uncertainties** (what we don't know)
4. **Answer to Query** (direct answer, 2-3 sentences)"""

        result = call_gemini(prompt, system_instruction=SUMMARIZER_SYSTEM)
        
        return {
            "summary": result["text"],
            "input_tokens": result["input_tokens"],
            "output_tokens": result["output_tokens"],
            "cost": calculate_cost(result["input_tokens"], result["output_tokens"]),
            "latency": round(time.time() - start, 3)
        }
