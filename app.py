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
role = st.sidebar.radio("Select Role", [
    "Student Registration", 
    "Student View (Results)", 
    "Panelist / Examiner", 
    "Research Coordinator"
])

# --- ROLE 0: STUDENT REGISTRATION (One-off Entry) ---
if role == "Student Registration":
    st.header("📝 Research Project Registration")
    st.info("Note: This is a once-off registration. If you need to update your details after submitting, please contact the Research Coordinator.")
    
    with st.form("registration_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            reg_name = st.text_input("Full Name")
            reg_id = st.text_input("Student Number (e.g., 202201234)")
        with col2:
            reg_supervisor = st.text_input("Assigned Supervisor")
            reg_title = st.text_area("Research Project Title")
            
        submit_reg = st.form_submit_button("Register Project")
        
        if submit_reg:
            if not reg_name or not reg_id or not reg_supervisor or not reg_title:
                st.error("All fields are required for registration.")
            else:
                existing_students = load_students()
                
                # Clean and standardize ID for comparison
                clean_reg_id = str(reg_id).strip()
                
                # Check for duplicates
                is_duplicate = False
                if not existing_students.empty:
                    # Convert existing IDs to clean strings for accurate matching
                    existing_ids = existing_students['student_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().values
                    if clean_reg_id in existing_ids:
                        is_duplicate = True

                if is_duplicate:
                    st.error(f"Registration Failed: Student Number {clean_reg_id} is already registered. Please contact the Coordinator for any modifications.")
                else:
                    new_student = pd.DataFrame([{
                        "student_id": clean_reg_id,
                        "student_name": str(reg_name).strip(),
                        "supervisor": str(reg_supervisor).strip(),
                        "research_title": str(reg_title).strip()
                    }])
                    updated_students = pd.concat([existing_students, new_student], ignore_index=True)
                    try:
                        conn.update(worksheet="students", data=updated_students)
                        st.success(f"Registration successful for {reg_name}! You are now in the system.")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Connection Error: Could not save to database. {e}")

# --- ROLE 1: STUDENT VIEW (RESULTS) ---
elif role == "Student View (Results)":
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
                summary['total_out_of_30'] = summary['total_out_of_30'].map('{:,.1f}'.format)
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
        
        selected_title = ""
        if s_name_sel != "[New Student]":
            student_data = students_df[students_df['student_name'] == s_name_sel]
            id_opts = student_data['student_id'].unique().tolist()
            if 'research_title' in student_data.columns:
                selected_title = student_data.iloc[0]['research_title']
        else:
            id_opts = ["[New ID]"]

        s_id_sel = st.selectbox("Search ID", options=id_opts)

        with st.form("scoring_form", clear_on_submit=True):
            st.subheader("2. Assessment Rubric")
            col1, col2 = st.columns(2)
            with col1:
                final_name = st.text_input("Student Name", value="" if s_name_sel == "[New Student]" else s_name_sel)
                final_id = st.text_input("Student Number", value="" if s_id_sel == "[New ID]" else s_id_sel)
                final_title = st.text_input("Research Title", value=selected_title)
            with col2:
                p_type = st.selectbox("Assessment Stage", 
                                    ["Presentation 1 (10%)", "Presentation 2 (10%)", 
                                     "Presentation 3 (20%)", "Final Research Report (60%)"])
                ex_name = st.text_input("Name of Examiner")

            st.divider()
            d_coll = st.slider("1. Data Collection", 0.0, 10.0, 0.0, 0.5)
            d_anal = st.slider("2. Data Analysis & Interpretation", 0.0, 10.0, 0.0, 0.5)
            d_comm = st.slider("3. Professional Communication", 0.0, 10.0, 0.0, 0.5)

            st.divider()
            remarks = st.text_area("General Remarks")
            
            if st.form_submit_button("Submit Assessment"):
                if not final_id or not final_name or not ex_name:
                    st.error("Student Name, ID, and Examiner are required.")
                else:
                    total_score = float(d_coll + d_anal + d_comm)
                    new_entry = pd.DataFrame([{
                        "student_id": str(final_id).strip(),
                        "student_name": str(final_name).strip(),
                        "research_title": str(final_title).strip(),
                        "assessment_type": p_type,
                        "data_coll": d_coll, "data_anal": d_anal, "comm": d_comm,
                        "total_out_of_30": total_score,
                        "examiner": ex_name, "remarks": remarks,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }])
                    updated_df = pd.concat([marks_df, new_entry], ignore_index=True)
                    try:
                        conn.update(worksheet="marks", data=updated_df)
                        st.success(f"Score of {total_score:.1f} saved for {final_name}")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error saving marks: {e}")

# --- ROLE 3: RESEARCH COORDINATOR (Update Capability) ---
elif role == "Research Coordinator":
    st.header("🔑 Coordinator Dashboard")
    coord_pwd = st.sidebar.text_input("Coordinator Password", type="password")
    
    if coord_pwd == "Blackberry":
        students_df = load_students()
        marks_df = load_marks()
        
        if not students_df.empty:
            students_df['student_id'] = students_df['student_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            
            # Allow Coordinator to see the data and download it for manual edits in Google Sheets
            if not marks_df.empty:
                marks_df['student_id'] = marks_df['student_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                pivot = marks_df.pivot_table(index='student_id', columns='assessment_type', values='total_out_of_30', aggfunc='mean').reset_index()
                final_report = pd.merge(students_df, pivot, on='student_id', how='left')
            else:
                final_report = students_df.copy()
            
            mark_cols = ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Research Report (60%)"]
            for col in mark_cols:
                if col in final_report.columns:
                    final_report[col] = final_report[col].fillna(0.0).astype(float).round(1)
            
            st.subheader("📊 Master Grade Sheet")
            st.dataframe(final_report, use_container_width=True)
            
            st.info("💡 To update student details or fix mistakes, please edit the Google Sheet directly. Changes will reflect here upon refresh.")
    elif coord_pwd:
        st.error("Incorrect Password.")
