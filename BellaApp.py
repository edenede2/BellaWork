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

raw_data = load_data()  # raw_data is a list of lists
header = raw_data[0]
rows = raw_data[1:]  # everything below the header

# Create a DataFrame
df = pd.DataFrame(rows, columns=header)

# -------------------------------------------------------------
# 2) PAGE HEADER (with RTL styling for Hebrew)
# -------------------------------------------------------------
st.markdown(
    """
    <div style="direction:rtl; text-align:right">
    <h1>ניתוח שאלון תקשורת</h1>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div style="direction:rtl; text-align:right">
    <p>להלן הנתונים הגולמיים כפי שנקלטו מטופס Google</p>
    </div>
    """,
    unsafe_allow_html=True
)

# Show the raw dataframe
st.dataframe(df)

# -------------------------------------------------------------
# 3) RENAME COLUMNS & CONVERT TO NUMERIC
#    Make sure the slices match your actual columns
# -------------------------------------------------------------
# For example, columns O–AC = indices 14..28 (that’s 15 columns).
# Double-check that these are indeed your Q1..Q15.
question_cols = df.columns[14:29]  # 14..28 -> 15 columns total
st.write("**DEBUG** question_cols:", list(question_cols))  # For debugging

# Rename them to שאלה_1..שאלה_15
mapping = {}
for i, old_col in enumerate(question_cols):
    mapping[old_col] = f"שאלה_{i+1}"

df.rename(columns=mapping, inplace=True)

# Convert question columns to numeric
for i in range(1, 16):
    q_col = f"שאלה_{i}"
    df[q_col] = pd.to_numeric(df[q_col], errors='coerce')

# -------------------------------------------------------------
# 4) CALCULATE SUMS & DETERMINE PATTERN
# -------------------------------------------------------------
# high: Q1,3,7,10,15 => תקשורת בטוחה
secure_questions   = [1, 3, 7, 10, 15]
# high: Q2,4,8,12,13 => תקשורת נמנעת
avoidant_questions = [2, 4, 8, 12, 13]
# high: Q5,6,9,11,14 => תקשורת אמביוולנטית חרדה
ambiv_questions    = [5, 6, 9, 11, 14]

df["sum_secure"]   = df[[f"שאלה_{q}" for q in secure_questions]].sum(axis=1)
df["sum_avoidant"] = df[[f"שאלה_{q}" for q in avoidant_questions]].sum(axis=1)
df["sum_ambiv"]    = df[[f"שאלה_{q}" for q in ambiv_questions]].sum(axis=1)

def determine_pattern(row):
    # Pick the pattern whose sum is highest
    secure_val = row["sum_secure"]
    avoid_val  = row["sum_avoidant"]
    ambiv_val  = row["sum_ambiv"]
    max_val = max(secure_val, avoid_val, ambiv_val)
    if max_val == secure_val:
        return "תקשורת בטוחה"
    elif max_val == avoid_val:
        return "תקשורת נמנעת"
    else:
        return "תקשורת אמביוולנטית חרדה"

df["סוג_תקשורת"] = df.apply(determine_pattern, axis=1)

# -------------------------------------------------------------
# 5) DISPLAY A DEBUG TABLE
# -------------------------------------------------------------
st.markdown(
    """
    <div style="direction:rtl; text-align:right">
    <h3>סיווג סוג תקשורת</h3>
    </div>
    """,
    unsafe_allow_html=True
)
st.dataframe(df[["sum_secure","sum_avoidant","sum_ambiv","סוג_תקשורת"]])

# -------------------------------------------------------------
# 6) PLOTLY EXAMPLES
# -------------------------------------------------------------
# 6.1) Pie chart - distribution of communication patterns
st.markdown(
    """
    <div style="direction:rtl; text-align:right">
    <h3>התפלגות סוגי תקשורת (תרשים עוגה)</h3>
    </div>
    """,
    unsafe_allow_html=True
)
pattern_counts = df["סוג_תקשורת"].value_counts().reset_index()
pattern_counts.columns = ["סוג_תקשורת", "נבדקים"]

fig_pie = px.pie(
    pattern_counts, 
    names="סוג_תקשורת", 
    values="נבדקים", 
    title="אחוז סוגי תקשורת"
)
st.plotly_chart(fig_pie, use_container_width=True)

# 6.2) Bar chart - average score in each question grouped by communication pattern
st.markdown(
    """
    <div style="direction:rtl; text-align:right">
    <h3>ממוצע ניקוד לכל שאלה לפי סוג תקשורת</h3>
    </div>
    """,
    unsafe_allow_html=True
)
# Group and compute mean
avg_by_pattern = df.groupby("סוג_תקשורת")[[f"שאלה_{i}" for i in range(1,16)]].mean().reset_index()
# Melt for tidy format (so we can do one figure with question on x-axis)
melted = avg_by_pattern.melt(
    id_vars=["סוג_תקשורת"],
    var_name="שאלה",
    value_name="ממוצע"
)

fig_bar = px.bar(
    melted, 
    x="שאלה", 
    y="ממוצע", 
    color="סוג_תקשורת", 
    barmode="group",
    title="ממוצע ניקוד לשאלה לפי סוג תקשורת"
)
st.plotly_chart(fig_bar, use_container_width=True)

# 6.3) Scatter example - sum_secure vs. sum_avoidant, color by pattern
st.markdown(
    """
    <div style="direction:rtl; text-align:right">
    <h3>דוגמה: תרשים פיזור</h3>
    <p>סכום בטוחה לעומת סכום נמנעת, צבוע לפי סוג תקשורת</p>
    </div>
    """,
    unsafe_allow_html=True
)
fig_scatter = px.scatter(
    df, 
    x="sum_secure", 
    y="sum_avoidant", 
    color="סוג_תקשורת",
    labels={"sum_secure": "סכום בטוחה", "sum_avoidant": "סכום נמנעת"},
    title="תרשים פיזור: סכום בטוחה מול סכום נמנעת"
)
st.plotly_chart(fig_scatter, use_container_width=True)

# -------------------------------------------------------------
# 7) DEBUG: CHECK IF YOU STILL GET ALL ZEROS
#    - Possibly the slices are off or the data is not numeric
# -------------------------------------------------------------
st.write("**DEBUG** - כמה שורות יש לנו?", len(df))
st.write("**DEBUG** - דוגמה לחלק מעמודות השאלות:", df[[f"שאלה_{i}" for i in range(1, 6)]].head(10))