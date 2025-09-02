"""
Retrieval Agent for Returns & Warranty Insights System

This agent handles:
1. Data ingestion and indexing from CSV files for RAG
2. Natural language processing for return submissions
3. Data validation and extraction from conversations
4. Database operations for storing return records
5. RAG-based search and retrieval of similar returns
"""

import os
import sys
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database_simple import ReturnsDatabase
from coordinator.mcp_coordinator import AgentResponse

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ReturnSubmission:
    """Structured representation of a return submission."""
    product_name: Optional[str] = None
    purchase_location: Optional[str] = None
    purchase_price: Optional[float] = None
    return_reason: Optional[str] = None
    purchase_date: Optional[str] = None
    customer_id: Optional[str] = None
    discount_percent: Optional[float] = None
    original_price: Optional[float] = None
    notes: Optional[str] = None
    
    def is_complete(self) -> bool:
        """Check if all required fields are present."""
        required_fields = [self.product_name, self.purchase_location, 
                          self.purchase_price, self.return_reason]
        return all(field is not None for field in required_fields)
    
    def missing_fields(self) -> List[str]:
        """Get list of missing required fields."""
        missing = []
        if not self.product_name:
            missing.append('product_name')
        if not self.purchase_location:
            missing.append('purchase_location')
        if not self.purchase_price:
            missing.append('purchase_price')
        if not self.return_reason:
            missing.append('return_reason')
        return missing


