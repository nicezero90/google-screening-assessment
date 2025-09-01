"""
Integration tests for AI agents working together.
"""

import unittest
import os
import sys

# Add the section-b-ai-agent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'section-b-ai-agent'))

from coordinator.mcp_coordinator import MCPCoordinator, IntentType
from retrieval_agent.retrieval_agent import RetrievalAgent
from report_agent.report_agent import ReportAgent
from database_simple import ReturnsDatabase


class TestAgentsIntegration(unittest.TestCase):
    """Test cases for agent integration and workflows."""
    
    def setUp(self):
        """Set up agents for testing."""
        self.coordinator = MCPCoordinator()
        self.retrieval_agent = RetrievalAgent("test_returns.db")
        self.report_agent = ReportAgent("test_returns.db")
        self.database = ReturnsDatabase("test_returns.db")
    
    def test_coordinator_intent_recognition(self):
        """Test coordinator's intent recognition accuracy."""
        test_cases = [
            ("Hello, I'd like to return something", IntentType.RETURN_SUBMISSION),
            ("I want to return an iPhone", IntentType.RETURN_SUBMISSION),
            ("How many products were returned?", IntentType.DATA_ANALYSIS),
            ("Generate a report", IntentType.REPORT_GENERATION),
            ("Hi there", IntentType.GREETING),
            ("What can you do?", IntentType.UNKNOWN)
        ]
        
        for message, expected_intent in test_cases:
            with self.subTest(message=message):
                user_intent, routing_info = self.coordinator.process_message(message)
                self.assertEqual(user_intent.intent_type, expected_intent)
    
    def test_complete_return_workflow(self):
        """Test complete return processing workflow."""
        # Test with complete return information
        message = "I want to return an Apple TV bought at Taipei 101 for 3000 NTD. USB port not working."
        
        # Process through coordinator
        user_intent, routing_info = self.coordinator.process_message(message)
        self.assertEqual(routing_info['target_agent'], 'retrieval_agent')
        
        # Process through retrieval agent
        response = self.retrieval_agent.process_return_request(
            message, user_intent.extracted_data, "test_session"
        )
        
        self.assertTrue(response.success)
        self.assertEqual(response.agent_name, "retrieval_agent")
        self.assertIn("Apple TV", response.response_text)
        self.assertIn("3000", response.response_text)
    
    def test_incomplete_return_workflow(self):
        """Test incomplete return requiring follow-up."""
        message = "I want to return my iPhone"
        
        # Process through coordinator
        user_intent, routing_info = self.coordinator.process_message(message)
        self.assertEqual(routing_info['target_agent'], 'retrieval_agent')
        
        # Process through retrieval agent
        response = self.retrieval_agent.process_return_request(
            message, user_intent.extracted_data, "test_session2"
        )
        
        self.assertTrue(response.success)
        self.assertTrue(response.follow_up_needed)
        self.assertIn("where", response.response_text.lower())
    
    def test_analytics_workflow(self):
        """Test analytics request workflow."""
        message = "How many iPhones were returned in the past month?"
        
        # Process through coordinator
        user_intent, routing_info = self.coordinator.process_message(message)
        self.assertEqual(routing_info['target_agent'], 'report_agent')
        
        # Process through report agent
        response = self.report_agent.process_analytics_request(
            message, user_intent.extracted_data
        )
        
        self.assertTrue(response.success)
        self.assertEqual(response.agent_name, "report_agent")
        self.assertIn("iPhone", response.response_text)
    
    def test_report_generation_workflow(self):
        """Test report generation workflow."""
        message = "Generate an Excel report"
        
        # Process through coordinator
        user_intent, routing_info = self.coordinator.process_message(message)
        self.assertEqual(routing_info['target_agent'], 'report_agent')
        
        # Process through report agent
        response = self.report_agent.process_analytics_request(
            message, user_intent.extracted_data
        )
        
        self.assertTrue(response.success)
        self.assertEqual(response.agent_name, "report_agent")
    
    def test_data_extraction_accuracy(self):
        """Test coordinator's data extraction accuracy."""
        message = "I bought an Apple TV for 3000 NTD with 10% discount at Taipei 101"
        
        user_intent, _ = self.coordinator.process_message(message)
        extracted = user_intent.extracted_data
        
        self.assertIn('product_name', extracted)
        self.assertEqual(extracted['product_name'], 'Apple TV')
        self.assertIn('purchase_price', extracted)
        self.assertEqual(extracted['purchase_price'], 3000.0)
        self.assertIn('discount_percent', extracted)
        self.assertEqual(extracted['discount_percent'], 10.0)
    
    def test_database_operations(self):
        """Test database operations work correctly."""
        # Test inserting a return
        return_data = {
            'product_name': 'Test iPhone',
            'purchase_location': 'Test Store',
            'purchase_price': 1000.0,
            'return_reason': 'Test issue'
        }
        
        return_id = self.database.insert_return(return_data)
        self.assertIsInstance(return_id, int)
        self.assertGreater(return_id, 0)
        
        # Test retrieving the return
        retrieved = self.database.get_return_by_id(return_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved['product_name'], 'Test iPhone')
        
        # Test analytics
        analytics = self.database.get_analytics_data(days_back=365)
        self.assertIsInstance(analytics, dict)
        self.assertIn('total_returns', analytics)
        self.assertIn('product_breakdown', analytics)
    
    def test_error_handling(self):
        """Test error handling in various scenarios."""
        # Test invalid return data
        try:
            response = self.retrieval_agent.process_return_request(
                "", {}, "error_session"
            )
            # Should handle gracefully
            self.assertIsNotNone(response)
        except Exception:
            self.fail("Retrieval agent should handle empty input gracefully")
        
        # Test invalid analytics request
        try:
            response = self.report_agent.process_analytics_request("", {})
            self.assertIsNotNone(response)
        except Exception:
            self.fail("Report agent should handle empty input gracefully")
    
    def tearDown(self):
        """Clean up test database."""
        try:
            os.remove("test_returns.db")
        except OSError:
            pass


if __name__ == '__main__':
    unittest.main(verbosity=2)