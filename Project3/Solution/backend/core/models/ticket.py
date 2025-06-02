from datetime import datetime
from typing import Optional, Literal, List
from pydantic import BaseModel, Field, validator

class TicketBase(BaseModel):
    """Base ticket model with common fields"""
    ticket_id: str = Field(..., description="Unique ticket identifier")
    location_id: int = Field(..., description="Location identifier")
    description: str = Field(..., min_length=20, description="Ticket description")
    
    @validator('description')
    def validate_description(cls, v):
        if len(v.strip()) < 20:
            raise ValueError('Description must be at least 20 characters')
        return v.strip()

class ActiveTicket(TicketBase):
    """Model for active tickets"""
    estimated_resolution_time: int = Field(..., gt=0, description="Estimated resolution time in hours")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticket_id": "12345",
                "location_id": 1,
                "description": "Network connectivity issues in building A, users unable to access internet",
                "estimated_resolution_time": 4
            }
        }

class HistoricTicket(TicketBase):
    """Model for historic tickets"""
    actual_resolution_time: float = Field(..., gt=0, description="Actual resolution time in hours")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticket_id": "67890",
                "location_id": 2,
                "description": "Server maintenance required for email system downtime",
                "actual_resolution_time": 6.5
            }
        }

class TicketSubmission(BaseModel):
    """Model for new ticket submissions"""
    location_id: int = Field(..., description="Location identifier")
    description: str = Field(..., min_length=20, description="Issue description")
    
    class Config:
        json_schema_extra = {
            "example": {
                "location_id": 1,
                "description": "Printer on the 3rd floor is not working, showing paper jam error but no paper is stuck"
            }
        }

class TicketResponse(BaseModel):
    """Model for ticket processing response"""
    ticket_id: str
    location_id: int
    description: str
    estimated_resolution_time: int
    processing_method: str
    notification_message: str
    created_at: datetime
    similarity_score: Optional[float] = None
    similar_tickets_count: int = 0

class VectorDBStats(BaseModel):
    """Model for vector database statistics"""
    collection_name: str
    total_objects: int
    status: str
    error: Optional[str] = None

class BatchUploadResponse(BaseModel):
    """Model for batch upload response"""
    message: str
    total_tickets: int
    successful: int
    failed: int
    status: str
