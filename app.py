import streamlit as st
import gspread
import json
import pandas as pd
from datetime import date
from oauth2client.service_account import ServiceAccountCredentials

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

# Login
def login():
    st.sidebar.title("Login")
    user = st.sidebar.text_input("Username")
    pwd = st.sidebar.text_input("Password", type="password")
    if user in st.secrets["users"] and pwd == st.secrets["users"][user]:
        st.session_state["username"] = user
        return True
    return False

# Show Dashboard
def show_dashboard(sheet):
    st.title("Salary & Advance Dashboard")
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        st.dataframe(df)
    except Exception as e:
        st.error(f"Error reading data: {e}")

# Add Advance Entry
def add_advance(sheet):
    st.title("Add Advance Entry")
    
    emp_name = st.text_input("Employee Name")
    doj = st.date_input("Date of Joining")
    group = st.text_input("Group")
    designation = st.text_input("Designation")
    net_salary = st.number_input("Net Salary PM", step=500.0)
    advance_taken = st.number_input("Advance Amount", step=500.0)
    advance_date = st.date_input("Advance Date", value=date.today())
    monthly_deduction = st.number_input("Monthly Deduction", step=100.0)

    if st.button("Submit"):
        try:
            row = [
                emp_name,
                str(doj),
                group,
                designation,
                net_salary,
                advance_taken,
                str(advance_date),
                monthly_deduction,
                "",  # Total Deducted (to be calculated later)
                "",  # Balance Advance (to be calculated later)
                "Advance Added"
            ]
            sheet.append_row(row)
            st.success("Advance submitted successfully!")
        except Exception as e:
            st.error(f"Error writing to sheet: {e}")

# Main app
def main():
    st.set_page_config(page_title="Salary Tracker", layout="wide")
    st.markdown("### App loaded...")

    if login():
        st.success("Login successful!")
        sheet = connect_to_sheet()

        if sheet:
            menu = st.sidebar.radio("Menu", ["Dashboard", "Add Advance"])
            if menu == "Dashboard":
                show_dashboard(sheet)
            elif menu == "Add Advance":
                add_advance(sheet)
    else:
        st.info("Please login with admin / 1234")

if __name__ == "__main__":
    main()
