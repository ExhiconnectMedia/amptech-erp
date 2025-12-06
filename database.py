# database.py
import sqlite3
import os
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "erp_data.sqlite3")

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no TEXT UNIQUE,
    type TEXT,
    company_name TEXT,
    email TEXT,
    gst_number TEXT,
    address TEXT,
    event_name TEXT,
    event_location TEXT,
    stall_number TEXT,
    qty_sqm REAL,
    space_type TEXT,
    rate_per_sqm REAL,
    total_sqm_amount REAL,
    discount_amount REAL,
    extras_basic_total REAL,
    sponsorship_basic REAL,
    taxable_value REAL,
    gst_percent REAL,
    gst_amount REAL,
    cgst REAL,
    sgst REAL,
    igst REAL,
    total_with_gst REAL,
    advance_paid REAL,
    balance REAL,
    account_manager TEXT,
    status TEXT,
    billing_state TEXT,
    billing_state_code TEXT,
    company_state_code TEXT,
    created_at TEXT
);
"""

# columns we want to ensure exist (column_name: sql_type)
WANTED_COLUMNS = {
    "billing_state": "TEXT",
    "billing_state_code": "TEXT",
    "company_state_code": "TEXT",
    "type": "TEXT"  # ensure 'type' exists (Proforma/Tax/Receipt)
}

def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript(CREATE_SQL)
    conn.commit()

    # ensure additional columns exist (safe ALTER)
    cur.execute("PRAGMA table_info(invoices)")
    existing = {r["name"] for r in cur.fetchall()}
    for col, coltype in WANTED_COLUMNS.items():
        if col not in existing:
            try:
                cur.execute(f"ALTER TABLE invoices ADD COLUMN {col} {coltype}")
            except Exception:
                pass
    conn.commit()
    conn.close()

def insert_invoice(data: dict):
    conn = get_conn()
    cur = conn.cursor()
    cols = [
        "invoice_no","type","company_name","email","gst_number","address",
        "event_name","event_location","stall_number","qty_sqm","space_type",
        "rate_per_sqm","total_sqm_amount","discount_amount","extras_basic_total",
        "sponsorship_basic","taxable_value","gst_percent","gst_amount","cgst","sgst","igst",
        "total_with_gst","advance_paid","balance","account_manager","status",
        "billing_state","billing_state_code","company_state_code","created_at"
    ]
    # if DB doesn't have some columns (older DB), trim cols list to available columns
    cur.execute("PRAGMA table_info(invoices)")
    existing = [r["name"] for r in cur.fetchall()]
    cols = [c for c in cols if c in existing]
    placeholders = ",".join("?" for _ in cols)
    values = [data.get(c) for c in cols]
    cur.execute(f"INSERT INTO invoices ({','.join(cols)}) VALUES ({placeholders})", values)
    conn.commit()
    invoice_id = cur.lastrowid
    conn.close()
    return invoice_id

def fetch_all_invoices():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM invoices ORDER BY id DESC")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows

def fetch_invoice_by_id(invoice_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def record_payment(invoice_id, amount, payment_note="", paid_on=None):
    """
    Simple payment recording: update advance_paid and balance.
    (This app stores single advance_paid amount; for mult payments you'd create a payments table.)
    """
    if paid_on is None:
        paid_on = datetime.utcnow().isoformat()
    inv = fetch_invoice_by_id(invoice_id)
    if not inv:
        raise ValueError("Invoice not found")
    new_advance = (inv.get("advance_paid") or 0) + float(amount)
    new_balance = float((inv.get("total_with_gst") or 0)) - new_advance
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE invoices SET advance_paid = ?, balance = ? WHERE id = ?", (new_advance, new_balance, invoice_id))
    conn.commit()
    conn.close()
    return {"invoice_id": invoice_id, "advance_paid": new_advance, "balance": new_balance}
