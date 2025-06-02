import logging
from typing import List
from langchain_openai import AzureOpenAIEmbeddings
from azure.identity import DefaultAzureCredential
from core.auth.azure_auth import AzureAuthManager

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service for generating text embeddings using Azure OpenAI"""
    
    def __init__(self, auth_manager: AzureAuthManager):
        self.auth_manager = auth_manager
        self._embedding_model = None
        
    def _get_embedding_model(self) -> AzureOpenAIEmbeddings:
        """Initialize Azure OpenAI embeddings model"""
        if not self._embedding_model:
            try:
                endpoint = self.auth_manager.get_secret("AZURE-OPENAI-ENDPOINT")
                
                if not endpoint:
                    raise ValueError("Azure OpenAI endpoint not found in Key Vault")
                
                credential = DefaultAzureCredential()
                token_provider = lambda: credential.get_token(
                    "https://cognitiveservices.azure.com/.default"
                ).token
                
                self._embedding_model = AzureOpenAIEmbeddings(
                    model="text-embedding-ada-002",
                    azure_endpoint=endpoint,
                    azure_deployment="text-embedding-ada-002",
                    azure_ad_token_provider=token_provider
                )
                
                # Test the model
                test_embedding = self._embedding_model.embed_documents(["test"])
                logger.info(f"Embedding model initialized successfully, dimension: {len(test_embedding[0])}")
                
            except Exception as e:
                logger.error(f"Failed to initialize embedding model: {e}")
                raise
                
        return self._embedding_model
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        try:
            model = self._get_embedding_model()
            embedding = model.embed_documents([text])[0]
            return embedding
        except Exception as e:
            logger.error(f"Failed to embed text: {e}")
            raise
    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        try:
            model = self._get_embedding_model()
            embeddings = model.embed_documents(texts)
            return embeddings
        except Exception as e:
            logger.error(f"Failed to embed texts: {e}")
            raise