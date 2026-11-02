# 🏢 Enterprise Hybrid RAG Chatbots & Semantic Search Suite

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=for-the-badge&logo=fastapi)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30%2B-FF4B4B?style=for-the-badge&logo=streamlit)
![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?style=for-the-badge&logo=docker)
![Qdrant](https://img.shields.io/badge/Qdrant-Vector_DB-red?style=for-the-badge)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon_DB-4169E1?style=for-the-badge&logo=postgresql)
![Render](https://img.shields.io/badge/Render-Deployed-46E3B7?style=for-the-badge&logo=render)

A production-grade, multi-tenant **Enterprise Hybrid Retrieval-Augmented Generation (RAG)** platform. Built with **FastAPI**, **Qdrant Vector Database**, **BM25 Keyword Search**, **Neon PostgreSQL**, and **Streamlit**. Designed for high-accuracy document search with full strict tenant isolation and source provenance tracking.

---

## 🚀 Live Demo & Deployments

* **Frontend UI (Streamlit):** [enterprise-hybrid-rag-frontend.onrender.com](https://enterprise-hybrid-rag-frontend.onrender.com/)
* **Backend API Docs (FastAPI Swagger):** [enterprise-hybrid-rag-api.onrender.com/docs](https://enterprise-hybrid-rag-api.onrender.com/docs)

---

## ✨ Key Features

* 🔍 **Hybrid Retrieval Pipeline:** Combines dense vector embeddings (Qdrant Cloud) with sparse keyword search (BM25) for high-precision document retrieval.
* 🛡️ **Multi-Tenant Isolation:** Enforces organization-level data security and strict tenant isolation across database queries and vector indices.
* 📚 **Source Provenance Tracking:** Every generated answer displays exact source document metadata (file names, page citations, and chunk origins).
* ⚡ **High-Performance FastAPI Backend:** Asynchronous microservice architecture designed for scale, containerized with Docker.
* 🎨 **Modern SaaS Interface:** Built using Streamlit with custom CSS glassmorphism styling, real-time analytics, and chat history management.

---

## 🛠️ Tech Stack & Architecture

* **Backend Engine:** Python, FastAPI, Pydantic, Uvicorn
* **Vector Store & Retrieval:** Qdrant Vector DB, RankBM25 Hybrid Reranking
* **Relational Data & Metadata:** PostgreSQL (Neon Serverless DB), SQLAlchemy
* **LLM & Embeddings Engine:** Groq API / OpenAI
* **Frontend Web App:** Streamlit (Custom Responsive Dark UI)
* **DevOps & Cloud:** Docker, Render Cloud Deployment, GitHub Actions CI/CD

---

## 🏃 Quickstart & Local Setup

### 1. Clone the Repository
```bash
git clone [https://github.com/Shantanu62/enterprise-hybrid-rag.git](https://github.com/Shantanu62/enterprise-hybrid-rag.git)
cd enterprise-hybrid-rag
