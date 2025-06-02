import logging
from typing import List, Dict, Any, Optional, Tuple
import weaviate
from weaviate.auth import AuthApiKey
from weaviate.classes.query import MetadataQuery, Filter
from weaviate.classes.init import AdditionalConfig, Timeout
from weaviate.classes.config import Property, DataType
from core.models.ticket import ActiveTicket, HistoricTicket, VectorDBStats
from core.auth.azure_auth import AzureAuthManager
from services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

class VectorStoreService:
    """Service for managing Weaviate vector store operations"""
    
    def __init__(self, auth_manager: AzureAuthManager, embedding_service: EmbeddingService):
        self.auth_manager = auth_manager
        self.embedding_service = embedding_service
        self._client = None
        
    def _get_client(self) -> weaviate.WeaviateClient:
        """Get Weaviate client connection"""
        if not self._client:
            try:
                url = self.auth_manager.get_secret("WEAVIATE-URL")
                api_key = self.auth_manager.get_secret("WEAVIATE-API-KEY")
                
                if not url:
                    raise ValueError("Weaviate URL not found in Key Vault")
                
                if not url.startswith(("http://", "https://")):
                    url = f"https://{url}"
                
                auth_config = AuthApiKey(api_key=api_key) if api_key else None
                
                additional_config = AdditionalConfig(
                    timeout=Timeout(init=60, query=30, insert=30)
                )
                
                self._client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=url,
                    auth_credentials=auth_config,
                    additional_config=additional_config
                )
                
                # Test connection
                self._client.collections.list_all()
                logger.info("Successfully connected to Weaviate")
                
                # Ensure collections exist
                self._ensure_collections()
                
            except Exception as e:
                logger.error(f"Failed to connect to Weaviate: {e}")
                raise
                
        return self._client
    
    def _ensure_collections(self):
        """Ensure required collections exist"""
        try:
            client = self._client
            collections = client.collections.list_all()
            
            # Active tickets collection
            if "ActiveTickets" not in collections:
                client.collections.create(
                    name="ActiveTickets",
                    properties=[
                        Property(name="ticket_id", data_type=DataType.TEXT),
                        Property(name="location_id", data_type=DataType.INT),
                        Property(name="description", data_type=DataType.TEXT),
                        Property(name="estimated_resolution_time", data_type=DataType.INT),
                    ]
                )
                logger.info("Created ActiveTickets collection")
            
            # Historic tickets collection
            if "HistoricTickets" not in collections:
                client.collections.create(
                    name="HistoricTickets",
                    properties=[
                        Property(name="ticket_id", data_type=DataType.TEXT),
                        Property(name="location_id", data_type=DataType.INT),
                        Property(name="description", data_type=DataType.TEXT),
                        Property(name="actual_resolution_time", data_type=DataType.NUMBER),
                    ]
                )
                logger.info("Created HistoricTickets collection")
                
        except Exception as e:
            logger.error(f"Failed to ensure collections: {e}")
            raise
    
    def upsert_active_ticket(self, ticket: ActiveTicket) -> bool:
        """Insert or update an active ticket"""
        try:
            client = self._get_client()
            collection = client.collections.get("ActiveTickets")
            
            # Check if ticket exists
            existing = self._get_ticket_by_id("ActiveTickets", ticket.ticket_id)
            
            # Generate embedding
            vector = self.embedding_service.embed_text(ticket.description)
            
            properties = {
                "ticket_id": ticket.ticket_id,
                "location_id": ticket.location_id,
                "description": ticket.description,
                "estimated_resolution_time": ticket.estimated_resolution_time,
            }
            
            if existing:
                # Update existing ticket
                collection.data.update(
                    uuid=existing["uuid"],
                    properties=properties,
                    vector=vector
                )
                logger.info(f"Updated active ticket {ticket.ticket_id}")
            else:
                # Insert new ticket
                collection.data.insert(
                    properties=properties,
                    vector=vector
                )
                logger.info(f"Inserted new active ticket {ticket.ticket_id}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to upsert active ticket {ticket.ticket_id}: {e}")
            return False
    
    def upsert_historic_ticket(self, ticket: HistoricTicket) -> bool:
        """Insert or update a historic ticket"""
        try:
            client = self._get_client()
            collection = client.collections.get("HistoricTickets")
            
            # Check if ticket exists
            existing = self._get_ticket_by_id("HistoricTickets", ticket.ticket_id)
            
            # Generate embedding
            vector = self.embedding_service.embed_text(ticket.description)
            
            properties = {
                "ticket_id": ticket.ticket_id,
                "location_id": ticket.location_id,
                "description": ticket.description,
                "actual_resolution_time": ticket.actual_resolution_time,
            }
            
            if existing:
                # Update existing ticket
                collection.data.update(
                    uuid=existing["uuid"],
                    properties=properties,
                    vector=vector
                )
                logger.info(f"Updated historic ticket {ticket.ticket_id}")
            else:
                # Insert new ticket
                collection.data.insert(
                    properties=properties,
                    vector=vector
                )
                logger.info(f"Inserted new historic ticket {ticket.ticket_id}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to upsert historic ticket {ticket.ticket_id}: {e}")
            return False
    
    def batch_upsert_active_tickets(self, tickets: List[ActiveTicket]) -> Tuple[int, int]:
        """Batch upsert active tickets"""
        successful = 0
        failed = 0
        
        try:
            client = self._get_client()
            collection = client.collections.get("ActiveTickets")
            
            # Generate embeddings for all tickets
            descriptions = [ticket.description for ticket in tickets]
            vectors = self.embedding_service.embed_texts(descriptions)
            
            with collection.batch.dynamic() as batch:
                for ticket, vector in zip(tickets, vectors):
                    try:
                        properties = {
                            "ticket_id": ticket.ticket_id,
                            "location_id": ticket.location_id,
                            "description": ticket.description,
                            "estimated_resolution_time": ticket.estimated_resolution_time,
                        }
                        
                        batch.add_object(properties=properties, vector=vector)
                        successful += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to add ticket {ticket.ticket_id}: {e}")
                        failed += 1
            
            logger.info(f"Batch upsert completed: {successful} successful, {failed} failed")
            
        except Exception as e:
            logger.error(f"Batch upsert failed: {e}")
            failed = len(tickets)
            
        return successful, failed
    
    def batch_upsert_historic_tickets(self, tickets: List[HistoricTicket]) -> Tuple[int, int]:
        """Batch upsert historic tickets"""
        successful = 0
        failed = 0
        
        try:
            client = self._get_client()
            collection = client.collections.get("HistoricTickets")
            
            # Generate embeddings for all tickets
            descriptions = [ticket.description for ticket in tickets]
            vectors = self.embedding_service.embed_texts(descriptions)
            
            with collection.batch.dynamic() as batch:
                for ticket, vector in zip(tickets, vectors):
                    try:
                        properties = {
                            "ticket_id": ticket.ticket_id,
                            "location_id": ticket.location_id,
                            "description": ticket.description,
                            "actual_resolution_time": ticket.actual_resolution_time,
                        }
                        
                        batch.add_object(properties=properties, vector=vector)
                        successful += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to add ticket {ticket.ticket_id}: {e}")
                        failed += 1
            
            logger.info(f"Batch upsert completed: {successful} successful, {failed} failed")
            
        except Exception as e:
            logger.error(f"Batch upsert failed: {e}")
            failed = len(tickets)
            
        return successful, failed
    
    def _get_ticket_by_id(self, collection_name: str, ticket_id: str) -> Optional[Dict]:
        """Get ticket by ID from collection"""
        try:
            client = self._get_client()
            collection = client.collections.get(collection_name)
            
            response = collection.query.fetch_objects(
                where=Filter.by_property("ticket_id").equal(ticket_id),
                limit=1
            )
            
            if response.objects:
                obj = response.objects[0]
                return {
                    "uuid": obj.uuid,
                    "properties": obj.properties
                }
            return None
        except Exception as e:
            logger.error(f"Error finding ticket {ticket_id} in {collection_name}: {e}")
            return None
    
    def search_similar_tickets(self, 
                             query: str, 
                             location_id: Optional[int] = None,
                             collection_name: str = "ActiveTickets",
                             limit: int = 10) -> List[Tuple[Dict, float]]:
        """Search for similar tickets using vector similarity"""
        try:
            client = self._get_client()
            collection = client.collections.get(collection_name)
            
            # Generate query embedding
            vector = self.embedding_service.embed_text(query)
            
            # Build filters
            filters = None
            if location_id is not None:
                filters = Filter.by_property("location_id").equal(location_id)
            
            # Search
            response = collection.query.near_vector(
                near_vector=vector,
                limit=limit,
                filters=filters,
                return_metadata=MetadataQuery(distance=True)
            )
            
            results = []
            for obj in response.objects:
                similarity_score = 1 - obj.metadata.distance if obj.metadata.distance else 0.99
                ticket_data = dict(obj.properties)
                results.append((ticket_data, similarity_score))
            
            logger.info(f"Found {len(results)} similar tickets in {collection_name}")
            return results
            
        except Exception as e:
            logger.error(f"Search failed in {collection_name}: {e}")
            return []
    
    def get_collection_stats(self, collection_name: str) -> VectorDBStats:
        """Get collection statistics"""
        try:
            client = self._get_client()
            collection = client.collections.get(collection_name)
            aggregate = collection.aggregate.over_all(total_count=True)
            
            return VectorDBStats(
                collection_name=collection_name,
                total_objects=aggregate.total_count,
                status="healthy"
            )
        except Exception as e:
            logger.error(f"Failed to get stats for {collection_name}: {e}")
            return VectorDBStats(
                collection_name=collection_name,
                total_objects=0,
                status="error",
                error=str(e)
            )
    
    def close(self):
        """Close Weaviate connection"""
        if self._client:
            try:
                self._client.close()
                self._client = None
                logger.info("Closed Weaviate connection")
            except Exception as e:
                logger.error(f"Error closing Weaviate connection: {e}")
