from fastapi import APIRouter, Depends
from typing import Dict, Any
from services.vector_store_service import VectorStoreService
from services.embedding_service import EmbeddingService
from api.dependencies import get_vector_store_service, get_embedding_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/health", tags=["Health"])

@router.get("/")
async def health_check() -> Dict[str, Any]:
    """General health check endpoint"""
    return {
        "status": "healthy",
        "service": "ticket-eta-engine",
        "version": "1.0.0"
    }

@router.get("/detailed")
async def detailed_health_check(
    vector_store: VectorStoreService = Depends(get_vector_store_service),
    embedding_service: EmbeddingService = Depends(get_embedding_service)
) -> Dict[str, Any]:
    """Detailed health check including all services"""
    
    health_status = {
        "status": "healthy",
        "services": {}
    }
    
    # Check Vector Store
    try:
        active_stats = vector_store.get_collection_stats("ActiveTickets")
        historic_stats = vector_store.get_collection_stats("HistoricTickets")
        
        health_status["services"]["vector_store"] = {
            "status": "healthy" if (active_stats.status == "healthy" and 
                                  historic_stats.status == "healthy") else "degraded",
            "active_tickets": active_stats.total_objects,
            "historic_tickets": historic_stats.total_objects
        }
    except Exception as e:
        health_status["services"]["vector_store"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Check Embedding Service
    try:
        # Test embedding generation
        test_embedding = embedding_service.embed_text("test connection")
        
        health_status["services"]["embedding_service"] = {
            "status": "healthy",
            "embedding_dimension": len(test_embedding)
        }
    except Exception as e:
        health_status["services"]["embedding_service"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    return health_status

