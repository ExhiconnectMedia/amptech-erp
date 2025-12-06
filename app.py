# app.py
import streamlit as st
from datetime import datetime
from database import ensure_tables, insert_invoice, fetch_all_invoices, fetch_invoice_by_id, record_payment
from invoice_template import render_html
import base64, io, requests

st.set_page_config(page_title="Amptech ERP", layout="wide")
ensure_tables()

# Company config and users from secrets (or defaults)
company_cfg = {"name":"Exhiconnect Media Pvt Ltd","address":"Opp. Vikas Bhavan, Sidcul, Haridwar","gstin":"","company_state_code":""}
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

# Indian states + GST state codes mapping (short list; expand if needed)
INDIAN_STATES = [
    ("Andhra Pradesh","28"),("Arunachal Pradesh","12"),("Assam","18"),("Bihar","10"),
    ("Chhattisgarh","22"),("Goa","30"),("Gujarat","24"),("Haryana","06"),("Himachal Pradesh","02"),
    ("Jammu & Kashmir","01"),("Jharkhand","20"),("Karnataka","29"),("Kerala","32"),("Madhya Pradesh","23"),
    ("Maharashtra","27"),("Manipur","14"),("Meghalaya","17"),("Mizoram","15"),("Nagaland","13"),
    ("Odisha","21"),("Punjab","03"),("Rajasthan","08"),("Sikkim","11"),("Tamil Nadu","33"),
    ("Telangana","36"),("Tripura","16"),("Uttar Pradesh","09"),("Uttarakhand","05"),("West Bengal","19"),
    ("Delhi","07"),("Puducherry","34"),("Chandigarh","04"),("Ladakh","38")
]

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
        for i in range(1,4):
            invoice_no = f"DEMO-{datetime.utcnow().strftime('%y%m%d%H%M%S')}-{i}"
            data = dict(
                invoice_no=invoice_no,
                type="Proforma",
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
                billing_state="Gujarat",
                billing_state_code="24",
                company_state_code=company_cfg.get("company_state_code",""),
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
        invoice_type = st.selectbox("Invoice Type", ["Proforma","Tax Invoice","Payment Receipt"])
        company_name = st.text_input("Company Name", "")
        address = st.text_area("Address", "")
        gst_number = st.text_input("GST Number")
        # Billing state
        billing_state = st.selectbox("Billing State", [s[0] for s in INDIAN_STATES])
        billing_state_code = dict(INDIAN_STATES)[billing_state]
        # Show company state code from config if set (company_cfg.company_state_code)
        company_state_code = company_cfg.get("company_state_code","")
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
        # decide cgst/sgst vs igst
        if company_state_code and str(billing_state_code) != str(company_state_code):
            igst = gst_amount
            cgst = 0.0
            sgst = 0.0
        else:
            igst = 0.0
            cgst = round(gst_amount/2, 2)
            sgst = round(gst_amount/2, 2)
        total_with_gst = round(taxable_value + gst_amount, 2)
        balance = round(total_with_gst - advance_paid, 2)
        invoice_no = f"{'PRO' if invoice_type=='Proforma' else ('TAX' if invoice_type=='Tax Invoice' else 'REC')}-{datetime.utcnow().year}-{str(abs(hash(datetime.utcnow())))[0:6]}"

        data = dict(
            invoice_no=invoice_no,
            type=invoice_type,
            company_name=company_name,
            email=gst_number and gst_number or "",
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
            billing_state=billing_state,
            billing_state_code=billing_state_code,
            company_state_code=company_state_code,
            created_at=datetime.utcnow().isoformat()
        )

        invoice_id = insert_invoice(data)
        st.success("Invoice saved: " + invoice_no)
        # Render HTML invoice
        html = render_html(data, company_cfg)
        st.markdown("### Invoice Preview (rendered HTML)")
        st.components.v1.html(html, height=800, scrolling=True)

        # DOWNLOAD options
        b = html.encode("utf-8")
        st.download_button("Download invoice as HTML", data=b, file_name=f"{invoice_no}.html", mime="text/html")

        # If pdfshift key in secrets, show one-click server PDF
        pdfshift_key = None
        try:
            pdfshift_key = st.secrets["pdfshift"]["key"]
        except Exception:
            pdfshift_key = None

        if pdfshift_key:
            if st.button("Generate PDF (server-side)"):
                with st.spinner("Generating PDF via PDFShift..."):
                    try:
                        resp = requests.post(
                            "https://api.pdfshift.io/v3/convert/",
                            json={"source": html},
                            auth=(pdfshift_key, "")
                        )
                        if resp.status_code == 200:
                            pdf_bytes = resp.content
                            st.download_button("Download PDF", data=pdf_bytes, file_name=f"{invoice_no}.pdf", mime="application/pdf")
                            st.success("PDF ready — download button shown.")
                        else:
                            st.error(f"PDF service error: {resp.status_code} - {resp.text[:200]}")
                    except Exception as e:
                        st.exception(e)
        else:
            st.info("Server-side PDF (one-click) is not enabled. To enable, add PDFShift API key in Streamlit Secrets as pdfshift.key. Meanwhile, use Print → Save as PDF from the preview.")

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
                # quick receipt/payment recording option
                if st.button("Record Payment for this invoice"):
                    amt = st.number_input("Payment amount", min_value=0.0, value=float(inv.get("total_with_gst") or 0))
                    if st.button("Confirm Payment"):
                        res = record_payment(inv["id"], amt)
                        st.success(f"Recorded payment. New advance: {res['advance_paid']:.2f}, Balance: {res['balance']:.2f}")
                        st.experimental_rerun()
            else:
                st.warning("Invoice ID not found")
else:
    st.info("No invoices yet.")
