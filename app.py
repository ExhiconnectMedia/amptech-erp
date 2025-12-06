# app.py
import streamlit as st
from datetime import datetime
from database import ensure_tables, insert_invoice, fetch_all_invoices, fetch_invoice_by_id
from invoice_template import render_html
import base64, io

st.set_page_config(page_title="Amptech ERP", layout="wide")
ensure_tables()

# Company config and users from secrets (or defaults)
company_cfg = {"name":"Exhiconnect Media Pvt Ltd","address":"Opp. Vikas Bhavan, Sidcul, Haridwar","gstin":""}
try:
    if st.secrets.get("company"):
        company_cfg.update(st.secrets.get("company"))
except Exception:
    pass

DEFAULT_USERS = {"bhavik":"12345","chirag":"12345","karishma":"12345"}
try:
    users = dict(st.secrets.get("users", DEFAULT_USERS))
except Exception:
    users = DEFAULT_USERS

def login_widget():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user = None
    if not st.session_state.logged_in:
        with st.sidebar.form("login"):
            st.write("Login")
            user = st.selectbox("User", list(users.keys()))
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if users.get(user) == pwd:
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.success("Logged in as " + user)
                    st.experimental_rerun()
                else:
                    st.error("Invalid credentials")
    else:
        st.sidebar.write("Logged in as", st.session_state.user)
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.experimental_rerun()

login_widget()
if not st.session_state.logged_in:
    st.stop()

st.title("Amptech ERP (Streamlit)")

col1, col2, col3 = st.columns([2,1,1])
with col1:
    if st.button("Create New Invoice"):
        st.session_state.show_create = True
with col2:
    if st.button("Load Demo Data"):
        # create 3 demo invoices
        for i in range(1,4):
            invoice_no = f"DEMO-{datetime.utcnow().strftime('%y%m%d%H%M%S')}-{i}"
            data = dict(
                invoice_no=invoice_no,
                type="ProForma",
                company_name=f"Demo Company {i}",
                email="demo@example.com",
                gst_number="",
                address="Demo Address",
                event_name="Amptech India Expo",
                event_location="Vadodara",
                stall_number=str(100+i),
                qty_sqm=9,
                space_type="Shell",
                rate_per_sqm=8000,
                total_sqm_amount=9*8000,
                discount_amount=0,
                extras_basic_total=0,
                sponsorship_basic=0,
                taxable_value=9*8000,
                gst_percent=18,
                gst_amount=(9*8000)*0.18,
                cgst=((9*8000)*0.18)/2,
                sgst=((9*8000)*0.18)/2,
                igst=0,
                total_with_gst=(9*8000)*(1+0.18),
                advance_paid=0,
                balance=(9*8000)*(1+0.18),
                account_manager=st.session_state.user,
                status="Pending",
                created_at=datetime.utcnow().isoformat()
            )
            insert_invoice(data)
        st.success("Inserted demo invoices.")
with col3:
    if st.button("Refresh"):
        st.experimental_rerun()

