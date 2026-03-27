import google.generativeai as genai
import os
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# We use Flash — fast, cheap, capable enough for agents
MODEL_NAME = "gemini-2.5-flash"

def get_model():
    return genai.GenerativeModel(MODEL_NAME)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def call_gemini(prompt: str, system_instruction: str = None) -> dict:
    """
    Wraps Gemini API call with retry logic.
    Returns dict with response text and usage metadata.
    """
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=system_instruction
    )
    
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.3,       # Low temp = more factual
            max_output_tokens=2048,
        )
    )
    
    # Extract token counts from response metadata
    usage = response.usage_metadata
    
    return {
        "text": response.text,
        "input_tokens": usage.prompt_token_count,
        "output_tokens": usage.candidates_token_count,
        "total_tokens": usage.total_token_count
    }


# ── Quick test — run this file directly to verify your key works ──
if __name__ == "__main__":
    result = call_gemini("What is the capital of France? Answer in one sentence.")
    print("Response:", result["text"])
    print("Tokens used:", result["total_tokens"])
