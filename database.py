# Enhanced database.py with analytics and reporting features

import sqlite3
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
import time

DB_NAME = "technician_records.db"

def get_db_connection():
    """Create a new database connection with timeout and retry logic"""
    conn = sqlite3.connect(DB_NAME, timeout=10)  # Set timeout to 10 seconds
    conn.execute('PRAGMA journal_mode=WAL')  # Use Write-Ahead Logging for better concurrency
    return conn

def init_db():
    """Initialize database with enhanced schema and indexes"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Main transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
                amount_paise INTEGER NOT NULL CHECK(amount_paise > 0),
                customer_name TEXT,
                details TEXT,
                timestamp DATETIME NOT NULL
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_customer ON transactions(customer_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)')
        
        # Business insights table (for future analytics)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS business_insights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                insight_date DATE NOT NULL,
                total_income_paise INTEGER DEFAULT 0,
                total_expense_paise INTEGER DEFAULT 0,
                transaction_count INTEGER DEFAULT 0,
                top_customer TEXT,
                notes TEXT,
                UNIQUE(insight_date)
            )
        ''')
        
        print("[✅ DB] Enhanced database initialized successfully with analytics support")

def add_transaction(payload: Dict) -> int:
    """Add a new transaction with validation"""
    for attempt in range(3):  # Retry up to 3 times
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Validate required fields
                if not payload.get('type') or not payload.get('amount_paise'):
                    raise ValueError("Transaction type and amount are required")
                
                cursor.execute('''
                    INSERT INTO transactions (type, amount_paise, customer_name, details, timestamp) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    payload.get('type').lower(),
                    payload.get('amount_paise'),
                    payload.get('customer'),
                    payload.get('details'),
                    datetime.now()
                ))
                
                transaction_id = cursor.lastrowid
                conn.commit()  # Explicit commit
                update_daily_insights()  # Update insights after commit
                return transaction_id
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < 2:
                time.sleep(0.1)  # Wait before retrying
                continue
            raise e

def update_transaction(transaction_id: int, payload: Dict) -> bool:
    """Update an existing transaction"""
    if not transaction_id:
        return False
        
    for attempt in range(3):
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE transactions 
                    SET type = ?, amount_paise = ?, customer_name = ?, details = ? 
                    WHERE id = ?
                ''', (
                    payload.get('type').lower(),
                    payload.get('amount_paise'),
                    payload.get('customer'),
                    payload.get('details'),
                    transaction_id
                ))
                
                update_daily_insights()
                return cursor.rowcount > 0
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < 2:
                time.sleep(0.1)
                continue
            raise e

def delete_todays_transactions() -> int:
    """Delete all transactions for the current day"""
    for attempt in range(3):
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                today = date.today().isoformat()
                cursor.execute('''
                    DELETE FROM transactions 
                    WHERE DATE(timestamp) = ?
                ''', (today,))
                deleted_count = cursor.rowcount
                update_daily_insights()
                return deleted_count
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < 2:
                time.sleep(0.1)
                continue
            raise e

def get_last_transaction() -> Optional[Tuple]:
    """Get the most recent transaction"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, type, amount_paise, customer_name, details 
            FROM transactions 
            ORDER BY id DESC 
            LIMIT 1
        ''')
        return cursor.fetchone()

def get_today_transactions() -> List[Tuple]:
    """Get all transactions from today for dashboard stats"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        today = date.today().isoformat()
        cursor.execute('''
            SELECT * FROM transactions 
            WHERE DATE(timestamp) = ? 
            ORDER BY timestamp DESC
        ''', (today,))
        return cursor.fetchall()

def get_all_transactions() -> List[Tuple]:
    """Get all transactions ordered by most recent first"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, type, amount_paise, customer_name, details, timestamp
            FROM transactions 
            ORDER BY timestamp DESC
        ''')
        return cursor.fetchall()

