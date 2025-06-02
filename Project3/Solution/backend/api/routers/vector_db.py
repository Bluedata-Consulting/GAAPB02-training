from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, UploadFile, File
from typing import List, Dict, Any
import pandas as pd
import io
from core.models.ticket import ActiveTicket, HistoricTicket, VectorDBStats, BatchUploadResponse
from services.vector_store_service import VectorStoreService
from data.csv_loader import CSVDataLoader
from api.dependencies import get_vector_store_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/vector-db", tags=["Vector Database"])

@router.post("/active-tickets/upsert")
async def upsert_active_ticket(
    ticket: ActiveTicket, 
    vector_store: VectorStoreService = Depends(get_vector_store_service)
) -> Dict[str, Any]:
    """Insert or update an active ticket in the vector database"""
    try:
        success = vector_store.upsert_active_ticket(ticket)
        if success:
            return {
                "message": "Active ticket upserted successfully",
                "ticket_id": ticket.ticket_id,
                "action": "upserted"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to upsert active ticket")
    except Exception as e:
        logger.error(f"Failed to upsert active ticket: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/historic-tickets/upsert")
async def upsert_historic_ticket(
    ticket: HistoricTicket,
    vector_store: VectorStoreService = Depends(get_vector_store_service)
) -> Dict[str, Any]:
    """Insert or update a historic ticket in the vector database"""
    try:
        success = vector_store.upsert_historic_ticket(ticket)
        if success:
            return {
                "message": "Historic ticket upserted successfully", 
                "ticket_id": ticket.ticket_id,
                "action": "upserted"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to upsert historic ticket")
    except Exception as e:
        logger.error(f"Failed to upsert historic ticket: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/active-tickets/batch-upsert")
async def batch_upsert_active_tickets(
    tickets: List[ActiveTicket],
    background_tasks: BackgroundTasks,
    vector_store: VectorStoreService = Depends(get_vector_store_service)
) -> BatchUploadResponse:
    """Batch insert or update active tickets"""
    
    def process_batch():
        try:
            successful, failed = vector_store.batch_upsert_active_tickets(tickets)
            logger.info(f"Batch processing complete: {successful} successful, {failed} failed")
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
    
    background_tasks.add_task(process_batch)
    
    return BatchUploadResponse(
        message="Batch processing started for active tickets",
        total_tickets=len(tickets),
        successful=0,
        failed=0,
        status="processing"
    )

@router.post("/historic-tickets/batch-upsert")
async def batch_upsert_historic_tickets(
    tickets: List[HistoricTicket],
    background_tasks: BackgroundTasks,
    vector_store: VectorStoreService = Depends(get_vector_store_service)
) -> BatchUploadResponse:
    """Batch insert or update historic tickets"""
    
    def process_batch():
        try:
            successful, failed = vector_store.batch_upsert_historic_tickets(tickets)
            logger.info(f"Batch processing complete: {successful} successful, {failed} failed")
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
    
    background_tasks.add_task(process_batch)
    
    return BatchUploadResponse(
        message="Batch processing started for historic tickets",
        total_tickets=len(tickets),
        successful=0,
        failed=0,
        status="processing"
    )

@router.post("/active-tickets/upload-csv")
async def upload_active_tickets_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    vector_store: VectorStoreService = Depends(get_vector_store_service)
) -> BatchUploadResponse:
    """Upload active tickets from CSV file"""
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        # Read file content
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        # Validate columns
        required_columns = ['TicketID', 'locationID', 'description', 'estimated_resolution_time']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required columns: {missing_columns}"
            )
        
        # Convert to ticket objects
        tickets = []
        for _, row in df.iterrows():
            try:
                ticket = ActiveTicket(
                    ticket_id=str(row['TicketID']),
                    location_id=int(row['locationID']),
                    description=str(row['description']),
                    estimated_resolution_time=int(row['estimated_resolution_time'])
                )
                tickets.append(ticket)
            except Exception as e:
                logger.warning(f"Skipping invalid row: {e}")
                continue
        
        if not tickets:
            raise HTTPException(status_code=400, detail="No valid tickets found in CSV")
        
        # Process in background
        def process_csv_batch():
            try:
                successful, failed = vector_store.batch_upsert_active_tickets(tickets)
                logger.info(f"CSV batch processing complete: {successful} successful, {failed} failed")
            except Exception as e:
                logger.error(f"CSV batch processing failed: {e}")
        
        background_tasks.add_task(process_csv_batch)
        
        return BatchUploadResponse(
            message="CSV upload processing started for active tickets",
            total_tickets=len(tickets),
            successful=0,
            failed=0,
            status="processing"
        )
        
    except Exception as e:
        logger.error(f"Failed to process CSV upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/historic-tickets/upload-csv")
async def upload_historic_tickets_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    vector_store: VectorStoreService = Depends(get_vector_store_service)
) -> BatchUploadResponse:
    """Upload historic tickets from CSV file"""
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    try:
        # Read file content
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        # Validate columns
        required_columns = ['TicketID', 'locationID', 'description', 'actual_resolution_time']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise HTTPException(
                status_code=400, 
                detail=f"Missing required columns: {missing_columns}"
            )
        
        # Convert to ticket objects
        tickets = []
        for _, row in df.iterrows():
            try:
                ticket = HistoricTicket(
                    ticket_id=str(row['TicketID']),
                    location_id=int(row['locationID']),
                    description=str(row['description']),
                    actual_resolution_time=float(row['actual_resolution_time'])
                )
                tickets.append(ticket)
            except Exception as e:
                logger.warning(f"Skipping invalid row: {e}")
                continue
        
        if not tickets:
            raise HTTPException(status_code=400, detail="No valid tickets found in CSV")
        
        # Process in background
        def process_csv_batch():
            try:
                successful, failed = vector_store.batch_upsert_historic_tickets(tickets)
                logger.info(f"CSV batch processing complete: {successful} successful, {failed} failed")
            except Exception as e:
                logger.error(f"CSV batch processing failed: {e}")
        
        background_tasks.add_task(process_csv_batch)
        
        return BatchUploadResponse(
            message="CSV upload processing started for historic tickets",
            total_tickets=len(tickets),
            successful=0,
            failed=0,
            status="processing"
        )
        
    except Exception as e:
        logger.error(f"Failed to process CSV upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/collections/stats")
async def get_collection_stats(
    vector_store: VectorStoreService = Depends(get_vector_store_service)
) -> Dict[str, Any]:
    """Get statistics for all collections"""
    try:
        active_stats = vector_store.get_collection_stats("ActiveTickets")
        historic_stats = vector_store.get_collection_stats("HistoricTickets")
        
        return {
            "active_tickets": active_stats.dict(),
            "historic_tickets": historic_stats.dict(),
            "total_tickets": (active_stats.total_objects + historic_stats.total_objects),
            "overall_status": "healthy" if (active_stats.status == "healthy" and 
                                          historic_stats.status == "healthy") else "degraded"
        }
    except Exception as e:
        logger.error(f"Failed to get collection stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def vector_db_health():
    """Health check endpoint for vector database service"""
    return {"status": "healthy", "service": "vector-db"}
