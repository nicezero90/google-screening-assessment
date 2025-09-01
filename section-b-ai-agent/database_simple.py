"""
Simplified Database operations for the Returns & Warranty Insights system.

This module handles all database operations using only standard library.
"""

import sqlite3
import csv
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
                    original_price REAL,
                    discount_percent REAL DEFAULT 0,
                    notes TEXT
                )
            """)
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    def load_csv_data(self, csv_path: str) -> int:
        """Load return data from CSV file into the database."""
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                records = list(reader)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM returns")
                existing_count = cursor.fetchone()[0]
                
                if existing_count == 0:
                    for record in records:
                        # Convert data types
                        if 'purchase_price' in record:
                            record['purchase_price'] = float(record['purchase_price'])
                        if 'original_price' not in record:
                            record['original_price'] = record['purchase_price']
                        
                        # Insert record
                        fields = list(record.keys())
                        values = list(record.values())
                        placeholders = ','.join(['?'] * len(fields))
                        
                        cursor.execute(f"""
                            INSERT INTO returns ({','.join(fields)})
                            VALUES ({placeholders})
                        """, values)
                    
                    conn.commit()
                    logger.info(f"Loaded {len(records)} records from {csv_path}")
                    return len(records)
                else:
                    logger.info(f"Data already exists ({existing_count} records), skipping CSV load")
                    return 0
                    
        except Exception as e:
            logger.error(f"Error loading CSV data: {e}")
            raise
    
    def insert_return(self, return_data: Dict[str, Any]) -> int:
        """Insert a new return record."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            required_fields = ['product_name', 'purchase_location', 'purchase_price', 'return_reason']
            for field in required_fields:
                if field not in return_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Prepare data with defaults
            field_mapping = {
                'product_name': return_data.get('product_name'),
                'category': return_data.get('category', 'Electronics'),
                'brand': return_data.get('brand', 'Unknown'),
                'purchase_location': return_data.get('purchase_location'),
                'purchase_price': return_data.get('purchase_price'),
                'purchase_date': return_data.get('purchase_date'),
                'return_date': return_data.get('return_date', datetime.now().isoformat()),
                'return_reason': return_data.get('return_reason'),
                'customer_id': return_data.get('customer_id', f"CUST_{datetime.now().strftime('%Y%m%d%H%M%S')}"),
                'warranty_status': return_data.get('warranty_status', 'Under Warranty'),
                'original_price': return_data.get('original_price', return_data.get('purchase_price')),
                'discount_percent': return_data.get('discount_percent', 0),
                'notes': return_data.get('notes')
            }
            
            fields = []
            values = []
            for field, value in field_mapping.items():
                if value is not None:
                    fields.append(field)
                    values.append(value)
            
            placeholders = ','.join(['?'] * len(fields))
            query = f"INSERT INTO returns ({','.join(fields)}) VALUES ({placeholders})"
            
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
        """Search return records with optional filters."""
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
        """Get analytics data for the specified time period."""
        cutoff_date = (datetime.now() - timedelta(days=days_back)).date().isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total returns in period (use date comparison for compatibility)
            cursor.execute("""
                SELECT COUNT(*), SUM(purchase_price)
                FROM returns 
                WHERE DATE(return_date) >= ?
            """, (cutoff_date,))
            result = cursor.fetchone()
            total_returns, total_loss = result[0] if result else (0, 0), result[1] if result and result[1] else 0
            
            # Returns by product
            cursor.execute("""
                SELECT product_name, COUNT(*) as count, SUM(purchase_price) as total_value
                FROM returns 
                WHERE DATE(return_date) >= ?
                GROUP BY product_name
                ORDER BY count DESC
            """, (cutoff_date,))
            product_returns = cursor.fetchall()
            
            # Returns by reason
            cursor.execute("""
                SELECT return_reason, COUNT(*) as count
                FROM returns 
                WHERE DATE(return_date) >= ?
                GROUP BY return_reason
                ORDER BY count DESC
            """, (cutoff_date,))
            reason_analysis = cursor.fetchall()
            
            return {
                'period_days': days_back,
                'total_returns': total_returns,
                'total_loss': total_loss,
                'product_breakdown': [
                    {'product': row[0], 'count': row[1], 'value': row[2]} 
                    for row in product_returns
                ],
                'reason_analysis': [
                    {'reason': row[0], 'count': row[1]} 
                    for row in reason_analysis
                ]
            }
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get overall database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM returns")
            total_records = cursor.fetchone()[0]
            
            cursor.execute("SELECT MIN(return_date), MAX(return_date) FROM returns WHERE return_date IS NOT NULL")
            date_range = cursor.fetchone()
            
            return {
                'total_records': total_records,
                'date_range': {
                    'earliest': date_range[0] if date_range and date_range[0] else None,
                    'latest': date_range[1] if date_range and date_range[1] else None
                }
            }


if __name__ == "__main__":
    # Test the database operations
    db = ReturnsDatabase()
    
    # Load sample data if empty
    stats = db.get_database_stats()
    if stats['total_records'] == 0:
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'sample_returns.csv')
        if os.path.exists(csv_path):
            db.load_csv_data(csv_path)
    
    # Print statistics
    stats = db.get_database_stats()
    print(f"Database Stats: {stats}")
    
    analytics = db.get_analytics_data(days_back=30)
    print(f"Analytics (30 days): {analytics['total_returns']} returns, ${analytics['total_loss']:.2f} loss")