
import tempfile
from pathlib import Path

import streamlit as st

from ingestion.pipeline import IngestionPipeline
from retrieval.rag_service import RAGService


st.set_page_config(
    page_title="Enterprise Hybrid RAG",
    page_icon="🔎",
    layout="wide",
)


@st.cache_resource(show_spinner="Initializing RAG system...")
def get_rag_service():
    """Create and reuse a shared RAG service instance."""
    return RAGService()


st.title("Enterprise Hybrid RAG Chatbot")

st.write(
    "AI-powered document search and question answering "
    "using hybrid retrieval and Groq LLM."
)

# ---------------------------------
# Document Management
# ---------------------------------

st.sidebar.header("Document Management")

uploaded_files = st.sidebar.file_uploader(
    "Upload your documents",
    type=["pdf", "docx", "txt"],
    accept_multiple_files=True,
)

if uploaded_files:
    st.sidebar.success(
        f"{len(uploaded_files)} document(s) selected."
    )

    if st.sidebar.button(
        "Ingest Selected Documents",
        type="primary",
    ):
        pipeline = None
        successful = 0
        failed = 0

        try:
            pipeline = IngestionPipeline()

            with st.sidebar:
                with st.spinner("Processing documents..."):

                    with tempfile.TemporaryDirectory() as temp_dir:

                        for uploaded_file in uploaded_files:

                            safe_name = (
                                uploaded_file.name
                                .replace("\\", "/")
                                .split("/")[-1]
                            )

                            file_path = Path(temp_dir) / safe_name

                            file_path.write_bytes(
                                uploaded_file.getvalue()
                            )

                            try:
                                result = pipeline.ingest_file(
                                    str(file_path)
                                )

                                if result["status"] == "success":
                                    successful += 1

                                    st.success(
                                        f"{safe_name}: "
                                        f"{result['chunks_stored']} "
                                        "chunk(s) stored."
                                    )

                                else:
                                    st.warning(
                                        f"{safe_name}: "
                                        f"{result['message']}"
                                    )

                            except Exception as exc:
                                failed += 1

                                st.error(
                                    f"{safe_name}: {exc}"
                                )

            if successful:
                st.sidebar.success(
                    f"Ingestion completed: "
                    f"{successful} file(s) processed."
                )

            if failed:
                st.sidebar.warning(
                    f"{failed} file(s) failed to process."
                )

        except Exception as exc:
            st.sidebar.error(
                f"Could not initialize ingestion: {exc}"
            )

        finally:
            if pipeline is not None:
                pipeline.close()

# ---------------------------------
# Sidebar Information
# ---------------------------------

st.sidebar.divider()

st.sidebar.caption(
    "Supported formats: PDF, DOCX, TXT"
)

# ---------------------------------
# Chat Interface
# ---------------------------------

st.subheader("Ask Your Documents")

st.caption(
    "Ask a question about documents already stored in "
    "your Qdrant Cloud collection."
)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])

        if message.get("sources"):

            with st.expander("View source documents"):

                for source in message["sources"]:
                    st.write(
                        f"- {source['source']}"
                    )

# User question

question = st.text_input(
    "Enter your question",
    placeholder=(
        "Example: How many days of annual leave "
        "do employees receive?"
    ),
    key="question_input",
)

if st.button("Ask AI", type="primary"):

    if not question.strip():

        st.warning("Please enter a question.")

    else:

        user_question = question.strip()

        st.session_state.messages.append(
            {
                "role": "user",
                "content": user_question,
            }
        )

        try:

            with st.spinner(
                "Searching documents and generating an answer..."
            ):

                rag = get_rag_service()

                result = rag.answer(user_question)

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": result["answer"],
                    "sources": result["sources"],
                }
            )

            st.rerun()

        except Exception as exc:

            st.error(
                f"Unable to generate an answer: {exc}"
            )

# ---------------------------------
# Footer
# ---------------------------------

st.divider()

st.caption(
    "Enterprise Hybrid RAG | "
    "Hybrid Search + Qdrant Cloud + Groq"
)
