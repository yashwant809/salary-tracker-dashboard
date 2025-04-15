# app.py
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import date

# Authenticate Google Sheets
def get_sheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open("Your Google Sheet Name")  # Replace with actual name
    return sheet.worksheet("master_data")

# Login (simple demo login)
def login():
    st.sidebar.title("Login")
    user = st.sidebar.text_input("Username")
    pwd = st.sidebar.text_input("Password", type="password")
    if user == "admin" and pwd == "1234":
        return True
    else:
        return False

# Dashboard display
def show_dashboard(sheet):
    st.title("Employee Salary Dashboard")
    df = pd.DataFrame(sheet.get_all_records())
    st.dataframe(df)

# Advance Entry
def add_advance(sheet):
    st.header("Add Advance Entry")
    name = st.text_input("Employee Name")
    adv = st.number_input("Advance Amount", min_value=0.0)
    adv_date = st.date_input("Advance Date", value=date.today())

    if st.button("Submit Advance"):
        # Append a new row (you may customize logic to match columns)
        sheet.append_row([name, "", "", "", "", adv, str(adv_date), "", "", "", "Advance added"])
        st.success("Advance recorded!")

# Main function
def main():
    if login():
        sheet = get_sheet()
        option = st.sidebar.radio("Navigation", ["Dashboard", "Add Advance"])
        if option == "Dashboard":
            show_dashboard(sheet)
        elif option == "Add Advance":
            add_advance(sheet)
    else:
        st.warning("Enter correct credentials")

if __name__ == "_main_":
    main()
