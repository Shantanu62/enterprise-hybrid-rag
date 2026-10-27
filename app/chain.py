from typing import Dict, Any, List
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from app.config import settings
from app.hybrid_search import HybridRetrievalEngine
from app.reranker import RerankingPipeline
from app.cache import SemanticCacheManager


class EnterpriseRAGChain:
    def __init__(self, retrieval_engine: HybridRetrievalEngine):
        self.retrieval_engine = retrieval_engine
        self.reranker = RerankingPipeline()
        self.cache_manager = SemanticCacheManager()
        self.llm = ChatGroq(
            groq_api_key=settings.GROQ_API_KEY,
            model_name=settings.LLM_MODEL,
            temperature=0.1
        )

        self.prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template="""You are an enterprise AI assistant. Answer the user query strictly based on the provided context below. Include precise citations referencing the source document and page number.

Context:
{context}

User Query: {question}

Answer with Citations:"""
        )

    def run(self, query: str) -> Dict[str, Any]:
        # 1. Check Semantic Cache
        cached_result = self.cache_manager.get(query)
        if cached_result:
            return {
                "answer": cached_result,
                "source": "semantic_cache",
                "citations": []
            }

        # 2. Hybrid Retrieval (Dense + Sparse + RRF)
        dense_docs = self.retrieval_engine.dense_search(query, top_k=5)
        sparse_docs = self.retrieval_engine.sparse_search(query, top_k=5)
        hybrid_docs = self.retrieval_engine.reciprocal_rank_fusion(dense_docs, sparse_docs)

        # 3. Cross-Encoder Reranking
        reranked_docs = self.reranker.rerank(query, hybrid_docs, top_k=3)

        # 4. Format Context and Citations
        context_str = ""
        citations = []
        for doc in reranked_docs:
            context_str += f"\n{doc.page_content}\n"
            citations.append({
                "source_document": doc.metadata.get("source"),
                "page_number": doc.metadata.get("page"),
                "chunk_id": doc.metadata.get("chunk_id")
            })

        # 5. LLM Generation via Free Groq API
        prompt = self.prompt_template.format(context=context_str, question=query)
        response = self.llm.invoke(prompt)
        answer_text = response.content

        # 6. Store in Semantic Cache
        self.cache_manager.set(query, answer_text)

        return {
            "answer": answer_text,
            "source": "llm_generation",
            "citations": citations
        }