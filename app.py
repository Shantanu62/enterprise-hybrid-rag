
import os

import httpx
import streamlit as st


# =========================================================
# CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Enterprise AI Workspace",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")


# =========================================================
# PROFESSIONAL UI THEME
# =========================================================

st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: "Segoe UI", sans-serif;
    }

    .stApp {
        background: #f5f7fb;
    }

    [data-testid="stSidebar"] {
        background: #111c30;
        border-right: 1px solid #25344d;
    }

    [data-testid="stSidebar"] * {
        color: #e8edf6;
    }

    .brand {
        font-size: 24px;
        font-weight: 750;
        color: #ffffff;
        letter-spacing: -0.8px;
        padding-top: 10px;
    }

    .brand-subtitle {
        font-size: 11px;
        letter-spacing: 1.5px;
        color: #9eacc2;
        margin-bottom: 24px;
    }

    .creator {
        color: #a9bad4;
        font-size: 12px;
        padding-top: 8px;
    }

    .eyebrow {
        color: #61728d;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1.5px;
        margin-bottom: 5px;
    }

    .page-title {
        color: #17263d;
        font-size: 31px;
        font-weight: 750;
        letter-spacing: -1px;
        margin-bottom: 4px;
    }

    .page-description {
        color: #718096;
        font-size: 14px;
        margin-bottom: 24px;
    }

    .metric-card {
        background: #ffffff;
        border: 1px solid #e5eaf2;
        border-radius: 13px;
        padding: 19px;
        min-height: 112px;
        box-shadow: 0 3px 10px rgba(16, 24, 40, 0.025);
    }

    .metric-label {
        color: #718096;
        font-size: 12px;
        font-weight: 600;
    }

    .metric-value {
        color: #17263d;
        font-size: 28px;
        font-weight: 750;
        margin-top: 8px;
    }

    .surface {
        background: #ffffff;
        border: 1px solid #e5eaf2;
        border-radius: 13px;
        padding: 21px;
        margin-bottom: 15px;
        min-height: 125px;
    }

    .surface-title {
        color: #17263d;
        font-size: 17px;
        font-weight: 700;
        margin-bottom: 8px;
    }

    .muted {
        color: #718096;
        font-size: 13px;
        line-height: 1.6;
    }

    .login-heading {
        color: #17263d;
        font-size: 31px;
        font-weight: 750;
        letter-spacing: -1px;
    }

    .login-description {
        color: #718096;
        font-size: 14px;
        margin-bottom: 20px;
    }

    div.stButton > button {
        border-radius: 9px;
        font-weight: 600;
        min-height: 40px;
    }

    div[data-testid="stChatMessage"] {
        background: #ffffff;
        border: 1px solid #e7edf5;
        border-radius: 12px;
        padding: 12px;
    }

    [data-testid="stFileUploader"] {
        background: #ffffff;
        border: 1px dashed #b8c6d9;
        border-radius: 12px;
        padding: 12px;
    }

    [data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e5eaf2;
        border-radius: 12px;
        padding: 15px;
    }

    footer {
        visibility: hidden;
    }

    #MainMenu {
        visibility: hidden;
    }
</style>
""", unsafe_allow_html=True)


# =========================================================
# SESSION STATE
# =========================================================

defaults = {
    "access_token": None,
    "user_email": None,
    "organization_id": None,
    "organizations": [],
    "messages": [],
    "uploaded_documents": [],
    "total_questions": 0,
    "navigation_radio": "Dashboard",
    "pending_question": None,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def api_headers():
    return {
        "Authorization": (
            f"Bearer {st.session_state.access_token}"
        )
    }


def api_error_message(response):
    try:
        data = response.json()
        return str(data.get("detail", data))
    except Exception:
        body = (response.text or "").strip()

        if body.startswith("<!DOCTYPE") or body.startswith("<html"):
            return (
                f"Server returned an HTML error page "
                f"(HTTP {response.status_code}). "
                "Please check the backend service and API URL."
            )

        return body[:400] or f"HTTP {response.status_code}"


def clear_session():
    st.session_state.access_token = None
    st.session_state.user_email = None
    st.session_state.organization_id = None
    st.session_state.organizations = []
    st.session_state.messages = []
    st.session_state.uploaded_documents = []
    st.session_state.total_questions = 0
    st.session_state.navigation_radio = "Dashboard"
    st.session_state.pending_question = None


def handle_unauthorized():
    clear_session()
    st.error("Your session has expired. Please log in again.")
    st.rerun()


def page_header(eyebrow, title, description):
    st.markdown(
        f"""
        <div class="eyebrow">{eyebrow}</div>
        <div class="page-title">{title}</div>
        <div class="page-description">{description}</div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label, value):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def go_to_chat():
    st.session_state.navigation_radio = "AI Chat"


