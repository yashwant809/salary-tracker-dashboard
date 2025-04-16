import streamlit as st
import gspread
import pandas as pd
import json
from datetime import date
from oauth2client.service_account import ServiceAccountCredentials
import io
from fpdf import FPDF

# Connect to Google Sheet
def connect_to_sheet():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDS"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open("Salary_Advance_Tracker").worksheet("master_data")  # Match your actual names
        return sheet
    except Exception as e:
        st.error(f"Error connecting to Google Sheet: {e}")
        return None

# Load Master Data
def load_employee_master():
    sheet = connect_to_sheet("Payroll_System", "employee_master")
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# Load Advances
def load_advance_data():
    sheet = connect_to_sheet("Payroll_System", "advance_data")
    data = sheet.get_all_records()
    return pd.DataFrame(data)

# Load Monthly Payroll Input
def load_payroll_input(month):
    sheet = connect_to_sheet("Payroll_System", "payroll_input")
    data = pd.DataFrame(sheet.get_all_records())
    return data[data['Month'] == month]

# Generate PDF for full payroll
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
        values = [row[h] for h in headers]
        for i, val in enumerate(values):
            pdf.cell(col_widths[i], 8, str(val), border=1)
        pdf.ln()

    return pdf.output(dest='S').encode('latin-1')

# Generate Excel file
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

    payroll = payroll_input.merge(emp_master, on='Emp Name', how='left')
    payroll['Per Day Salary'] = payroll['Net Salary PM'] / 30
    payroll['Monthly Salary'] = payroll['Per Day Salary'] * payroll['Working Days']

    payroll = payroll.merge(advances[['Emp Name', 'Remaining Advance']], on='Emp Name', how='left')
    payroll['Remaining Advance'] = payroll['Remaining Advance'].fillna(0)
    payroll['Final Payable'] = payroll['Monthly Salary'] - payroll['Remaining Advance']

    st.dataframe(payroll[['Emp Name', 'Area', 'Group', 'Department', 'Monthly Salary', 'Remaining Advance', 'Final Payable']])

    pdf_data = generate_pdf(payroll, month)
    st.download_button("Download Payroll PDF", data=pdf_data, file_name=f"Payroll_{month}.pdf", mime="application/pdf")

    excel_data = generate_excel(payroll, month)
    st.download_button("Download Payroll Excel", data=excel_data, file_name=f"Payroll_{month}.xlsx", mime="application/vnd.ms-excel")

# Secure Login using secrets
def login():
    st.sidebar.title("Login")
    user = st.sidebar.text_input("Username")
    pwd = st.sidebar.text_input("Password", type="password")
    if user in st.secrets["users"] and pwd == st.secrets["users"][user]:
        st.session_state["username"] = user
        return True
    return False

# Main Function
def main():
    st.set_page_config(page_title="Payroll Dashboard", layout="wide")

    if login():
        payroll_dashboard()
    else:
        st.warning("Please login to continue.")

if __name__ == "__main__":
    main()
