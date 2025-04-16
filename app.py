import streamlit as st
import gspread
import pandas as pd
import json
from datetime import datetime, date
from oauth2client.service_account import ServiceAccountCredentials
import io
from fpdf import FPDF
import plotly.express as px

# Connect to Google Sheets
def connect_to_sheet(sheet_name, worksheet, headers=None):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDS"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    try:
        sheet = client.open(sheet_name).worksheet(worksheet)
    except gspread.exceptions.WorksheetNotFound:
        sheet = client.open(sheet_name).add_worksheet(title=worksheet, rows="100", cols="20")
        if headers:
            sheet.insert_row(headers, index=1)
    return sheet

# Ensure all required sheets exist with headers
def ensure_all_sheets():
    connect_to_sheet("Salary_Advance_Tracker", "master_data", ["Emp Name", "DOJ", "Group", "Department", "Area", "Net Salary PM"])
    connect_to_sheet("Salary_Advance_Tracker", "advance_data", ["Emp Name", "Advance Taken", "Advance Date", "Remaining Advance"])
    connect_to_sheet("Salary_Advance_Tracker", "payroll_input", ["Month", "Emp Name", "Working Days"])
    connect_to_sheet("Salary_Advance_Tracker", "login_logs", ["Username", "Action", "Timestamp"])

# Load Data Functions
def load_employee_master():
    sheet = connect_to_sheet("Salary_Advance_Tracker", "master_data")
    data = pd.DataFrame(sheet.get_all_records())
    if not data.empty:
        data.columns = data.columns.astype(str).str.strip()
    return data

def load_advance_data():
    sheet = connect_to_sheet("Salary_Advance_Tracker", "advance_data")
    data = pd.DataFrame(sheet.get_all_records())
    data.columns = data.columns.str.strip()
    return data

def load_payroll_input(month):
    sheet = connect_to_sheet("Salary_Advance_Tracker", "payroll_input")
    data = pd.DataFrame(sheet.get_all_records())
    data.columns = data.columns.str.strip()
    if 'Month' not in data.columns:
        st.error("'Month' column not found in payroll_input sheet")
        return pd.DataFrame()
    return data[data['Month'] == month]

# Save login activity
def log_activity(username, action):
    try:
        sheet = connect_to_sheet("Salary_Advance_Tracker", "login_logs")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheet.append_row([username, action, timestamp])
    except:
        st.warning("Unable to log activity.")

# Generate PDF
def generate_pdf(payroll, month):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, f"BHP – Payroll Report ({month})", ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("Helvetica", "B", 12)
    headers = ["Emp Name", "Area", "Group", "Department", "Monthly Salary", "Remaining Advance", "Final Payable"]
    col_widths = [40, 25, 25, 30, 30, 30, 30]
    for i, header in enumerate(headers):
        pdf.cell(col_widths[i], 10, header, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 11)
    for _, row in payroll.iterrows():
        values = [row.get(h, "") for h in headers]
        for i, val in enumerate(values):
            pdf.cell(col_widths[i], 8, str(val), border=1)
        pdf.ln()

    return pdf.output(dest='S').encode('latin-1')

# Generate Excel
def generate_excel(payroll, month):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        payroll.to_excel(writer, index=False, sheet_name='Payroll', startrow=2)
        workbook  = writer.book
        worksheet = writer.sheets['Payroll']
        header_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
        worksheet.merge_range('A1:G1', f"BHP Payroll Report – {month}", header_format)
        writer.close()
    return output.getvalue()

# Main Dashboard
def payroll_dashboard():
    st.title("Payroll Dashboard")
    month = st.selectbox("Select Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])

    emp_master = load_employee_master()
    advances = load_advance_data()
    payroll_input = load_payroll_input(month)

    if emp_master.empty or payroll_input.empty:
        st.error("Missing or empty sheet data.")
        return

    if 'Emp Name' not in emp_master.columns or 'Emp Name' not in payroll_input.columns:
        st.error("Missing 'Emp Name' in sheet columns")
        return

    # Validate required column
    required_column = 'Emp Name'
    if required_column not in emp_master.columns or required_column not in payroll_input.columns:
        st.error(f"Missing '{required_column}' column in master or payroll sheet.")
        st.write("emp_master columns:", emp_master.columns.tolist())
        st.write("payroll_input columns:", payroll_input.columns.tolist())
        st.stop()

    payroll = payroll_input.merge(emp_master, on='Emp Name', how='left')
    payroll['Per Day Salary'] = payroll['Net Salary PM'] / 30
    payroll['Monthly Salary'] = payroll['Per Day Salary'] * payroll['Working Days']
    payroll = payroll.merge(advances[['Emp Name', 'Remaining Advance']], on='Emp Name', how='left')
    payroll['Remaining Advance'] = payroll['Remaining Advance'].fillna(0)
    payroll['Final Payable'] = payroll['Monthly Salary'] - payroll['Remaining Advance']

    st.dataframe(payroll[['Emp Name', 'Area', 'Group', 'Department', 'Monthly Salary', 'Remaining Advance', 'Final Payable']])

    # Store report in Google Sheet tab
    try:
        client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["GOOGLE_SHEETS_CREDS"]), ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]))
        spreadsheet = client.open("Salary_Advance_Tracker")
        try:
            worksheet = spreadsheet.worksheet(month)
            spreadsheet.del_worksheet(worksheet)
        except:
            pass
        new_ws = spreadsheet.add_worksheet(title=month, rows="100", cols="20")
        new_ws.update([payroll.columns.values.tolist()] + payroll.values.tolist())
    except Exception as e:
        st.warning(f"Failed to update Google Sheet for {month}: {e}")

    pdf_data = generate_pdf(payroll, month)
    st.download_button("Download Payroll PDF", data=pdf_data, file_name=f"Payroll_{month}.pdf", mime="application/pdf")

    excel_data = generate_excel(payroll, month)
    st.download_button("Download Payroll Excel", data=excel_data, file_name=f"Payroll_{month}.xlsx", mime="application/vnd.ms-excel")

    st.markdown("### Export Employee-wise Report")
    emp_selected = st.selectbox("Select employee for report", payroll['Emp Name'].unique())
    emp_data = payroll[payroll['Emp Name'] == emp_selected]
    st.dataframe(emp_data)
    emp_pdf = generate_pdf(emp_data, month)
    st.download_button("Download Employee PDF", data=emp_pdf, file_name=f"{emp_selected}_{month}.pdf", mime="application/pdf")

# Main Execution
if __name__ == "__main__":
    ensure_all_sheets()
    payroll_dashboard()
