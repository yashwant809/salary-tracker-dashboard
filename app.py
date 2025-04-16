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
def connect_to_sheet(sheet_name, worksheet):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDS"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    try:
        sheet = client.open(sheet_name).worksheet(worksheet)
    except gspread.exceptions.WorksheetNotFound:
        sheet = client.open(sheet_name).add_worksheet(title=worksheet, rows="100", cols="20")
    return sheet

# Load Data Functions
def load_employee_master():
    sheet = connect_to_sheet("Payroll_System", "employee_master")
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def load_advance_data():
    sheet = connect_to_sheet("Payroll_System", "advance_data")
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def load_payroll_input(month):
    sheet = connect_to_sheet("Payroll_System", "payroll_input")
    data = pd.DataFrame(sheet.get_all_records())
    return data[data['Month'] == month]

# Save login activity
def log_activity(username, action):
    try:
        sheet = connect_to_sheet("Payroll_System", "login_logs")
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
        values = [row[h] for h in headers]
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

    payroll = payroll_input.merge(emp_master, on='Emp Name', how='left')
    payroll['Per Day Salary'] = payroll['Net Salary PM'] / 30
    payroll['Monthly Salary'] = payroll['Per Day Salary'] * payroll['Working Days']
    payroll = payroll.merge(advances[['Emp Name', 'Remaining Advance']], on='Emp Name', how='left')
    payroll['Remaining Advance'] = payroll['Remaining Advance'].fillna(0)
    payroll['Final Payable'] = payroll['Monthly Salary'] - payroll['Remaining Advance']

    payroll['Paid Amount'] = payroll['Paid Amount'].fillna(0)
    payroll['Pending Amount'] = payroll['Final Payable'] - payroll['Paid Amount']

    total_needed = payroll['Final Payable'].sum()
    total_paid = payroll['Paid Amount'].sum()
    total_pending = total_needed - total_paid

    st.metric("Total Required for Payroll", f"₹{total_needed:,.2f}")
    st.metric("Total Paid", f"₹{total_paid:,.2f}")
    st.metric("Pending Balance", f"₹{total_pending:,.2f}")

    # Charts
    st.subheader("Group-wise Payroll")
    group_chart = payroll.groupby("Group")["Final Payable"].sum().reset_index()
    st.plotly_chart(px.pie(group_chart, names='Group', values='Final Payable', title='Group-wise Payroll'))

    st.subheader("Location-wise Payroll")
    location_chart = payroll.groupby("Area")["Final Payable"].sum().reset_index()
    st.plotly_chart(px.bar(location_chart, x='Area', y='Final Payable', title='Location-wise Payroll'))

    # Filter
    search = st.text_input("Search Employee")
    if search:
        payroll = payroll[payroll['Emp Name'].str.contains(search, case=False)]

    st.dataframe(payroll[['Emp Name', 'Area', 'Group', 'Department', 'Monthly Salary', 'Remaining Advance', 'Final Payable', 'Paid Amount', 'Pending Amount']])

    # Export
    pdf_data = generate_pdf(payroll, month)
    st.download_button("Download Payroll PDF", data=pdf_data, file_name=f"Payroll_{month}.pdf", mime="application/pdf")

    excel_data = generate_excel(payroll, month)
    st.download_button("Download Payroll Excel", data=excel_data, file_name=f"Payroll_{month}.xlsx", mime="application/vnd.ms-excel")

# Secure Login with Role
ADMIN_USERS = ["admin"]

def login():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""

    if st.session_state.logged_in:
        st.sidebar.write(f"Logged in as: {st.session_state.username}")
        if st.sidebar.button("Logout"):
            log_activity(st.session_state.username, "Logout")
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.experimental_rerun()
        return True
    else:
        st.sidebar.title("Login")
        user = st.sidebar.text_input("Username")
        pwd = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Login"):
            if user in st.secrets["users"] and pwd == st.secrets["users"][user]:
                st.session_state.logged_in = True
                st.session_state.username = user
                log_activity(user, "Login")
                st.success("Login successful!")
                st.experimental_rerun()
            else:
                st.error("Invalid credentials")
        return False

# Main Function
def main():
    st.set_page_config(page_title="Payroll Dashboard", layout="wide")
    if login():
        payroll_dashboard()

if __name__ == "__main__":
    main()
