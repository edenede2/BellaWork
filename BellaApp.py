import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt
import plotly.express as px


st.set_page_config(page_title="Bella Work", layout="wide")

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], 
                scopes=scopes
            )
client = gspread.authorize(credentials)

def load_data():
    spreadsheet = client.open_by_key("1RuR8lSCLeh61VQq0uHl2DMW3-vnu2IftswkR3Qt4RTM")
    sheet = spreadsheet.worksheet("Ответы на форму (1)")
    data = sheet.get_all_values()
    return data
raw_data = load_data()
header = raw_data[0]
rows = raw_data[1:]
df = pd.DataFrame(rows, columns=header)

st.title("ניתוח שאלון תקשורת")
st.write("#### נתונים גולמיים")
st.dataframe(df)

# --- Rename columns for Q1..Q15 (columns O–AC) ---
# *** IMPORTANT: verify these indices are correct! ***
question_cols = df.columns[14:29]  # O..AC
q_map = {old: f"שאלה_{i+1}" for i, old in enumerate(question_cols)}
df.rename(columns=q_map, inplace=True)

# -- DEBUG: Check which columns got renamed
st.write("### Debug: Renamed Question Columns")
st.write(question_cols)

# Convert question columns to numeric
for i in range(1, 16):
    col_name = f"שאלה_{i}"
    df[col_name] = pd.to_numeric(df[col_name], errors='coerce')

# -- DEBUG: Check if numeric conversion worked
st.write("### Debug: Questions After Conversion")
st.dataframe(df[[f"שאלה_{i}" for i in range(1,16)]].head(10))

# --- Calculate sums for the 3 patterns ---
secure_questions   = [1,3,7,10,15]
avoidant_questions = [2,4,8,12,13]
ambiv_questions    = [5,6,9,11,14]

df["sum_secure"]   = df[[f"שאלה_{q}" for q in secure_questions]].sum(axis=1)
df["sum_avoidant"] = df[[f"שאלה_{q}" for q in avoidant_questions]].sum(axis=1)
df["sum_ambiv"]    = df[[f"שאלה_{q}" for q in ambiv_questions]].sum(axis=1)

def determine_pattern(row):
    vals = [row["sum_secure"], row["sum_avoidant"], row["sum_ambiv"]]
    labels = ["תקשורת בטוחה", "תקשורת נמנעת", "תקשורת אמביוולנטית חרדה"]
    return labels[vals.index(max(vals))]

df["סוג_תקשורת"] = df.apply(determine_pattern, axis=1)

st.write("### תצוגה: סיווג סוג תקשורת")
st.dataframe(df[["sum_secure","sum_avoidant","sum_ambiv","סוג_תקשורת"]])

# --- PLOTLY Pie Chart for distribution of communication patterns ---
st.write("### התפלגות סוגי תקשורת (תרשים עוגה)")
pattern_counts = df["סוג_תקשורת"].value_counts().reset_index()
pattern_counts.columns = ["סוג_תקשורת", "counts"]
fig_pie = px.pie(
    pattern_counts,
    values="counts",
    names="סוג_תקשורת",
    title="אחוז סוגי תקשורת בקרב המשתתפים"
)
st.plotly_chart(fig_pie)

# --- Summaries by communication pattern ---
st.write("### סיכום סטטיסטי של שאלות לפי סוג תקשורת (ממוצע, סטיית תקן, כמות)")
summary_questions = df.groupby("סוג_תקשורת")[
    [f"שאלה_{i}" for i in range(1,16)]
].agg(['mean','std','count'])

st.dataframe(summary_questions)

# --- Example bar chart of average for each question by pattern (Plotly) ---
st.write("### ממוצעים בשאלות (תרשים עמודות)")
avg_by_pattern = df.groupby("סוג_תקשורת")[
    [f"שאלה_{i}" for i in range(1,16)]
].mean()

# Reshape for easier Plotly usage
avg_by_pattern_long = avg_by_pattern.reset_index().melt(
    id_vars="סוג_תקשורת",
    var_name="שאלה",
    value_name="ממוצע"
)

fig_bar = px.bar(
    avg_by_pattern_long,
    x="סוג_תקשורת",
    y="ממוצע",
    color="סוג_תקשורת",
    facet_col="שאלה",
    title="ממוצעים בשאלות לפי סוג תקשורת",
    barmode="group"
)
# This will create multiple facet columns. If it's too wide, you can tweak or
# facet by row, or just do a single chart at a time
st.plotly_chart(fig_bar)

# --- Example Scatter (sum_secure vs sum_avoidant) to see distribution ---
st.write("### פיזור: סכום בטוחה מול סכום נמנעת")
fig_scatter = px.scatter(
    df, 
    x="sum_secure", 
    y="sum_avoidant",
    color="סוג_תקשורת",
    title="Scatter: סכומי שאלות בטוחה מול נמנעת"
)
st.plotly_chart(fig_scatter)

# --- Similarly, rename and analyze section1, section2, section3 ---

st.write("### ניתוח לפי מדדים נוספים (מדד1, מדד2, מדד3) - לדוגמה")
