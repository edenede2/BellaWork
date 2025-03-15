import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import pymongo as pm
from collections import defaultdict


# Set page configuration
st.set_page_config(page_title="Bella Work", layout="centered")

scopes = ["https://www.googleapis.com/auth/spreadsheets"]

credentials = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], scopes=scopes
            )

client = gspread.authorize(credentials)

# Load data from Google Sheets
def load_data():
    spreadsheet = client.open_by_key("1RuR8lSCLeh61VQq0uHl2DMW3-vnu2IftswkR3Qt4RTM")
    sheet = spreadsheet.worksheet("Ответы на форму (1)")
    data = sheet.get_all_values()
    return data


df = pd.DataFrame(load_data()[1:], columns=load_data()[0])

st.title("Bella Work")

st.write("## Data from Google Sheets")
st.write(df)



