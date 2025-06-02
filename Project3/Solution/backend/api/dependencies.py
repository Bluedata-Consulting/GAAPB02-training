from functools import lru_cache
from core.auth.azure_auth import AzureAuthManager
from services.embedding_service import EmbeddingService
from services.vector_store_service import VectorStoreService
from services.ticket_processor_service import TicketProcessorService

@lru_cache()
def get_auth_manager() -> AzureAuthManager:
    """Get Azure authentication manager instance"""
    return AzureAuthManager()

@lru_cache()
def get_embedding_service() -> EmbeddingService:
    """Get embedding service instance"""
    auth_manager = get_auth_manager()
    return EmbeddingService(auth_manager)

@lru_cache()
def get_vector_store_service() -> VectorStoreService:
    """Get vector store service instance"""
    auth_manager = get_auth_manager()
    embedding_service = get_embedding_service()
    return VectorStoreService(auth_manager, embedding_service)

@lru_cache()
def get_ticket_processor_service() -> TicketProcessorService:
    """Get ticket processor service instance"""
    vector_store_service = get_vector_store_service()
    return TicketProcessorService(vector_store_service)