# Create invoice form
if st.session_state.get("show_create", False):
    st.subheader("Create New Invoice")
    with st.form("invoice_create"):
        company_name = st.text_input("Company Name", "")
        address = st.text_area("Address", "")
        gst_number = st.text_input("GST Number", "")
        email = st.text_input("Email")
        event_name = st.selectbox("Event Name", ["Amptech India Expo", "Auto India Expo", "Career Bonanza Expo"])
        event_location = st.selectbox("Event Location", ["Vadodara","Haridwar","Indore","Ahmedabad","Surat"])
        stall_number = st.text_input("Stall Number")
        space_type = st.selectbox("Space Type", ["Shell","Bare"])
        qty_sqm = st.number_input("Qty (sqm)", min_value=0.0, value=9.0, step=0.5)
        rate_per_sqm = st.number_input("Rate per sqm (₹)", min_value=0.0, value=8000.0, step=100.0)
        discount_amount = st.number_input("Discount Amount (₹)", min_value=0.0, value=0.0, step=1.0)
        extras_basic_total = st.number_input("Extras Basic Total (₹)", min_value=0.0, value=0.0)
        sponsorship_basic = st.number_input("Sponsorship Basic (₹)", min_value=0.0, value=0.0)
        gst_percent = st.number_input("GST %", min_value=0.0, value=18.0)
        advance_paid = st.number_input("Advance Paid (₹)", min_value=0.0, value=0.0)
        account_manager = st.selectbox("Account Manager", ["Bhavik","Chirag","Karishma"])
        status = st.selectbox("Status", ["Pending","Clear","Complimentary","Media Partner","Cancelled","Defaulted"])
        submit = st.form_submit_button("Save & Render Invoice")

    if submit:
        total_sqm_amount = round(qty_sqm * rate_per_sqm, 2)
        taxable_value = round(total_sqm_amount - discount_amount + extras_basic_total + sponsorship_basic, 2)
        gst_amount = round(taxable_value * gst_percent / 100.0, 2)
        cgst = round(gst_amount/2, 2)
        sgst = round(gst_amount/2, 2)
        igst = 0.0
        total_with_gst = round(taxable_value + gst_amount, 2)
        balance = round(total_with_gst - advance_paid, 2)
        invoice_no = f"PRO-{datetime.utcnow().year}-{str(abs(hash(datetime.utcnow())))[0:6]}"

        data = dict(
            invoice_no=invoice_no,
            type="ProForma",
            company_name=company_name,
            email=email,
            gst_number=gst_number,
            address=address,
            event_name=event_name,
            event_location=event_location,
            stall_number=stall_number,
            qty_sqm=qty_sqm,
            space_type=space_type,
            rate_per_sqm=rate_per_sqm,
            total_sqm_amount=total_sqm_amount,
            discount_amount=discount_amount,
            extras_basic_total=extras_basic_total,
            sponsorship_basic=sponsorship_basic,
            taxable_value=taxable_value,
            gst_percent=gst_percent,
            gst_amount=gst_amount,
            cgst=cgst,
            sgst=sgst,
            igst=igst,
            total_with_gst=total_with_gst,
            advance_paid=advance_paid,
            balance=balance,
            account_manager=account_manager,
            status=status,
            created_at=datetime.utcnow().isoformat()
        )

        invoice_id = insert_invoice(data)
        st.success("Invoice saved: " + invoice_no)
        # Render HTML invoice
        html = render_html(data, company_cfg)
        st.markdown("### Invoice Preview (rendered HTML)")
        st.components.v1.html(html, height=800, scrolling=True)

        # Download HTML as file
        b = html.encode("utf-8")
        st.download_button("Download invoice as HTML", data=b, file_name=f"{invoice_no}.html", mime="text/html")

        st.info("To get a PDF: open the downloaded HTML in your browser and use Print → Save as PDF (or right-click on preview and Print).")

# Show list of invoices
st.subheader("Invoices")
rows = fetch_all_invoices()
if rows:
    import pandas as pd
    df = pd.DataFrame(rows)
    st.dataframe(df[["id","invoice_no","company_name","event_name","total_with_gst","balance","status","created_at"]].rename(columns={
        "id":"ID","invoice_no":"Invoice","company_name":"Company","event_name":"Event","total_with_gst":"Total (₹)","balance":"Balance (₹)","status":"Status","created_at":"Date"
    }))
    sel = st.number_input("View invoice ID", min_value=0, value=0, step=1)
    if st.button("Render Selected Invoice"):
        if sel>0:
            inv = fetch_invoice_by_id(sel)
            if inv:
                html = render_html(inv, company_cfg)
                st.components.v1.html(html, height=800, scrolling=True)
                st.download_button("Download HTML", data=html.encode("utf-8"), file_name=f"{inv['invoice_no']}.html", mime="text/html")
            else:
                st.warning("Invoice ID not found")
else:
    st.info("No invoices yet.")
