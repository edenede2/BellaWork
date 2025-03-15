import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import re

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

# --- Utility: extract numeric from strings like '3. нетрудно' -> 3
def extract_numeric(cell_value):
    match = re.search(r'\\d+', str(cell_value))
    return int(match.group(0)) if match else None

# --- Identify columns for Q1..Q15, section1, section2, section3
question_cols  = df.columns[14:29]   # O..AC
section1_cols  = df.columns[29:37]  # AD..AK
section2_cols  = df.columns[37:45]  # AL..AS
section3_cols  = df.columns[45:57]  # AT..BE

# --- Rename Q1..Q15 columns to שאלה_1..שאלה_15
q_map = {old: f"שאלה_{i+1}" for i, old in enumerate(question_cols)}
df.rename(columns=q_map, inplace=True)

# --- Rename the section columns to מדד1_1.., מדד2_1.., מדד3_1..
df_sections = {
    "מדד1": section1_cols,
    "מדד2": section2_cols,
    "מדד3": section3_cols
}
for section_name, cols in df_sections.items():
    rename_dict = {old: f"{section_name}_{i+1}" for i, old in enumerate(cols)}
    df.rename(columns=rename_dict, inplace=True)

# --- Gather the ACTUAL renamed columns so we can parse them
renamed_questions = list(q_map.values())  # e.g. ['שאלה_1', 'שאלה_2', ... 'שאלה_15']
renamed_sections = []
for section_name, cols in df_sections.items():
    # Each original column in `cols` is now renamed to f"{section_name}_{i+1}"
    for i, old_col in enumerate(cols):
        new_col = f"{section_name}_{i+1}"
        renamed_sections.append(new_col)

all_renamed_cols = renamed_questions + renamed_sections

# --- Convert those renamed columns to numeric
for col in all_renamed_cols:
    df[col] = df[col].apply(extract_numeric)           # from str to int
    df[col] = pd.to_numeric(df[col], errors='coerce')  # ensure numeric

# =============================================================================
#  Now that the columns are numeric, do your communication pattern logic
# =============================================================================

secure_questions   = [1, 3, 7, 10, 15]
avoidant_questions = [2, 4, 8, 12, 13]
ambiv_questions    = [5, 6, 9, 11, 14]

# Sum up the relevant questions
df["sum_secure"]   = df[[f"שאלה_{q}" for q in secure_questions]].sum(axis=1)
df["sum_avoidant"] = df[[f"שאלה_{q}" for q in avoidant_questions]].sum(axis=1)
df["sum_ambiv"]    = df[[f"שאלה_{q}" for q in ambiv_questions]].sum(axis=1)

def determine_pattern(row):
    vals = [row["sum_secure"], row["sum_avoidant"], row["sum_ambiv"]]
    labels = ["תקשורת בטוחה", "תקשורת נמנעת", "תקשורת אמביוולנטית חרדה"]
    return labels[vals.index(max(vals))]

df["סוג_תקשורת"] = df.apply(determine_pattern, axis=1)

# --- Display communication patterns
st.write("### תצוגה: סיווג סוג תקשורת")
st.dataframe(df[["sum_secure", "sum_avoidant", "sum_ambiv", "סוג_תקשורת"]])

# --- Pie Chart
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

# --- Summaries by communication pattern
st.write("### סיכום סטטיסטי של שאלות לפי סוג תקשורת (ממוצע, סטיית תקן, כמות)")
question_cols_renamed = [f"שאלה_{i}" for i in range(1,16)]
summary_questions = df.groupby("סוג_תקשורת")[question_cols_renamed].agg(['mean','std','count'])
st.dataframe(summary_questions)

# --- Bar Chart of Averages
st.write("### ממוצעים בשאלות (תרשים עמודות)")
avg_by_pattern = df.groupby("סוג_תקשורת")[question_cols_renamed].mean()
df_long = avg_by_pattern.reset_index().melt(
    id_vars="סוג_תקשורת", var_name="שאלה", value_name="ממוצע"
)
fig_bar = px.bar(
    df_long,
    x="סוג_תקשורת",
    y="ממוצע",
    color="סוג_תקשורת",
    facet_col="שאלה",
    title="ממוצעים בשאלות לפי סוג תקשורת",
    barmode="group"
)
st.plotly_chart(fig_bar)

# --- Scatter Plot
st.write("### פיזור: סכום בטוחה מול סכום נמנעת")
fig_scatter = px.scatter(
    df, 
    x="sum_secure",
    y="sum_avoidant",
    color="סוג_תקשורת",
    title="Scatter: סכומי שאלות בטוחה מול נמנעת"
)
st.plotly_chart(fig_scatter)

# --- Summary for Additional Sections
for section_name, original_cols in df_sections.items():
    st.write(f"### סיכום סטטיסטי עבור {section_name}")
    # each original col got renamed to e.g. מדד1_1, מדד1_2, ...
    renamed_cols = [f"{section_name}_{i+1}" for i in range(len(original_cols))]
    summary_sec = df.groupby("סוג_תקשורת")[renamed_cols].agg(['mean','std','count'])
    st.dataframe(summary_sec)

st.write("### ניתוח לפי מדדים נוספים (מדד1, מדד2, מדד3) - לדוגמה")