def go_to_knowledge_base():
    st.session_state.navigation_radio = "Knowledge Base"


def logout():
    clear_session()


# =========================================================
# LOGIN SCREEN
# =========================================================

if not st.session_state.access_token:

    _, login_col, _ = st.columns([1, 1.6, 1])

    with login_col:

        st.write("")
        st.write("")

        st.markdown(
            """
            <div class="eyebrow">ENTERPRISE AI PLATFORM</div>
            <div class="login-heading">Welcome back.</div>
            <div class="login-description">
                Your organization's intelligent document workspace.
                Sign in to continue.
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.form("login_form"):

            email = st.text_input(
                "Email address",
                placeholder="you@company.com",
            )

            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
            )

            login_button = st.form_submit_button(
                "Sign in",
                type="primary",
                use_container_width=True,
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

                        organizations = login_data.get(
                            "organizations",
                            [],
                        )

                        if not token:

                            st.error(
                                "Login response did not contain "
                                "an access token."
                            )

                        elif not organizations:

                            st.error(
                                "No active organization found "
                                "for this account."
                            )

                        else:

                            st.session_state.access_token = token

                            st.session_state.user_email = (
                                email.strip()
                            )

                            st.session_state.organizations = (
                                organizations
                            )

                            st.session_state.organization_id = (
                                organizations[0]["id"]
                            )

                            st.session_state.messages = []

                            st.session_state.navigation_radio = (
                                "Dashboard"
                            )

                            st.rerun()

                    else:

                        st.error(
                            f"Login failed: "
                            f"{api_error_message(response)}"
                        )

                except httpx.RequestError:

                    st.error(
                        "Could not connect to the backend API. "
                        "Please check the backend service."
                    )

        st.divider()

        st.markdown(
            """
            <div style="text-align:center;color:#718096;font-size:12px">
                Built with Python · FastAPI · Streamlit · Qdrant · Groq
                <br><br>
                Developed by <b>Shantanu Anand</b>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.stop()


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        """
        <div class="brand">✦ Enterprise AI</div>
        <div class="brand-subtitle">KNOWLEDGE WORKSPACE</div>
        """,
        unsafe_allow_html=True,
    )

    st.caption("WORKSPACE")

    selected_page = st.radio(
        "Navigation",
        [
            "Dashboard",
            "AI Chat",
            "Knowledge Base",
        ],
        key="navigation_radio",
        label_visibility="collapsed",
    )

    st.divider()

    st.caption("ORGANIZATION")

    organizations = st.session_state.organizations

    if not organizations:

        st.error("No organization available.")

        clear_session()
        st.rerun()

    organization_options = {
        f"{org['name']} ({org['role']})": org["id"]
        for org in organizations
    }

    option_labels = list(organization_options.keys())

    current_index = next(
        (
            index
            for index, org_id in enumerate(
                organization_options.values()
            )
            if org_id == st.session_state.organization_id
        ),
        0,
    )

    selected_label = st.selectbox(
        "Select organization",
        options=option_labels,
        index=current_index,
    )

    selected_org_id = organization_options[selected_label]

    if selected_org_id != st.session_state.organization_id:

        st.session_state.organization_id = selected_org_id

        st.session_state.messages = []
        st.session_state.uploaded_documents = []
        st.session_state.total_questions = 0

        st.rerun()

    st.divider()

    st.caption("ACCOUNT")

    st.write(st.session_state.user_email)

    st.button(
        "Log out",
        use_container_width=True,
        on_click=logout,
    )

    st.divider()

    st.markdown(
        """
        <div class="creator">
            Built with care by<br>
            <b>Shantanu Anand</b>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# DASHBOARD
# =========================================================

if selected_page == "Dashboard":

    page_header(
        "WORKSPACE OVERVIEW",
        "Your knowledge, connected.",
        (
            "Search, explore and get answers from "
            "your organization's documents."
        ),
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        metric_card(
            "Documents uploaded this session",
            len(st.session_state.uploaded_documents),
        )

    with col2:
        metric_card(
            "Questions asked this session",
            st.session_state.total_questions,
        )

    with col3:
        metric_card(
            "Answers this session",
            sum(
                1
                for message in st.session_state.messages
                if message["role"] == "assistant"
            ),
        )

    st.write("")

    left, right = st.columns(2)

    with left:

        st.markdown(
            """
            <div class="surface">
                <div class="surface-title">
                    ✦ AI Document Assistant
                </div>
                <div class="muted">
                    Ask natural-language questions and get
                    answers grounded in your organization's
                    indexed documents.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.button(
            "Open AI Chat →",
            type="primary",
            use_container_width=True,
            on_click=go_to_chat,
        )

    with right:

        st.markdown(
            """
            <div class="surface">
                <div class="surface-title">
                    ▤ Knowledge Base
                </div>
                <div class="muted">
                    Upload PDF, DOCX and TXT documents
                    to your searchable knowledge base.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.button(
            "Manage Documents →",
            use_container_width=True,
            on_click=go_to_knowledge_base,
        )

    st.write("")

    st.info(
        "These statistics represent the current browser session only. "
        "They are not organization-wide totals."
    )


# =========================================================
# KNOWLEDGE BASE
# =========================================================

elif selected_page == "Knowledge Base":

    page_header(
        "DOCUMENT MANAGEMENT",
        "Knowledge Base",
        (
            "Upload documents to make them searchable "
            "by your AI assistant."
        ),
    )

    st.markdown(
        """
        <div class="surface">
            <div class="surface-title">Add documents</div>
            <div class="muted">
                Supported formats: PDF, DOCX and TXT.
                Documents are processed and indexed by the backend.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_files = st.file_uploader(
        "Choose documents",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        key="knowledge_base_uploader",
    )

    if uploaded_files:

        st.info(
            f"{len(uploaded_files)} document(s) selected."
        )

        if st.button(
            "Upload and index documents",
            type="primary",
        ):

            successful = 0
            failed = 0

            progress = st.progress(0)

            for index, uploaded_file in enumerate(uploaded_files):

                try:

                    with st.spinner(
                        f"Processing {uploaded_file.name}..."
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

                    if response.status_code == 401:
                        handle_unauthorized()

                    if response.status_code == 201:

                        result = response.json()

                        document = result.get(
                            "document",
                            {},
                        )

                        ingestion = result.get(
                            "ingestion",
                            {},
                        )

                        if document.get("status") == "completed":

                            successful += 1

                            st.session_state.uploaded_documents.append(
                                {
                                    "name": uploaded_file.name,
                                    "document_id": document.get(
                                        "document_id",
                                        "N/A",
                                    ),
                                    "chunks": document.get(
                                        "chunks_stored",
                                        0,
                                    ),
                                    "status": "completed",
                                }
                            )

                            st.success(
                                f"{uploaded_file.name} indexed successfully. "
                                f"Chunks: {document.get('chunks_stored', 0)}"
                            )

                        else:

                            failed += 1

                            st.error(
                                f"{uploaded_file.name}: "
                                "Ingestion completion was not confirmed. "
                                f"Status: {ingestion.get('status', 'unknown')}"
                            )

                    else:

                        failed += 1

                        st.error(
                            f"{uploaded_file.name}: "
                            f"{api_error_message(response)}"
                        )

                except httpx.RequestError:

                    failed += 1

                    st.error(
                        f"{uploaded_file.name}: Backend connection failed."
                    )

                progress.progress(
                    (index + 1) / len(uploaded_files)
                )

            st.divider()

            if successful:
                st.success(
                    f"Successfully processed: {successful}"
                )

            if failed:
                st.warning(
                    f"Failed uploads: {failed}"
                )

    st.write("")

    st.markdown("### Recently uploaded in this session")

    if st.session_state.uploaded_documents:

        for document in reversed(
            st.session_state.uploaded_documents
        ):

            with st.container(border=True):

                col1, col2 = st.columns([3, 1])

                with col1:

                    st.write(
                        f"**▤ {document['name']}**"
                    )

                    st.caption(
                        f"Document ID: {document['document_id']}"
                    )

                with col2:

                    st.success("Indexed")

                    st.caption(
                        f"{document['chunks']} chunks"
                    )

    else:

        st.info(
            "No uploads recorded in this session yet. "
            "This is not the full server document inventory."
        )


# =========================================================
# AI CHAT
# =========================================================

elif selected_page == "AI Chat":

    page_header(
        "AI ASSISTANT",
        "Chat with your documents",
        (
            "Ask questions and receive answers grounded "
            "in your organization's knowledge base."
        ),
    )

    top_left, top_right = st.columns([4, 1])

    with top_left:

        st.caption(
            "Your conversation and source references appear below."
        )

    with top_right:

        if st.button(
            "＋ New chat",
            use_container_width=True,
        ):

            st.session_state.messages = []
            st.rerun()

    if not st.session_state.messages:

        st.markdown(
            """
            <div class="surface">
                <div class="surface-title">
                    What would you like to know?
                </div>
                <div class="muted">
                    Ask about policies, procedures, security
                    requirements, employee rules or information
                    in your uploaded documents.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("**Suggested questions**")

        suggestions = [
            "Summarize the key points in my documents.",
            "What are the important employee policies?",
            "What security requirements are mentioned?",
        ]

        suggestion_cols = st.columns(3)

        for index, suggestion in enumerate(suggestions):

            with suggestion_cols[index]:

                if st.button(
                    suggestion,
                    key=f"suggestion_{index}",
                    use_container_width=True,
                ):

                    st.session_state.pending_question = suggestion
                    st.rerun()

    # Display conversation history

    for message in st.session_state.messages:

        with st.chat_message(message["role"]):

            st.markdown(message["content"])

            if message.get("sources"):

                with st.expander(
                    f"Sources and citations "
                    f"({len(message['sources'])})"
                ):

                    for source in message["sources"]:

                        citation_id = source.get(
                            "citation_id",
                            "Source",
                        )

                        source_name = source.get(
                            "source",
                            "Unknown document",
                        )

                        st.markdown(
                            f"**[{citation_id}] {source_name}**"
                        )

                        details = []

                        page = source.get("page")

                        if page is not None:
                            details.append(f"Page {page}")

                        chunk_indices = source.get(
                            "chunk_indices"
                        ) or []

                        if chunk_indices:

                            details.append(
                                "Chunks: "
                                + ", ".join(
                                    str(item)
                                    for item in chunk_indices
                                )
                            )

                        file_type = source.get("file_type")

                        if file_type:
                            details.append(str(file_type).upper())

                        if details:
                            st.caption(" · ".join(details))

            if message.get("performance"):

                with st.expander("Performance details"):

                    st.json(message["performance"])

    # Chat input

    question = st.chat_input(
        "Ask anything about your organization's documents..."
    )

    pending_question = st.session_state.pop(
        "pending_question",
        None,
    )

    user_question = question or pending_question

    if user_question:

        user_question = user_question.strip()

        if not user_question:

            st.warning("Please enter a valid question.")

        elif len(user_question) > 4000:

            st.warning(
                "Question cannot exceed 4000 characters."
            )

        else:

            st.session_state.messages.append(
                {
                    "role": "user",
                    "content": user_question,
                }
            )

            st.session_state.total_questions += 1

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
                            "sources": result.get(
                                "sources",
                                [],
                            ),
                            "performance": result.get(
                                "performance",
                                {},
                            ),
                        }
                    )

                    st.rerun()

                elif response.status_code == 401:

                    handle_unauthorized()

                elif response.status_code == 403:

                    st.session_state.messages.pop()

                    st.session_state.total_questions = max(
                        0,
                        st.session_state.total_questions - 1,
                    )

                    st.error(
                        "You do not have permission "
                        "to access this organization."
                    )

                else:

                    st.session_state.messages.pop()

                    st.session_state.total_questions = max(
                        0,
                        st.session_state.total_questions - 1,
                    )

                    st.error(
                        f"Request failed: "
                        f"{api_error_message(response)}"
                    )

            except httpx.RequestError:

                st.session_state.messages.pop()

                st.session_state.total_questions = max(
                    0,
                    st.session_state.total_questions - 1,
                )

                st.error(
                    "Could not connect to the backend API."
                )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.markdown(
    """
    <div style="
        text-align:center;
        color:#718096;
        font-size:12px;
        padding:8px 0 16px 0;
    ">
        Enterprise AI Workspace
        · Hybrid Retrieval
        · FastAPI
        · Streamlit
        · Qdrant
        · Groq
        <br><br>
        Designed and Developed by
        <b style="color:#34445c">Shantanu Anand</b>
    </div>
    """,
    unsafe_allow_html=True,
)
