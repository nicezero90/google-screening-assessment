# Section B - AI Agent Coding (RAG)

Returns & Warranty Insights system with MCP-style architecture.

## Architecture

- **Coordinator**: Routes requests between agents
- **Retrieval Agent**: Handles data ingestion and return insertions
- **Report Agent**: Generates insights and Excel reports

## User Prompt Rules

1. For returns: Start with "I'd like to return something" or similar
2. For reports: Start with "I'd like to perform data analysis" or "generate a report"
3. Provide all required details when prompted (item, reason, price, location)
4. Be specific about time ranges for analysis (e.g., "past 2 weeks")

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Run the application: `python app.py`
3. Access the web interface at `http://localhost:5000`

## Files

- `app.py`: Main Flask application
- `coordinator/`: MCP-style coordinator
- `retrieval_agent/`: Data ingestion and return handling
- `report_agent/`: Analytics and report generation