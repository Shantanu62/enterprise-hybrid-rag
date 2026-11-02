
import os

import httpx
import streamlit as st


# ---------------------------------
# Configuration
# ---------------------------------

st.set_page_config(
    page_title="Enterprise Hybrid RAG",
    page_icon="🔎",
    layout="wide",
)

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

DEFAULT_ORGANIZATION_ID = "61a95709-2c5b-4d6e-aed3-875d886b1450"


# ---------------------------------
# Session State
# ---------------------------------

defaults = {
    "access_token": None,
    "user_email": None,
    "organization_id": DEFAULT_ORGANIZATION_ID,
    "messages": [],
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ---------------------------------
# API Helpers
# ---------------------------------

def api_headers():
    return {
        "Authorization": f"Bearer {st.session_state.access_token}"
    }


def api_error_message(response):
    try:
        data = response.json()
        return str(data.get("detail", data))
    except Exception:
        return response.text or f"HTTP {response.status_code}"


def clear_session():
    st.session_state.access_token = None
    st.session_state.user_email = None
    st.session_state.messages = []


# ---------------------------------
# Header
# ---------------------------------

st.title("Enterprise Hybrid RAG Chatbot")

st.write(
    "AI-powered document search and question answering "
    "using hybrid retrieval, Qdrant Cloud and Groq."
)


# ---------------------------------
# Authentication
# ---------------------------------

if not st.session_state.access_token:

    st.subheader("Login")

    with st.form("login_form"):

        email = st.text_input("Email")

        password = st.text_input(
            "Password",
            type="password",
        )

        login_button = st.form_submit_button(
            "Login",
            type="primary",
        )

    if login_button:

        if not email.strip() or not password:
            st.warning("Please enter your email and password.")

        else:
            try:
                with st.spinner("Authenticating..."):

                    response = httpx.post(
                        f"{API_BASE_URL}/auth/login",
                        json={
                            "email": email.strip(),
                            "password": password,
                        },
                        timeout=30.0,
                    )

                if response.status_code == 200:

                    login_data = response.json()
                    token = login_data.get("access_token")

                    if not token:
                        st.error(
                            "Login response did not contain an access token."
                        )
                    else:
                        st.session_state.access_token = token
                        st.session_state.user_email = email.strip()
                        st.session_state.messages = []

                        st.rerun()

                else:
                    st.error(
                        f"Login failed: {api_error_message(response)}"
                    )

            except httpx.RequestError:
                st.error(
                    "Could not connect to FastAPI. "
                    "Make sure the backend server is running."
                )

    st.stop()


# ---------------------------------
# Sidebar - Workspace
# ---------------------------------

st.sidebar.title("Workspace")

st.sidebar.success("Authenticated")

st.sidebar.caption(
    f"Logged in as: {st.session_state.user_email}"
)

if st.sidebar.button("Logout"):

    clear_session()
    st.rerun()


# ---------------------------------
# Organization
# ---------------------------------

st.sidebar.divider()
st.sidebar.subheader("Organization")

organization_id = st.sidebar.text_input(
    "Organization ID",
    value=st.session_state.organization_id,
)

if st.sidebar.button("Apply Organization"):

    if organization_id.strip():

        st.session_state.organization_id = organization_id.strip()
        st.session_state.messages = []

        st.sidebar.success("Organization updated.")
        st.rerun()

    else:
        st.sidebar.error("Organization ID cannot be empty.")


# ---------------------------------
# Document Upload
# ---------------------------------

st.sidebar.divider()
st.sidebar.subheader("Document Management")

uploaded_files = st.sidebar.file_uploader(
    "Upload documents",
    type=["pdf", "docx", "txt"],
    accept_multiple_files=True,
)

if uploaded_files:

    st.sidebar.info(
        f"{len(uploaded_files)} document(s) selected."
    )

    if st.sidebar.button(
        "Upload Documents",
        type="primary",
    ):

        successful = 0
        failed = 0

        for uploaded_file in uploaded_files:

            try:
                with st.spinner(
                    f"Uploading {uploaded_file.name}..."
                ):

                    response = httpx.post(
                        (
                            f"{API_BASE_URL}/organizations/"
                            f"{st.session_state.organization_id}"
                            f"/documents/upload"
                        ),
                        headers=api_headers(),
                        files={
                            "file": (
                                uploaded_file.name,
                                uploaded_file.getvalue(),
                                uploaded_file.type
                                or "application/octet-stream",
                            )
                        },
                        timeout=300.0,
                    )

                if response.status_code == 201:

                    result = response.json()

                    # Correct response structure:
                    # result["document"]["status"]
                    document = result.get("document", {})
                    ingestion = result.get("ingestion", {})

                    if document.get("status") == "completed":

                        successful += 1

                        st.sidebar.success(
                            f"{uploaded_file.name} uploaded successfully."
                        )

                        st.sidebar.write(
                            f"Chunks indexed: "
                            f"{document.get('chunks_stored', 0)}"
                        )

                        st.sidebar.caption(
                            f"Document ID: "
                            f"{document.get('document_id', 'N/A')}"
                        )

                        st.sidebar.caption(
                            f"Ingestion status: "
                            f"{ingestion.get('status', 'N/A')}"
                        )

                    else:

                        failed += 1

                        st.sidebar.error(
                            f"{uploaded_file.name}: "
                            "Upload response did not confirm completion."
                        )

                elif response.status_code == 401:

                    st.session_state.access_token = None

                    st.error(
                        "Session expired. Please login again."
                    )

                    st.rerun()

                else:

                    failed += 1

                    st.sidebar.error(
                        f"{uploaded_file.name}: "
                        f"{api_error_message(response)}"
                    )

            except httpx.RequestError:

                failed += 1

                st.sidebar.error(
                    f"{uploaded_file.name}: Backend connection failed."
                )

        st.sidebar.divider()

        if successful:
            st.sidebar.success(
                f"Successfully processed: {successful}"
            )

        if failed:
            st.sidebar.warning(
                f"Failed uploads: {failed}"
            )


st.sidebar.caption(
    "Supported formats: PDF, DOCX, TXT | Maximum size: 10 MB"
)


# ---------------------------------
# Chat Interface
# ---------------------------------

st.subheader("Ask Your Documents")

st.caption(
    "Ask questions about documents belonging to your organization."
)


# Display previous messages

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])

        if message.get("sources"):

            with st.expander("View source documents"):

                for source in message["sources"]:

                    st.write(
                        f"- {source.get('source', 'Unknown source')}"
                    )

        if message.get("performance"):

            with st.expander("Performance metrics"):

                st.json(message["performance"])


