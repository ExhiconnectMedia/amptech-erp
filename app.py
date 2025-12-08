# app.py (improved UI + dashboard + payments + full export)
import streamlit as st
from datetime import datetime
from database import ensure_tables, insert_invoice, fetch_all_invoices, fetch_invoice_by_id, record_payment, fetch_payments_for_invoice, export_all_invoices_csv
from invoice_template import render_html
import base64, requests, json, os

st.set_page_config(page_title="Amptech ERP", layout="wide")
ensure_tables()

# defaults from secrets or fallback
default_company = {"name":"Exhiconnect Media Pvt Ltd","address":"Opp. Vikas Bhavan, Sidcul, Haridwar","gstin":"","company_state_code":"" , "logo_url":""}
try:
    if st.secrets.get("company"):
        default_company.update(st.secrets.get("company"))
except Exception:
    pass

company_cfg = default_company

# Users
DEFAULT_USERS = {"bhavik":"12345","chirag":"12345","karishma":"12345"}
try:
    users = dict(st.secrets.get("users", DEFAULT_USERS))
except Exception:
    users = DEFAULT_USERS

# Simple settings file for event-rate mapping (persisted locally)
SET_FILE = os.path.join(os.path.dirname(__file__), "settings.json")
def load_settings():
    if os.path.exists(SET_FILE):
        try:
            with open(SET_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}
def save_settings(d):
    with open(SET_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)
settings = load_settings()
if "event_rates" not in settings:
    settings["event_rates"] = {"Amptech India Expo":8000, "Auto India Expo":9000, "Career Bonanza Expo":4000}
    save_settings(settings)

# Auth widget
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

# Navigation
PAGES = ["Dashboard","Invoices","Create Invoice","Payments","Settings"]
page = st.sidebar.radio("Navigation", PAGES)

# helper: PDFShift key
def has_pdfshift():
    try:
        return bool(st.secrets["pdfshift"]["key"])
    except Exception:
        return False

def generate_pdf_via_pdfshift(html):
    key = st.secrets["pdfshift"]["key"]
    resp = requests.post("https://api.pdfshift.io/v3/convert/", json={"source": html}, auth=(key,""))
    if resp.status_code == 200:
        return resp.content
    raise Exception(f"PDF API error: {resp.status_code} {resp.text[:200]}")

# Dashboard
if page == "Dashboard":
    st.title("Dashboard")
    rows = fetch_all_invoices()
    total_invoices = len(rows)
    total_revenue = sum([r.get("total_with_gst") or 0 for r in rows])
    total_balance = sum([r.get("balance") or 0 for r in rows])
    pending_count = sum([1 for r in rows if (r.get("balance") or 0) > 0])
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Invoices", total_invoices)
    col2.metric("Total (₹)", f"{total_revenue:,.2f}")
    col3.metric("Pending (₹)", f"{total_balance:,.2f}")
    col4.metric("Pending Count", pending_count)

    st.subheader("Revenue by Event")
    # aggregate revenue by event
    agg = {}
    for r in rows:
        evt = r.get("event_name") or "Unknown"
        agg[evt] = agg.get(evt, 0) + float(r.get("total_with_gst") or 0)
    if agg:
        st.bar_chart(agg)

    st.subheader("Balance by Account Manager")
    agg2 = {}
    for r in rows:
        am = r.get("account_manager") or "Unknown"
        agg2[am] = agg2.get(am, 0) + float(r.get("balance") or 0)
    if agg2:
        st.bar_chart(agg2)

    st.subheader("Latest Invoices")
    latest = rows[:10]
    if latest:
        st.table([{k:v for k,v in {
            "Invoice":r.get("invoice_no"),
            "Company":r.get("company_name"),
            "Event":r.get("event_name"),
            "Total":r.get("total_with_gst"),
            "Balance":r.get("balance"),
            "Status":r.get("status"),
            "Date":r.get("created_at")
        }.items()} for r in latest])
    else:
        st.info("No invoices yet.")

