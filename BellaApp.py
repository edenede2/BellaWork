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
    "BAOS": section1_cols,
    "BPAS": section2_cols,
    "BSAS": section3_cols
}
for section_name, cols in df_sections.items():
    rename_dict = {old: f"{section_name}_{i+1}" for i, old in enumerate(cols)}
    df.rename(columns=rename_dict, inplace=True)

# --- Gather the ACTUAL renamed columns so we can parse them
renamed_questions = list(q_map.values())  # e.g. ['שאלה_1' ... 'שאלה_15']
renamed_sections = []
for section_name, cols in df_sections.items():
    for i, old_col in enumerate(cols):
        new_col = f"{section_name}_{i+1}"
        renamed_sections.append(new_col)

all_renamed_cols = renamed_questions + renamed_sections

# --- Convert those renamed columns to numeric
for col in all_renamed_cols:
    df[col] = df[col].apply(extract_numeric)
    df[col] = pd.to_numeric(df[col], errors='coerce')

# --- Display the cleaned data
st.write("#### נתונים מעודכנים")
st.dataframe(df)

# =============================================================================
#  Communication pattern logic
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
possible_group_cols = ["סוג_תקשורת"]
chosen_group_col = st.sidebar.selectbox("בחר משתנה לקיבוץ (Grouping):", options=possible_group_cols)

# Add a checkbox to display raw data
show_data = st.sidebar.checkbox("הצג נתונים גולמיים", value=False)
if show_data:
    st.write("#### נתונים גולמיים")
    st.dataframe(df)

# =============================================================================
#  Section Summaries
# =============================================================================

def calc_section_sum(section_name, original_cols):
    renamed_cols = [f"{section_name}_{i+1}" for i in range(len(original_cols))]
    total_col_name = f"sum_{section_name}"
    df[total_col_name] = df[renamed_cols].sum(axis=1)
    return total_col_name

section_totals = []
for section_name, original_cols in df_sections.items():
    total_col = calc_section_sum(section_name, original_cols)
    section_totals.append(total_col)

st.write("### סיכום ניקוד כולל עבור כל מדד")
st.dataframe(df[section_totals + ["סוג_תקשורת"]].head(10))

# =============================================================================
#  Basic Summaries & Plots
# =============================================================================
st.markdown("## ASQ - סיכום סטטיסטי ותרשימים")

st.write("### סיכום סטטיסטי לשאלות (1–15) לפי תקשורת")

question_cols_renamed = [f"שאלה_{i}" for i in range(1,16)]
summary_questions = df.groupby("סוג_תקשורת")[question_cols_renamed].agg(['mean','std','count']).T
# Change the metrics columns to hebrew
column_mapping = {
    ('mean', 'שאלה_' + str(i)): 'ממוצע_שאלה_' + str(i) for i in range(1, 16)
}
column_mapping.update({
    ('std', 'שאלה_' + str(i)): 'סטיית_תקן_שאלה_' + str(i) for i in range(1, 16)
})
column_mapping.update({
    ('count', 'שאלה_' + str(i)): 'ספירת_שאלה_' + str(i) for i in range(1, 16)
})
summary_questions = summary_questions.rename(columns=lambda x: column_mapping.get(x, x))

# summary_questions = summary_questions.rename(columns=map)
st.dataframe(summary_questions)

# Summaries of each section by group
st.write("### Ceriterion Summaries")
# Generate columns for each criterion section
col1, col2, col3 = st.columns(3)

# # with col1:
# st.write("#### BAOS - סיכום")
# df_baos = df.groupby("סוג_תקשורת")[section1_cols].agg(['mean', 'std', 'count'])
# df_baos.columns = [f"BAOS_{i+1}" for i in range(len(section1_cols))]
# df_baos = df_baos.reset_index()


# group by communication type and summarize BAOS section
df[[f"BAOS_{i+1}" for i in range(len(section1_cols))]] = df[[f"BAOS_{i+1}" for i in range(len(section1_cols))]].apply(pd.to_numeric, errors='coerce')
st.dataframe(df[[f"BAOS_{i+1}" for i in range(len(section1_cols))]].describe().T)

# with col2:
st.write("#### BPAS - סיכום")
df[[f"BPAS_{i+1}" for i in range(len(section2_cols))]] = df[[f"BPAS_{i+1}" for i in range(len(section2_cols))]].apply(pd.to_numeric, errors='coerce')
st.dataframe(df[[f"BPAS_{i+1}" for i in range(len(section2_cols))]].describe().T)

# with col3:
st.write("#### BSAS - סיכום")
df[[f"BSAS_{i+1}" for i in range(len(section3_cols))]] = df[[f"BSAS_{i+1}" for i in range(len(section3_cols))]].apply(pd.to_numeric, errors='coerce')
st.dataframe(df[[f"BSAS_{i+1}" for i in range(len(section3_cols))]].describe().T)


# for section_name, original_cols in df_sections.items():

