import streamlit as st
import time
import os
import sys
from datetime import datetime

# Add project root to python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator import get_orchestrator
from app.monitoring.tracker import read_logs

# ── Page Config & Styling ──────────────────────────────────────
st.set_page_config(
    page_title="Autonomous Research Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Premium Custom CSS
st.markdown("""
<style>
    /* Main container styling */
    .stApp {
        background-color: #050d1a;
        color: #e2e8f0;
    }
    
    /* Customize headers */
    h1, h2, h3 {
        color: #f8fafc !important;
        font-weight: 700 !important;
    }
    
    /* Styled container cards */
    div.element-container:has(div.metric-card) {
        background-color: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 12px;
    }
    
    /* Custom status indicators */
    .status-text {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if "query" not in st.session_state:
    st.session_state.query = ""
if "research_results" not in st.session_state:
    st.session_state.research_results = None

# Helper to prefill query
def set_query(q):
    st.session_state.query = q

# ── Sidebar: History & Status ──────────────────────────────────
with st.sidebar:
    st.title("⚙️ System Panel")
    
    # Environment Status Indicators
    st.markdown("### Status")
    gemini_ok = bool(os.getenv("GEMINI_API_KEY"))
    serp_ok = bool(os.getenv("SERPAPI_API_KEY"))
    
    col_g, col_s = st.columns(2)
    with col_g:
        st.markdown(f"**Gemini API**<br>{'🟢 Connected' if gemini_ok else '🔴 Missing'}", unsafe_allow_html=True)
    with col_s:
        st.markdown(f"**SerpAPI**<br>{'🟢 Live' if serp_ok else '🟡 Simulated'}", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 📋 Research History")
    
    # Read history logs
    try:
        logs = read_logs(limit=20)
    except Exception:
        logs = []
        
    if not logs:
        st.info("No research history found yet.")
    else:
        for log in logs:
            score = log.get("validation_score", 0.0)
            latency = log.get("metrics", {}).get("total_latency_s", 0.0)
            time_str = log.get("timestamp", "")[:16].replace("T", " ")
            
            # Create a clickable item in sidebar using st.button
            query_trunc = log["query"][:35] + "..." if len(log["query"]) > 35 else log["query"]
            if st.button(
                f"📝 {query_trunc}\n({time_str})",
                key=f"hist_{log.get('request_id')}",
                use_container_width=True
            ):
                st.session_state.query = log["query"]
                st.session_state.research_results = {
                    "answer": log.get("final_answer", ""),
                    "sources": log.get("sources", []),
                    "validation_score": score,
                    "validation": {
                        "overall_score": score,
                        "relevance_score": log.get("validation_score", 0.0), # Fallback mapping
                        "completeness_score": score,
                        "accuracy_confidence": score,
                        "is_acceptable": score >= 0.6,
                        "issues": [],
                        "improvement_suggestions": "N/A"
                    },
                    "metrics": log.get("metrics", {}),
                    "request_id": log.get("request_id", "N/A")
                }
                st.rerun()

# ── Main Content Area ──────────────────────────────────────────
st.markdown("# 🤖 Autonomous Research Agent")
st.markdown("Submit a research topic and watch a multi-agent system retrieve facts, synthesize answers, and validate quality in real time.")

# Query Form
with st.container(border=True):
    query_input = st.text_area(
        "Enter your research question or topic:",
        value=st.session_state.query,
        placeholder="e.g. What is quantum computing and how does it work?",
        max_chars=500,
        height=100
    )
    
    # Example prompts
    st.markdown("<small>Quick Examples:</small>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("What is quantum computing?", use_container_width=True):
            set_query("What is quantum computing?")
            st.rerun()
    with col2:
        if st.button("How does machine learning work?", use_container_width=True):
            set_query("How does machine learning work?")
            st.rerun()
    with col3:
        if st.button("Explain artificial intelligence", use_container_width=True):
            set_query("Explain artificial intelligence")
            st.rerun()
            
    btn_col, _ = st.columns([1, 4])
    with btn_col:
        submit_btn = st.button("🚀 Conduct Research", type="primary", use_container_width=True)

# ── Pipeline Run & Processing ──────────────────────────────────
if submit_btn and query_input:
    st.session_state.query = query_input
    
    # Create steps using st.status container
    with st.status("🔬 Running Multi-Agent Research Pipeline...", expanded=True) as status:
        st.write("🔍 **Stage 1: Research Agent** — Searching web and building local database index...")
        time.sleep(1.0)
        
        st.write("📦 **Stage 2: RAG Synthesizer** — Fetching facts and generating answer via Gemini...")
        time.sleep(1.5)
        
        st.write("⚖️ **Stage 3: Validator Agent** — Running quality checks and scoring accuracy...")
        
        try:
            orchestrator = get_orchestrator()
            results = orchestrator.run(query=query_input)
            
            # Map keys to fit the UI output safely
            if "validation" not in results:
                results["validation"] = {
                    "overall_score": results.get("validation_score", 0.0),
                    "relevance_score": results.get("validation_score", 0.0),
                    "completeness_score": results.get("validation_score", 0.0),
                    "accuracy_confidence": results.get("validation_score", 0.0),
                    "is_acceptable": results.get("validation_score", 0.0) >= 0.6,
                    "issues": results.get("issues", []),
                    "improvement_suggestions": results.get("recommendation", "N/A")
                }
            
            st.session_state.research_results = results
            status.update(label="✅ Research Pipeline Completed!", state="complete", expanded=False)
        except Exception as e:
            status.update(label="❌ Pipeline Execution Failed", state="error", expanded=True)
            st.error(f"Error executing agent pipeline: {str(e)}")
            st.session_state.research_results = None

# ── Render Results ─────────────────────────────────────────────
if st.session_state.research_results:
    res = st.session_state.research_results
    
    col_left, col_right = st.columns([7, 3])
    
    # Left Column: Answer & Sources
    with col_left:
        st.markdown("### 📝 Research Answer")
        
        # Display request ID
        req_id = res.get("request_id", "N/A")
        st.markdown(f"<small style='color: #64748b;'>Request ID: `{req_id}`</small>", unsafe_allow_html=True)
        
        # Answer content
        st.markdown(res.get("answer", "No answer generated."))
        
        # Sources Section
        st.markdown("### 🌐 Information Sources")
        sources = res.get("sources", [])
        if sources:
            for i, src in enumerate(sources):
                st.markdown(f"- [{src}]({src})")
        else:
            st.warning("No reference sources available for this query.")
            
    # Right Column: Score, Metrics & Latency
    with col_right:
        # Score gauge
        st.markdown("### 🏆 Quality Validator")
        score = res.get("validation_score", 0.0)
        
        # Display nice metric color based on score
        if score >= 0.75:
            st.success(f"**Score: {score:.2f} (Excellent)**")
        elif score >= 0.6:
            st.warning(f"**Score: {score:.2f} (Acceptable)**")
        else:
            st.error(f"**Score: {score:.2f} (Poor / Rejected)**")
            
        # Display validation criteria sliders (disabled, just for visualization)
        val_details = res.get("validation", {})
        st.slider("Relevance Score", 0.0, 1.0, float(val_details.get("relevance_score", score)), disabled=True)
        st.slider("Completeness Score", 0.0, 1.0, float(val_details.get("completeness_score", score)), disabled=True)
        st.slider("Accuracy Confidence", 0.0, 1.0, float(val_details.get("accuracy_confidence", score)), disabled=True)
        
        if val_details.get("issues"):
            st.markdown("**Issues Flagged:**")
            for issue in val_details.get("issues"):
                st.markdown(f"- ⚠️ {issue}")
        
        st.markdown("---")
        
        # Performance Metrics
        st.markdown("### ⚡ Metrics Tracker")
        metrics = res.get("metrics", {})
        
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            st.metric("Total Latency", f"{metrics.get('total_latency_s', metrics.get('latency_seconds', 0.0)):.2f}s")
            st.metric("Estimated Cost", f"${metrics.get('estimated_cost_usd', 0.0):.5f}")
        with m_col2:
            st.metric("Total Tokens", f"{metrics.get('total_tokens', 0)}")
            st.metric("DB Chunks Stored", f"{metrics.get('breakdown', {}).get('chunks_stored', 0)}")
            
        # Latency breakdown chart
        st.markdown("**Execution Latency Breakdown**")
        bd = metrics.get("breakdown", {})
        if bd:
            latency_data = {
                "Research Agent": bd.get("research_latency", 0.0),
                "Summarizer Agent": bd.get("summarizer_latency", 0.0),
                "Validator Agent": bd.get("validator_latency", 0.0),
            }
            st.bar_chart(latency_data)