# Invoices list & export
elif page == "Invoices":
    st.title("Invoices")
    rows = fetch_all_invoices()
    if not rows:
        st.info("No invoices yet.")
    else:
        # search & filters
        q = st.text_input("Search Company or Invoice No")
        status_filter = st.multiselect("Status", options=list(sorted(set([r.get("status") or "" for r in rows]))), default=[])
        filtered = []
        for r in rows:
            ok = True
            if q:
                if q.lower() not in str(r.get("company_name","")).lower() and q.lower() not in str(r.get("invoice_no","")).lower():
                    ok = False
            if status_filter and (r.get("status") not in status_filter):
                ok = False
            if ok:
                filtered.append(r)
        # show table with all columns requested
        if filtered:
            # build table rows list of dicts with specific columns
            cols = ["id","invoice_no","type","company_name","event_name","event_location","event_month_year","stall_number","qty_sqm","space_type","rate_per_sqm","total_sqm_amount","discount_amount","extras_basic_total","sponsorship_basic","taxable_value","gst_percent","gst_amount","cgst","sgst","igst","total_with_gst","advance_paid","balance","account_manager","status","gst_number","address","pin","billing_state","billing_state_code","created_at"]
            table = []
            for r in filtered:
                row = {c: r.get(c) for c in cols}
                table.append(row)
            st.write(f"Showing {len(table)} invoices")
            st.dataframe(table)
            # CSV export
            csv = export_all_invoices_csv()
            st.download_button("Download all invoices CSV", data=csv.encode("utf-8"), file_name="invoices_full.csv", mime="text/csv")
            # view invoice
            sel = st.number_input("Open invoice ID", min_value=0, value=0, step=1)
            if st.button("Open Invoice"):
                if sel>0:
                    inv = fetch_invoice_by_id(sel)
                    if inv:
                        html = render_html(inv, company_cfg)
                        st.components.v1.html(html, height=800, scrolling=True)
                        st.download_button("Download invoice HTML", data=html.encode("utf-8"), file_name=f"{inv['invoice_no']}.html", mime="text/html")
                        if has_pdfshift():
                            if st.button("Generate PDF (server-side)"):
                                with st.spinner("Generating PDF..."):
                                    try:
                                        pdf_bytes = generate_pdf_via_pdfshift(html)
                                        st.download_button("Download PDF", data=pdf_bytes, file_name=f"{inv['invoice_no']}.pdf", mime="application/pdf")
                                    except Exception as e:
                                        st.error("PDF error: " + str(e))
                        else:
                            st.info("PDF API not configured. Use Print → Save as PDF on the preview or add pdfshift.key to secrets.")
                    else:
                        st.warning("Not found")

# Create invoice
elif page == "Create Invoice":
    st.title("Create Invoice")
    with st.form("create"):
        invoice_type = st.selectbox("Invoice Type", ["Proforma","Tax Invoice","Payment Receipt"])
        company_name = st.text_input("Company Name")
        address = st.text_area("Address")
        address2 = st.text_input("Address 2 (optional)")
        address3 = st.text_input("Address 3 (optional)")
        pin = st.text_input("PIN")
        gst_number = st.text_input("GST Number / Email")
        event_name = st.selectbox("Event Name", list(settings.get("event_rates", {}).keys()))
        event_month_year = st.text_input("Event Month-Year (e.g., Feb-2026)")
        event_location = st.text_input("Event Location", "Vadodara")
        event_dates = st.text_input("Event Dates (optional)")
        stall_number = st.text_input("Stall Number")
        space_type = st.selectbox("Space Type", ["Bare","Shell"])
        default_rate = settings["event_rates"].get(event_name, 0)
        rate_per_sqm = st.number_input("Rate per sqm (₹)", value=float(default_rate))
        qty_sqm = st.number_input("Qty (sqm)", value=9.0, step=0.5)
        discount_amount = st.number_input("Discount (₹)", value=0.0)
        extras_basic_total = st.number_input("Extras (₹)", value=0.0)
        sponsorship_basic = st.number_input("Sponsorship (₹)", value=0.0)
        # billing state dropdown
        states = [
            ("Gujarat","24"),("Maharashtra","27"),("Delhi","07"),("Uttar Pradesh","09"),
            ("Karnataka","29"),("Tamil Nadu","33"),("Madhya Pradesh","23"),("Rajasthan","08")
        ]
        billing_state = st.selectbox("Billing State", [s[0] for s in states])
        billing_state_code = dict(states)[billing_state]
        gst_percent = st.number_input("GST %", value=18.0)
        advance_paid = st.number_input("Advance Paid (₹)", value=0.0)
        account_manager = st.selectbox("Account Manager", ["Bhavik","Chirag","Karishma"])
        status = st.selectbox("Status", ["Pending","Clear","Complimentary","Media Partner","Cancelled","Defaulted"])
        remarks = st.text_area("Remarks (internal, not in printed invoice)")
        submitted = st.form_submit_button("Save Invoice")
    if submitted:
        total_sqm_amount = round(float(qty_sqm) * float(rate_per_sqm),2)
        taxable_value = round(total_sqm_amount - float(discount_amount) + float(extras_basic_total) + float(sponsorship_basic),2)
        gst_amount = round(taxable_value * float(gst_percent)/100.0,2)
        company_state_code = company_cfg.get("company_state_code","")
        if company_state_code and str(company_state_code) != str(billing_state_code):
            igst = gst_amount
            cgst = 0.0
            sgst = 0.0
        else:
            igst = 0.0
            cgst = round(gst_amount/2,2)
            sgst = round(gst_amount/2,2)
        total_with_gst = round(taxable_value + gst_amount,2)
        balance = round(total_with_gst - float(advance_paid),2)
        prefix = "PRO" if invoice_type=="Proforma" else ("TAX" if invoice_type=="Tax Invoice" else "REC")
        invoice_no = f"{prefix}-{datetime.utcnow().year}-{str(abs(hash(datetime.utcnow())))[0:6]}"
        data = {
            "invoice_no": invoice_no,
            "type": invoice_type,
            "company_name": company_name,
            "email": gst_number,
            "gst_number": gst_number,
            "address": address,
            "address2": address2,
            "address3": address3,
            "pin": pin,
            "state": company_cfg.get("company_state_code",""),
            "billing_state": billing_state,
            "billing_state_code": billing_state_code,
            "company_state_code": company_cfg.get("company_state_code",""),
            "event_name": event_name,
            "event_location": event_location,
            "event_month_year": event_month_year,
            "event_dates": event_dates,
            "stall_number": stall_number,
            "qty_sqm": qty_sqm,
            "space_type": space_type,
            "rate_per_sqm": rate_per_sqm,
            "total_sqm_amount": total_sqm_amount,
            "discount_amount": discount_amount,
            "extras_basic_total": extras_basic_total,
            "sponsorship_basic": sponsorship_basic,
            "taxable_value": taxable_value,
            "gst_percent": gst_percent,
            "gst_amount": gst_amount,
            "cgst": cgst,
            "sgst": sgst,
            "igst": igst,
            "total_with_gst": total_with_gst,
            "advance_paid": advance_paid,
            "balance": balance,
            "account_manager": account_manager,
            "status": status,
            "remarks": remarks,
            "created_at": datetime.utcnow().isoformat()
        }
        invoice_id = insert_invoice(data)
        st.success(f"Saved {invoice_no} (ID: {invoice_id})")
        html = render_html(data, company_cfg)
        st.components.v1.html(html, height=800, scrolling=True)
        st.download_button("Download invoice HTML", data=html.encode("utf-8"), file_name=f"{invoice_no}.html", mime="text/html")
        if has_pdfshift():
            if st.button("Generate PDF (server-side)"):
                with st.spinner("Generating PDF..."):
                    try:
                        pdf_bytes = generate_pdf_via_pdfshift(html)
                        st.download_button("Download PDF", data=pdf_bytes, file_name=f"{invoice_no}.pdf", mime="application/pdf")
                    except Exception as e:
                        st.error("PDF error: " + str(e))
        else:
            st.info("To get PDF in one click add pdfshift.key in Streamlit Secrets. Otherwise use browser Print → Save as PDF.")

