# Amptech ERP (Streamlit)

## Quick deploy to Streamlit Cloud
1. Create a GitHub repo. Add files: app.py, database.py, invoice_template.py, requirements.txt.
2. Go to https://streamlit.io/cloud and deploy new app using the GitHub repo.
3. Add Secrets (Repo settings > Secrets or Streamlit Cloud > Secrets):
   - db: JSON object for MySQL (or omit to use SQLite)
     ```json
     {
       "dialect": "mysql",
       "user": "your_db_user",
       "password": "your_db_password",
       "host": "your_db_host",
       "port": "3306",
       "database": "u669232811_erp"
     }
     ```
   - smtp: JSON with SMTP credentials
     ```json
     {
       "host": "smtp.yourhost.com",
       "port": 587,
       "username": "smtp_user",
       "password": "smtp_password",
       "from_email": "billing@amptechindia.com"
     }
     ```
   - company: optional
     ```json
     {"name":"Exhiconnect Media Pvt Ltd","address":"Opp Vikas Bhavan, Sidcul, Haridwar","gstin":""}
     ```
4. Deploy and open the Streamlit app URL.

## Notes
- If you use Hostinger MySQL, use Remote MySQL settings and add the Streamlit Cloud IP(s) to Hostinger DB whitelist (Hostinger allows remote MySQL connection configuration).
- For small teams Streamlit Cloud is easiest and free for basic usage.
