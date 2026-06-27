import sys
from pathlib import Path
import os
import streamlit as st
ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
from core.core_engine import refresh_knowledge_base
from core.knowledge_manager import (
    get_documents,
    get_document_count,
    get_company_list
)
from core.core_engine import run_rag, get_chunk_count, refresh_knowledge_base

# 后续 Phase3 实现时启用
# from core.ingest import process_pdf

# =========================
# Page Config
# =========================

st.set_page_config(
    page_title="Financial RAG Assistant",
    layout="wide"
)

st.title("📊 Financial Research Copilot")
st.caption("AI-powered multi-document financial analysis system")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================
# Sidebar
# =========================

st.sidebar.title("🔎 Knowledge Sources")

pdf_files = get_documents()

if pdf_files:

    company_list = get_company_list()

    selected_companies = st.sidebar.multiselect(
        "Select Companies",
        options=company_list,
        default=[]
    )

    st.sidebar.divider()

    st.sidebar.metric(
        "Documents",
        get_document_count()
    )
    st.sidebar.metric(
        "Chunks",
        get_chunk_count()
    )

else:

    st.sidebar.info(
        "No document loaded"
    )
    selected_companies = []
# =========================
# Upload PDF
# =========================

st.sidebar.divider()
st.sidebar.subheader("Upload PDF")
uploaded_file = st.sidebar.file_uploader(
    "Upload PDF",
    type=["pdf"]
)

if uploaded_file:

    file_path = os.path.join(
        UPLOAD_DIR,
        uploaded_file.name
    )

    try:
        # 1. 保存到 uploads
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.success(f"Uploaded: {uploaded_file.name}")

        refresh_knowledge_base()

        st.success("Knowledge base updated")

        st.rerun()

    except Exception as e:
        st.error(f"Upload failed: {e}")
# =========================
# Question Input
# =========================

question = st.text_input(
    "Ask a question about companies or markets"
)

if st.button("Analyze", type="primary"):

    if not question:
        st.warning("Please enter a question")
    else:
        try:
            with st.spinner("🧠 AI is analyzing financial reports and building investment insights..."):
                selected_company = selected_companies[0] if selected_companies else None
                report, citations, context, research_mode, intent_result, all_evidence, plan = run_rag(
                    question,
                    company=selected_company
                )
                intent = intent_result["intent"]
                companies = intent_result["companies"]

            # =========================
            # Level 1: Research Scope (Product Understanding Layer)
            # =========================

            st.markdown("## 🧠 Research Scope")

            scope_text = f"""
**Intent:** `{intent_result['intent']}`

**Companies:** {intent_result['companies']}

**Documents:** {list(set(ev.metadata.get('document_id', '') for ev in all_evidence))}

**Chunks Retrieved:** {len(all_evidence)}
"""

            st.info(scope_text)

            st.markdown("## 📋 Execution Plan")
            plan_tasks = plan.tasks
            for i, task in enumerate(plan_tasks):
                task_type = task.step_type.value
                task_query = task.query or ", ".join(task.parameters.get("metrics", []))
                emoji = {"retrieve": "🔍", "compare": "⚖️", "synthesis": "🧩"}.get(task_type, "📌")
                st.caption(f"{emoji} **Step {i+1}:** `{task_type}` — {task_query}")

            # =========================
            # Intent 可视化（Sidebar）
            # =========================

            st.sidebar.divider()
            st.sidebar.markdown("## 🧭 Intent Analysis")

            if intent == "SINGLE_COMPANY":
                st.sidebar.success("🟢 Single Company Analysis")
            elif intent == "COMPARE_COMPANIES":
                st.sidebar.info("🔵 Comparative Analysis")
            elif intent == "GLOBAL_RESEARCH":
                st.sidebar.warning("🟣 Global Research Mode")
            else:
                st.sidebar.error("⚪ Unknown Intent")

            if companies:
                st.sidebar.markdown("**Companies:**")
                for c in companies:
                    st.sidebar.write(f"- {c}")

            st.divider()

            # =========================
            # Level 2: Answer Report (Result Layer)
            # =========================

            st.markdown("## 📊 Investment Research Report")
            st.markdown(report)

            with st.expander("Show Raw Retrieved Context"):
                st.text(context)

            st.divider()

            # =========================
            # Level 3: Evidence (Citation Layer)
            # =========================

            st.markdown("## 📎 Evidence")

            if citations:
                for c in citations:
                    with st.container():
                        st.markdown(f"""
**[{c['rank']}] {c['source']}**

- Chunk ID: `{c['chunk_id']}`
- Score: `{c['similarity']:.4f}`

> {c['preview']}
""")
                        st.divider()
            else:
                st.warning("No relevant evidence found")

        except Exception as e:
            st.error(f"Analysis failed: {e}")
            import traceback
            st.code(traceback.format_exc())

if not get_documents():
    st.info("Please upload at least one PDF document to get started")