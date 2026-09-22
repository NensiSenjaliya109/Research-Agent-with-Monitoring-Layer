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

import base64

def get_base64_bg(img_path):
    if os.path.exists(img_path):
        try:
            with open(img_path, "rb") as f:
                data = base64.b64encode(f.read()).decode()
                return f"data:image/png;base64,{data}"
        except Exception:
            pass
    return ""

bg_image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "bg_chatbot.png")
bg_uri = get_base64_bg(bg_image_path)

bg_style = f"background: linear-gradient(rgba(5, 13, 26, 0.86), rgba(5, 13, 26, 0.90)), url('{bg_uri}') no-repeat center center fixed !important; background-size: cover !important;" if bg_uri else "background-color: #050d1a;"
sidebar_bg_style = f"background: linear-gradient(rgba(15, 23, 42, 0.88), rgba(15, 23, 42, 0.93)), url('{bg_uri}') no-repeat center center !important; background-size: cover !important;" if bg_uri else "background-color: #0b1528;"

# Premium Custom CSS
st.markdown(f"""
<style>
    /* Main container styling */
    .stApp {{
        {bg_style}
        color: #e2e8f0;
    }}
    
    /* Sidebar container styling */
    [data-testid="stSidebar"] {{
        {sidebar_bg_style}
    }}
    
    /* Customize headers */
    h1, h2, h3 {{
        color: #f8fafc !important;
        font-weight: 700 !important;
    }}
    
    /* Styled container cards */
    div.element-container:has(div.metric-card) {{
        background-color: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 12px;
        backdrop-filter: blur(10px);
    }}
    
    /* Custom status indicators */
    .status-text {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
    }}
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

import re
from fpdf import FPDF

class PDFReport(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 116, 139)
        self.cell(0, 8, "Autonomous Research Agent - Official Report", align="R", new_x="LMARGIN", new_y="NEXT")
        self.line(10, 16, 200, 16)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

def clean_text_for_pdf(text: str) -> str:
    replacements = {
        "—": "-", "–": "-", "’": "'", "‘": "'",
        "“": '"', "”": '"', "…": "...", "•": "*",
        "―": "-", "?": "-"
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)
    text = re.sub(r'[^\x00-\xFF]', '', text)
    return text

def parse_markdown_to_pdf(pdf: FPDF, markdown_text: str):
    cleaned = clean_text_for_pdf(markdown_text)
    lines = cleaned.split("\n")
    
    for line in lines:
        pdf.set_x(pdf.l_margin)
        line_str = line.strip()
        if not line_str:
            pdf.ln(2)
            continue
            
        # Ignore markdown table separator lines like |---|---|
        if re.match(r"^\|?\s*:?-+:?\s*\|", line_str):
            continue
            
        # Table rows (| Col | Col |)
        if line_str.startswith("|") and line_str.endswith("|"):
            cells = [c.strip() for c in line_str.strip("|").split("|")]
            cells = [re.sub(r"\*\*|\*|`", "", c) for c in cells]
            row_text = "  |  ".join(cells)
            safe_row = row_text.encode('latin-1', 'replace').decode('latin-1')
            pdf.set_font("Helvetica", "B" if pdf.get_y() < 60 else "", 9)
            pdf.set_text_color(51, 65, 85)
            pdf.multi_cell(190, 5, safe_row)
            continue

        # Headings (#, ##, ###, ####)
        if line_str.startswith("#"):
            heading_text = re.sub(r"^#+\s*", "", line_str)
            heading_text = re.sub(r"\*\*|\*|`", "", heading_text) # strip stars
            safe_h = heading_text.encode('latin-1', 'replace').decode('latin-1')
            
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(190, 7, safe_h, new_x="LMARGIN", new_y="NEXT")
            continue

        # Bullet points (*, -, +)
        if line_str.startswith(("* ", "- ", "+ ")):
            bullet_text = re.sub(r"^[\*\-\+]\s*", "", line_str)
            clean_b = re.sub(r"\*\*(.*?)\*\*", r"\1", bullet_text) # strip bold stars
            clean_b = re.sub(r"\*(.*?)\*", r"\1", clean_b)
            clean_b = re.sub(r"`(.*?)`", r"\1", clean_b)
            
            safe_b = f"  - {clean_b}".encode('latin-1', 'replace').decode('latin-1')
            
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(51, 65, 85)
            pdf.multi_cell(190, 6, safe_b)
            continue

        # Normal paragraph text
        clean_p = re.sub(r"\*\*(.*?)\*\*", r"\1", line_str)
        clean_p = re.sub(r"\*(.*?)\*", r"\1", clean_p)
        clean_p = re.sub(r"`(.*?)`", r"\1", clean_p)
        
        safe_p = clean_p.encode('latin-1', 'replace').decode('latin-1')
        
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(190, 6, safe_p)

def generate_report_pdf(res: dict, query: str) -> bytes:
    pdf = PDFReport()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(190, 10, "Research & Quality Audit Report", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(71, 85, 105)
    safe_q = clean_text_for_pdf(query).encode('latin-1', 'replace').decode('latin-1')
    safe_req = str(res.get('request_id', 'N/A')).encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(190, 6, f"Query: {safe_q}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(190, 6, f"Request ID: {safe_req}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(190, 6, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    
    # Section 1: Executive Summary
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(190, 8, "1. Executive Research Answer", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    
    answer_text = res.get("answer", "No answer generated.")
    parse_markdown_to_pdf(pdf, answer_text)
    pdf.ln(4)
    
    # Section 2: Sources
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(190, 8, "2. Information Sources", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    
    sources = res.get("sources", [])
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(37, 99, 235)
    if sources:
        for src in sources:
            pdf.set_x(pdf.l_margin)
            safe_src = str(src).encode('latin-1', 'replace').decode('latin-1')
            pdf.cell(190, 6, f"- {safe_src}", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.set_x(pdf.l_margin)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(190, 6, "- No reference sources available.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    
    # Section 3: Quality Validation
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(190, 8, "3. Quality Validation Breakdown", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    
    val = res.get("validation", {})
    score = res.get("validation_score", 0.0)
    score_status = "Excellent" if score >= 0.75 else "Acceptable" if score >= 0.6 else "Poor / Rejected"
    
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(51, 65, 85)
    pdf.set_x(pdf.l_margin)
    pdf.cell(190, 6, f"Overall Quality Score: {score:.2f} ({score_status})", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin)
    pdf.cell(190, 6, f"Relevance Score: {val.get('relevance_score', 0.0):.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin)
    pdf.cell(190, 6, f"Completeness Score: {val.get('completeness_score', 0.0):.2f}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin)
    pdf.cell(190, 6, f"Accuracy Confidence: {val.get('accuracy_confidence', 0.0):.2f}", new_x="LMARGIN", new_y="NEXT")
    
    issues = val.get("issues", [])
    issues_str = ", ".join(issues) if issues else "None"
    safe_issues = clean_text_for_pdf(issues_str).encode('latin-1', 'replace').decode('latin-1')
    pdf.set_x(pdf.l_margin)
    pdf.cell(190, 6, f"Issues Flagged: {safe_issues}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    
    # Section 4: Performance Metrics
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(190, 8, "4. Performance Metrics", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    
    metrics = res.get("metrics", {})
    total_tokens = metrics.get('total_tokens') or (metrics.get('total_input_tokens', 0) + metrics.get('total_output_tokens', 0))
    cost = metrics.get('estimated_cost_usd', 0.0)
    latency = metrics.get('total_latency_s', metrics.get('latency_seconds', 0.0))
    chunks = metrics.get('stored_chunks', metrics.get('breakdown', {}).get('chunks_stored', 0))
    
    pdf.set_font("Helvetica", "", 10)
    pdf.set_x(pdf.l_margin)
    pdf.cell(190, 6, f"Total Latency: {latency:.2f}s", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin)
    pdf.cell(190, 6, f"Total Tokens Consumed: {total_tokens}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin)
    pdf.cell(190, 6, f"Estimated Cost: ${cost:.6f}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin)
    pdf.cell(190, 6, f"Vector DB Chunks Stored: {chunks}", new_x="LMARGIN", new_y="NEXT")
    
    return bytes(pdf.output())

def generate_report_markdown(res: dict, query: str) -> str:
    req_id = res.get("request_id", "N/A")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    val = res.get("validation", {})
    metrics = res.get("metrics", {})
    sources = res.get("sources", [])
    
    score = res.get("validation_score", 0.0)
    score_status = "Excellent" if score >= 0.75 else "Acceptable" if score >= 0.6 else "Poor"
    issues = val.get("issues", [])
    issues_str = ", ".join(issues) if issues else "None"
    
    total_tokens = metrics.get('total_tokens') or (metrics.get('total_input_tokens', 0) + metrics.get('total_output_tokens', 0))
    cost = metrics.get('estimated_cost_usd', 0.0)
    latency = metrics.get('total_latency_s', metrics.get('latency_seconds', 0.0))
    chunks = metrics.get('stored_chunks', metrics.get('breakdown', {}).get('chunks_stored', 0))

    report = f"""# 🤖 Autonomous Research Report

**Query:** {query}  
**Request ID:** `{req_id}`  
**Generated At:** {timestamp}  

---

## 📝 Executive Summary

{res.get("answer", "No answer generated.")}

---

## 🌐 Information Sources

"""
    if sources:
        for src in sources:
            report += f"- {src}\n"
    else:
        report += "- No reference sources available.\n"
        
    report += f"""
---

## 🏆 Quality Validation Breakdown

- **Overall Score:** `{score:.2f}` ({score_status})
- **Relevance Score:** `{val.get("relevance_score", 0.0):.2f}`
- **Completeness Score:** `{val.get("completeness_score", 0.0):.2f}`
- **Accuracy Confidence:** `{val.get("accuracy_confidence", 0.0):.2f}`
- **Issues Flagged:** {issues_str}
- **Improvement Suggestion:** {val.get("improvement_suggestions", "N/A")}

---

## ⚡ Performance Metrics

- **Total Execution Latency:** `{latency:.2f}s`
- **Total Tokens Consumed:** `{total_tokens}`
- **Estimated Cost:** `${cost:.6f}`
- **Vector DB Chunks Stored:** `{chunks}`

---
*Report generated by Autonomous Research Agent with Monitoring Layer.*
"""
    return report

# ── Sidebar: History & Status ──────────────────────────────────
with st.sidebar:
    st.title("⚙️ System Panel")
    
    # Environment Status Indicators
    st.markdown("### Status")
    gemini_ok = bool(os.getenv("GEMINI_API_KEY"))
    serp_ok = bool(os.getenv("SERPAPI_KEY")) or bool(os.getenv("SERPAPI_API_KEY"))
    tavily_ok = bool(os.getenv("TAVILY_API_KEY"))
    
    col_g, col_s = st.columns(2)
    with col_g:
        st.markdown(f"**Gemini API**<br>{'🟢 Connected' if gemini_ok else '🔴 Missing'}", unsafe_allow_html=True)
    with col_s:
        if tavily_ok:
            st.markdown(f"**Tavily API**<br>🟢 Connected", unsafe_allow_html=True)
        elif serp_ok:
            st.markdown(f"**SerpAPI**<br>🟢 Connected", unsafe_allow_html=True)
        else:
            st.markdown(f"**Search API**<br>🟡 Simulated", unsafe_allow_html=True)
    
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
                log_err = log.get("error")
                issues_list = [f"Pipeline Error: {log_err}"] if log_err else []
                st.session_state.research_results = {
                    "answer": log.get("final_answer", ""),
                    "sources": log.get("sources", []),
                    "validation_score": score,
                    "validation": {
                        "overall_score": score,
                        "relevance_score": score,
                        "completeness_score": score,
                        "accuracy_confidence": score,
                        "is_acceptable": score >= 0.6,
                        "issues": issues_list,
                        "improvement_suggestions": "N/A"
                    },
                    "metrics": log.get("metrics", {}),
                    "request_id": log.get("request_id", "N/A"),
                    "error": log_err
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
            val_data = results.get("validation") or {}
            err_data = results.get("error")
            issues = val_data.get("issues", [])
            if err_data and err_data not in issues:
                issues = [f"Pipeline Error: {err_data}"] + issues

            results["validation"] = {
                "overall_score": val_data.get("overall_score", results.get("validation_score", 0.0)),
                "relevance_score": val_data.get("relevance_score", results.get("validation_score", 0.0)),
                "completeness_score": val_data.get("completeness_score", results.get("validation_score", 0.0)),
                "accuracy_confidence": val_data.get("accuracy_confidence", results.get("validation_score", 0.0)),
                "is_acceptable": val_data.get("is_acceptable", results.get("validation_score", 0.0) >= 0.6),
                "issues": issues,
                "improvement_suggestions": val_data.get("improvement_suggestions", "N/A")
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
        
        # Display request ID & Cache status
        req_id = res.get("request_id", "N/A")
        is_cached = res.get("cached") or res.get("metrics", {}).get("cache_hit")
        sim = res.get("cache_similarity")
        
        badge_html = f"<small style='color: #64748b;'>Request ID: `{req_id}`</small>"
        if is_cached:
            sim_str = f" ({sim*100:.1f}% match)" if sim else ""
            badge_html += f" &nbsp; <span style='background-color: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid #059669; padding: 2px 8px; border-radius: 6px; font-size: 0.8rem;'>⚡ Semantic Cache Hit{sim_str} ($0 Cost, 0.03s)</span>"
        
        st.markdown(badge_html, unsafe_allow_html=True)
        
        if res.get("error"):
            st.error(f"⚠️ **Pipeline Execution Error:** `{res.get('error')}`")
        
        # Answer content
        st.markdown(res.get("answer", "No answer generated."))
        
        # Sources Section
        st.markdown("### 🌐 Information Sources")
        sources = res.get("sources", [])
        if sources:
            for i, src in enumerate(sources):
                if src.startswith("http://") or src.startswith("https://"):
                    st.markdown(f"- [{src}]({src})")
                else:
                    st.markdown(f"- 📄 {src}")
        else:
            st.warning("No reference sources available for this query.")

        # Export Report Section
        st.markdown("---")
        st.markdown("### 📥 Export Research Report")
        
        pdf_bytes = generate_report_pdf(res, st.session_state.query)
        st.download_button(
            label="📕 Download PDF Report (.pdf)",
            data=pdf_bytes,
            file_name=f"research_report_{res.get('request_id', 'output')}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
            
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
        
        # Calculate total tokens dynamically if the overall key is missing (fallback for history logs)
        total_tokens = metrics.get('total_tokens') or (metrics.get('total_input_tokens', 0) + metrics.get('total_output_tokens', 0))
        
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            st.metric("Total Latency", f"{metrics.get('total_latency_s', metrics.get('latency_seconds', 0.0)):.2f}s")
            cost = metrics.get('estimated_cost_usd', 0.0)
            st.metric("Estimated Cost", f"${cost:.6f}" if cost > 0 else "$0.000000")
        with m_col2:
            st.metric("Total Tokens", f"{total_tokens}")
            chunks = metrics.get('stored_chunks', metrics.get('breakdown', {}).get('chunks_stored', 0))
            st.metric("DB Chunks Stored", f"{chunks}")
            
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
