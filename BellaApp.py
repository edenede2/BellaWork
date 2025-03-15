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
    match = re.search(r'\d+', str(cell_value))
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

# --- Display the cleaned data
st.write("#### נתונים מעודכנים")
st.dataframe(df)

# =============================================================================
#  Now that the columns are numeric, do your communication pattern logic
# =============================================================================

secure_questions   = [1, 3, 7, 10, 15]
avoidant_questions = [2, 4, 8, 12, 13]
ambiv_questions    = [5, 6, 9, 11, 14]

df["sum_secure"]   = df[[f"שאלה_{q}" for q in secure_questions]].sum(axis=1)
df["sum_avoidant"] = df[[f"שאלה_{q}" for q in avoidant_questions]].sum(axis=1)
df["sum_ambiv"]    = df[[f"שאלה_{q}" for q in ambiv_questions]].sum(axis=1)

def determine_pattern(row):
    vals = [row["sum_secure"], row["sum_avoidant"], row["sum_ambiv"]]
    labels = ["תקשורת בטוחה", "תקשורת נמנעת", "תקשורת אמביוולנטית חרדה"]
    return labels[vals.index(max(vals))]

df["סוג_תקשורת"] = df.apply(determine_pattern, axis=1)

# =============================================================================
#  SIDEBAR - Interactive Controls
# =============================================================================
st.sidebar.title("התאמה אישית")
# Let user pick grouping variable:
possible_group_cols = ["סוג_תקשורת"]  # Add more columns if you want to let user group by something else
chosen_group_col = st.sidebar.selectbox("בחר משתנה לקיבוץ (Grouping):", options=possible_group_cols)

# Add a checkbox to display raw data
show_data = st.sidebar.checkbox("הצג נתונים גולמיים", value=False)
if show_data:
    st.write("#### נתונים גולמיים")
    st.dataframe(df)

# =============================================================================
#  Display Summaries & Plots by the chosen grouping
# =============================================================================

st.write("### סיכום סטטיסטי לפי קבוצות")
question_cols_renamed = [f"שאלה_{i}" for i in range(1,16)]

summary_questions = df.groupby(chosen_group_col)[question_cols_renamed].agg(['mean','std','count'])
st.write(f"#### סיכום סטטיסטי לשאלות (1-15) לפי {chosen_group_col}")
st.dataframe(summary_questions)

# Section Summaries - sums for each section
def calc_section_sum(section_name, original_cols):
    # original_cols might be something like 8 columns -> renamed to מדד1_1..מדד1_8
    renamed_cols = [f"{section_name}_{i+1}" for i in range(len(original_cols))]
    # create a new column for total
    total_col_name = f"sum_{section_name}"
    df[total_col_name] = df[renamed_cols].sum(axis=1)
    return total_col_name

section_totals = []
for section_name, original_cols in df_sections.items():
    col_sum = calc_section_sum(section_name, original_cols)
    section_totals.append(col_sum)

# Show the user a table of sums for each section
st.write("### סיכום ניקוד כולל עבור כל מדד")
st.dataframe(df[section_totals + [chosen_group_col]].head(10))

# Summaries of each section by group
for section_name, original_cols in df_sections.items():
    renamed_cols = [f"{section_name}_{i+1}" for i in range(len(original_cols))]
    st.write(f"#### סיכום סטטיסטי עבור {section_name}")
    summary_sec = df.groupby(chosen_group_col)[renamed_cols].agg(['mean','std','count'])
    st.dataframe(summary_sec)

# =============================================================================
#  EXAMPLE PLOTS
# =============================================================================

st.write("### התפלגות סוג תקשורת (תרשים עוגה)")
pattern_counts = df["סוג_תקשורת"].value_counts().reset_index()
pattern_counts.columns = ["סוג_תקשורת", "counts"]
fig_pie = px.pie(pattern_counts, values="counts", names="סוג_תקשורת",
                 title="אחוז סוגי תקשורת בקרב המשתתפים")
st.plotly_chart(fig_pie)

# Bar chart of average question scores by group
st.write("### ממוצעים בשאלות (תרשים עמודות)")
avg_by_pattern = df.groupby(chosen_group_col)[question_cols_renamed].mean().reset_index()
df_long = avg_by_pattern.melt(id_vars=chosen_group_col, var_name="שאלה", value_name="ממוצע")
fig_bar = px.bar(df_long, x=chosen_group_col, y="ממוצע", color=chosen_group_col,
                 facet_col="שאלה", barmode="group",
                 title=f"ממוצעים בשאלות לפי {chosen_group_col}")
st.plotly_chart(fig_bar)

# Scatter Plot
st.write("### פיזור: סכום בטוחה מול סכום נמנעת")
fig_scatter = px.scatter(df, x="sum_secure", y="sum_avoidant",
                         color=chosen_group_col,
                         title=f"Scatter: סכומי שאלות בטוחה מול נמנעת לפי {chosen_group_col}")
st.plotly_chart(fig_scatter)

# =============================================================================
#  Group Comparison: pick two groups and compare means
# =============================================================================
st.write("### השוואה בין קבוצות")
unique_groups = df[chosen_group_col].unique()
if len(unique_groups) < 2:
    st.write("לא ניתן להשוות קבוצות, כי יש פחות משתי קבוצות.")
else:
    group_choices = st.multiselect("בחר שתי קבוצות להשוואה",
                                   options=unique_groups,
                                   default=unique_groups[:2])
    if len(group_choices) == 2:
        # Filter data for just those two groups
        group_a, group_b = group_choices
        df_a = df[df[chosen_group_col] == group_a]
        df_b = df[df[chosen_group_col] == group_b]
        
        # Compare means for questions
        mean_a = df_a[question_cols_renamed].mean()
        mean_b = df_b[question_cols_renamed].mean()
        diff = mean_a - mean_b
        
        compare_df = pd.DataFrame({
            f"ממוצע-{group_a}": mean_a,
            f"ממוצע-{group_b}": mean_b,
            "הפרש (A - B)": diff
        })
        st.write("#### השוואת ממוצעים לשאלות בין שתי קבוצות")
        st.dataframe(compare_df)

        # Optional: do the same for sections
        compare_secs = {}
        for total_col in section_totals:
            compare_secs[f"{total_col}-{group_a}"] = df_a[total_col].mean()
            compare_secs[f"{total_col}-{group_b}"] = df_b[total_col].mean()
            compare_secs[f"diff_{total_col}"] = compare_secs[f"{total_col}-{group_a}"] - compare_secs[f"{total_col}-{group_b}"]
        st.write("#### השוואת ממוצעים סה\"כ מדדים בין שתי קבוצות")
        st.dataframe(pd.DataFrame([compare_secs]))

st.write("### ניתוח לפי מדדים נוספים - סיום")