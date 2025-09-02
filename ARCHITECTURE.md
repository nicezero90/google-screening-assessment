# AI Agent RAG System Architecture

## Overview
A 2-Agent MCP-style system for Returns & Warranty Insights with natural language interface.

## System Components

### 1. MCP-Style Coordinator (`coordinator/`)
- **Purpose**: Route user requests to appropriate agents
- **Responsibilities**:
  - Parse natural language prompts
  - Determine intent (return submission vs. analytics request)
  - Route to Retrieval or Report Agent
  - Orchestrate multi-agent workflows

### 2. Retrieval Agent (`retrieval_agent/`)
- **Purpose**: Handle data operations and return insertions
- **Responsibilities**:
  - Ingest and index CSV data for RAG
  - Accept NL prompts to insert new returns
  - Validate and extract return details from conversation
  - Store data in SQLite database
  - Provide confirmation with item details

### 3. Report Agent (`report_agent/`)
- **Purpose**: Generate insights and reports
- **Responsibilities**:
  - Accept NL prompts for data analysis
  - Query database for insights
  - Generate natural language summaries
  - Create downloadable Excel reports
  - Provide trend analysis and recommendations

## Data Flow

```
User Input (Natural Language)
        ↓
   Coordinator
   /         \
Retrieval    Report
 Agent       Agent
   ↓           ↓
Database ←→ Analytics
   ↓           ↓
Response ←  Excel Report
```

## Technology Stack

- **Backend**: Python Flask
- **Database**: SQLite with pandas integration
- **LLM**: OpenAI GPT-4 or Anthropic Claude
- **Data Processing**: pandas, numpy
- **Report Generation**: openpyxl, xlsxwriter
- **Frontend**: HTML/CSS/JavaScript (GPT-like UI)
- **Deployment**: Railway/Render/Vercel

## Database Schema

```sql
CREATE TABLE returns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    purchase_location TEXT NOT NULL,
    purchase_price REAL NOT NULL,
    return_reason TEXT NOT NULL,
    return_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    customer_id TEXT,
    category TEXT,
    brand TEXT,
    purchase_date DATE,
    warranty_status TEXT
);
```

## User Interaction Rules

### For Returns:
1. Start with: "I'd like to return something" or similar
2. System will ask for: product, reason, location, price
3. System calculates original price if discount mentioned
4. Confirmation provided with all details

### For Reports:
1. Start with: "I'd like to perform data analysis" or "generate a report"
2. Specify what information needed
3. Include time ranges if relevant
4. System provides insights and optional Excel download

## API Endpoints

- `POST /chat` - Main chat interface
- `GET /download/<report_id>` - Download Excel reports
- `GET /health` - System health check
- `POST /upload_csv` - Upload initial data (admin)

## Security & Validation

- Input sanitization for all user inputs
- SQL injection prevention
- Rate limiting on API calls
- Secure file handling for uploads/downloads
- Environment variables for API keys