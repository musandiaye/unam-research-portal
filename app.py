import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="UNAM Research Portal", layout="wide")
st.title("UNAM: School of Engineering and the Built Environment")
st.subheader("Department of Electrical and Computer Engineering")

# --- GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- HELPERS: DATA LOADING ---
def load_marks():
    try:
        return conn.read(worksheet="marks", ttl=0)
    except Exception:
        return pd.DataFrame()

def load_students():
    try:
        return conn.read(worksheet="students", ttl=0)
    except Exception:
        return pd.DataFrame()

# --- ROLE SELECTION ---
st.sidebar.title("Management Menu")
role = st.sidebar.radio("Select Role", ["Student View", "Panelist / Examiner", "Research Coordinator"])

# --- ROLE 1: STUDENT VIEW ---
if role == "Student View":
    st.header("📋 Student Grade Tracker")
    search_id = st.text_input("Enter Student Number to view your marks").strip()
    
    if search_id:
        df = load_marks()
        if not df.empty and 'student_id' in df.columns:
            df['student_id'] = df['student_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            clean_search = str(search_id).replace('.0', '').strip()
            res = df[df['student_id'] == clean_search].copy()
            
            if not res.empty:
                student_name = res.iloc[0]['student_name']
                st.write(f"### Results for: **{student_name}**")
                summary = res.groupby('assessment_type')['total_out_of_30'].mean().reset_index()
                summary['total_out_of_30'] = summary['total_out_of_30'].round(0).astype(int)
                summary.columns = ['Assessment Stage', 'Average Mark (/30)']
                st.table(summary)
            else:
                st.info(f"🔍 No marks found for Student Number: **{search_id}**")

# --- ROLE 2: PANELIST / EXAMINER ---
elif role == "Panelist / Examiner":
    st.header("🧑‍🏫 Examiner Portal")
    ex_pwd = st.sidebar.text_input("Examiner Access Code", type="password")
    
    if ex_pwd == "Engineering@2026":
        students_df = load_students()
        marks_df = load_marks()
        
        st.subheader("1. Identify Student")
        names_list = []
        if not students_df.empty:
            students_df['student_id'] = students_df['student_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            names_list = sorted(students_df['student_name'].unique().tolist())

        s_name_sel = st.selectbox("Search Name", options=["[New Student]"] + names_list)
        
        if s_name_sel != "[New Student]":
            id_opts = students_df[students_df['student_name'] == s_name_sel]['student_id'].unique().tolist()
        else:
            id_opts = ["[New ID]"]

        s_id_sel = st.selectbox("Search ID", options=id_opts)

        with st.form("scoring_form", clear_on_submit=True):
            st.subheader("2. Assessment Rubric")
            
            col1, col2 = st.columns(2)
            with col1:
                final_name = st.text_input("Student Name", value="" if s_name_sel == "[New Student]" else s_name_sel)
                final_id = st.text_input("Student Number", value="" if s_id_sel == "[New ID]" else s_id_sel)
                # Added Project Title from PDF requirement
                project_title = st.text_input("Project Title")
            with col2:
                p_type = st.selectbox("Assessment Stage", 
                                    ["Presentation 1 (10%)", "Presentation 2 (10%)", 
                                     "Presentation 3 (20%)", "Final Research Report (60%)"])
                ex_name = st.text_input("Name of Examiner")

            st.divider()

            # Criterion 1: Data Collection
            st.markdown("### 1. Data Collection")
            st.caption("Learning Outcome 1, 2 and 3 + ECN ELO 4 and 5")
            st.info("Guideline: Valid data collection method (experiments/simulations) using appropriate tools. Sample of data presented effectively.")
            d_coll = st.slider("Marks (1.1 & 1.2)", 0, 10, 0)

            # Criterion 2: Data analysis and interpretation
            st.markdown("### 2. Data analysis and interpretation")
            st.caption("Learning Outcomes 1, 2 and 3 + ECN ELO 4 and 5")
            st.info("Guideline: Appropriate analysis tools used. Results interpreted relative to objectives. Valid conclusions drawn.")
            d_anal = st.slider("Marks (2.1 - 2.4)", 0, 10, 0)

            # Criterion 3: Professional and Technical Communication
            st.markdown("### 3. Professional and Technical Communication")
            st.caption("Learning outcome 5 and ELO 6")
            st.info("Guideline: Effective presentation using appropriate terminology/illustrations. Ability to answer questions convincingly.")
            d_comm = st.slider("Marks (3.1 - 3.3)", 0, 10, 0)

            st.divider()
            remarks = st.text_area("General Remarks")
            
            submit_button = st.form_submit_button("Submit Assessment")
            
            if submit_button:
                if not final_id or not final_name or not ex_name:
                    st.error("Error: Student Name, Number,
