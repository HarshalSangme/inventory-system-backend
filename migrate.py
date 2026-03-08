import sqlite3

db_path = r'c:\Users\HarshalSangame\Documents\JOTA\inventory-system-backend\inventory.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# ── Create ledger_entries table ──────────────────────────────
cursor.execute('''
CREATE TABLE IF NOT EXISTS ledger_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    partner_id INTEGER,
    transaction_id INTEGER,
    payment_id INTEGER,
    amount FLOAT,
    type VARCHAR,
    date DATETIME,
    description VARCHAR,
    FOREIGN KEY(partner_id) REFERENCES partners(id),
    FOREIGN KEY(transaction_id) REFERENCES transactions(id),
    FOREIGN KEY(payment_id) REFERENCES payments(id)
)
''')
print("ledger_entries table ensured.")

# ── Create payments table ────────────────────────────────────
cursor.execute('''
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER,
    partner_id INTEGER,
    amount FLOAT NOT NULL,
    date DATETIME DEFAULT CURRENT_TIMESTAMP,
    payment_method VARCHAR DEFAULT 'Cash',
    channel VARCHAR DEFAULT 'cash',
    reference_id VARCHAR,
    notes VARCHAR,
    FOREIGN KEY(transaction_id) REFERENCES transactions(id),
    FOREIGN KEY(partner_id) REFERENCES partners(id)
)
''')
print("payments table ensured.")

# ── Alter payments table: add extra columns ──────────────────
for col, definition in [
    ("channel",      "VARCHAR DEFAULT 'cash'"),
    ("reference_id", "VARCHAR"),
    ("notes",        "VARCHAR"),
]:
    try:
        cursor.execute(f"ALTER TABLE payments ADD COLUMN {col} {definition}")
        print(f"  Added payments.{col}")
    except Exception as e:
        print(f"  payments.{col}: {e}")

# ── Alter transactions: add payment tracking columns ──────────
try:
    cursor.execute("ALTER TABLE transactions ADD COLUMN amount_paid FLOAT DEFAULT 0.0")
    print("Added transactions.amount_paid")
except Exception as e:
    print(f"transactions.amount_paid: {e}")

try:
    # DEFAULT 'unpaid' — fixed from old incorrect 'paid' default
    cursor.execute("ALTER TABLE transactions ADD COLUMN payment_status VARCHAR DEFAULT 'unpaid'")
    print("Added transactions.payment_status")
except Exception as e:
    print(f"transactions.payment_status: {e}")

# ── Data fix: any row with status='paid' but amount_paid=0 ────
cursor.execute("""
    UPDATE transactions
    SET payment_status = 'unpaid'
    WHERE payment_status = 'paid'
      AND (amount_paid IS NULL OR amount_paid = 0.0)
""")
fixed = cursor.rowcount
if fixed > 0:
    print(f"Fixed {fixed} transaction(s) with incorrect 'paid' status and 0 amount_paid -> set to 'unpaid'")
else:
    print("No corrupt payment_status records found.")

conn.commit()
conn.close()
print("\nMigration done.")