#     renamed_cols = [f"{section_name}_{i+1}" for i in range(len(original_cols))]
#     summary_sec = df.groupby("סוג_תקשורת")[renamed_cols].agg(['mean','std','count'])
#     st.write(f"#### {section_name}")
#     st.dataframe(summary_sec)

# =============================================================================
#  PLOTS
# =============================================================================

# Pie chart of communication patterns
st.write("### התפלגות סוג תקשורת (תרשים עוגה)")
pattern_counts = df["סוג_תקשורת"].value_counts().reset_index()
pattern_counts.columns = ["סוג_תקשורת", "counts"]
fig_pie = px.pie(pattern_counts, values="counts", names="סוג_תקשורת",
                 title="אחוז סוגי תקשורת בקרב המשתתפים")
st.plotly_chart(fig_pie)

# Bar chart of average question scores
st.write("### ממוצעים בשאלות (תרשים עמודות)")
avg_by_pattern = df.groupby("סוג_תקשורת")[question_cols_renamed].mean().reset_index()
df_long = avg_by_pattern.melt(id_vars="סוג_תקשורת", var_name="שאלה", value_name="ממוצע")
fig_bar = px.bar(df_long, x="סוג_תקשורת", y="ממוצע", color="סוג_תקשורת",
                 facet_col="שאלה", barmode="group",
                 title="ממוצעים בשאלות לפי סוג תקשורת")
st.plotly_chart(fig_bar)

# Scatter Plot: sum_secure vs sum_avoidant
st.write("### פיזור: סכום בטוחה מול סכום נמנעת")
fig_scatter = px.scatter(df, x="sum_secure", y="sum_avoidant",
                         color="סוג_תקשורת",
                         title="Scatter: סכומי שאלות בטוחה מול נמנעת")
st.plotly_chart(fig_scatter)

# =============================================================================
#  1) Box Plots for Each Summed מדד by Communication Pattern
# =============================================================================
st.write("## השוואת מדדים בין סוגי תקשורת")
for total_col in section_totals:
    st.write(f"### Box Plot: {total_col} לפי סוג תקשורת")
    fig_box = px.box(df, x="סוג_תקשורת", y=total_col, color="סוג_תקשורת",
                     title=f"התפלגות {total_col} לפי סוג תקשורת",
                     points="all")  # show all sample points
    st.plotly_chart(fig_box)

# =============================================================================
#  2) Correlation between each summed מדד and communication sums
# =============================================================================
st.write("## מתאמים בין מדדים לסכומי תקשורת")
# We'll create a mini DataFrame with sum_secure, sum_avoidant, sum_ambiv + sum_מדד1, sum_מדד2, sum_מדד3
corr_cols = ["sum_secure", "sum_avoidant", "sum_ambiv"] + section_totals
corr_df = df[corr_cols].corr()

fig_corr = px.imshow(corr_df,
                     text_auto=True,
                     title="מטריצת מתאם (תקשורת מול מדדים)",
                     color_continuous_scale="RdBu_r",
                     range_color=(-1, 1))
st.plotly_chart(fig_corr)

# =============================================================================
#  Group Comparison
# =============================================================================
st.write("## השוואה בין קבוצות")
unique_groups = df["סוג_תקשורת"].unique()
if len(unique_groups) < 2:
    st.write("לא ניתן להשוות קבוצות, כי יש פחות משתי קבוצות.")
else:
    group_choices = st.multiselect("בחר שתי קבוצות להשוואה",
                                   options=unique_groups,
                                   default=unique_groups[:2])
    if len(group_choices) == 2:
        group_a, group_b = group_choices
        df_a = df[df["סוג_תקשורת"] == group_a]
        df_b = df[df["סוג_תקשורת"] == group_b]
        
        # Compare means for questions
        mean_a = df_a[question_cols_renamed].mean()
        mean_b = df_b[question_cols_renamed].mean()
        diff = mean_a - mean_b
        
        compare_df = pd.DataFrame({
            f"ממוצע-{group_a}": mean_a,
            f"ממוצע-{group_b}": mean_b,
            "הפרש (A - B)": diff
        })
        st.write("### השוואת ממוצעים לשאלות בין שתי קבוצות")
        st.dataframe(compare_df)

        # Compare means for each summed section
        compare_secs = {}
        for total_col in section_totals:
            compare_secs[f"{total_col}-{group_a}"] = df_a[total_col].mean()
            compare_secs[f"{total_col}-{group_b}"] = df_b[total_col].mean()
            compare_secs[f"diff_{total_col}"] = compare_secs[f"{total_col}-{group_a}"] - compare_secs[f"{total_col}-{group_b}"]
        st.write("### השוואת ממוצעים של סה\"כ מדדים בין שתי קבוצות")
        st.dataframe(pd.DataFrame([compare_secs]))

st.write("### ניתוח מורחב לפי תקשורת ומדדים – סיום")