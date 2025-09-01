"""
MCP-style Coordinator for Returns & Warranty Insights System

This coordinator implements a Message-driven Client Protocol (MCP) style architecture
to route user requests between the Retrieval Agent and Report Agent based on intent.
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntentType(Enum):
    """Intent types for routing requests."""
    RETURN_SUBMISSION = "return_submission"
    DATA_ANALYSIS = "data_analysis"  
    REPORT_GENERATION = "report_generation"
    GREETING = "greeting"
    UNKNOWN = "unknown"


@dataclass
class UserIntent:
    """Structured representation of user intent."""
    intent_type: IntentType
    confidence: float
    extracted_data: Dict[str, Any]
    raw_message: str


@dataclass
class AgentResponse:
    """Structured response from an agent."""
    success: bool
    response_text: str
    data: Optional[Dict[str, Any]] = None
    follow_up_needed: bool = False
    agent_name: str = ""


class MCPCoordinator:
    """
    MCP-style coordinator that routes messages between agents.
    
    This coordinator:
    1. Analyzes user intent from natural language input
    2. Routes requests to appropriate agents (Retrieval or Report)
    3. Manages conversation state and context
    4. Orchestrates multi-turn conversations for data collection
    """
    
    def __init__(self):
        """Initialize the coordinator with intent patterns."""
        self.conversation_state = {}
        self.active_sessions = {}
        
        # Intent recognition patterns
        self.intent_patterns = {
            IntentType.RETURN_SUBMISSION: [
                r'\b(return|returning|want to return|need to return|like to return)\b',
                r'\b(refund|exchange|send back|give back)\b',
                r'\b(defective|broken|not working|faulty|problem with)\b',
                r'\b(bought|purchased|got).*\b(return|problem|issue)\b'
            ],
            IntentType.DATA_ANALYSIS: [
                r'\b(analysis|analyze|data analysis|insights|statistics)\b',
                r'\b(how many|count|total|number of)\b',
                r'\b(trend|frequency|pattern|increase|decrease)\b',
                r'\b(past|last|previous)\s+\d+\s+(day|week|month)s?\b',
                r'\b(performance|metrics|dashboard|summary)\b'
            ],
            IntentType.REPORT_GENERATION: [
                r'\b(report|generate report|create report|download)\b',
                r'\b(excel|spreadsheet|export|file)\b',
                r'\b(summary|findings|detailed analysis)\b'
            ],
            IntentType.GREETING: [
                r'\b(hi|hello|hey|good morning|good afternoon|how are you)\b',
                r'\b(thanks|thank you|appreciate)\b'
            ]
        }
        
        # Data extraction patterns
        self.extraction_patterns = {
            'price': r'\$?(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:ntd|dollars?|usd)?',
            'discount': r'(\d+)%\s*(?:off|discount)',
            'time_period': r'(?:past|last|previous)\s+(\d+)\s+(day|week|month)s?',
            'product_name': r'\b(iphone|macbook|ipad|apple tv|airpods|apple watch)\s*[\w\s]*',
            'location': r'(?:at|from|in)\s+([\w\s]+(?:store|shop|mall|101)[\w\s]*)',
        }
    
    def analyze_intent(self, message: str) -> UserIntent:
        """
        Analyze user message to determine intent and extract relevant data.
        
        Args:
            message: User's natural language input
            
        Returns:
            UserIntent object with classified intent and extracted data
        """
        message_lower = message.lower()
        intent_scores = {}
        extracted_data = {}
        
        # Calculate intent scores
        for intent_type, patterns in self.intent_patterns.items():
            score = 0
            matches = 0
            
            for pattern in patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    matches += 1
                    score += 1
            
            if matches > 0:
                intent_scores[intent_type] = score / len(patterns)
        
        # Determine primary intent
        if not intent_scores:
            primary_intent = IntentType.UNKNOWN
            confidence = 0.0
        else:
            primary_intent = max(intent_scores.keys(), key=lambda k: intent_scores[k])
            confidence = intent_scores[primary_intent]
        
        # Extract relevant data based on intent
        if primary_intent in [IntentType.RETURN_SUBMISSION, IntentType.DATA_ANALYSIS]:
            extracted_data = self._extract_data_from_message(message)
        
        return UserIntent(
            intent_type=primary_intent,
            confidence=confidence,
            extracted_data=extracted_data,
            raw_message=message
        )
    
    def _extract_data_from_message(self, message: str) -> Dict[str, Any]:
        """Extract structured data from user message using regex patterns."""
        extracted = {}
        
        for data_type, pattern in self.extraction_patterns.items():
            matches = re.findall(pattern, message, re.IGNORECASE)
            if matches:
                if data_type == 'price':
                    # Handle price extraction
                    prices = []
                    for match in matches:
                        try:
                            price = float(match.replace(',', ''))
                            prices.append(price)
                        except ValueError:
                            continue
                    if prices:
                        extracted['prices'] = prices
                        extracted['purchase_price'] = prices[0]  # Assume first is purchase price
                
                elif data_type == 'discount':
                    try:
                        extracted['discount_percent'] = float(matches[0])
                    except (ValueError, IndexError):
                        pass
                
                elif data_type == 'time_period':
                    try:
                        number, unit = matches[0]
                        extracted['time_period'] = {
                            'number': int(number),
                            'unit': unit
                        }
                    except (ValueError, IndexError):
                        pass
                
                elif data_type == 'product_name':
                    extracted['product_name'] = matches[0].strip()
                
                elif data_type == 'location':
                    extracted['purchase_location'] = matches[0].strip()
        
        # Calculate original price if discount mentioned
        if 'purchase_price' in extracted and 'discount_percent' in extracted:
            purchase_price = extracted['purchase_price']
            discount = extracted['discount_percent']
            original_price = purchase_price / (1 - discount / 100)
            extracted['original_price'] = round(original_price, 2)
        
        return extracted
    
    def route_request(self, user_intent: UserIntent, session_id: str = None) -> Dict[str, Any]:
        """
        Route user request to appropriate agent based on intent.
        
        Args:
            user_intent: Analyzed user intent
            session_id: Optional session identifier for conversation tracking
            
        Returns:
            Dictionary containing routing decision and parameters
        """
        routing_info = {
            'target_agent': None,
            'action': None,
            'parameters': user_intent.extracted_data,
            'requires_followup': False,
            'conversation_state': None
        }
        
        if user_intent.intent_type == IntentType.RETURN_SUBMISSION:
            routing_info.update({
                'target_agent': 'retrieval_agent',
                'action': 'process_return',
                'requires_followup': self._needs_more_return_info(user_intent.extracted_data),
                'conversation_state': self._get_return_conversation_state(user_intent.extracted_data)
            })
        
        elif user_intent.intent_type == IntentType.DATA_ANALYSIS:
            routing_info.update({
                'target_agent': 'report_agent',
                'action': 'analyze_data',
                'requires_followup': False
            })
        
        elif user_intent.intent_type == IntentType.REPORT_GENERATION:
            routing_info.update({
                'target_agent': 'report_agent',
                'action': 'generate_report',
                'requires_followup': False
            })
        
        elif user_intent.intent_type == IntentType.GREETING:
            routing_info.update({
                'target_agent': 'coordinator',
                'action': 'handle_greeting',
                'requires_followup': False
            })
        
        else:
            routing_info.update({
                'target_agent': 'coordinator',
                'action': 'handle_unknown',
                'requires_followup': True
            })
        
        return routing_info
    
    def _needs_more_return_info(self, extracted_data: Dict[str, Any]) -> bool:
        """Check if we need more information to process a return."""
        required_fields = ['product_name', 'purchase_location', 'purchase_price', 'return_reason']
        
        # Check for return reason in the original message context
        if 'return_reason' not in extracted_data:
            # Try to infer return reason from common phrases
            return_reason_indicators = [
                'not working', 'broken', 'defective', 'cracked', 'faulty',
                'poor quality', 'damaged', 'wrong item', 'changed mind'
            ]
            # This would need the original message - simplified for now
            extracted_data['return_reason'] = 'not specified'
        
        missing_fields = [field for field in required_fields if field not in extracted_data]
        return len(missing_fields) > 0
    
    def _get_return_conversation_state(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate conversation state for return processing."""
        required_fields = ['product_name', 'purchase_location', 'purchase_price', 'return_reason']
        collected_fields = {field: extracted_data.get(field) for field in required_fields}
        missing_fields = [field for field, value in collected_fields.items() if not value]
        
        return {
            'collected_data': collected_fields,
            'missing_fields': missing_fields,
            'next_question': self._get_next_question(missing_fields)
        }
    
    def _get_next_question(self, missing_fields: List[str]) -> str:
        """Generate the next question to ask based on missing information."""
        question_map = {
            'product_name': "What product would you like to return?",
            'purchase_location': "Where did you purchase this item?",
            'purchase_price': "How much did you pay for it?",
            'return_reason': "What's the reason for the return?"
        }
        
        if missing_fields:
            return question_map.get(missing_fields[0], "Could you provide more details?")
        
        return ""
    
    def handle_greeting(self, message: str) -> AgentResponse:
        """Handle greeting messages."""
        greetings = [
            "Hi! I'm here to help you with returns and warranty insights. How can I assist you today?",
            "Hello! I can help you return items or analyze return data. What would you like to do?",
            "Hi there! I'm your returns and warranty assistant. How may I help you?"
        ]
        
        # Simple greeting selection based on message content
        if "data" in message.lower() or "analysis" in message.lower():
            response = "Hello! I can help you analyze return data and generate insights. What would you like to know?"
        elif "return" in message.lower():
            response = "Hi! I'm here to help you process returns. What item would you like to return?"
        else:
            response = greetings[0]
        
        return AgentResponse(
            success=True,
            response_text=response,
            agent_name="coordinator"
        )
    
    def handle_unknown(self, message: str) -> AgentResponse:
        """Handle unknown or unclear requests."""
        response = (
            "I'm not sure exactly what you'd like to do. I can help you with:\n"
            "• Processing returns (just say 'I'd like to return something')\n"
            "• Analyzing return data (ask about trends, statistics, or insights)\n"
            "• Generating reports (request Excel reports or summaries)\n\n"
            "What would you like to do?"
        )
        
        return AgentResponse(
            success=True,
            response_text=response,
            follow_up_needed=True,
            agent_name="coordinator"
        )
    
    def update_conversation_state(self, session_id: str, new_data: Dict[str, Any]):
        """Update conversation state for a session."""
        if session_id not in self.conversation_state:
            self.conversation_state[session_id] = {}
        
        self.conversation_state[session_id].update(new_data)
    
    def get_conversation_state(self, session_id: str) -> Dict[str, Any]:
        """Get current conversation state for a session."""
        return self.conversation_state.get(session_id, {})
    
    def process_message(self, message: str, session_id: str = None) -> Tuple[UserIntent, Dict[str, Any]]:
        """
        Main entry point for processing user messages.
        
        Args:
            message: User's natural language input
            session_id: Optional session identifier
            
        Returns:
            Tuple of (UserIntent, routing_info)
        """
        # Analyze intent
        user_intent = self.analyze_intent(message)
        
        # Route request
        routing_info = self.route_request(user_intent, session_id)
        
        # Update conversation state if needed
        if session_id and routing_info.get('conversation_state'):
            self.update_conversation_state(session_id, routing_info['conversation_state'])
        
        logger.info(f"Intent: {user_intent.intent_type.value}, "
                   f"Confidence: {user_intent.confidence:.2f}, "
                   f"Target: {routing_info['target_agent']}")
        
        return user_intent, routing_info


