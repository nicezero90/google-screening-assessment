"""
Flask Web Application for Returns & Warranty Insights System

This is the main entry point for the AI Agent RAG system.
Provides a GPT-like chat interface for users to interact with 
the Retrieval and Report agents.
"""

import os
import sys
import uuid
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from flask import Flask, render_template, request, jsonify, send_file, session
from flask import abort, redirect, url_for

# Add current directory to Python path
sys.path.append(os.path.dirname(__file__))

# Import our agents
from coordinator.mcp_coordinator import MCPCoordinator
from retrieval_agent.retrieval_agent import RetrievalAgent
from report_agent.report_agent import ReportAgent
from database_simple import ReturnsDatabase

# Configure logging for the application
# This helps track system behavior and debug issues in production
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask web application
app = Flask(__name__)
# Set secret key for session management (should be randomized in production)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
# Limit file upload size to 16MB to prevent abuse
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  

# Initialize the MCP-style multi-agent system components
# These agents work together to process returns and generate insights
coordinator = MCPCoordinator()        # Routes requests between agents
retrieval_agent = RetrievalAgent()    # Handles return processing and data retrieval
report_agent = ReportAgent()          # Handles analytics and report generation
database = ReturnsDatabase()          # Manages SQLite database operations

# Global store for active conversation sessions
# Each session tracks multi-turn conversations for incomplete return submissions
conversation_sessions = {}


class ConversationManager:
    """
    Central conversation management system for the multi-agent application.
    
    This class handles:
    - Session management for multi-turn conversations
    - Message routing between MCP coordinator and agents
    - Response formatting for the web interface
    - Conversation history tracking
    """
    
    def __init__(self):
        """Initialize the conversation manager with empty session storage."""
        self.sessions = {}
    
    def get_session_id(self) -> str:
        """
        Get or create a unique session identifier for the current user.
        
        Uses Flask's session management to maintain user sessions across requests.
        Each session gets a UUID to ensure uniqueness and prevent conflicts.
        
        Returns:
            str: Unique session identifier
        """
        if 'session_id' not in session:
            session['session_id'] = str(uuid.uuid4())
        return session['session_id']
    
    def process_message(self, message: str, session_id: str) -> Dict[str, Any]:
        """
        Process a user message through the MCP coordinator and agents.
        
        Returns:
            Dictionary with response data
        """
        try:
            # Get conversation history for context
            conversation_history = self.sessions.get(session_id, {}).get('messages', [])
            
            # Analyze intent and route request with context
            user_intent, routing_info = coordinator.process_message(message, session_id, conversation_history)
            
            logger.info(f"Session {session_id[:8]}: Intent={user_intent.intent_type.value}, "
                       f"Target={routing_info['target_agent']}")
            
            # Route to appropriate agent
            if routing_info['target_agent'] == 'retrieval_agent':
                response = retrieval_agent.process_return_request(
                    message, user_intent.extracted_data, session_id
                )
            
            elif routing_info['target_agent'] == 'report_agent':
                response = report_agent.process_analytics_request(
                    message, user_intent.extracted_data
                )
            
            elif routing_info['target_agent'] == 'coordinator':
                if routing_info['action'] == 'handle_greeting':
                    response = coordinator.handle_greeting(message)
                else:
                    response = coordinator.handle_unknown(message)
            
            else:
                response = coordinator.handle_unknown(message)
            
            # Format response for web interface
            response_data = {
                'success': response.success,
                'message': response.response_text,
                'agent': response.agent_name,
                'follow_up_needed': response.follow_up_needed,
                'data': response.data or {},
                'intent': user_intent.intent_type.value,
                'confidence': user_intent.confidence
            }
            
            # Store conversation history
            if session_id not in self.sessions:
                self.sessions[session_id] = {'messages': []}
            
            self.sessions[session_id]['messages'].append({
                'timestamp': datetime.now().isoformat(),
                'user_message': message,
                'agent_response': response_data,
                'intent': user_intent.intent_type.value
            })
            
            return response_data
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                'success': False,
                'message': f'I encountered an error: {str(e)}. Please try again.',
                'agent': 'system',
                'follow_up_needed': False,
                'data': {},
                'intent': 'error'
            }
    
    def get_conversation_history(self, session_id: str, limit: int = 10) -> list:
        """Get conversation history for a session."""
        if session_id in self.sessions:
            messages = self.sessions[session_id]['messages']
            return messages[-limit:] if limit else messages
        return []


