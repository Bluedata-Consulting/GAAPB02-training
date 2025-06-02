from fastapi import APIRouter, HTTPException, Depends
from core.models.ticket import TicketSubmission, TicketResponse
from services.ticket_processor_service import TicketProcessorService
from api.dependencies import get_ticket_processor_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/tickets", tags=["Tickets"])

@router.post("/submit", response_model=TicketResponse)
async def submit_ticket(
    submission: TicketSubmission,
    processor: TicketProcessorService = Depends(get_ticket_processor_service)
) -> TicketResponse:
    """Submit a new support ticket and get estimated resolution time"""
    try:
        logger.info(f"Processing ticket submission for location {submission.location_id}")
        response = processor.process_ticket_submission(submission)
        return response
    except Exception as e:
        logger.error(f"Failed to process ticket submission: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process ticket: {str(e)}")

@router.get("/health")
async def tickets_health():
    """Health check endpoint for tickets service"""
    return {"status": "healthy", "service": "tickets"}
