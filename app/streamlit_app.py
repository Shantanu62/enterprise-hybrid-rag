import streamlit as st
import requests

# Page Configuration
st.set_page_config(
    page_title="Enterprise Hybrid RAG | AI Neural Core",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Futuristic Tesla/OpenAI Style CSS (Dark Theme & Glassmorphism)
st.markdown("""
    <style>
    /* Global Dark Theme Background */
    .stApp {
        background-color: #0b0f19;
        color: #f3f4f6;
    }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #1f2937;
    }

    /* Chat Input Bar */
    [data-testid="stChatInput"] textarea {
        background-color: #1f2937 !important;
        color: #ffffff !important;
        border: 1px solid #374151 !important;
        border-radius: 12px !important;
    }

    /* Headers */
    h1, h2, h3 {
        color: #ffffff !important;
        font-family: 'Inter', sans-serif;
        letter-spacing: -0.5px;
    }

    /* Chat Messages */
    .stChatMessage {
        background-color: #1f2937;
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar - Telemetry & System Architecture
with st.sidebar:
    st.markdown("### ⚡ Neural Core Telemetry")
    st.markdown("---")
    st.info("System Status: **ONLINE (24/7 Active)**")
    st.markdown("**Architecture Stack:**")
    st.markdown("- **Vector DB:** Qdrant (Dense)")
    st.markdown("- **Lexical Engine:** BM25 (Sparse)")
    st.markdown("- **Reranker:** Cross-Encoder")
    st.markdown("- **LLM Core:** Groq Llama-3.1")
    
    st.markdown("---")
    st.markdown("### 🎛️ Pipeline Controls")
    search_mode = st.selectbox("Search Strategy", ["Hybrid (Dense + Sparse)", "Pure Dense Vector", "Pure Sparse Keyword"])
    temperature = st.slider("LLM Temperature", 0.0, 1.0, 0.1, 0.05)

# 🚀 Futuristic AI Neural Banner / Graphic
st.image(
    "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1200&auto=format&fit=crop", 
    use_container_width=True
)

# Main Chat Interface Header
st.markdown("# 🧠 Enterprise Hybrid RAG Intelligence")
st.markdown("##### Next-Gen Semantic Search & Knowledge Retrieval Suite")
st.markdown("---")

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input Box
if prompt := st.chat_input("Query enterprise knowledge base..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Executing multi-stage hybrid retrieval & LLM generation..."):
            try:
                # API Endpoint pointing to FastAPI backend
                api_url = "http://127.0.0.1:8000/api/v1/chat"
                payload = {"query": prompt}
                
                response = requests.post(api_url, json=payload, timeout=30)
                
                if response.status_code == 200:
                    res_data = response.json()
                    answer = res_data.get("answer", "No response generated.")
                    sources = res_data.get("sources", [])
                    
                    st.markdown(answer)
                    
                    # Expandable Source Telemetry
                    if sources:
                        with st.expander("🔍 View Retrieved Context & Telemetry"):
                            for idx, src in enumerate(sources):
                                st.code(f"Source [{idx+1}]: {src}", language="text")
                else:
                    st.error(f"Backend Error: Status code {response.status_code}")
            except Exception as e:
                st.error(f"Connection Error: Unable to reach FastAPI backend. Details: {e}")