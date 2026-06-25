import sys
from pathlib import Path
import os
import streamlit as st
ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
from core.core_engine import refresh_knowledge_base





from core.core_engine import run_rag

# 后续 Phase3 实现时启用
# from core.ingest import process_pdf

# =========================
# Page Config
# =========================

st.set_page_config(
    page_title="Financial RAG Assistant",
    layout="wide"
)

st.title("Financial RAG Assistant")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================
# Sidebar
# =========================

st.sidebar.title("Knowledge Base")

pdf_files = sorted(
    [
        f for f in os.listdir("pdfs")
        if f.endswith(".pdf")
    ]
)

if pdf_files:

    st.sidebar.subheader("Knowledge Sources")

    for pdf in pdf_files:
        st.sidebar.success(f"✓ {pdf}")

    st.sidebar.divider()

    st.sidebar.metric(
        "Documents",
        len(pdf_files)
    )

else:

    st.sidebar.info(
        "No document loaded"
    )
# =========================
# Upload PDF
# =========================

uploaded_file = st.file_uploader(
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

    except Exception as e:
        st.error(f"Upload failed: {e}")
# =========================
# Question Input
# =========================

if uploaded_file:

    question = st.text_input(
        "Ask a question"
    )

    if st.button("Search"):

        if not question:

            st.warning(
                "Please enter a question"
            )

        else:

            try:

                with st.spinner(
                    "Analyzing documents..."
                ):

                    report, citations, context, mode = run_rag(question)

                st.success(
                    f"Mode: {mode}"
                )

                st.info(
                    f"Evidence Count: {len(citations)}"
                )

                left_col, right_col = st.columns(
                    [2, 1]
                )

                # =========================
                # Answer Area
                # =========================

                with left_col:
                    st.markdown(
                        "## Report"
                    )

                    st.markdown(
                        report
                    )

                    with st.expander(
                        "Retrieved Context"
                    ):

                        st.text(
                            context
                        )

                # =========================
                # Evidence Area
                # =========================

                with right_col:

                    st.markdown(
                        "## Evidence"
                    )

                    if citations:

                        for c in citations:

                            with st.expander(
                                f"Evidence {c['rank']}"
                            ):

                                st.caption(
                                    f"📄 {c['source']}"
                                )

                                st.caption(
                                    f"Chunk {c['chunk_id']}"
                                )

                                st.write(
                                    f"Confidence: {c['similarity']:.3f}"
                                )

                                st.progress(
                                    float(
                                        c["similarity"]
                                    )
                                )

                                st.markdown(
                                    "**Preview**"
                                )

                                st.caption(
                                    c["preview"]
                                )

                    else:

                        st.warning(
                            "No evidence found"
                        )

            except Exception as e:

                st.error(
                    f"Search failed: {e}"
                )

else:

    st.info(
        "Please upload a PDF first"
    )