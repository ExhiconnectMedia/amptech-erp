# app.py
import streamlit as st
from database import ensure_tables, get_engine
from sqlalchemy import insert, select
from invoice_template import generate_invoice_pdf
import pandas as pd
import base64, io, smtplib
from email.message import EmailMessage
from datetime import datetime

st.set_page_config(page_title="Amptech ERP", layout="wide")

# --- Setup DB ---
engine, invoices_table = ensure_tables()

# Company config: override with st.secrets.company optional
company_cfg = st.secrets.get("company", {"name":"Exhiconnect Media Pvt Ltd", "address":"Ahmedabad, India", "gstin":""})

# Simple user auth (not secure for production). You can add password in secrets.users
USERS = {
    "bhavik":"pass",
    "chirag":"pass",
    "karishma":"pass"
}
if "users" in st.secrets:
    u = st.secrets["users"]
    for k,v in u.items():
        USERS[k] = v

def login_widget():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user = None
    if not st.session_state.logged_in:
        with st.sidebar.form("login"):
            st.write("Login")
            user = st.selectbox("User", list(USERS.keys()))
            pwd = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                if USERS.get(user) == pwd:
                    st.session_state.logged_in = True
                    st.session_state.user = user
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
    st.info("Please login from the left panel.")
    st.stop()

st.title("Amptech ERP - Invoicing")

# Top-level actions
col1, col2, col3 = st.columns([2,1,1])
with col1:
    if st.button("Create New Invoice"):
        st.session_state.show_create = True
with col2:
    if st.button("Load Demo Data"):
        # insert few fake entries
        conn = engine.connect()
        for i in range(1,4):
            invoice_no = f"DEMO-{datetime.utcnow().strftime('%y%m')}-{i}"
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
                created_at=datetime.utcnow()
            )
            conn.execute(invoices_table.insert().values(**data))
        conn.close()
        st.success("Demo data inserted.")
with col3:
    if st.button("Refresh List"):
        st.experimental_rerun()

# Sidebar filters
st.sidebar.header("Filters")
q_company = st.sidebar.text_input("Company (search)")
status_filter = st.sidebar.multiselect("Status", options=["Pending","Clear","Complimentary","Media Partner","Cancelled","Defaulted"], default=["Pending","Clear"])

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
        submit = st.form_submit_button("Save & Generate PDF")

    if submit:
        # calculations
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
            created_at=datetime.utcnow()
        )

        conn = engine.connect()
        res = conn.execute(invoices_table.insert().values(**data))
        conn.close()
        st.success("Invoice saved: " + invoice_no)

        # generate PDF bytes
        pdf_bytes = generate_invoice_pdf(data, company_cfg)
        b64 = base64.b64encode(pdf_bytes).decode()
        href = f'<a href="data:application/pdf;base64,{b64}" download="{invoice_no}.pdf">Download PDF</a>'
        st.markdown(href, unsafe_allow_html=True)

        # optional: email pdf
        send_email = st.checkbox("Send invoice by email to client (requires SMTP secrets)", value=False)
        if send_email and email:
            try:
                send_pdf_via_smtp(pdf_bytes, invoice_no, email, company_cfg)
                st.success("Email sent to " + email)
            except Exception as e:
                st.error("Email failed: " + str(e))

# List invoices
st.subheader("Invoices")
conn = engine.connect()
qry = select(invoices_table).order_by(invoices_table.c.created_at.desc())
rows = conn.execute(qry).mappings().all()
conn.close()
df = pd.DataFrame(rows)
if not df.empty:
    if q_company:
        df = df[df['company_name'].str.contains(q_company, case=False, na=False)]
    if status_filter:
        df = df[df['status'].isin(status_filter)]
    st.dataframe(df[['id','invoice_no','company_name','event_name','total_with_gst','balance','status','created_at']].rename(columns={
        'id':'ID','invoice_no':'Invoice','company_name':'Company','event_name':'Event','total_with_gst':'Total (₹)','balance':'Balance (₹)','status':'Status','created_at':'Date'
    }))
    # download CSV
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("Export as CSV", data=csv, file_name="invoices.csv", mime="text/csv")
    # download selected invoice pdf
    sel = st.number_input("Download Invoice ID", min_value=0, value=0, step=1)
    if st.button("Download Selected as PDF"):
        if sel>0:
            row = df[df['id']==sel]
            if not row.empty:
                invoice_data = row.iloc[0].to_dict()
                pdf_bytes = generate_invoice_pdf(invoice_data, company_cfg)
                st.download_button(label="Download PDF", data=pdf_bytes, file_name=f"{invoice_data['invoice_no']}.pdf", mime="application/pdf")
            else:
                st.warning("ID not found")
else:
    st.info("No invoices yet - create one or load demo data.")

# helper for email
def send_pdf_via_smtp(pdf_bytes, invoice_no, recipient, company_cfg):
    # streamlit secrets for smtp: st.secrets["smtp"]
    import streamlit as st
    smtp = st.secrets.get("smtp", {})
    if not smtp:
        raise Exception("SMTP config missing in streamlit secrets.")
    host = smtp.get("host")
    port = smtp.get("port", 587)
    username = smtp.get("username")
    password = smtp.get("password")
    from_email = smtp.get("from_email", f"no-reply@{st.secrets.get('site','localhost')}")
    subject = f"Proforma Invoice - {invoice_no}"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = recipient
    msg.set_content(f"Please find attached the Proforma Invoice {invoice_no}.")
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=f"{invoice_no}.pdf")
    # send
    server = smtplib.SMTP(host, int(port))
    try:
        server.starttls()
    except Exception:
        pass
    if username:
        server.login(username, password)
    server.send_message(msg)
    server.quit()
