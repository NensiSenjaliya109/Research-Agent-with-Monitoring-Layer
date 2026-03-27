from app.vector_store.chroma_store import ChromaStore
from app.utils.gemini_client import call_gemini
from app.utils.text_processor import calculate_cost
from typing import Dict

store = ChromaStore()

RAG_SYSTEM_PROMPT = """You are a precise research assistant. 
Answer questions using ONLY the provided context.
If the context doesn't contain enough information, say so explicitly.
Always be factual and cite which source supports your answer."""

def rag_query(user_query: str, n_context_chunks: int = 4) -> Dict:
    """
    Full RAG pipeline:
    1. Embed the query
    2. Retrieve top-N relevant chunks from ChromaDB
    3. Build a grounded prompt
    4. Call Gemini with the context
    """
    # Step 1+2: Retrieve relevant context
    chunks = store.search(user_query, n_results=n_context_chunks)
    
    if not chunks:
        context = "No relevant information found in the knowledge base."
        sources = []
    else:
        context_parts = []
        sources = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"[{i}] {chunk['text']}")
            url = chunk["metadata"].get("url", "unknown")
            if url not in sources:
                sources.append(url)
        context = "\n\n".join(context_parts)

    # Step 3: Build grounded prompt
    prompt = f"""Context from knowledge base:
{context}

---
User Question: {user_query}

Answer based strictly on the context above:"""

    # Step 4: Generate answer
    result = call_gemini(prompt, system_instruction=RAG_SYSTEM_PROMPT)

    return {
        "answer": result["text"],
        "sources": sources,
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
        "cost": calculate_cost(result["input_tokens"], result["output_tokens"])
    }
