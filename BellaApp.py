import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt

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
# Example (check exact indexing!)
question_cols = df.columns[14:29]  # O..AC
q_map = {old: f"שאלה_{i+1}" for i, old in enumerate(question_cols)}
df.rename(columns=q_map, inplace=True)

# Convert question columns to numeric
for i in range(1, 16):
    df[f"שאלה_{i}"] = pd.to_numeric(df[f"שאלה_{i}"], errors='coerce')

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

# --- Display a pie chart of distribution of communication patterns ---
st.write("### התפלגות סוגי תקשורת (תרשים עוגה)")
fig, ax = plt.subplots()
pattern_counts = df["סוג_תקשורת"].value_counts()
ax.pie(pattern_counts, labels=pattern_counts.index, autopct='%1.1f%%')
ax.set_title("אחוז סוגי תקשורת בקרב המשתתפים")
st.pyplot(fig)

# --- Summaries by communication pattern ---
st.write("### סיכום סטטיסטי של שאלות לפי סוג תקשורת (ממוצע, סטיית תקן, כמות)")
summary_questions = df.groupby("סוג_תקשורת")[[f"שאלה_{i}" for i in range(1,16)]].agg(['mean','std','count'])
st.dataframe(summary_questions)

# --- Example bar chart of average for each question by pattern ---
st.write("### ממוצעים בשאלות (תרשים עמודות)")
avg_by_pattern = df.groupby("סוג_תקשורת")[[f"שאלה_{i}" for i in range(1,16)]].mean()
for q in avg_by_pattern.columns:
    fig_q, ax_q = plt.subplots()
    avg_by_pattern[q].plot(kind='bar', ax=ax_q)
    ax_q.set_title(f"ממוצע עבור {q} לפי סוג תקשורת")
    ax_q.set_ylabel("ממוצע ניקוד")
    ax_q.set_xlabel("סוג תקשורת")
    st.pyplot(fig_q)

# --- Similarly, rename and analyze section1, section2, section3 ---
# Example below: check the actual column indexes
section1_cols = df.columns[29:37]  # rename them to מדד1_1 ...
# etc. Then do groupby summaries or create plots as needed

st.write("### ניתוח לפי מדדים נוספים (מדד1, מדד2, מדד3), דוגמה...")
# (Add your code similarly)
