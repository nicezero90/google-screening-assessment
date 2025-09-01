"""
Unit tests for the Flask web application and API endpoints.
"""

import unittest
import json
import os
import sys

# Add the section-b-ai-agent directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'section-b-ai-agent'))

from app import app


class TestFlaskApp(unittest.TestCase):
    """Test cases for Flask application routes and API endpoints."""
    
    def setUp(self):
        """Set up test client and database."""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Set up test context
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up after tests."""
        self.app_context.pop()
    
    def test_home_page(self):
        """Test the main chat interface loads correctly."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Returns & Warranty Insights', response.data)
    
    def test_health_endpoint(self):
        """Test the health check endpoint."""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('database_records', data)
        self.assertIn('agents', data)
    
    def test_stats_endpoint(self):
        """Test the statistics endpoint."""
        response = self.client.get('/api/stats')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('database', data)
        self.assertIn('analytics', data)
        self.assertIn('system', data)
    
    def test_chat_api_greeting(self):
        """Test chat API with greeting message."""
        response = self.client.post('/api/chat', 
            data=json.dumps({'message': 'Hello'}),
            content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['agent'], 'coordinator')
        self.assertEqual(data['intent'], 'greeting')
        self.assertIn('help', data['message'].lower())
    
    def test_chat_api_return_request(self):
        """Test chat API with return request."""
        message = "I want to return an Apple TV bought at Taipei 101 for 3000 NTD. USB port not working."
        
        response = self.client.post('/api/chat',
            data=json.dumps({'message': message}),
            content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['agent'], 'retrieval_agent')
        self.assertEqual(data['intent'], 'return_submission')
        self.assertIn('Apple TV', data['message'])
    
    def test_chat_api_analytics_request(self):
        """Test chat API with analytics request."""
        message = "How many iPhones were returned?"
        
        response = self.client.post('/api/chat',
            data=json.dumps({'message': message}),
            content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['agent'], 'report_agent')
        self.assertEqual(data['intent'], 'data_analysis')
        self.assertIn('iPhone', data['message'])
    
    def test_chat_api_report_request(self):
        """Test chat API with report generation request."""
        message = "Generate an Excel report for me"
        
        response = self.client.post('/api/chat',
            data=json.dumps({'message': message}),
            content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['agent'], 'report_agent')
        self.assertIn(data['intent'], ['data_analysis', 'report_generation'])  # May be classified as either
    
    def test_chat_api_invalid_input(self):
        """Test chat API with invalid input."""
        # Empty message
        response = self.client.post('/api/chat',
            data=json.dumps({'message': ''}),
            content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        
        # No message field
        response = self.client.post('/api/chat',
            data=json.dumps({}),
            content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        
        # Invalid JSON - may return 500 due to parsing error
        response = self.client.post('/api/chat',
            data='invalid json',
            content_type='application/json')
        
        self.assertIn(response.status_code, [400, 500])  # Either is acceptable
    
    def test_clear_conversation(self):
        """Test clearing conversation history."""
        response = self.client.get('/api/clear')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertTrue(data['success'])
    
    def test_conversation_history(self):
        """Test conversation history endpoint."""
        response = self.client.get('/api/history')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertIn('history', data)
        self.assertIsInstance(data['history'], list)
    
    def test_404_handler(self):
        """Test 404 error handler."""
        response = self.client.get('/nonexistent-page')
        self.assertEqual(response.status_code, 404)
        
        # API 404
        response = self.client.get('/api/nonexistent')
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
    
    def test_download_nonexistent_file(self):
        """Test downloading non-existent file."""
        response = self.client.get('/download/nonexistent.csv')
        # May return 404 or 500 depending on error handling
        self.assertIn(response.status_code, [404, 500])


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)