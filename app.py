import streamlit as st
import gspread
import json
import pandas as pd
from datetime import date
from oauth2client.service_account import ServiceAccountCredentials

# Connect to Google Sheet using Streamlit secrets
def connect_to_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDS"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open("Salary_Advance_Tracker")  # Change to your actual Sheet name
    return sheet.worksheet("master_data")

# Login (simple)
def login():
    st.sidebar.title("Login")
    user = st.sidebar.text_input("Username")
    pwd = st.sidebar.text_input("Password", type="password")
    return user == "admin" and pwd == "1234"

# Dashboard view
def show_dashboard(sheet):
    st.title("Employee Salary Dashboard")
    try:
        df = pd.DataFrame(sheet.get_all_records())
        st.dataframe(df)
    except Exception as e:
        st.error(f"Failed to fetch data: {e}")

# Advance entry form
def add_advance(sheet):
    st.title("Add Advance Entry")

    emp_name = st.text_input("Employee Name")
    adv_amount = st.number_input("Advance Amount", min_value=0.0, step=100.0)
    adv_date = st.date_input("Advance Date", value=date.today())

    if st.button("Submit"):
        try:
            new_row = [emp_name, "", "", "", "", adv_amount, str(adv_date), "", "", "", "Advance Added"]
            sheet.append_row(new_row)
            st.success("Advance submitted successfully!")
        except Exception as e:
            st.error(f"Error submitting advance: {e}")

# Main App
def main():
    st.set_page_config(page_title="Salary Advance Tracker", layout="wide")
    st.write("App loaded...")  # Debug line to confirm app renders

    if login():
        st.success("Login successful!")
        try:
            sheet = connect_to_sheet()
            menu = st.sidebar.radio("Menu", ["Dashboard", "Add Advance"])

            if menu == "Dashboard":
                show_dashboard(sheet)
            elif menu == "Add Advance":
                add_advance(sheet)
        except Exception as e:
            st.error(f"Error loading sheet: {e}")
    else:
        st.info("Please login using 'admin' / '1234'")

if __name__ == "__main__":
    main()