def query_transactions(filters: Dict) -> List[Tuple]:
    """Enhanced query function with better search capabilities"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        query = "SELECT id, type, amount_paise, customer_name, details, timestamp FROM transactions WHERE 1=1"
        params = []
        
        if filters.get('customer_name'):
            query += " AND LOWER(customer_name) LIKE LOWER(?)"
            params.append(f"%{filters['customer_name']}%")
        
        if filters.get('details_keyword'):
            query += " AND LOWER(details) LIKE LOWER(?)"
            params.append(f"%{filters['details_keyword']}%")
        
        if filters.get('type'):
            query += " AND type = ?"
            params.append(filters['type'].lower())
        
        if filters.get('min_amount_paise'):
            query += " AND amount_paise >= ?"
            params.append(filters['min_amount_paise'])
            
        if filters.get('max_amount_paise'):
            query += " AND amount_paise <= ?"
            params.append(filters['max_amount_paise'])
        
        if filters.get('date_from'):
            query += " AND DATE(timestamp) >= ?"
            params.append(filters['date_from'])
            
        if filters.get('date_to'):
            query += " AND DATE(timestamp) <= ?"
            params.append(filters['date_to'])
        
        query += " ORDER BY timestamp DESC"
        
        if filters.get('limit'):
            query += f" LIMIT {int(filters['limit'])}"
        
        cursor.execute(query, params)
        return cursor.fetchall()

def get_business_summary(days: int = 30) -> Dict:
    """Get comprehensive business summary for the last N days"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_transactions,
                SUM(CASE WHEN type = 'income' THEN amount_paise ELSE 0 END) as total_income_paise,
                SUM(CASE WHEN type = 'expense' THEN amount_paise ELSE 0 END) as total_expense_paise,
                COUNT(CASE WHEN type = 'income' THEN 1 END) as income_count,
                COUNT(CASE WHEN type = 'expense' THEN 1 END) as expense_count
            FROM transactions 
            WHERE timestamp >= datetime('now', ?)
        ''', (f'-{days} days',))
        
        summary = cursor.fetchone()
        
        cursor.execute('''
            SELECT customer_name, SUM(amount_paise) as total_amount, COUNT(*) as job_count
            FROM transactions 
            WHERE type = 'income' AND customer_name IS NOT NULL 
                AND timestamp >= datetime('now', ?)
            GROUP BY customer_name 
            ORDER BY total_amount DESC 
            LIMIT 5
        ''', (f'-{days} days',))
        
        top_customers = cursor.fetchall()
        
        cursor.execute('''
            SELECT 
                DATE(timestamp) as day,
                SUM(CASE WHEN type = 'income' THEN amount_paise ELSE 0 END) as daily_income,
                SUM(CASE WHEN type = 'expense' THEN amount_paise ELSE 0 END) as daily_expense
            FROM transactions 
            WHERE timestamp >= datetime('now', '-7 days')
            GROUP BY DATE(timestamp)
            ORDER BY day DESC
        ''')
        
        daily_trends = cursor.fetchall()
        
        return {
            'period_days': days,
            'total_transactions': summary[0] or 0,
            'total_income_paise': summary[1] or 0,
            'total_expense_paise': summary[2] or 0,
            'income_count': summary[3] or 0,
            'expense_count': summary[4] or 0,
            'net_profit_paise': (summary[1] or 0) - (summary[2] or 0),
            'top_customers': top_customers,
            'daily_trends': daily_trends
        }

def update_daily_insights():
    """Update daily business insights (called after each transaction)"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        today = date.today().isoformat()
        
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN type = 'income' THEN amount_paise ELSE 0 END) as income,
                SUM(CASE WHEN type = 'expense' THEN amount_paise ELSE 0 END) as expense,
                COUNT(*) as count
            FROM transactions 
            WHERE DATE(timestamp) = ?
        ''', (today,))
        
        totals = cursor.fetchone()
        
        cursor.execute('''
            SELECT customer_name, SUM(amount_paise) as total
            FROM transactions 
            WHERE type = 'income' AND DATE(timestamp) = ? AND customer_name IS NOT NULL
            GROUP BY customer_name 
            ORDER BY total DESC 
            LIMIT 1
        ''', (today,))
        
        top_customer_result = cursor.fetchone()
        top_customer = top_customer_result[0] if top_customer_result else None
        
        cursor.execute('''
            INSERT OR REPLACE INTO business_insights 
            (insight_date, total_income_paise, total_expense_paise, transaction_count, top_customer)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            today,
            totals[0] or 0,
            totals[1] or 0, 
            totals[2] or 0,
            top_customer
        ))

def get_customer_history(customer_name: str) -> List[Tuple]:
    """Get complete transaction history for a specific customer"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, type, amount_paise, customer_name, details, timestamp
            FROM transactions 
            WHERE LOWER(customer_name) LIKE LOWER(?)
            ORDER BY timestamp DESC
        ''', (f"%{customer_name}%",))
        return cursor.fetchall()

def search_transactions_by_keyword(keyword: str) -> List[Tuple]:
    """Search transactions by keyword in details or customer name"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, type, amount_paise, customer_name, details, timestamp
            FROM transactions 
            WHERE LOWER(details) LIKE LOWER(?) 
               OR LOWER(customer_name) LIKE LOWER(?)
            ORDER BY timestamp DESC
        ''', (f"%{keyword}%", f"%{keyword}%"))
        return cursor.fetchall()

def get_monthly_report(year: int, month: int) -> Dict:
    """Generate detailed monthly business report"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                type,
                COUNT(*) as count,
                SUM(amount_paise) as total_paise,
                AVG(amount_paise) as avg_paise
            FROM transactions 
            WHERE strftime('%Y', timestamp) = ? AND strftime('%m', timestamp) = ?
            GROUP BY type
        ''', (str(year), f"{month:02d}"))
        
        monthly_data = {row[0]: {
            'count': row[1], 
            'total_paise': row[2], 
            'avg_paise': row[3]
        } for row in cursor.fetchall()}
        
        return {
            'year': year,
            'month': month,
            'income_data': monthly_data.get('income', {'count': 0, 'total_paise': 0, 'avg_paise': 0}),
            'expense_data': monthly_data.get('expense', {'count': 0, 'total_paise': 0, 'avg_paise': 0}),
        }

def backup_database(backup_path: str = None) -> str:
    """Create a backup of the database"""
    if not backup_path:
        backup_path = f"backup_technician_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    with get_db_connection() as source:
        with sqlite3.connect(backup_path) as backup:
            source.backup(backup)
    
    return backup_path

def validate_transaction_data(payload: Dict) -> Tuple[bool, str]:
    """Validate transaction data before insertion"""
    if not payload.get('type'):
        return False, "Transaction type is required"
    
    if payload['type'].lower() not in ['income', 'expense']:
        return False, "Transaction type must be 'income' or 'expense'"
    
    if not payload.get('amount_paise') or payload['amount_paise'] <= 0:
        return False, "Amount must be greater than 0"
    
    if payload.get('customer') and len(payload['customer']) > 100:
        return False, "Customer name too long (max 100 characters)"
    
    if payload.get('details') and len(payload['details']) > 500:
        return False, "Details too long (max 500 characters)"
    
    return True, "Valid"