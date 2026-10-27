from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.config import settings
from app.ingestion import DocumentIngestionPipeline
from app.chunking import AdvancedChunkingEngine
from app.hybrid_search import HybridRetrievalEngine
from app.chain import EnterpriseRAGChain

app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0")

# Global pipeline initialization on startup
ingestion_pipeline = DocumentIngestionPipeline(data_dir="data/sample_docs")
raw_docs = ingestion_pipeline.load_documents()

chunker = AdvancedChunkingEngine()
chunked_docs = chunker.split_documents(raw_docs)

retrieval_engine = HybridRetrievalEngine(documents=chunked_docs)
rag_chain = EnterpriseRAGChain(retrieval_engine=retrieval_engine)

class QueryRequest(BaseModel):
    query: str

@app.post("/api/v1/chat")
def chat_endpoint(request: QueryRequest):
    try:
        result = rag_chain.run(request.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy", "project": settings.PROJECT_NAME}