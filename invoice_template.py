# invoice_template.py
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from io import BytesIO
from datetime import datetime

def generate_invoice_pdf(invoice: dict, company_config: dict = None):
    """
    invoice: dict with keys used in app (company_name, invoice_no, qty_sqm, rate_per_sqm, etc.)
    company_config: dict like {'name':..., 'address':..., 'gstin':..., 'logo_url':...}
    Returns bytes of PDF.
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 20*mm

    # Header
    c.setFont("Helvetica-Bold", 14)
    company_name = company_config.get("name") if company_config else "Your Company"
    c.drawString(margin, height - margin, company_name)
    c.setFont("Helvetica", 9)
    if company_config and company_config.get("address"):
        text = company_config.get("address")
        c.drawString(margin, height - margin - 14, text)
    if company_config and company_config.get("gstin"):
        c.drawString(margin, height - margin - 28, "GSTIN: " + company_config.get("gstin"))

    # Invoice metadata on right
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(width - margin, height - margin, f"Invoice: {invoice.get('invoice_no')}")
    c.setFont("Helvetica", 9)
    c.drawRightString(width - margin, height - margin - 14, f"Date: {invoice.get('created_at', datetime.utcnow()).strftime('%d-%b-%Y')}")

    # Bill To
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, height - margin - 60, "Bill To:")
    c.setFont("Helvetica", 9)
    y = height - margin - 76
    c.drawString(margin, y, invoice.get("company_name",""))
    y -= 14
    addr = invoice.get("address","")
    for line in str(addr).split("\n"):
        c.drawString(margin, y, line)
        y -= 12
    if invoice.get("gst_number"):
        c.drawString(margin, y, "GSTIN: " + invoice.get("gst_number"))
        y -= 14

    # Event details
    x_event = width/2 + 10
    y_event = height - margin - 76
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x_event, y_event, "Event / Booking")
    c.setFont("Helvetica", 9)
    y_event -= 14
    c.drawString(x_event, y_event, f"Event: {invoice.get('event_name','')}")
    y_event -= 12
    c.drawString(x_event, y_event, f"Location: {invoice.get('event_location','')}")
    y_event -= 12
    c.drawString(x_event, y_event, f"Stall No: {invoice.get('stall_number','')}")
    y_event -= 12
    c.drawString(x_event, y_event, f"Account Manager: {invoice.get('account_manager','')}")

    # Table header
    y_table = y - 30
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin, y_table, "#")
    c.drawString(margin + 20, y_table, "Description")
    c.drawRightString(width - margin - 120, y_table, "Qty")
    c.drawRightString(width - margin - 60, y_table, "Rate")
    c.drawRightString(width - margin, y_table, "Amount")
    y_table -= 10
    c.line(margin, y_table, width - margin, y_table)
    y_table -= 14

    # line: stall space
    c.setFont("Helvetica", 9)
    qty = float(invoice.get("qty_sqm") or 0)
    rate = float(invoice.get("rate_per_sqm") or 0)
    amount = float(invoice.get("total_sqm_amount") or qty*rate)
    c.drawString(margin, y_table, "1")
    c.drawString(margin + 20, y_table, f"Stall / Space ({invoice.get('space_type','')})")
    c.drawRightString(width - margin - 120, y_table, f"{qty:.2f}")
    c.drawRightString(width - margin - 60, y_table, f"{rate:.2f}")
    c.drawRightString(width - margin, y_table, f"{amount:.2f}")
    y_table -= 18

    # extras and sponsorship rows if any
    if float(invoice.get("extras_basic_total") or 0) > 0:
        ex = float(invoice.get("extras_basic_total") or 0)
        c.drawString(margin, y_table, " ")
        c.drawString(margin + 20, y_table, "Extras (Electricity / CFM / Hoarding)")
        c.drawRightString(width - margin, y_table, f"{ex:.2f}")
        y_table -= 14
    if float(invoice.get("sponsorship_basic") or 0) > 0:
        sp = float(invoice.get("sponsorship_basic") or 0)
        c.drawString(margin, y_table, " ")
        c.drawString(margin + 20, y_table, "Sponsorship")
        c.drawRightString(width - margin, y_table, f"{sp:.2f}")
        y_table -= 14
    if float(invoice.get("discount_amount") or 0) > 0:
        disc = float(invoice.get("discount_amount") or 0)
        c.drawString(margin, y_table, " ")
        c.drawString(margin + 20, y_table, "Discount")
        c.drawRightString(width - margin, y_table, f"-{disc:.2f}")
        y_table -= 14

    # totals block
    y_tot = y_table - 10
    c.setFont("Helvetica-Bold", 9)
    c.drawRightString(width - margin - 120, y_tot, "Taxable Value (₹):")
    c.drawRightString(width - margin, y_tot, f"{float(invoice.get('taxable_value') or 0):.2f}")
    y_tot -= 14
    c.setFont("Helvetica", 9)
    c.drawRightString(width - margin - 120, y_tot, f"GST @ {invoice.get('gst_percent',18)}%")
    c.drawRightString(width - margin, y_tot, f"{float(invoice.get('gst_amount') or 0):.2f}")
    y_tot -= 12
    c.drawRightString(width - margin - 120, y_tot, "CGST")
    c.drawRightString(width - margin, y_tot, f"{float(invoice.get('cgst') or 0):.2f}")
    y_tot -= 12
    c.drawRightString(width - margin - 120, y_tot, "SGST")
    c.drawRightString(width - margin, y_tot, f"{float(invoice.get('sgst') or 0):.2f}")
    y_tot -= 12
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(width - margin - 120, y_tot, "Total (Incl. GST):")
    c.drawRightString(width - margin, y_tot, f"{float(invoice.get('total_with_gst') or 0):.2f}")
    y_tot -= 18
    c.setFont("Helvetica", 9)
    c.drawRightString(width - margin - 120, y_tot, "Advance Paid:")
    c.drawRightString(width - margin, y_tot, f"{float(invoice.get('advance_paid') or 0):.2f}")
    y_tot -= 12
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(width - margin - 120, y_tot, "Balance Due:")
    c.drawRightString(width - margin, y_tot, f"{float(invoice.get('balance') or 0):.2f}")

    # Footer notes
    y_footer = 70
    c.setFont("Helvetica", 8)
    c.drawString(margin, y_footer + 40, "Notes:")
    c.setFont("Helvetica", 7)
    c.drawString(margin, y_footer + 28, "1) This is a Proforma Invoice. Final tax invoice will be issued on receipt of payment.")
    c.drawString(margin, y_footer + 16, "2) Please make payment to the account notified in final invoice.")
    c.drawString(margin, y_footer + 4, "3) For clarifications contact the account manager listed above.")

    # signature
    c.drawRightString(width - margin, y_footer, "Authorised Signatory")
    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
