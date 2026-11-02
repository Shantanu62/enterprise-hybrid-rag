
from fastapi import FastAPI

from backend.api import auth_router, organization_router


app = FastAPI(
    title="Enterprise Hybrid RAG API",
    description=(
        "Secure multi-tenant RAG API "
        "with JWT authentication and RBAC."
    ),
    version="1.0.0",
)


# Register authentication and organization routes
app.include_router(auth_router)
app.include_router(organization_router)


@app.get("/health", tags=["Health"])
def health_check():
    """Check whether the API is running."""

    return {
        "status": "healthy",
        "service": "Enterprise Hybrid RAG API",
    }
