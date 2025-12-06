# database.py
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.exc import OperationalError
import os
from datetime import datetime

def get_engine():
    # Streamlit cloud secrets expected:
    # {"db": {"dialect":"mysql", "user":"...", "password":"...", "host":"...", "port":"3306", "database":"u669232811_erp"}}
    # If not present, use local sqlite file
    try:
        import streamlit as st
        secret = st.secrets.get("db", None)
    except Exception:
        secret = None

    if secret and secret.get("dialect","").startswith("mysql"):
        user = secret["user"]
        password = secret["password"]
        host = secret["host"]
        port = secret.get("port", "3306")
        database = secret["database"]
        url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    else:
        # local sqlite fallback
        db_file = os.path.join(os.path.dirname(__file__), "erp_data.sqlite")
        url = f"sqlite:///{db_file}"

    engine = create_engine(url, echo=False, future=True)
    return engine

def ensure_tables():
    engine = get_engine()
    meta = MetaData()
    invoices = Table(
        "invoices", meta,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("invoice_no", String(100), nullable=False, unique=True),
        Column("type", String(50)),
        Column("company_name", String(255)),
        Column("email", String(255)),
        Column("gst_number", String(50)),
        Column("address", Text),
        Column("event_name", String(150)),
        Column("event_location", String(150)),
        Column("stall_number", String(50)),
        Column("qty_sqm", Float),
        Column("space_type", String(50)),
        Column("rate_per_sqm", Float),
        Column("total_sqm_amount", Float),
        Column("discount_amount", Float),
        Column("extras_basic_total", Float),
        Column("sponsorship_basic", Float),
        Column("taxable_value", Float),
        Column("gst_percent", Float),
        Column("gst_amount", Float),
        Column("cgst", Float),
        Column("sgst", Float),
        Column("igst", Float),
        Column("total_with_gst", Float),
        Column("advance_paid", Float),
        Column("balance", Float),
        Column("account_manager", String(100)),
        Column("status", String(100)),
        Column("created_at", DateTime, default=datetime.utcnow)
    )
    try:
        meta.create_all(engine)
    except OperationalError as e:
        raise
    return engine, invoices
