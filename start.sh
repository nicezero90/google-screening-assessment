#!/bin/bash

# Install dependencies
pip install -r requirements.txt

# Initialize database with sample data
python3 -c "
from database_simple import ReturnsDatabase
import os

# Initialize database
db = ReturnsDatabase()

# Load CSV data if database is empty
stats = db.get_database_stats()
if stats['total_records'] == 0:
    csv_path = 'data/official_sample.csv'
    if os.path.exists(csv_path):
        db.load_csv_data(csv_path)
        print('CSV data loaded successfully')
    else:
        print('CSV file not found, using empty database')
"

# Start the application
exec gunicorn --bind 0.0.0.0:$PORT app:app --timeout 120