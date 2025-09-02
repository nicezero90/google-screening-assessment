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
    suggested_responses: Optional[List[str]] = None  # Smart suggestion bubbles


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
                r'\b(bought|purchased|got).*\b(return|problem|issue)\b',
                # Enhanced natural language patterns
                r'\b(not (happy|satisfied)|disappointed|regret buying|wrong (item|product|color|size))\b',
                r'\b(doesn\'t work|doesn\'t function|stop(ped)? working)\b',
                r'\b(change my mind|don\'t (want|need) (this|it)|no longer (want|need))\b',
                r'\b(receipt|warranty|guarantee).*\b(return|refund)\b',
                r'\b(mistake|error|wrong).*\b(purchase|order|buy)\b'
            ],
            IntentType.DATA_ANALYSIS: [
                r'\b(analysis|analyze|data analysis|insights|statistics)\b',
                r'\b(how many|count|total|number of)\b',
                r'\b(trend|frequency|pattern|increase|decrease)\b',
                r'\b(past|last|previous)\s+\d+\s+(day|week|month)s?\b',
                r'\b(performance|metrics|dashboard|summary)\b',
                # Enhanced casual inquiry patterns
                r'\b(what\'s (the|our)|tell me about|show me)\b',
                r'\b(any (trends|patterns|issues)|common (problems|issues))\b',
                r'\b((most|least) (popular|common|frequent))\b',
                r'\b(which (products?|items?)|what (products?|items?))\b',
                r'\b(why (are|do)|what (causes?|reasons?))\b'
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
            'price': r'(?:cost|paid|price|bought.*for|for)\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:ntd|dollars?|usd)',
            'discount': r'(\d+)%\s*(?:off|discount)',
            'time_period': r'(?:past|last|previous)\s+(\d+)\s+(day|week|month)s?',
            'product_name': r'\b(iphone|macbook|ipad|apple tv|airpods|apple watch)\s*[\w\s]*',
            'location': r'(?:at|from|in)\s+([\w\s]+(?:store|shop|mall|101)[\w\s]*)',
        }
    
    def analyze_intent(self, message: str, conversation_history: List[Dict] = None) -> UserIntent:
        """
        Analyze user message to determine intent and extract relevant data with context awareness.
        
        Args:
            message: User's natural language input
            conversation_history: Previous conversation context
            
        Returns:
            UserIntent object with classified intent and extracted data
        """
        message_lower = message.lower()
        intent_scores = {}
        extracted_data = {}
        
        # Add context-aware processing
        if conversation_history:
            extracted_data.update(self._extract_context_from_history(message, conversation_history))
        
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
            # Check if this might be a follow-up response based on context
            if extracted_data.get('is_followup_response'):
                primary_intent = IntentType.RETURN_SUBMISSION
                confidence = 0.8  # High confidence for follow-up responses
            else:
                primary_intent = IntentType.UNKNOWN
                confidence = 0.0
        else:
            primary_intent = max(intent_scores.keys(), key=lambda k: intent_scores[k])
            confidence = intent_scores[primary_intent]
        
        # Extract relevant data based on intent
        if primary_intent in [IntentType.RETURN_SUBMISSION, IntentType.DATA_ANALYSIS]:
            data_from_message = self._extract_data_from_message(message)
            # Merge context data with extracted data
            extracted_data.update(data_from_message)
        
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
        
        # Handle "after X% discount" pattern specifically
        discount_after_match = re.search(r'(\d+).*after\s+(\d+)%\s*discount', message.lower())
        if discount_after_match:
            discounted_price = float(discount_after_match.group(1))
            discount_percent = float(discount_after_match.group(2))
            original_price = discounted_price / (1 - discount_percent / 100)
            extracted['purchase_price'] = discounted_price
            extracted['discount_percent'] = discount_percent  
            extracted['original_price'] = round(original_price, 2)
        
        return extracted
    
    def _extract_context_from_history(self, message: str, history: List[Dict]) -> Dict[str, Any]:
        """Extract contextual information from conversation history."""
        context_data = {}
        message_lower = message.lower()
        
        # Look for reference words that need context resolution
        reference_patterns = {
            'product_references': [
                r'\b(that|this|it|them|those|these)\b',
                r'\b(the (item|product|device|thing))\b'
            ],
            'quantity_references': [
                r'\b(how many|count|number of)\s+(that|those|them|it)\b',
                r'\b(those|these|them)\s+(were|are|have been)\b'
            ]
        }
        
        # Check if message contains references that need context
        has_references = any(
            re.search(pattern, message_lower) 
            for patterns in reference_patterns.values() 
            for pattern in patterns
        )
        
        # Also check if this might be a response to a system question
        is_simple_product_name = any(
            product in message_lower 
            for product in ['iphone', 'ipad', 'macbook', 'apple tv', 'airpods', 'apple watch']
        ) and len(message.split()) <= 3  # Simple, short product mentions
        
        # Check if this looks like a price response (contains price + currency)
        is_price_response = bool(re.search(r'\d+\s*(?:ntd|dollars?|usd)', message_lower)) and (
            'bought' in message_lower or 'paid' in message_lower or 'cost' in message_lower or 'for' in message_lower
        )
        
        if (has_references or is_simple_product_name or is_price_response) and history:
            # Check recent conversation for context
            for msg in reversed(history[-3:]):  # Check last 3 messages
                agent_response = msg.get('agent_response', {})
                
                # If system recently asked for product and this looks like a product answer
                if is_simple_product_name and agent_response.get('follow_up_needed'):
                    response_text = agent_response.get('message', '').lower()
                    if 'product' in response_text or 'item' in response_text:
                        # This is likely a product name in response to system question
                        for product in ['iphone', 'ipad', 'macbook', 'apple tv', 'airpods', 'apple watch']:
                            if product in message_lower:
                                context_data['product_name'] = message.strip()  # Use exact user input
                                context_data['is_followup_response'] = True
                                break
                        break
                
                # If system recently asked for price and this looks like a price answer
                if is_price_response and agent_response.get('follow_up_needed'):
                    response_text = agent_response.get('message', '').lower()
                    if any(keyword in response_text for keyword in ['price', 'cost', 'paid', 'much']):
                        # This is a price response to system question
                        context_data['is_followup_response'] = True
                        context_data['responding_to'] = 'price_question'
                        break
                
                # Handle other references 
                if has_references:
                    user_msg = msg.get('user_message', '').lower()
                    # Extract product names from history
                    for product_pattern in ['iphone', 'ipad', 'macbook', 'apple tv', 'airpods', 'apple watch']:
                        if product_pattern in user_msg:
                            context_data['product_name'] = product_pattern.title()
                            break
                    
                    # If we found context, break
                    if context_data:
                        break
        
        return context_data
    
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
        # More natural and empathetic question templates
        question_templates = {
            'product_name': [
                "I'd be happy to help with your return. What product are you looking to return?",
                "Sure thing! Which item would you like to return?",
                "I can help you with that. What product needs to be returned?"
            ],
            'purchase_location': [
                "To process your return efficiently, could you let me know where you purchased this item?",
                "Which store or website did you buy this from?",
                "Where did you originally purchase this product?"
            ],
            'purchase_price': [
                "got it. Sorry to hear that. Can you also tell me how much you bought it for?",
                "Thanks for the details. How much did you pay for it?",
                "I understand. What was the purchase price?"
            ],
            'return_reason': [
                "I'm sorry you're having issues. Could you tell me what's wrong with the product?",
                "What seems to be the problem with your purchase?",
                "What's prompting you to return this item?"
            ]
        }
        
        if missing_fields:
            field = missing_fields[0]
            if field in question_templates:
                import random
                return random.choice(question_templates[field])
            return "Could you provide a bit more information to help me assist you better?"
        
        return ""
    
    def handle_greeting(self, message: str) -> AgentResponse:
        """Handle greeting messages with tone matching the problem requirements."""
        # Check message content for specific intents within greetings
        message_lower = message.lower()
        
        if "data analysis" in message_lower or "perform some data analysis" in message_lower:
            # Data analysis greeting - match problem statement exactly
            response = "sure, what information would you like?"
        elif "return" in message_lower and not ("data" in message_lower or "analysis" in message_lower):
            # Return greeting - match problem statement exactly  
            response = "sure, please provide me with the details of the item and why you are returning it."
        else:
            # Generic greeting
            response = "Hi! How can I assist you today?"
        
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
    
    def process_message(self, message: str, session_id: str = None, conversation_history: List[Dict] = None) -> Tuple[UserIntent, Dict[str, Any]]:
        """
        Main entry point for processing user messages with context awareness.
        
        Args:
            message: User's natural language input
            session_id: Optional session identifier
            conversation_history: Previous conversation context
            
        Returns:
            Tuple of (UserIntent, routing_info)
        """
        # Analyze intent with conversation context
        user_intent = self.analyze_intent(message, conversation_history)
        
        # Route request
        routing_info = self.route_request(user_intent, session_id)
        
        # Update conversation state if needed
        if session_id and routing_info.get('conversation_state'):
            self.update_conversation_state(session_id, routing_info['conversation_state'])
        
        logger.info(f"Intent: {user_intent.intent_type.value}, "
                   f"Confidence: {user_intent.confidence:.2f}, "
                   f"Target: {routing_info['target_agent']}")
        
        return user_intent, routing_info
    
    def generate_smart_suggestions(self, user_intent: UserIntent, agent_response: AgentResponse, 
                                 conversation_history: List[Dict] = None) -> List[str]:
        """
        Generate contextual smart suggestions based on the current conversation state.
        
        Args:
            user_intent: The analyzed user intent
            agent_response: The agent's response
            conversation_history: Previous conversation context
            
        Returns:
            List of 3 suggested follow-up messages
        """
        suggestions = []
        
        # Base suggestions by intent type and agent
        if user_intent.intent_type == IntentType.GREETING:
            suggestions = [
                "I want to return something",
                "Show me return statistics",
                "Generate a report for me"
            ]
        
        elif user_intent.intent_type == IntentType.RETURN_SUBMISSION:
            if agent_response.follow_up_needed:
                # During return process - suggest completion based on what's actually being asked
                missing_fields = agent_response.data.get('missing_fields', [])
                
                # Check what the system is currently asking for by analyzing the response text
                response_lower = agent_response.response_text.lower()
                
                if 'product' in response_lower and ('what product' in response_lower or 'which item' in response_lower):
                    # System is asking for product - suggest common products
                    suggestions = [
                        "iPhone 14 Pro",
                        "MacBook Pro", 
                        "iPad Air"
                    ]
                elif 'where' in response_lower and ('purchase' in response_lower or 'bought' in response_lower):
                    # System is asking for purchase location
                    suggestions = [
                        "Apple Store Taipei 101",
                        "Online store",
                        "Apple Store Xinyi"
                    ]
                elif 'price' in response_lower or 'cost' in response_lower or 'paid' in response_lower:
                    # System is asking for price
                    suggestions = [
                        "Around $1000",
                        "About 28,000 NTD", 
                        "It was expensive"
                    ]
                elif 'reason' in response_lower or 'problem' in response_lower or 'wrong' in response_lower:
                    # System is asking for return reason
                    suggestions = [
                        "Screen cracked",
                        "Not working properly",
                        "Wrong color/size"
                    ]
                else:
                    # Fallback - general return-related suggestions
                    suggestions = [
                        "I need help with this",
                        "Let me explain the issue",
                        "Can you guide me?"
                    ]
            else:
                # Return completed - suggest logical next actions matching problem context
                suggestions = [
                    "How many similar products were returned?",
                    "Generate a return analysis report", 
                    "What else can you help me with?"
                ]
        
        elif user_intent.intent_type == IntentType.DATA_ANALYSIS:
            # After data analysis - suggest deeper insights
            if 'product_name' in user_intent.extracted_data:
                product = user_intent.extracted_data['product_name']
                suggestions = [
                    f"What causes {product} returns?",
                    f"Show {product} return trends",
                    f"Generate {product} analysis report"
                ]
            else:
                suggestions = [
                    "Which product has most returns?",
                    "Show me return trends over time",
                    "What are the main return reasons?"
                ]
        
        elif user_intent.intent_type == IntentType.REPORT_GENERATION:
            # After report generation - suggest analysis
            suggestions = [
                "Analyze the biggest problem areas",
                "What trends do you see?",
                "How can we reduce returns?"
            ]
        
        elif user_intent.intent_type == IntentType.UNKNOWN:
            # Help guide users
            suggestions = [
                "I want to return a product",
                "Show me return statistics",
                "What can you help me with?"
            ]
        
        # Context-aware enhancement
        if conversation_history:
            suggestions = self._enhance_suggestions_with_context(suggestions, conversation_history)
        
        # Ensure we always return exactly 3 suggestions
        return suggestions[:3] if len(suggestions) >= 3 else suggestions + ["Tell me more", "What else can you help with?", "Generate a report"][:3-len(suggestions)]
    
    def _enhance_suggestions_with_context(self, base_suggestions: List[str], history: List[Dict]) -> List[str]:
        """Enhance suggestions based on conversation history."""
        enhanced = base_suggestions.copy()
        
        # Find recently mentioned products
        recent_products = []
        for msg in reversed(history[-3:]):  # Last 3 messages
            user_msg = msg.get('user_message', '').lower()
            for product in ['iphone', 'ipad', 'macbook', 'apple tv', 'airpods', 'apple watch']:
                if product in user_msg and product not in recent_products:
                    recent_products.append(product.title())
        
        # Replace generic suggestions with specific ones
        if recent_products:
            product = recent_products[0]
            for i, suggestion in enumerate(enhanced):
                if "similar" in suggestion.lower():
                    enhanced[i] = f"How many {product} returns were there?"
                elif "trend" in suggestion.lower() and "show" in suggestion.lower():
                    enhanced[i] = f"Show {product} return patterns"
        
        return enhanced


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