# Payments page
elif page == "Payments":
    st.title("Payments")
    rows = fetch_all_invoices()
    if not rows:
        st.info("No invoices to record payment against.")
    else:
        st.subheader("Record Payment")
        invoice_ids = [r["id"] for r in rows]
        sel = st.selectbox("Invoice ID", invoice_ids)
        amount = st.number_input("Amount (₹)", min_value=0.0, value=0.0)
        mode = st.selectbox("Mode", ["Cash","Bank Transfer","UPI","Other"])
        note = st.text_input("Note")
        if st.button("Record Payment"):
            res = record_payment(sel, amount, mode, note)
            st.success(f"Payment recorded. New advance: {res['advance_paid']:.2f}, Balance: {res['balance']:.2f}")
        st.subheader("Payments for an invoice")
        sel2 = st.number_input("Show payments for Invoice ID", min_value=0, value=0, step=1)
        if st.button("Show Payments"):
            if sel2>0:
                pays = fetch_payments_for_invoice(sel2)
                if pays:
                    st.table(pays)
                else:
                    st.info("No payments for this invoice.")

# Settings
elif page == "Settings":
    st.title("Settings")
    st.subheader("Company details (update secrets for persistent across deploys)")
    with st.form("company_form"):
        cname = st.text_input("Company Name", value=company_cfg.get("name",""))
        caddr = st.text_area("Address", value=company_cfg.get("address",""))
        cgst = st.text_input("Company GSTIN", value=company_cfg.get("gstin",""))
        ccode = st.text_input("Company State Code (e.g., 24)", value=company_cfg.get("company_state_code",""))
        logo = st.text_input("Logo URL (optional)", value=company_cfg.get("logo_url",""))
        savec = st.form_submit_button("Save (local only)")
    if savec:
        # local settings only: write to settings.json
        settings["company"] = {"name":cname,"address":caddr,"gstin":cgst,"company_state_code":ccode,"logo_url":logo}
        save_settings(settings)
        st.success("Saved locally. Add to Streamlit secrets if you want persistent secrets across redeploys.")
    st.subheader("Event rates")
    evts = settings.get("event_rates", {})
    for k,v in list(evts.items()):
        newv = st.number_input(f"Rate for {k}", value=float(v))
        evts[k] = newv
    if st.button("Save event rates"):
        settings["event_rates"] = evts
        save_settings(settings)
        st.success("Rates saved locally.")

    st.markdown("**Notes**: Company secrets (like company_state_code, smtp, pdfshift) are safer in Streamlit Secrets. Local Settings are saved in `settings.json` in the app folder.")

# End
