import streamlit as st
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from qdrant_client import QdrantClient
from fastembed import TextEmbedding
import os

st.set_page_config(page_title="Enterprise Hybrid RAG Chatbot", layout="wide")

st.title("🤖 Enterprise Hybrid RAG Intelligence")
st.write("Next-Gen Semantic Search & Knowledge Retrieval Suite")

# Load API keys from Streamlit Secrets or environment variables
groq_api_key = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
qdrant_url = st.secrets.get("QDRANT_URL") or os.getenv("QDRANT_URL")
qdrant_api_key = st.secrets.get("QDRANT_API_KEY") or os.getenv("QDRANT_API_KEY")

if not groq_api_key or not qdrant_url:
    st.error("Please configure GROQ_API_KEY and QDRANT_URL in Streamlit Secrets or .env!")
    st.stop()

@st.cache_resource
def init_rag_components():
    # Initialize Groq LLM
    llm = ChatGroq(
        groq_api_key=groq_api_key,
        model_name="llama-3.1-8b-instant",
        temperature=0.1
    )
    
    # Initialize Qdrant Client
    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
    
    # Initialize FastEmbed
    embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    
    return llm, client, embedding_model

llm, qdrant_client, embedding_model = init_rag_components()

# Sidebar Setup
with st.sidebar:
    st.subheader("System Status")
    st.success("ONLINE (24/7 Active)")
    
    st.subheader("Architecture Stack:")
    st.markdown("- **Vector DB:** Qdrant (Dense)")
    st.markdown("- **Embedding:** FastEmbed")
    st.markdown("- **LLM Core:** Groq Llama-3.1")

# User Query Input
query = st.text_input("Query enterprise knowledge base...")

if query:
    with st.spinner("Searching documents and generating answer..."):
        try:
            # 1. Embed query using FastEmbed
            query_vector = list(embedding_model.embed([query]))[0].tolist()
            
            # 2. Search in Qdrant Cloud collection
            search_results = qdrant_client.search(
                collection_name="enterprise_docs",
                query_vector=query_vector,
                limit=3
            )
            
            context_str = ""
            citations = []
            for hit in search_results:
                payload = hit.payload or {}
                text = payload.get("page_content", "")
                context_str += f"\n{text}\n"
                citations.append(f"Doc: {payload.get('source', 'Unknown')} (Score: {hit.score:.2f})")
            
            # 3. Prompt & LLM Generation via Groq
            prompt_template = PromptTemplate(
                input_variables=["context", "question"],
                template="""You are an enterprise AI assistant. Answer the user query strictly based on the provided context below. Include precise citations.

Context:
{context}

User Query: {question}

Answer with Citations:"""
            )
            
            prompt = prompt_template.format(context=context_str if context_str else "No direct context found.", question=query)
            response = llm.invoke(prompt)
            
            # Display Answer
            st.subheader("Answer")
            st.write(response.content)
            
            if citations:
                st.subheader("Sources / Citations")
                for c in citations:
                    st.markdown(f"- {c}")
                    
        except Exception as e:
            st.error(f"An error occurred during retrieval: {e}")