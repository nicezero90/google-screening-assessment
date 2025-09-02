"""
Database operations for the Returns & Warranty Insights system.

This module handles all database operations including schema creation,
data ingestion from CSV, and CRUD operations for returns data.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReturnsDatabase:
    """Database manager for returns and warranty data."""
    
    def __init__(self, db_path: str = "returns_warranty.db"):
        """Initialize database connection and create tables if needed."""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create returns table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS returns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_name TEXT NOT NULL,
                    category TEXT,
                    brand TEXT,
                    purchase_location TEXT NOT NULL,
                    purchase_price REAL NOT NULL,
                    purchase_date DATE,
                    return_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    return_reason TEXT NOT NULL,
                    customer_id TEXT,
                    warranty_status TEXT,
                    original_price REAL,  -- calculated original price before discount
                    discount_percent REAL DEFAULT 0,
                    notes TEXT
                )
            """)
            
            # Create embeddings table for RAG
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS return_embeddings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    return_id INTEGER NOT NULL,
                    text_content TEXT NOT NULL,
                    embedding BLOB,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (return_id) REFERENCES returns (id)
                )
            """)
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    def load_csv_data(self, csv_path: str) -> int:
        """
        Load return data from CSV file into the database.
        
        Args:
            csv_path: Path to the CSV file
            
        Returns:
            Number of records loaded
        """
        try:
            # Read CSV file
            df = pd.read_csv(csv_path)
            
            # Convert date columns
            if 'purchase_date' in df.columns:
                df['purchase_date'] = pd.to_datetime(df['purchase_date']).dt.date
            if 'return_date' in df.columns:
                df['return_date'] = pd.to_datetime(df['return_date'])
            
            # Add original_price column if not exists (same as purchase_price initially)
            if 'original_price' not in df.columns:
                df['original_price'] = df['purchase_price']
            
            # Load into database
            with sqlite3.connect(self.db_path) as conn:
                # Check if data already exists to avoid duplicates
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM returns")
                existing_count = cursor.fetchone()[0]
                
                if existing_count == 0:
                    records_loaded = df.to_sql('returns', conn, if_exists='append', index=False)
                    logger.info(f"Loaded {len(df)} records from {csv_path}")
                    return len(df)
                else:
                    logger.info(f"Data already exists ({existing_count} records), skipping CSV load")
                    return 0
                    
        except Exception as e:
            logger.error(f"Error loading CSV data: {e}")
            raise
    
    def insert_return(self, return_data: Dict[str, Any]) -> int:
        """
        Insert a new return record.
        
        Args:
            return_data: Dictionary containing return information
            
        Returns:
            ID of the inserted record
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Prepare data
            fields = []
            values = []
            placeholders = []
            
            required_fields = ['product_name', 'purchase_location', 'purchase_price', 'return_reason']
            for field in required_fields:
                if field not in return_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Map all provided fields
            field_mapping = {
                'product_name': return_data.get('product_name'),
                'category': return_data.get('category', 'Electronics'),
                'brand': return_data.get('brand', 'Unknown'),
                'purchase_location': return_data.get('purchase_location'),
                'purchase_price': return_data.get('purchase_price'),
                'purchase_date': return_data.get('purchase_date'),
                'return_date': return_data.get('return_date', datetime.now()),
                'return_reason': return_data.get('return_reason'),
                'customer_id': return_data.get('customer_id', f"CUST_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
                'warranty_status': return_data.get('warranty_status', 'Under Warranty'),
                'original_price': return_data.get('original_price', return_data.get('purchase_price')),
                'discount_percent': return_data.get('discount_percent', 0),
                'notes': return_data.get('notes')
            }
            
            for field, value in field_mapping.items():
                if value is not None:
                    fields.append(field)
                    values.append(value)
                    placeholders.append('?')
            
            query = f"""
                INSERT INTO returns ({', '.join(fields)})
                VALUES ({', '.join(placeholders)})
            """
            
            cursor.execute(query, values)
            return_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"Inserted return record with ID: {return_id}")
            return return_id
    
    def get_return_by_id(self, return_id: int) -> Optional[Dict[str, Any]]:
        """Get return record by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM returns WHERE id = ?", (return_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    def search_returns(self, filters: Dict[str, Any] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Search return records with optional filters.
        
        Args:
            filters: Dictionary of filter conditions
            limit: Maximum number of records to return
            
        Returns:
            List of return records
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM returns"
            params = []
            
            if filters:
                conditions = []
                
                if 'product_name' in filters:
                    conditions.append("product_name LIKE ?")
                    params.append(f"%{filters['product_name']}%")
                
                if 'category' in filters:
                    conditions.append("category = ?")
                    params.append(filters['category'])
                
                if 'brand' in filters:
                    conditions.append("brand = ?")
                    params.append(filters['brand'])
                
                if 'return_reason' in filters:
                    conditions.append("return_reason LIKE ?")
                    params.append(f"%{filters['return_reason']}%")
                
                if 'date_from' in filters:
                    conditions.append("return_date >= ?")
                    params.append(filters['date_from'])
                
                if 'date_to' in filters:
                    conditions.append("return_date <= ?")
                    params.append(filters['date_to'])
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY return_date DESC"
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
    
    def get_analytics_data(self, days_back: int = 14) -> Dict[str, Any]:
        """
        Get analytics data for the specified time period.
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            Dictionary containing analytics data
        """
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total returns in period
            cursor.execute("""
                SELECT COUNT(*), SUM(purchase_price)
                FROM returns 
                WHERE return_date >= ?
            """, (cutoff_date,))
            total_returns, total_loss = cursor.fetchone()
            
            # Returns by product
            cursor.execute("""
                SELECT product_name, COUNT(*) as count, SUM(purchase_price) as total_value
                FROM returns 
                WHERE return_date >= ?
                GROUP BY product_name
                ORDER BY count DESC
            """, (cutoff_date,))
            product_returns = cursor.fetchall()
            
            # Returns by reason
            cursor.execute("""
                SELECT return_reason, COUNT(*) as count
                FROM returns 
                WHERE return_date >= ?
                GROUP BY return_reason
                ORDER BY count DESC
            """, (cutoff_date,))
            reason_analysis = cursor.fetchall()
            
            # Daily trend
            cursor.execute("""
                SELECT DATE(return_date) as date, COUNT(*) as count
                FROM returns 
                WHERE return_date >= ?
                GROUP BY DATE(return_date)
                ORDER BY date
            """, (cutoff_date,))
            daily_trend = cursor.fetchall()
            
            # Previous period for comparison
            prev_cutoff = cutoff_date - timedelta(days=days_back)
            cursor.execute("""
                SELECT COUNT(*)
                FROM returns 
                WHERE return_date >= ? AND return_date < ?
            """, (prev_cutoff, cutoff_date))
            prev_returns = cursor.fetchone()[0]
            
            return {
                'period_days': days_back,
                'total_returns': total_returns or 0,
                'total_loss': total_loss or 0,
                'previous_period_returns': prev_returns,
                'trend': 'increasing' if (total_returns or 0) > prev_returns else 'decreasing',
                'product_breakdown': [
                    {'product': row[0], 'count': row[1], 'value': row[2]} 
                    for row in product_returns
                ],
                'reason_analysis': [
                    {'reason': row[0], 'count': row[1]} 
                    for row in reason_analysis
                ],
                'daily_trend': [
                    {'date': row[0], 'count': row[1]} 
                    for row in daily_trend
                ]
            }
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get overall database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total records
            cursor.execute("SELECT COUNT(*) FROM returns")
            total_records = cursor.fetchone()[0]
            
            # Date range
            cursor.execute("""
                SELECT MIN(return_date), MAX(return_date)
                FROM returns
                WHERE return_date IS NOT NULL
            """)
            date_range = cursor.fetchone()
            
            # Top categories
            cursor.execute("""
                SELECT category, COUNT(*) as count
                FROM returns
                GROUP BY category
                ORDER BY count DESC
                LIMIT 5
            """)
            top_categories = cursor.fetchall()
            
            return {
                'total_records': total_records,
                'date_range': {
                    'earliest': date_range[0] if date_range[0] else None,
                    'latest': date_range[1] if date_range[1] else None
                },
                'top_categories': [
                    {'category': row[0], 'count': row[1]} 
                    for row in top_categories
                ]
            }


def init_sample_data():
    """Initialize database with sample data if it doesn't exist."""
    db = ReturnsDatabase()
    
    # Check if we need to load sample data
    stats = db.get_database_stats()
    if stats['total_records'] == 0:
        # Load sample CSV data
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'sample_returns.csv')
        if os.path.exists(csv_path):
            records_loaded = db.load_csv_data(csv_path)
            logger.info(f"Initialized database with {records_loaded} sample records")
        else:
            logger.warning(f"Sample CSV file not found at {csv_path}")
    
    return db


if __name__ == "__main__":
    # Test the database operations
    db = init_sample_data()
    
    # Print statistics
    stats = db.get_database_stats()
    print(f"Database Stats: {stats}")
    
    # Test analytics
    analytics = db.get_analytics_data(days_back=30)
    print(f"Analytics (30 days): {analytics['total_returns']} returns, ${analytics['total_loss']:.2f} loss")