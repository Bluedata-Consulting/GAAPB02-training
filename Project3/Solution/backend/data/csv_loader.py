import pandas as pd
import logging
from typing import List, Tuple
from pathlib import Path
from core.models.ticket import ActiveTicket, HistoricTicket

logger = logging.getLogger(__name__)

class CSVDataLoader:
    """Loads ticket data from CSV files"""
    
    @staticmethod
    def load_active_tickets(file_path: str) -> List[ActiveTicket]:
        """Load active tickets from CSV file"""
        try:
            df = pd.read_csv(file_path)
            
            # Validate required columns
            required_columns = ['TicketID', 'locationID', 'description', 'estimated_resolution_time']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
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
                    logger.warning(f"Skipping invalid active ticket row: {e}")
                    continue
            
            logger.info(f"Loaded {len(tickets)} active tickets from {file_path}")
            return tickets
            
        except Exception as e:
            logger.error(f"Failed to load active tickets from {file_path}: {e}")
            raise
    
    @staticmethod
    def load_historic_tickets(file_path: str) -> List[HistoricTicket]:
        """Load historic tickets from CSV file"""
        try:
            df = pd.read_csv(file_path)
            
            # Validate required columns
            required_columns = ['TicketID', 'locationID', 'description', 'actual_resolution_time']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
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
                    logger.warning(f"Skipping invalid historic ticket row: {e}")
                    continue
            
            logger.info(f"Loaded {len(tickets)} historic tickets from {file_path}")
            return tickets
            
        except Exception as e:
            logger.error(f"Failed to load historic tickets from {file_path}: {e}")
            raise