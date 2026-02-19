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
        # Pulls from your 'students' tab where your test student is located
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

# --- ROLE 2: PANELIST / EXAMINER (Updated to look at Student Tab) ---
elif role == "Panelist / Examiner":
    st.header("🧑‍🏫 Examiner Portal")
    ex_pwd = st.sidebar.text_input("Examiner Access Code", type="password")
    
    if ex_pwd == "Engineering@2026":
        # Load from both tabs
        students_df = load_students()
        marks_df = load_marks()
        
        # Merge lists to find all possible students
        names_list = []
        if not students_df.empty:
            # Clean student ID format 
            students_df['student_id'] = students_df['student_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            names_list = sorted(students_df['student_name'].unique().tolist())

        st.subheader("1. Identify Student")
        s_name_sel = st.selectbox("Search Name", options=["[New Student]"] + names_list)
        
        # Filter ID list based on Name selection
        if s_name_sel != "[New Student]":
            id_opts = students_df[students_df['student_name'] == s_name_sel]['student_id'].unique().tolist()
        else:
            # If new, allow them to see IDs already in the marks database
            all_marks_ids = []
            if not marks_df.empty:
                all_marks_ids = marks_df['student_id'].unique().tolist()
            id_opts = ["[New ID]"] + all_marks_ids
            
        s_id_sel = st.selectbox("Search ID", options=id_opts)

        with st.form("scoring_form", clear_on_submit=True):
            st.subheader("2. Assessment Rubric")
            col1, col2 = st.columns(2)
            with col1:
                final_name = st.text_input("Student Name", value="" if s_name_sel == "[New Student]" else s_name_sel)
                final_id = st.text_input("Student ID", value="" if s_id_sel == "[New ID]" else s_id_sel)
            with col2:
                # Stages as per Research Project Final Presentation Assessment [cite: 3]
                p_type = st.selectbox("Assessment Stage", 
                                    ["Presentation 1 (10%)", "Presentation 2 (10%)", 
                                     "Presentation 3 (20%)", "Final Research Report (60%)"])
                ex_name = st.text_input("Examiner Name") [cite: 7]

            st.divider()

            # Criterion 1: Data Collection 
            st.markdown("### 1. Data Collection")
            st.caption("Learning Outcome 1, 2 and 3 + ECN ELO 4 and 5") [cite: 4]
            st.info("Guideline: Valid data collection method (experiments/simulations) using appropriate tools. Sample of collected data is presented effectively.") [cite: 4]
            d_coll = st.slider("Marks", 0, 10, 0, key="c1") [cite: 4]

            # Criterion 2: Data analysis and interpretation 
            st.markdown("### 2. Data analysis and interpretation")
            st.caption("Learning Outcomes 1, 2 and 3 + ECN ELO 4 and 5") [cite: 4]
            st.info("Guideline: Appropriate analysis tools (ICT/statistical) used. Results interpreted relative to research objectives. Valid conclusions and future work recommendations provided.") [cite: 4]
            d_anal = st.slider("Marks", 0, 10, 0, key="c2") [cite: 4]

            # Criterion 3: Professional and Technical Communication 
            st.markdown("### 3. Professional and Technical Communication")
            st.caption("Learning outcome 5 and ELO 6") [cite: 4]
            st.info("Guideline: Effective presentation of findings using appropriate terminology and illustrations. Ability to convincingly answer research-related questions.") [cite: 4]
            d_comm = st.slider("Marks", 0, 10, 0, key="c3") [cite: 4]

            st.divider()
            remarks = st.text_area("General Remarks") [cite: 6]
            
            if st.form_submit_button("Submit Assessment"):
                if not final_id or not final_name or not ex_name:
                    st.error("Error: Student Name, ID, and Examiner Name are required.")
                else:
                    total_score = d_coll + d_anal + d_comm
                    new_entry = pd.DataFrame([{
                        "student_id": str(final_id).strip(),
                        "student_name": str(final_name).strip(),
                        "assessment_type": p_type,
                        "data_coll": d_coll,
                        "data_anal": d_anal,
                        "comm": d_comm,
                        "total_out_of_30": total_score,
                        "examiner": ex_name, 
                        "remarks": remarks,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }])
                    
                    # Always append to the 'marks' tab
                    updated_df = pd.concat([marks_df, new_entry], ignore_index=True)
                    try:
                        conn.update(worksheet="marks", data=updated_df)
                        st.success(f"Assessment for {final_name} submitted successfully!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Save failed: {e}")

# --- ROLE 3: RESEARCH COORDINATOR ---
elif role == "Research Coordinator":
    st.header("🔑 Coordinator Dashboard")
    coord_pwd = st.sidebar.text_input("Coordinator Password", type="password")
    
    if coord_pwd == "Blackberry":
        marks_df = load_marks()
        if not marks_df.empty:
            st.subheader("📊 Average Grade Summary")
            pivot = marks_df.pivot_table(index=['student_id', 'student_name'], 
                                       columns='assessment_type', 
                                       values='total_out_of_30',
                                       aggfunc='mean').reset_index()
            
            for col in pivot.columns:
                if col not in ['student_id', 'student_name']:
                    pivot[col] = pivot[col].fillna(0).round(0).astype(int)
            
            st.dataframe(pivot, use_container_width=True)
            with st.expander("Full Marks Log"):
                st.dataframe(marks_df)
    elif coord_pwd:
        st.error("Incorrect Password.")
