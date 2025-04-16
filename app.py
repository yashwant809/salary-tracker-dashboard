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
    data.columns = data.columns.str.strip()
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

# Admin Section: Add/Delete Employees
def admin_controls():
    st.subheader("Admin Controls")
    tab1, tab2 = st.tabs(["Add Employee", "Delete Employee"])

    with tab1:
        st.markdown("### Add New Employee")
        emp = st.text_input("Employee Name")
        doj = st.date_input("Date of Joining", date.today())
        grp = st.text_input("Group")
        dept = st.text_input("Department")
        area = st.text_input("Area")
        net_sal = st.number_input("Net Salary PM", min_value=0)
        if st.button("Add Employee"):
            sheet = connect_to_sheet("Salary_Advance_Tracker", "master_data")
            sheet.append_row([emp, doj.strftime('%Y-%m-%d'), grp, dept, area, net_sal])
            st.success("Employee added successfully!")

    with tab2:
        st.markdown("### Delete Employee")
        emp_master = load_employee_master()
        emp_list = emp_master['Emp Name'].tolist()
        emp_to_delete = st.selectbox("Select Employee", emp_list)
        if st.button("Delete Employee"):
            sheet = connect_to_sheet("Salary_Advance_Tracker", "master_data")
            cell = sheet.find(emp_to_delete)
            if cell:
                sheet.delete_rows(cell.row)
                st.success(f"Deleted {emp_to_delete}")

# Main Dashboard
def payroll_dashboard():
    st.title("Payroll Dashboard")
    month = st.selectbox("Select Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])

    emp_master = load_employee_master()
    advances = load_advance_data()
    payroll_input = load_payroll_input(month)

    if 'Emp Name' not in emp_master.columns or 'Emp Name' not in payroll_input.columns:
        st.error("Missing 'Emp Name' column in either master_data or payroll_input sheet.")
        st.stop()

    payroll = payroll_input.merge(emp_master, on='Emp Name', how='left')
    payroll['Per Day Salary'] = payroll['Net Salary PM'] / 30
    payroll['Monthly Salary'] = payroll['Per Day Salary'] * payroll['Working Days']
    payroll = payroll.merge(advances[['Emp Name', 'Remaining Advance']], on='Emp Name', how='left')
    payroll['Remaining Advance'] = payroll['Remaining Advance'].fillna(0)
    payroll['Final Payable'] = payroll['Monthly Salary'] - payroll['Remaining Advance']

    st.markdown("### Full Payroll Report")
    search = st.text_input("Search by Employee Name")
    if search:
        payroll = payroll[payroll['Emp Name'].str.contains(search, case=False)]

    st.dataframe(payroll[['Emp Name', 'Area', 'Group', 'Department', 'Monthly Salary', 'Remaining Advance', 'Final Payable']])

    pdf_data = generate_pdf(payroll, month)
    st.download_button("Download Payroll PDF", data=pdf_data, file_name=f"Payroll_{month}.pdf", mime="application/pdf")

    excel_data = generate_excel(payroll, month)
    st.download_button("Download Payroll Excel", data=excel_data, file_name=f"Payroll_{month}.xlsx", mime="application/vnd.ms-excel")

# Secure Login with Role-based Access
def login():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.role = ""

    if st.session_state.logged_in:
        st.sidebar.write(f"Logged in as: {st.session_state.username} ({st.session_state.role})")
        if st.sidebar.button("Logout"):
            log_activity(st.session_state.username, "Logout")
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()
        return True
    else:
        st.sidebar.title("Login")
        user = st.sidebar.text_input("Username")
        pwd = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Login"):
            if user in st.secrets["users"] and pwd == st.secrets["users"][user]["password"]:
                st.session_state.logged_in = True
                st.session_state.username = user
                st.session_state.role = st.secrets["users"][user]["role"]
                log_activity(user, "Login")
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials")
        return False

# Main Function
def main():
    st.set_page_config(page_title="Payroll Dashboard", layout="wide")
    ensure_all_sheets()
    if login():
        payroll_dashboard()
        if st.session_state.role == "admin":
            admin_controls()

if __name__ == "__main__":
    main()
