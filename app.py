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
            with col2:
                p_type = st.selectbox("Assessment Stage", 
                                    ["Presentation 1 (10%)", "Presentation 2 (10%)", 
                                     "Presentation 3 (20%)", "Final Research Report (60%)"])
                ex_name = st.text_input("Name of Examiner")

            st.divider()
            st.markdown("### 1. Data Collection")
            st.caption("LO 1, 2 & 3 + ECN ELO 4 & 5")
            d_coll = st.slider("Marks", 0, 10, 0, key="c1")

            st.markdown("### 2. Data analysis and interpretation")
            st.caption("LO 1, 2 & 3 + ECN ELO 4 & 5")
            d_anal = st.slider("Marks", 0, 10, 0, key="c2")

            st.markdown("### 3. Professional and Technical Communication")
            st.caption("LO 5 and ELO 6")
            d_comm = st.slider("Marks", 0, 10, 0, key="c3")

            st.divider()
            remarks = st.text_area("General Remarks")
            
            if st.form_submit_button("Submit Assessment"):
                if not final_id or not final_name or not ex_name:
                    st.error("Error: All identity fields and Examiner Name are required.")
                else:
                    total_score = d_coll + d_anal + d_comm
                    new_entry = pd.DataFrame([{
                        "student_id": str(final_id).strip(),
                        "student_name": str(final_name).strip(),
                        "assessment_type": p_type,
                        "data_coll": d_coll, "data_anal": d_anal, "comm": d_comm,
                        "total_out_of_30": total_score,
                        "examiner": ex_name, "remarks": remarks,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }])
                    
                    updated_df = pd.concat([marks_df, new_entry], ignore_index=True)
                    try:
                        conn.update(worksheet="marks", data=updated_df)
                        st.success(f"Assessment for {final_name} submitted successfully!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Save failed: {e}")

# --- ROLE 3: RESEARCH COORDINATOR (Merged View) ---
elif role == "Research Coordinator":
    st.header("🔑 Coordinator Dashboard")
    coord_pwd = st.sidebar.text_input("Coordinator Password", type="password")
    
    if coord_pwd == "Blackberry":
        students_df = load_students()
        marks_df = load_marks()
        
        if not students_df.empty:
            # Standardize student_id for merging
            students_df['student_id'] = students_df['student_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
            if not marks_df.empty:
                marks_df['student_id'] = marks_df['student_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                
                # Create pivot of marks
                pivot = marks_df.pivot_table(index='student_id', 
                                           columns='assessment_type', 
                                           values='total_out_of_30',
                                           aggfunc='mean').reset_index()
                
                # Merge student info (name, supervisor) with marks
                # This ensures students with NO marks still appear
                final_report = pd.merge(students_df, pivot, on='student_id', how='left')
            else:
                # No marks exist yet, just show student list with empty columns
                final_report = students_df.copy()
            
            st.subheader("📊 Master Research Grade Sheet")
            
            # Fill NaN values with 0 and convert marks to integers
            mark_cols = ["Presentation 1 (10%)", "Presentation 2 (10%)", 
                         "Presentation 3 (20%)", "Final Research Report (60%)"]
            
            for col in mark_cols:
                if col in final_report.columns:
                    final_report[col] = final_report[col].fillna(0).round(0).astype(int)
                else:
                    final_report[col] = 0 # Placeholder if stage hasn't been graded yet
            
            st.dataframe(final_report, use_container_width=True)
            
            csv = final_report.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Master Sheet", csv, "Master_Grades.csv", "text/csv")
        else:
            st.warning("The 'students' tab is empty. Please add students to the database.")
    elif coord_pwd:
        st.error("Incorrect Password.")
