from app.tools.web_search import search_web
from app.vector_store.chroma_store import ChromaStore
from app.utils.text_processor import clean_text, format_search_results
from typing import Dict, List
import time

store = ChromaStore()

class ResearchAgent:
    """
    Responsibility: Gather raw information from the web and store it.
    It does NOT summarize or judge — that's other agents' jobs.
    """
    
    def run(self, query: str) -> Dict:
        start = time.time()
        
        print(f"🔍 ResearchAgent: Searching for '{query}'")
        raw_results: List[Dict] = search_web(query)
        
        if not raw_results:
            return {
                "status": "no_results",
                "raw_text": "",
                "sources": [],
                "chunks_stored": 0,
                "latency": time.time() - start
            }

        # Clean and format the text
        texts = [clean_text(r["text"]) for r in raw_results if r.get("text")]
        sources = [r["url"] for r in raw_results if r.get("url")]
        combined_text = format_search_results(raw_results)

        # Store in ChromaDB with source metadata
        metadatas = [{"url": r["url"], "title": r["title"], "query": query}
                     for r in raw_results]
        chunks_stored = store.add_documents(texts, metadatas=metadatas)
        
        print(f"📦 ResearchAgent: Stored {chunks_stored} chunks from {len(sources)} sources")

        return {
            "status": "success",
            "raw_text": combined_text,
            "sources": sources,
            "chunks_stored": chunks_stored,
            "latency": round(time.time() - start, 3)
        }
