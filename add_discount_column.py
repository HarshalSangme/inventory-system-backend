"""
Migration script to add 'discount' column to transaction_items table.
Run this once to update the existing SQLite database.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'inventory.db')

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("PRAGMA table_info(transaction_items)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'discount' in columns:
        print("Column 'discount' already exists in transaction_items. No migration needed.")
    else:
        cursor.execute("ALTER TABLE transaction_items ADD COLUMN discount FLOAT DEFAULT 0.0")
        conn.commit()
        print("Successfully added 'discount' column to transaction_items table.")
    
    conn.close()

if __name__ == '__main__':
    migrate()
