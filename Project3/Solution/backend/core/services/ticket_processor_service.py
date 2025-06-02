import logging
import hashlib
from typing import Dict, Any, Tuple, List, Optional
import numpy as np
from datetime import datetime
from core.models.ticket import TicketSubmission, TicketResponse
from services.vector_store_service import VectorStoreService

logger = logging.getLogger(__name__)

class TicketProcessorService:
    """Service for processing ticket submissions and estimating resolution times"""
    
    def __init__(self, vector_store_service: VectorStoreService):
        self.vector_store = vector_store_service
        
    def process_ticket_submission(self, submission: TicketSubmission) -> TicketResponse:
        """Process a new ticket submission and estimate resolution time"""
        try:
            # Generate unique ticket ID
            ticket_id = self._generate_ticket_id(submission)
            
            # Search for similar tickets and estimate resolution time
            estimated_time, method, similarity_score, count = self._estimate_resolution_time(
                submission.description, 
                submission.location_id
            )
            
            # Generate notification message
            notification = self._generate_notification(
                submission.description,
                estimated_time,
                submission.location_id,
                method
            )
            
            response = TicketResponse(
                ticket_id=ticket_id,
                location_id=submission.location_id,
                description=submission.description,
                estimated_resolution_time=estimated_time,
                processing_method=method,
                notification_message=notification,
                created_at=datetime.utcnow(),
                similarity_score=similarity_score,
                similar_tickets_count=count
            )
            
            logger.info(f"Processed ticket {ticket_id} with {estimated_time}h ETA using {method}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to process ticket submission: {e}")
            raise
    
    def _estimate_resolution_time(self, description: str, location_id: int) -> Tuple[int, str, Optional[float], int]:
        """Estimate resolution time based on similar tickets"""
        
        # Strategy 1: Search active tickets with location filter
        active_matches = self.vector_store.search_similar_tickets(
            query=description,
            location_id=location_id,
            collection_name="ActiveTickets",
            limit=15
        )
        
        high_similarity_active = [(ticket, score) for ticket, score in active_matches if score > 0.75]
        
        if high_similarity_active and len(high_similarity_active) >= 3:
            times = [ticket.get('estimated_resolution_time', 24) for ticket, _ in high_similarity_active]
            avg_time = int(np.mean(times))
            best_score = max(score for _, score in high_similarity_active)
            logger.info(f"Estimated {avg_time}h from {len(times)} similar active tickets")
            return avg_time, "Similar Active Tickets (Location-Specific)", best_score, len(high_similarity_active)
        
        # Strategy 2: Search historic tickets with location filter
        historic_matches = self.vector_store.search_similar_tickets(
            query=description,
            location_id=location_id,
            collection_name="HistoricTickets",
            limit=15
        )
        
        high_similarity_historic = [(ticket, score) for ticket, score in historic_matches if score > 0.75]
        
        if high_similarity_historic and len(high_similarity_historic) >= 3:
            times = [ticket.get('actual_resolution_time', 24) for ticket, _ in high_similarity_historic]
            avg_time = int(np.mean(times))
            best_score = max(score for _, score in high_similarity_historic)
            logger.info(f"Estimated {avg_time}h from {len(times)} similar historic tickets")
            return avg_time, "Similar Historic Tickets (Location-Specific)", best_score, len(high_similarity_historic)
        
        # Strategy 3: Search active tickets globally (any location)
        global_active_matches = self.vector_store.search_similar_tickets(
            query=description,
            location_id=None,
            collection_name="ActiveTickets",
            limit=15
        )
        
        medium_similarity_active = [(ticket, score) for ticket, score in global_active_matches if score > 0.65]
        
        if medium_similarity_active:
            times = [ticket.get('estimated_resolution_time', 24) for ticket, _ in medium_similarity_active]
            avg_time = int(np.mean(times))
            best_score = max(score for _, score in medium_similarity_active)
            logger.info(f"Estimated {avg_time}h from {len(times)} global active tickets")
            return avg_time, "Similar Active Tickets (Global)", best_score, len(medium_similarity_active)
        
        # Strategy 4: Search historic tickets globally
        global_historic_matches = self.vector_store.search_similar_tickets(
            query=description,
            location_id=None,
            collection_name="HistoricTickets",
            limit=15
        )
        
        medium_similarity_historic = [(ticket, score) for ticket, score in global_historic_matches if score > 0.65]
        
        if medium_similarity_historic:
            times = [ticket.get('actual_resolution_time', 24) for ticket, _ in medium_similarity_historic]
            avg_time = int(np.mean(times))
            best_score = max(score for _, score in medium_similarity_historic)
            logger.info(f"Estimated {avg_time}h from {len(times)} global historic tickets")
            return avg_time, "Similar Historic Tickets (Global)", best_score, len(medium_similarity_historic)
        
        # Fallback: Default estimation
        logger.info("No similar tickets found, using default 24h estimate")
        return 24, "Default Estimate (No Similar Tickets)", None, 0
    
    def _generate_ticket_id(self, submission: TicketSubmission) -> str:
        """Generate unique ticket ID"""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        hash_input = f"{submission.location_id}{submission.description}{timestamp}"
        hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:6]
        return f"TKT{timestamp}{hash_suffix.upper()}"
    
    def _generate_notification(self, description: str, estimated_time: int, 
                             location_id: int, method: str) -> str:
        """Generate customer notification message"""
        return f"""Dear Customer,

Thank you for submitting your support ticket. We have received your request and our technical team is working to resolve it.

Issue Description: {description[:100]}{'...' if len(description) > 100 else ''}
Location: {location_id}
Estimated Resolution Time: {estimated_time} hours
Analysis Method: {method}

Our team has analyzed similar issues to provide this estimate. You will receive updates as we make progress on your ticket.

Best regards,
BlueConnect Technical Support Team"""