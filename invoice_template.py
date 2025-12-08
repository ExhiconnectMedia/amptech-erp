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
    @page { size: A4; margin: 18mm }
    body { font-family: 'Helvetica', Arial, sans-serif; color: #222; font-size:13px; }
    .wrap { max-width: 800px; margin: 0 auto; }
    header { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px; }
    .brand { max-width: 60%; }
    .brand .company { font-size:18px; font-weight:700; }
    .meta { text-align:right; font-size:13px; }
    .meta .badge { display:inline-block; padding:6px 10px; background:#0d6efd; color:#fff; border-radius:4px; font-weight:700; }
    .addresses { display:flex; justify-content:space-between; margin-top:10px; }
    .box { border:1px solid #e6e6e6; padding:10px; border-radius:6px; }
    .table { width:100%; border-collapse: collapse; margin-top:12px; }
    .table th, .table td { padding:8px; border:1px solid #eaeaea; text-align:left; }
    .table th { background:#fafafa; }
    .totals { float:right; width:320px; margin-top:12px; border:1px solid #eaeaea; padding:8px; border-radius:6px; }
    .totals-row { display:flex; justify-content:space-between; padding:4px 0; }
    footer { margin-top:40px; font-size:11px; color:#555; }
    .small { font-size:12px; color:#666; }
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="brand">
        {% if company.logo_url %}
          <div><img src="{{ company.logo_url }}" style="max-height:60px;"/></div>
        {% endif %}
        <div class="company">{{ company.name }}</div>
        <div class="small">{{ company.address }}</div>
        {% if company.gstin %}<div class="small">GSTIN: {{ company.gstin }} | State Code: {{ company.company_state_code or '' }}</div>{% endif %}
      </div>
      <div class="meta">
        <div class="badge">{{ invoice.type }}</div>
        <div style="margin-top:10px;"><strong>Invoice:</strong> {{ invoice.invoice_no }}</div>
        <div><strong>Date:</strong> {{ invoice.created_at }}</div>
      </div>
    </header>

    <div class="addresses">
      <div style="width:60%">
        <div class="small">Bill To</div>
        <div style="font-weight:700;">{{ invoice.company_name }}</div>
        <div class="small">{{ invoice.address }}</div>
        {% if invoice.gst_number %}<div class="small">GSTIN: {{ invoice.gst_number }} | State: {{ invoice.billing_state }} ({{ invoice.billing_state_code }})</div>{% endif %}
      </div>
      <div style="width:35%">
        <div class="small">Booking Details</div>
        <div class="small">Event: {{ invoice.event_name }}</div>
        <div class="small">Location: {{ invoice.event_location }}</div>
        <div class="small">Month/Year: {{ invoice.event_month_year }}</div>
        <div class="small">Stall No: {{ invoice.stall_number }}</div>
        <div class="small">Account Manager: {{ invoice.account_manager }}</div>
      </div>
    </div>

    <table class="table">
      <thead>
        <tr>
          <th style="width:40px">#</th><th>Description</th><th style="width:90px">Qty</th><th style="width:120px">Rate</th><th style="width:120px">Amount</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>1</td>
          <td>Stall / Space ({{ invoice.space_type or '' }})</td>
          <td style="text-align:right">{{ '%.2f'|format(invoice.qty_sqm or 0) }}</td>
          <td style="text-align:right">{{ '%.2f'|format(invoice.rate_per_sqm or 0) }}</td>
          <td style="text-align:right">{{ '%.2f'|format(invoice.total_sqm_amount or 0) }}</td>
        </tr>
        {% if invoice.extras_basic_total and invoice.extras_basic_total>0 %}
        <tr>
          <td></td><td>Extras (Electricity/CFM/Hoarding)</td><td></td><td></td><td style="text-align:right">{{ '%.2f'|format(invoice.extras_basic_total) }}</td>
        </tr>
        {% endif %}
        {% if invoice.sponsorship_basic and invoice.sponsorship_basic>0 %}
        <tr>
          <td></td><td>Sponsorship</td><td></td><td></td><td style="text-align:right">{{ '%.2f'|format(invoice.sponsorship_basic) }}</td>
        </tr>
        {% endif %}
        {% if invoice.discount_amount and invoice.discount_amount>0 %}
        <tr>
          <td></td><td>Discount</td><td></td><td></td><td style="text-align:right">-{{ '%.2f'|format(invoice.discount_amount) }}</td>
        </tr>
        {% endif %}
      </tbody>
    </table>

    <div class="totals">
      <div class="totals-row"><div>Taxable Value (₹)</div><div>{{ '%.2f'|format(invoice.taxable_value or 0) }}</div></div>
      <div class="totals-row"><div>GST ({{ invoice.gst_percent or 18 }}%)</div><div>{{ '%.2f'|format(invoice.gst_amount or 0) }}</div></div>
      {% if invoice.igst and invoice.igst>0 %}
        <div class="totals-row"><div>IGST</div><div>{{ '%.2f'|format(invoice.igst) }}</div></div>
      {% else %}
        <div class="totals-row"><div>CGST</div><div>{{ '%.2f'|format(invoice.cgst or 0) }}</div></div>
        <div class="totals-row"><div>SGST</div><div>{{ '%.2f'|format(invoice.sgst or 0) }}</div></div>
      {% endif %}
      <hr/>
      <div class="totals-row" style="font-weight:700"><div>Total (Incl. GST)</div><div>{{ '%.2f'|format(invoice.total_with_gst or 0) }}</div></div>
      <div class="totals-row"><div>Advance Paid</div><div>{{ '%.2f'|format(invoice.advance_paid or 0) }}</div></div>
      <div class="totals-row" style="font-weight:700"><div>Balance Due</div><div>{{ '%.2f'|format(invoice.balance or 0) }}</div></div>
    </div>

    <div style="clear:both"></div>

    <footer>
      <div class="small">Notes:</div>
      <div class="small">1) This is a {{ invoice.type }}. Final tax invoice will be issued on receipt of payment where applicable.</div>
      <div class="small">2) Bank details will be provided on final invoice/receipt.</div>
    </footer>
  </div>
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
    # numeric normalization
    for k in ["qty_sqm","rate_per_sqm","total_sqm_amount","discount_amount","extras_basic_total","sponsorship_basic","taxable_value","gst_percent","gst_amount","cgst","sgst","igst","total_with_gst","advance_paid","balance"]:
        invoice[k] = float(invoice.get(k) or 0)
    tpl = Template(INVOICE_HTML)
    return tpl.render(invoice=invoice, company=company)