# ---------------------------------
# Ask AI
# ---------------------------------

question = st.chat_input(
    "Ask a question about your documents..."
)

if question:

    user_question = question.strip()

    if not user_question:

        st.warning("Please enter a valid question.")

    elif len(user_question) > 4000:

        st.warning("Question cannot exceed 4000 characters.")

    else:

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

                response = httpx.post(
                    (
                        f"{API_BASE_URL}/organizations/"
                        f"{st.session_state.organization_id}/ask"
                    ),
                    headers=api_headers(),
                    json={
                        "question": user_question,
                    },
                    timeout=180.0,
                )

            if response.status_code == 200:

                result = response.json()

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": result.get(
                            "answer",
                            "No answer returned.",
                        ),
                        "sources": result.get("sources", []),
                        "performance": result.get("performance", {}),
                    }
                )

                st.rerun()

            elif response.status_code == 401:

                st.session_state.messages.pop()
                clear_session()

                st.error(
                    "Your session expired. Please login again."
                )

                st.rerun()

            elif response.status_code == 403:

                st.session_state.messages.pop()

                st.error(
                    "You do not have permission to access this organization."
                )

            else:

                st.session_state.messages.pop()

                st.error(
                    f"Request failed: {api_error_message(response)}"
                )

        except httpx.RequestError:

            st.session_state.messages.pop()

            st.error(
                "Could not connect to the backend API."
            )


# ---------------------------------
# Footer
# ---------------------------------

st.divider()

st.caption(
    "Enterprise Hybrid RAG | "
    "FastAPI + Streamlit + Qdrant Cloud + Groq"
)