# Initialize conversation manager
conversation_manager = ConversationManager()


@app.route('/')
def index():
    """Main chat interface."""
    return render_template('index.html')


@app.route('/test')
def test():
    """Simple test chat interface."""
    return send_file('test.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """Process chat messages."""
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400
        
        message = data['message'].strip()
        if not message:
            return jsonify({'error': 'Message cannot be empty'}), 400
        
        session_id = conversation_manager.get_session_id()
        
        # Process message through agents
        response = conversation_manager.process_message(message, session_id)
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Chat API error: {e}")
        return jsonify({
            'success': False,
            'message': 'An error occurred processing your message.',
            'agent': 'system'
        }), 500


@app.route('/api/history')
def get_history():
    """Get conversation history."""
    try:
        session_id = conversation_manager.get_session_id()
        history = conversation_manager.get_conversation_history(session_id)
        return jsonify({'history': history})
        
    except Exception as e:
        logger.error(f"History API error: {e}")
        return jsonify({'error': 'Failed to retrieve history'}), 500


@app.route('/api/clear')
def clear_history():
    """Clear conversation history."""
    try:
        session_id = conversation_manager.get_session_id()
        if session_id in conversation_manager.sessions:
            del conversation_manager.sessions[session_id]
        
        # Also clear session data
        session.clear()
        
        return jsonify({'success': True, 'message': 'Conversation cleared'})
        
    except Exception as e:
        logger.error(f"Clear API error: {e}")
        return jsonify({'error': 'Failed to clear history'}), 500


@app.route('/api/stats')
def get_stats():
    """Get system statistics."""
    try:
        # Get database stats
        db_stats = database.get_database_stats()
        
        # Get recent analytics
        analytics = database.get_analytics_data(days_back=30)
        
        stats = {
            'database': db_stats,
            'analytics': {
                'total_returns_30d': analytics['total_returns'],
                'total_loss_30d': analytics['total_loss'],
                'top_products': analytics['product_breakdown'][:5],
                'common_reasons': analytics['reason_analysis'][:5]
            },
            'system': {
                'active_sessions': len(conversation_manager.sessions),
                'total_conversations': sum(len(s['messages']) for s in conversation_manager.sessions.values())
            }
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Stats API error: {e}")
        return jsonify({'error': 'Failed to retrieve statistics'}), 500


@app.route('/download/<path:filename>')
def download_report(filename):
    """Download generated reports."""
    try:
        # Sanitize filename to prevent directory traversal
        safe_filename = os.path.basename(filename)
        
        # Check if file exists in reports folder
        reports_folder = os.path.join(app.root_path, 'report_agent', 'reports')
        file_path = os.path.join(reports_folder, safe_filename)
        
        if not os.path.exists(file_path):
            logger.warning(f"Report file not found: {safe_filename}")
            abort(404)
        
        # Check file age (optional security measure)
        file_age = datetime.now().timestamp() - os.path.getmtime(file_path)
        if file_age > 86400:  # 24 hours
            logger.warning(f"Report file expired: {safe_filename}")
            abort(410, "Report has expired")
        
        return send_file(file_path, as_attachment=True, download_name=safe_filename)
        
    except Exception as e:
        logger.error(f"Download error: {e}")
        abort(500, "Failed to download report")


@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        stats = database.get_database_stats()
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database_records': stats['total_records'],
            'agents': {
                'coordinator': 'active',
                'retrieval_agent': 'active',
                'report_agent': 'active'
            }
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'API endpoint not found'}), 404
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('500.html'), 500


# Initialize database with sample data on startup
def initialize_system():
    """Initialize the system with sample data if needed."""
    try:
        stats = database.get_database_stats()
        logger.info(f"Database initialized with {stats['total_records']} records")
        
        # Clean up old reports
        report_agent.cleanup_old_reports()
        logger.info("Old reports cleaned up")
        
    except Exception as e:
        logger.error(f"System initialization error: {e}")


if __name__ == '__main__':
    # Initialize system
    initialize_system()
    
    # Run the application
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting Returns & Warranty Insights System on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)