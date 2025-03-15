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

# Function to extract numeric values from strings
def extract_numeric(cell_value):
    match = re.search(r'\d+', str(cell_value))
    return int(match.group(0)) if match else None

# Define column indices
question_cols = df.columns[14:29]  # O-AC (Questions 1-15 for communication patterns)
section1_cols = df.columns[29:37]  # AD-AK
section2_cols = df.columns[37:45]  # AL-AS
section3_cols = df.columns[45:57]  # AT-BE

# Rename columns for clarity
q_map = {old: f"שאלה_{i+1}" for i, old in enumerate(question_cols)}
df.rename(columns=q_map, inplace=True)

df_sections = {"מדד1": section1_cols, "מדד2": section2_cols, "מדד3": section3_cols}
for section_name, cols in df_sections.items():
    df.rename(columns={old: f"{section_name}_{i+1}" for i, old in enumerate(cols)}, inplace=True)

# Convert all question and section columns to numeric
for col in list(q_map.values()) + list(df_sections.keys()):
    df[col] = df[col].apply(extract_numeric)
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Communication pattern calculation
secure_questions = [1, 3, 7, 10, 15]
avoidant_questions = [2, 4, 8, 12, 13]
ambiv_questions = [5, 6, 9, 11, 14]

df["sum_secure"] = df[[f"שאלה_{q}" for q in secure_questions]].sum(axis=1)
df["sum_avoidant"] = df[[f"שאלה_{q}" for q in avoidant_questions]].sum(axis=1)
df["sum_ambiv"] = df[[f"שאלה_{q}" for q in ambiv_questions]].sum(axis=1)

def determine_pattern(row):
    vals = [row["sum_secure"], row["sum_avoidant"], row["sum_ambiv"]]
    labels = ["תקשורת בטוחה", "תקשורת נמנעת", "תקשורת אמביוולנטית חרדה"]
    return labels[vals.index(max(vals))]

df["סוג_תקשורת"] = df.apply(determine_pattern, axis=1)

# Display communication patterns
st.write("### תצוגה: סיווג סוג תקשורת")
st.dataframe(df[["sum_secure", "sum_avoidant", "sum_ambiv", "סוג_תקשורת"]])

# Pie Chart - Communication Pattern Distribution
st.write("### התפלגות סוגי תקשורת (תרשים עוגה)")
pattern_counts = df["סוג_תקשורת"].value_counts().reset_index()
pattern_counts.columns = ["סוג_תקשורת", "counts"]
fig_pie = px.pie(pattern_counts, values="counts", names="סוג_תקשורת", title="אחוז סוגי תקשורת בקרב המשתתפים")
st.plotly_chart(fig_pie)

# Statistical Summary by Communication Pattern
st.write("### סיכום סטטיסטי של שאלות לפי סוג תקשורת (ממוצע, סטיית תקן, כמות)")
summary_questions = df.groupby("סוג_תקשורת")[[f"שאלה_{i}" for i in range(1, 16)]].agg(['mean', 'std', 'count'])
st.dataframe(summary_questions)

# Bar Chart of Average Scores by Question
st.write("### ממוצעים בשאלות (תרשים עמודות)")
avg_by_pattern = df.groupby("סוג_תקשורת")[[f"שאלה_{i}" for i in range(1, 16)]].mean()

df_long = avg_by_pattern.reset_index().melt(id_vars="סוג_תקשורת", var_name="שאלה", value_name="ממוצע")
fig_bar = px.bar(df_long, x="סוג_תקשורת", y="ממוצע", color="סוג_תקשורת", facet_col="שאלה", title="ממוצעים בשאלות לפי סוג תקשורת", barmode="group")
st.plotly_chart(fig_bar)

# Scatter Plot - Secure vs Avoidant
st.write("### פיזור: סכום בטוחה מול סכום נמנעת")
fig_scatter = px.scatter(df, x="sum_secure", y="sum_avoidant", color="סוג_תקשורת", title="Scatter: סכומי שאלות בטוחה מול נמנעת")
st.plotly_chart(fig_scatter)

# Statistical Summary for Additional Sections
for section_name in df_sections.keys():
    st.write(f"### סיכום סטטיסטי עבור {section_name}")
    summary_sec = df.groupby("סוג_תקשורת")[list(df_sections[section_name])].agg(['mean', 'std', 'count'])
    st.dataframe(summary_sec)

st.write("### ניתוח לפי מדדים נוספים (מדד1, מדד2, מדד3) - לדוגמה")