# Test and demonstration functions
def test_coordinator():
    """Test the coordinator with sample messages."""
    coordinator = MCPCoordinator()
    
    test_messages = [
        "Hi, how are you? I'd like to return something.",
        "I want to return an Apple TV that was bought last week at Taipei 101 Apple store. The Apple TV's usb port is not working.",
        "I bought it for 3000 NTD after 10% discount.",
        "Hi, how are you? I'd like to perform some data analysis on the items returned.",
        "I'd like to know how many iPhones were returned in the past 2 weeks",
        "Please generate an excel report for me to download",
        "Hello there!",
        "What can you do?"
    ]
    
    print("MCP Coordinator Test Results:")
    print("=" * 50)
    
    for i, message in enumerate(test_messages, 1):
        print(f"\nTest {i}: '{message}'")
        
        user_intent, routing_info = coordinator.process_message(message, session_id=f"test_{i}")
        
        print(f"  Intent: {user_intent.intent_type.value}")
        print(f"  Confidence: {user_intent.confidence:.2f}")
        print(f"  Target Agent: {routing_info['target_agent']}")
        print(f"  Action: {routing_info['action']}")
        
        if user_intent.extracted_data:
            print(f"  Extracted Data: {user_intent.extracted_data}")
        
        if routing_info['requires_followup']:
            print(f"  Needs Follow-up: Yes")
            conv_state = routing_info.get('conversation_state')
            if conv_state and conv_state.get('next_question'):
                print(f"  Next Question: {conv_state['next_question']}")


if __name__ == "__main__":
    test_coordinator()