class RetrievalAgent:
    """
    Agent responsible for data retrieval, ingestion, and return processing.
    
    This agent implements RAG (Retrieval-Augmented Generation) capabilities
    for finding similar returns and processing new return submissions.
    """
    
    def __init__(self, db_path: str = "returns_warranty.db"):
        """Initialize the retrieval agent with database connection."""
        self.db = ReturnsDatabase(db_path)
        self.conversation_sessions = {}
        
        # Initialize with sample data if database is empty
        stats = self.db.get_database_stats()
        if stats['total_records'] == 0:
            self._load_initial_data()
        
        # Common return reasons for inference
        self.return_reasons_map = {
            'not working': 'Device not functioning properly',
            'broken': 'Physical damage or defect',
            'cracked': 'Screen or housing damage',
            'screen cracked': 'Screen cracked out of the box',
            'battery': 'Battery related issues',
            'charging': 'Charging port or cable issues',
            'usb port': 'USB port not working',
            'defective': 'Manufacturing defect',
            'faulty': 'Product malfunction',
            'overheating': 'Device overheating issues',
            'dead pixels': 'Screen has dead pixels',
            'unresponsive': 'Touch screen unresponsive'
        }
    
    def _load_initial_data(self):
        """Load initial sample data into the database."""
        try:
            # Try to load official CSV first
            official_csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'official_sample.csv')
            if os.path.exists(official_csv_path):
                records_loaded = self.db.load_csv_data(official_csv_path)
                logger.info(f"Loaded {records_loaded} records from official CSV")
                return
            
            # Fallback to original sample data
            csv_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'sample_returns.csv')
            if os.path.exists(csv_path):
                records_loaded = self.db.load_csv_data(csv_path)
                logger.info(f"Loaded {records_loaded} initial records from fallback CSV")
            else:
                logger.warning(f"No CSV files found for initial data loading")
        except Exception as e:
            logger.error(f"Error loading initial data: {e}")
    
    def process_return_request(self, message: str, extracted_data: Dict[str, Any], 
                             session_id: str = None) -> AgentResponse:
        """
        Process a return request from user input.
        
        Args:
            message: Original user message
            extracted_data: Data extracted by coordinator
            session_id: Session identifier for conversation tracking
            
        Returns:
            AgentResponse with processing result
        """
        try:
            # Get or create session
            if not session_id:
                session_id = f"return_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if session_id not in self.conversation_sessions:
                self.conversation_sessions[session_id] = ReturnSubmission()
            
            submission = self.conversation_sessions[session_id]
            
            # Update submission with new data
            self._update_submission_from_data(submission, extracted_data, message)
            
            # Check if submission is complete
            if submission.is_complete():
                # Process the complete return
                return self._finalize_return(submission, session_id)
            else:
                # Ask for missing information
                return self._request_missing_info(submission, session_id)
                
        except Exception as e:
            logger.error(f"Error processing return request: {e}")
            return AgentResponse(
                success=False,
                response_text=f"I encountered an error processing your return request: {e}",
                agent_name="retrieval_agent"
            )
    
    def _update_submission_from_data(self, submission: ReturnSubmission, 
                                   extracted_data: Dict[str, Any], message: str):
        """Update submission object with extracted data and inferred information."""
        
        # Update from extracted data
        if 'product_name' in extracted_data:
            submission.product_name = self._clean_product_name(extracted_data['product_name'])
        
        if 'purchase_location' in extracted_data:
            submission.purchase_location = self._clean_location(extracted_data['purchase_location'])
        
        if 'purchase_price' in extracted_data:
            submission.purchase_price = extracted_data['purchase_price']
        
        if 'original_price' in extracted_data:
            submission.original_price = extracted_data['original_price']
        
        if 'discount_percent' in extracted_data:
            submission.discount_percent = extracted_data['discount_percent']
        
        # Infer return reason from message
        if not submission.return_reason:
            submission.return_reason = self._infer_return_reason(message)
        
        # Set default category and brand based on product
        if submission.product_name and not hasattr(submission, 'category'):
            submission.category = self._infer_category(submission.product_name)
            submission.brand = self._infer_brand(submission.product_name)
    
    def _clean_product_name(self, product_name: str) -> str:
        """Clean and standardize product name."""
        # Remove extra whitespace and common prefixes
        cleaned = re.sub(r'\s+', ' ', product_name.strip())
        
        # Standardize common product names
        standardization_map = {
            r'apple tv': 'Apple TV',
            r'iphone': 'iPhone',
            r'ipad': 'iPad',
            r'macbook': 'MacBook',
            r'airpods': 'AirPods',
            r'apple watch': 'Apple Watch'
        }
        
        for pattern, replacement in standardization_map.items():
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        
        return cleaned
    
    def _clean_location(self, location: str) -> str:
        """Clean and standardize purchase location."""
        # Remove common prefixes and clean up
        location = re.sub(r'^(at|from|in)\s+', '', location, flags=re.IGNORECASE)
        location = re.sub(r'\s+', ' ', location.strip())
        
        # Standardize common locations
        if '101' in location.lower():
            return 'Apple Store Taipei 101'
        elif 'xinyi' in location.lower():
            return 'Apple Store Xinyi'
        elif 'online' in location.lower():
            return 'Online Store'
        
        return location
    
    def _infer_return_reason(self, message: str) -> str:
        """Infer return reason from message content."""
        message_lower = message.lower()
        
        for keyword, reason in self.return_reasons_map.items():
            if keyword in message_lower:
                return reason
        
        # Default if no specific reason found
        return "Product issue reported"
    
    def _infer_category(self, product_name: str) -> str:
        """Infer product category from product name."""
        return "Electronics"  # All Apple products are electronics
    
    def _infer_brand(self, product_name: str) -> str:
        """Infer brand from product name."""
        apple_products = ['iphone', 'ipad', 'macbook', 'apple tv', 'airpods', 'apple watch']
        if any(product in product_name.lower() for product in apple_products):
            return "Apple"
        return "Unknown"
    
    def _finalize_return(self, submission: ReturnSubmission, session_id: str) -> AgentResponse:
        """Process a complete return submission."""
        try:
            # Prepare data for database insertion
            return_data = {
                'product_name': submission.product_name,
                'category': getattr(submission, 'category', 'Electronics'),
                'brand': getattr(submission, 'brand', 'Apple'),
                'purchase_location': submission.purchase_location,
                'purchase_price': submission.purchase_price,
                'return_reason': submission.return_reason,
                'return_date': datetime.now(),
                'warranty_status': 'Under Warranty',
                'customer_id': submission.customer_id or f"CUST_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
            
            # Add original price and discount if available
            if submission.original_price:
                return_data['original_price'] = submission.original_price
            if submission.discount_percent:
                return_data['discount_percent'] = submission.discount_percent
            
            # Insert into database
            return_id = self.db.insert_return(return_data)
            
            # Get the inserted record for confirmation
            inserted_record = self.db.get_return_by_id(return_id)
            
            # Generate confirmation message
            confirmation = self._generate_confirmation_message(inserted_record)
            
            # Clean up session
            if session_id in self.conversation_sessions:
                del self.conversation_sessions[session_id]
            
            return AgentResponse(
                success=True,
                response_text=confirmation,
                data={'return_id': return_id, 'record': inserted_record},
                agent_name="retrieval_agent"
            )
            
        except Exception as e:
            logger.error(f"Error finalizing return: {e}")
            return AgentResponse(
                success=False,
                response_text=f"I encountered an error processing your return: {e}",
                agent_name="retrieval_agent"
            )
    
    def _generate_confirmation_message(self, record: Dict[str, Any]) -> str:
        """Generate a confirmation message matching the problem statement tone."""
        product = record.get('product_name', 'item')
        location = record.get('purchase_location', 'unknown location')
        price = record.get('purchase_price', 0)
        original_price = record.get('original_price')
        reason = record.get('return_reason', 'reported issue')
        return_id = record.get('id')
        
        # Calculate original price if discount was applied
        if original_price and original_price != price:
            final_price = original_price
        else:
            final_price = price
        
        # Format message to match problem statement tone
        confirmation = (
            f"got it. I have inserted a new item for refund which is {product}, "
            f"purchased at {location} at {final_price:.0f} NTD "
            f"because {reason.lower()}. Is there anything else I can help you with? Have a great day!"
        )
        
        return confirmation
    
    def _request_missing_info(self, submission: ReturnSubmission, session_id: str) -> AgentResponse:
        """Request missing information from user."""
        missing_fields = submission.missing_fields()
        
        if not missing_fields:
            return self._finalize_return(submission, session_id)
        
        # Generate specific question for the first missing field
        question_map = {
            'product_name': "What product would you like to return?",
            'purchase_location': "Where did you purchase this item?",
            'purchase_price': "How much did you pay for it? (Please include the currency, e.g., 3000 NTD)",
            'return_reason': "What's the reason for returning this item?"
        }
        
        next_field = missing_fields[0]
        question = question_map.get(next_field, "Could you provide more details?")
        
        # Add context about what we already know
        known_info = []
        if submission.product_name:
            known_info.append(f"Product: {submission.product_name}")
        if submission.purchase_location:
            known_info.append(f"Location: {submission.purchase_location}")
        if submission.purchase_price:
            known_info.append(f"Price: {submission.purchase_price} NTD")
        if submission.return_reason:
            known_info.append(f"Reason: {submission.return_reason}")
        
        context = ""
        if known_info:
            context = f"I have: {', '.join(known_info)}.\n\n"
        
        response_text = f"{context}{question}"
        
        return AgentResponse(
            success=True,
            response_text=response_text,
            follow_up_needed=True,
            data={'session_id': session_id, 'missing_fields': missing_fields},
            agent_name="retrieval_agent"
        )
    
    def search_similar_returns(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for similar returns using simple text matching.
        This is a simplified RAG implementation.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of similar return records
        """
        try:
            # Simple keyword-based search
            search_terms = query.lower().split()
            
            # Search in product names and return reasons
            all_returns = self.db.search_returns(limit=1000)  # Get more records for filtering
            
            scored_results = []
            for return_record in all_returns:
                score = 0
                
                # Score based on product name match
                product_name = (return_record.get('product_name', '') or '').lower()
                for term in search_terms:
                    if term in product_name:
                        score += 2
                
                # Score based on return reason match
                return_reason = (return_record.get('return_reason', '') or '').lower()
                for term in search_terms:
                    if term in return_reason:
                        score += 1
                
                if score > 0:
                    scored_results.append((score, return_record))
            
            # Sort by score and return top results
            scored_results.sort(key=lambda x: x[0], reverse=True)
            return [result[1] for result in scored_results[:limit]]
            
        except Exception as e:
            logger.error(f"Error searching similar returns: {e}")
            return []
    
    def handle_followup_message(self, message: str, session_id: str, 
                               extracted_data: Dict[str, Any]) -> AgentResponse:
        """Handle follow-up messages in an ongoing conversation."""
        if session_id not in self.conversation_sessions:
            # Session expired or doesn't exist, start new return process
            return self.process_return_request(message, extracted_data, session_id)
        
        # Continue with existing session
        return self.process_return_request(message, extracted_data, session_id)
    
    def get_ingestion_stats(self) -> Dict[str, Any]:
        """Get statistics about ingested data."""
        return self.db.get_database_stats()


# Test function
def test_retrieval_agent():
    """Test the retrieval agent with sample interactions."""
    agent = RetrievalAgent()
    
    print("Retrieval Agent Test")
    print("=" * 40)
    
    # Test 1: Complete return submission
    print("\nTest 1: Complete return submission")
    extracted_data1 = {
        'product_name': 'Apple TV',
        'purchase_location': 'Apple Store Taipei 101',
        'purchase_price': 3300,
        'original_price': 3300,
        'return_reason': 'USB port not working'
    }
    
    response1 = agent.process_return_request(
        "I want to return an Apple TV bought at Taipei 101 for 3300 NTD. USB port not working.",
        extracted_data1,
        "test_session_1"
    )
    
    print(f"Success: {response1.success}")
    print(f"Response: {response1.response_text}")
    
    # Test 2: Incomplete submission requiring follow-up
    print("\nTest 2: Incomplete submission")
    extracted_data2 = {
        'product_name': 'iPhone 14'
    }
    
    response2 = agent.process_return_request(
        "I want to return my iPhone 14",
        extracted_data2,
        "test_session_2"
    )
    
    print(f"Success: {response2.success}")
    print(f"Response: {response2.response_text}")
    print(f"Follow-up needed: {response2.follow_up_needed}")
    
    # Test 3: Search similar returns
    print("\nTest 3: Search similar returns")
    similar = agent.search_similar_returns("iPhone screen cracked")
    print(f"Found {len(similar)} similar returns:")
    for i, return_record in enumerate(similar[:3], 1):
        print(f"  {i}. {return_record['product_name']} - {return_record['return_reason']}")


if __name__ == "__main__":
    test_retrieval_agent()