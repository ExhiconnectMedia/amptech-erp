# invoice_template.py
from jinja2 import Template
from datetime import datetime

INVOICE_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>{{ invoice.type }} - {{ invoice.invoice_no }}</title>
  <style>
    body { font-family: Arial, Helvetica, sans-serif; color: #222; margin: 24px; }
    header { display:flex; justify-content:space-between; align-items:center; margin-bottom:18px; }
    .company { font-weight:700; font-size:18px; }
    .meta { text-align:right; font-size:13px; }
    .bill-to { margin-bottom:14px; }
    .table { width:100%; border-collapse: collapse; margin-top:8px; }
    .table th, .table td { padding:8px; border:1px solid #ddd; text-align:left; font-size:13px; }
    .table th { background:#f6f6f6; }
    .totals { margin-top:14px; float:right; width:360px; }
    .totals table { width:100%; border-collapse: collapse; }
    .totals td { padding:6px; font-size:13px; }
    footer { margin-top:60px; font-size:12px; color:#555; }
    .small { font-size:12px; color:#666; }
    .badge { display:inline-block; padding:6px 10px; background:#f2f2f2; border-radius:4px; font-weight:700; }
  </style>
</head>
<body>
  <header>
    <div>
      <div class="company">{{ company.name }}</div>
      <div class="small">{{ company.address }}</div>
      {% if company.gstin %}<div class="small">GSTIN: {{ company.gstin }} | State Code: {{ company.company_state_code or '' }}</div>{% endif %}
    </div>
    <div class="meta">
      <div><span class="badge">{{ invoice.type }}</span></div>
      <div style="margin-top:6px"><strong>Invoice:</strong> {{ invoice.invoice_no }}</div>
      <div><strong>Date:</strong> {{ invoice.created_at }}</div>
    </div>
  </header>

  <section>
    <div style="display:flex; justify-content:space-between;">
      <div style="width:48%;">
        <div class="small">Bill To</div>
        <div style="font-weight:600;">{{ invoice.company_name }}</div>
        <div class="small">{{ invoice.address }}</div>
        {% if invoice.gst_number %}<div class="small">GSTIN: {{ invoice.gst_number }} | State: {{ invoice.billing_state }} ({{ invoice.billing_state_code }})</div>{% endif %}
      </div>
      <div style="width:48%;">
        <div class="small">Event / Booking</div>
        <div class="small">Event: {{ invoice.event_name }}</div>
        <div class="small">Location: {{ invoice.event_location }}</div>
        <div class="small">Stall: {{ invoice.stall_number }}</div>
        <div class="small">Account Manager: {{ invoice.account_manager }}</div>
        <div class="small">Status: {{ invoice.status }}</div>
      </div>
    </div>
  </section>

  <table class="table" style="margin-top:18px;">
    <thead>
      <tr>
        <th style="width:50px">#</th>
        <th>Description</th>
        <th style="width:90px">Qty</th>
        <th style="width:120px">Rate (₹)</th>
        <th style="width:120px">Amount (₹)</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>1</td>
        <td>Stall / Space ({{ invoice.space_type or '' }})</td>
        <td style="text-align:right">{{ "%.2f"|format(invoice.qty_sqm or 0) }}</td>
        <td style="text-align:right">{{ "%.2f"|format(invoice.rate_per_sqm or 0) }}</td>
        <td style="text-align:right">{{ "%.2f"|format(invoice.total_sqm_amount or 0) }}</td>
      </tr>
      {% if invoice.extras_basic_total and invoice.extras_basic_total>0 %}
      <tr>
        <td></td><td>Extras (Electricity/CFM/Hoarding)</td><td></td><td></td>
        <td style="text-align:right">{{ "%.2f"|format(invoice.extras_basic_total) }}</td>
      </tr>
      {% endif %}
      {% if invoice.sponsorship_basic and invoice.sponsorship_basic>0 %}
      <tr>
        <td></td><td>Sponsorship</td><td></td><td></td>
        <td style="text-align:right">{{ "%.2f"|format(invoice.sponsorship_basic) }}</td>
      </tr>
      {% endif %}
      {% if invoice.discount_amount and invoice.discount_amount>0 %}
      <tr>
        <td></td><td>Discount</td><td></td><td></td>
        <td style="text-align:right">-{{ "%.2f"|format(invoice.discount_amount) }}</td>
      </tr>
      {% endif %}
    </tbody>
  </table>

  <div class="totals">
    <table>
      <tr><td>Taxable Value (₹)</td><td style="text-align:right">{{ "%.2f"|format(invoice.taxable_value or 0) }}</td></tr>
      <tr><td>GST ({{ invoice.gst_percent or 18 }}%)</td><td style="text-align:right">{{ "%.2f"|format(invoice.gst_amount or 0) }}</td></tr>
      {% if invoice.igst and invoice.igst>0 %}
        <tr><td>IGST</td><td style="text-align:right">{{ "%.2f"|format(invoice.igst) }}</td></tr>
      {% else %}
        <tr><td>CGST</td><td style="text-align:right">{{ "%.2f"|format(invoice.cgst or 0) }}</td></tr>
        <tr><td>SGST</td><td style="text-align:right">{{ "%.2f"|format(invoice.sgst or 0) }}</td></tr>
      {% endif %}
      <tr style="font-weight:700;"><td>Total (Incl. GST)</td><td style="text-align:right">{{ "%.2f"|format(invoice.total_with_gst or 0) }}</td></tr>
      <tr><td>Advance Paid</td><td style="text-align:right">{{ "%.2f"|format(invoice.advance_paid or 0) }}</td></tr>
      <tr style="font-weight:700;"><td>Balance Due</td><td style="text-align:right">{{ "%.2f"|format(invoice.balance or 0) }}</td></tr>
    </table>
  </div>

  <div style="clear:both"></div>

  <footer>
    <div>Notes:</div>
    <div class="small">1) This is a {{ invoice.type }}. For Tax Invoice, GST details are shown above.</div>
    <div class="small">2) Bank details will be shared on final invoice/receipt.</div>
  </footer>
</body>
</html>
"""

def render_html(invoice: dict, company: dict):
    invoice = invoice.copy()
    if invoice.get("created_at") is None:
        invoice["created_at"] = datetime.utcnow().strftime("%d-%b-%Y")
    else:
        try:
            invoice["created_at"] = datetime.fromisoformat(invoice["created_at"]).strftime("%d-%b-%Y")
        except Exception:
            pass
    # Ensure numeric types are floats (for template formatting)
    for k in ["qty_sqm","rate_per_sqm","total_sqm_amount","discount_amount","extras_basic_total","sponsorship_basic","taxable_value","gst_percent","gst_amount","cgst","sgst","igst","total_with_gst","advance_paid","balance"]:
        invoice[k] = float(invoice.get(k) or 0)
    # Company state code may be in secrets.company.company_state_code; ensure provided
    if company.get("company_state_code") is None:
        company["company_state_code"] = ""
    tpl = Template(INVOICE_HTML)
    return tpl.render(invoice=invoice, company=company)
