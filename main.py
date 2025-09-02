#!/usr/bin/env python3
"""
Main entry point for Replit deployment.
Redirects to the section-b-ai-agent Flask application.
"""

import sys
import os

# Add the section-b-ai-agent directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'section-b-ai-agent'))

# Change to the correct directory
os.chdir(os.path.join(os.path.dirname(__file__), 'section-b-ai-agent'))

# Import and run the Flask application
from app import app

if __name__ == '__main__':
    # Run the Flask app on port 5000 for Replit
    app.run(host='0.0.0.0', port=5000, debug=False)