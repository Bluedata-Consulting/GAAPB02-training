#!/usr/bin/env python3
"""
Script to populate vector database with initial ticket data from CSV files
"""
import asyncio
import logging
import sys
from pathlib import Path
from typing import List
import argparse

# Add backend directory to path
sys.path.append(str(Path(__file__).parent.parent))

from data.csv_loader import CSVDataLoader
from core.auth.azure_auth import AzureAuthManager
from services.embedding_service import EmbeddingService
from services.vector_store_service import VectorStoreService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def populate_database(active_csv_path: str, historic_csv_path: str):
    """Populate the vector database with ticket data"""
    
    try:
        # Initialize services
        logger.info("Initializing services...")
        auth_manager = AzureAuthManager()
        embedding_service = EmbeddingService(auth_manager)
        vector_store = VectorStoreService(auth_manager, embedding_service)
        
        # Load active tickets
        if Path(active_csv_path).exists():
            logger.info(f"Loading active tickets from {active_csv_path}")
            active_tickets = CSVDataLoader.load_active_tickets(active_csv_path)
            
            if active_tickets:
                logger.info(f"Upserting {len(active_tickets)} active tickets...")
                successful, failed = vector_store.batch_upsert_active_tickets(active_tickets)
                logger.info(f"Active tickets: {successful} successful, {failed} failed")
            else:
                logger.warning("No active tickets found")
        else:
            logger.warning(f"Active tickets file not found: {active_csv_path}")
        
        # Load historic tickets
        if Path(historic_csv_path).exists():
            logger.info(f"Loading historic tickets from {historic_csv_path}")
            historic_tickets = CSVDataLoader.load_historic_tickets(historic_csv_path)
            
            if historic_tickets:
                logger.info(f"Upserting {len(historic_tickets)} historic tickets...")
                successful, failed = vector_store.batch_upsert_historic_tickets(historic_tickets)
                logger.info(f"Historic tickets: {successful} successful, {failed} failed")
            else:
                logger.warning("No historic tickets found")
        else:
            logger.warning(f"Historic tickets file not found: {historic_csv_path}")
        
        # Get final stats
        active_stats = vector_store.get_collection_stats("ActiveTickets")
        historic_stats = vector_store.get_collection_stats("HistoricTickets")
        
        logger.info("Database population completed!")
        logger.info(f"Final stats:")
        logger.info(f"  Active tickets: {active_stats.total_objects}")
        logger.info(f"  Historic tickets: {historic_stats.total_objects}")
        logger.info(f"  Total tickets: {active_stats.total_objects + historic_stats.total_objects}")
        
        # Cleanup
        vector_store.close()
        
    except Exception as e:
        logger.error(f"Failed to populate database: {e}")
        raise

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Populate vector database with ticket data")
    parser.add_argument(
        "--active-csv", 
        default="data/active_ticket_detail.csv",
        help="Path to active tickets CSV file"
    )
    parser.add_argument(
        "--historic-csv", 
        default="data/historic_ticket_detail.csv",
        help="Path to historic tickets CSV file"
    )
    
    args = parser.parse_args()
    
    # Run the population
    asyncio.run(populate_database(args.active_csv, args.historic_csv))

if __name__ == "__main__":
    main()

