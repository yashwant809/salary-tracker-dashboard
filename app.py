import streamlit as st
import gspread
import json
import pandas as pd
from datetime import date
from oauth2client.service_account import ServiceAccountCredentials

# Google Sheets connection
def connect_to_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDS"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open("Salary_Advance_Tracker")  # Change this to your actual sheet name
    return sheet.worksheet("master_data")

# Login
def login():
    st.sidebar.title("Login")
    user = st.sidebar.text_input("Username")
    pwd = st.sidebar.text_input("Password", type="password")
    return user == "admin" and pwd == "1234"

# Dashboard view
def show_dashboard(sheet):
    st.title("Salary & Advance Dashboard")
    df = pd.DataFrame(sheet.get_all_records())
    st.dataframe(df)

# Advance entry form
def add_advance(sheet):
    st.title("Add Advance Entry")

    emp_name = st.text_input("Employee Name")
    adv_amount = st.number_input("Advance Amount", min_value=0.0, step=100.0)
    adv_date = st.date_input("Advance Date", value=date.today())

    if st.button("Submit"):
        # Append to the next row in master_data (you can customize)
        new_row = [emp_name, "", "", "", "", adv_amount, str(adv_date), "", "", "", "Advance Added"]
        sheet.append_row(new_row)
        st.success("Advance submitted successfully!")

# App Main
def main():
    st.set_page_config(page_title="Salary Advance Tracker", layout="wide")

    if login():
        sheet = connect_to_sheet()
        menu = st.sidebar.radio("Menu", ["Dashboard", "Add Advance"])

        if menu == "Dashboard":
            show_dashboard(sheet)
        elif menu == "Add Advance":
            add_advance(sheet)
    else:
        st.warning("Please enter valid credentials.")

if __name__ == "_main_":
    main()
