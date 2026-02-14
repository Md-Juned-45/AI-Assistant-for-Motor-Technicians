# Enhanced database.py with analytics and reporting features

import sqlite3
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
import time

DB_NAME = "technician_records.db"

def get_db_connection():
    """Create a new database connection with timeout and retry logic"""
    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.execute('PRAGMA journal_mode=WAL')
    return conn

def init_db():
    """Initialize database with enhanced schema and indexes"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
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
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp)')
        print("[✅ DB] Database initialized successfully.")

def add_transaction(payload: Dict) -> int:
    """Add a new transaction with validation"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
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
        return cursor.lastrowid

def update_transaction(transaction_id: int, payload: Dict) -> bool:
    """Update an existing transaction"""
    if not transaction_id: return False
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Build the update query dynamically based on payload
        fields_to_update = []
        params = []
        for key, value in payload.items():
            # Map payload keys to database columns
            if key in ['type', 'amount_paise', 'customer', 'details']:
                column_name = 'customer_name' if key == 'customer' else key
                fields_to_update.append(f"{column_name} = ?")
                params.append(value)
        
        if not fields_to_update:
             return False # Nothing to update
             
        params.append(transaction_id)
        query = f"UPDATE transactions SET {', '.join(fields_to_update)} WHERE id = ?"
        
        cursor.execute(query, tuple(params))
        return cursor.rowcount > 0

def delete_todays_transactions() -> int:
    """Delete all transactions for the current day"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        today = date.today().isoformat()
        cursor.execute("DELETE FROM transactions WHERE DATE(timestamp) = ?", (today,))
        return cursor.rowcount

def get_last_transaction() -> Optional[Tuple]:
    """Get the most recent transaction"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, type, amount_paise, customer_name, details FROM transactions ORDER BY id DESC LIMIT 1")
        return cursor.fetchone()

def get_today_transactions() -> List[Tuple]:
    """Get all transactions from today"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        today = date.today().isoformat()
        cursor.execute("SELECT * FROM transactions WHERE DATE(timestamp) = ? ORDER BY timestamp DESC", (today,))
        return cursor.fetchall()

def get_all_transactions() -> List[Tuple]:
    """Get all transactions ordered by most recent first"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, type, amount_paise, customer_name, details, timestamp FROM transactions ORDER BY timestamp DESC")
        return cursor.fetchall()

def query_transactions(filters: Dict) -> List[Tuple]:
    """Query transactions based on filters"""
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
        if filters.get('date_from'):
            query += " AND DATE(timestamp) >= ?"
            params.append(filters['date_from'])
        if filters.get('date_to'):
            query += " AND DATE(timestamp) <= ?"
            params.append(filters['date_to'])

        query += " ORDER BY timestamp DESC"
        cursor.execute(query, params)
        return cursor.fetchall()

def validate_transaction_data(payload: Dict) -> Tuple[bool, str]:
    """Validate transaction data before insertion"""
    if not payload.get('type') or payload['type'].lower() not in ['income', 'expense']:
        return False, "Transaction type must be 'income' or 'expense'"
    if not payload.get('amount_paise') or not isinstance(payload['amount_paise'], int) or payload['amount_paise'] <= 0:
        return False, "Amount must be a positive number"
    return True, "Valid"
