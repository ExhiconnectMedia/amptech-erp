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
    address2 TEXT,
    address3 TEXT,
    pin TEXT,
    state TEXT,
    billing_state TEXT,
    billing_state_code TEXT,
    company_state_code TEXT,
    event_name TEXT,
    event_location TEXT,
    event_month_year TEXT,
    event_dates TEXT,
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
    remarks TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER,
    amount REAL,
    mode TEXT,
    note TEXT,
    paid_on TEXT
);
"""

def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def ensure_tables():
    conn = get_conn()
    cur = conn.cursor()
    cur.executescript(CREATE_SQL)
    conn.commit()
    conn.close()

def insert_invoice(data: dict):
    conn = get_conn()
    cur = conn.cursor()
    cols = [
        "invoice_no","type","company_name","email","gst_number","address","address2","address3","pin","state",
        "billing_state","billing_state_code","company_state_code","event_name","event_location","event_month_year","event_dates","stall_number",
        "qty_sqm","space_type","rate_per_sqm","total_sqm_amount","discount_amount","extras_basic_total","sponsorship_basic",
        "taxable_value","gst_percent","gst_amount","cgst","sgst","igst","total_with_gst","advance_paid","balance",
        "account_manager","status","remarks","created_at"
    ]
    # ensure we only insert columns that exist (for compatibility)
    cur.execute("PRAGMA table_info(invoices)")
    existing = [r["name"] for r in cur.fetchall()]
    cols_use = [c for c in cols if c in existing]
    placeholders = ",".join("?" for _ in cols_use)
    values = [data.get(c) for c in cols_use]
    cur.execute(f"INSERT INTO invoices ({','.join(cols_use)}) VALUES ({placeholders})", values)
    conn.commit()
    invoice_id = cur.lastrowid
    conn.close()
    return invoice_id

def fetch_all_invoices():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM invoices ORDER BY id DESC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def fetch_invoice_by_id(invoice_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def record_payment(invoice_id, amount, mode="Other", note=""):
    conn = get_conn()
    cur = conn.cursor()
    paid_on = datetime.utcnow().isoformat()
    cur.execute("INSERT INTO payments (invoice_id, amount, mode, note, paid_on) VALUES (?,?,?,?,?)",
                (invoice_id, amount, mode, note, paid_on))
    # update invoice's advance_paid & balance
    cur.execute("SELECT advance_paid, total_with_gst FROM invoices WHERE id = ?", (invoice_id,))
    row = cur.fetchone()
    if row:
        prev_advance = row["advance_paid"] or 0.0
        total = row["total_with_gst"] or 0.0
        new_advance = prev_advance + float(amount)
        new_balance = round(total - new_advance, 2)
        cur.execute("UPDATE invoices SET advance_paid = ?, balance = ? WHERE id = ?", (new_advance, new_balance, invoice_id))
    conn.commit()
    conn.close()
    return {"invoice_id": invoice_id, "advance_paid": new_advance, "balance": new_balance}

def fetch_payments_for_invoice(invoice_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM payments WHERE invoice_id = ? ORDER BY paid_on DESC", (invoice_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def export_all_invoices_csv():
    rows = fetch_all_invoices()
    # header as requested (include all columns)
    if not rows:
        return ""
    headers = list(rows[0].keys())
    lines = [",".join(headers)]
    for r in rows:
        vals = []
        for h in headers:
            v = r.get(h)
            if v is None:
                vals.append("")
            else:
                s = str(v).replace('"','""')
                if "," in s or "\n" in s:
                    vals.append(f'"{s}"')
                else:
                    vals.append(s)
        lines.append(",".join(vals))
    return "\n".join(lines)
