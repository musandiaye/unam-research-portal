import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import re

# --- PAGE CONFIG ---
st.set_page_config(page_title="UNAM Research Portal", layout="wide")
st.title("UNAM: School of Engineering and the Built Environment")
st.subheader("Department of Electrical and Computer Engineering")

# --- GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- HELPERS: DATA CLEANING ---
def clean_id(val):
    """Force Student ID to be a clean string without decimals."""
    if pd.isna(val) or val == "":
        return ""
    # Remove .0 if it exists at the end, then strip whitespace
    s = str(val).split('.')[0]
    return s.strip()

def load_marks():
    try:
        df = conn.read(worksheet="marks", ttl=0)
        if not df.empty and 'student_id' in df.columns:
            df['student_id'] = df['student_id'].apply(clean_id)
        return df
    except Exception:
        return pd.DataFrame()

def load_students():
    try:
        df = conn.read(worksheet="students", ttl=0)
        if not df.empty and 'student_id' in df.columns:
            df['student_id'] = df['student_id'].apply(clean_id)
        return df
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

# --- ROLE 0: STUDENT REGISTRATION ---
if role == "Student Registration":
    st.header("📝 Research Project Registration")
    st.info("Registration is a once-off entry. Ensure your Student ID is correct.")
    
    with st.form("registration_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            reg_name = st.text_input("Full Name")
            reg_id = st.text_input("Student Number (Numbers only)")
            reg_email = st.text_input("Email Address")
        with col2:
            reg_supervisor = st.text_input("Assigned Supervisor")
            reg_title = st.text_area("Research Project Title")
            
        submit_reg = st.form_submit_button("Register Project")
        
        if submit_reg:
            # Standardize ID immediately
            id_to_save = clean_id(reg_id)
            
            if not all([reg_name, id_to_save, reg_email, reg_supervisor, reg_title]):
                st.error("All fields are required.")
            else:
                existing_students = load_students()
                
                if not existing_students.empty and id_to_save in existing_students['student_id'].values:
                    st.error(f"ID {id_to_save} is already registered. Contact the Coordinator for updates.")
                else:
                    new_student = pd.DataFrame([{
                        "student_id": id_to_save,
                        "student_name": str(reg_name).strip(),
                        "email": str(reg_email).strip().lower(),
                        "supervisor": str(reg_supervisor).strip(),
                        "research_title": str(reg_title).strip()
                    }])
                    updated_students = pd.concat([existing_students, new_student], ignore_index=True)
                    try:
                        conn.update(worksheet="students", data=updated_students)
                        st.success(f"Registration successful for ID: {id_to_save}")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error: {e}")

# --- ROLE 1: STUDENT VIEW (RESULTS) ---
elif role == "Student View (Results)":
    st.header("📋 Student Grade Tracker")
    search_id = st.text_input("Enter Student Number").strip()
    
    if search_id:
        target_id = clean_id(search_id)
        df = load_marks()
        if not df.empty:
            res = df[df['student_id'] == target_id].copy()
            
            if not res.empty:
                st.write(f"### Results for: **{res.iloc[0]['student_name']}**")
                summary = res.groupby('assessment_type')['total_out_of_30'].mean().reset_index()
                summary['total_out_of_30'] = summary['total_out_of_30'].map('{:,.1f}'.format)
                st.table(summary)
            else:
                st.info(f"No marks found for ID: {target_id}")

# --- ROLE 2: PANELIST / EXAMINER ---
elif role == "Panelist / Examiner":
    st.header("🧑‍🏫 Examiner Portal")
    ex_pwd = st.sidebar.text_input("Examiner Access Code", type="password")
    
    if ex_pwd == "Engineering@2026":
        students_df = load_students()
        marks_df = load_marks()
        
        st.subheader("1. Identify Student")
        names_list = sorted(students_df['student_name'].unique().tolist()) if not students_df.empty else []
        s_name_sel = st.selectbox("Search Name", options=["[New Student]"] + names_list)
        
        selected_title, selected_email, selected_id = "", "", ""
        if s_name_sel != "[New Student]":
            student_data = students_df[students_df['student_name'] == s_name_sel]
            selected_id = student_data.iloc[0]['student_id']
            selected_title = student_data.iloc[0].get('research_title', "")
            selected_email = student_data.iloc[0].get('email', "")

        with st.form("scoring_form", clear_on_submit=True):
            st.subheader("2. Assessment Rubric")
            col1, col2 = st.columns(2)
            with col1:
                final_name = st.text_input("Student Name", value=s_name_sel if s_name_sel != "[New Student]" else "")
                final_id = st.text_input("Student Number", value=selected_id)
                final_email = st.text_input("Email", value=selected_email)
            with col2:
                final_title = st.text_area("Research Title", value=selected_title)
                p_type = st.selectbox("Assessment Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Research Report (60%)"])
                ex_name = st.text_input("Name of Examiner")

            st.divider()
            d_coll = st.slider("1. Data Collection", 0.0, 10.0, 0.0, 0.5)
            d_anal = st.slider("2. Data Analysis", 0.0, 10.0, 0.0, 0.5)
            d_comm = st.slider("3. Communication", 0.0, 10.0, 0.0, 0.5)
            remarks = st.text_area("General Remarks")
            
            if st.form_submit_button("Submit Assessment"):
                clean_final_id = clean_id(final_id)
                if not clean_final_id or not final_name or not ex_name:
                    st.error("Student Name, ID, and Examiner are required.")
                else:
                    total_score = float(d_coll + d_anal + d_comm)
                    new_entry = pd.DataFrame([{
                        "student_id": clean_final_id,
                        "student_name": str(final_name).strip(),
                        "email": str(final_email).strip().lower(),
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
                        st.success(f"Marks saved for ID: {clean_final_id}")
                    except Exception as e:
                        st.error(f"Error: {e}")

# --- ROLE 3: RESEARCH COORDINATOR ---
elif role == "Research Coordinator":
    st.header("🔑 Coordinator Dashboard")
    coord_pwd = st.sidebar.text_input("Coordinator Password", type="password")
    
    if coord_pwd == "Blackberry":
        students_df = load_students()
        marks_df = load_marks()
        
        if not students_df.empty:
            if not marks_df.empty:
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
    elif coord_pwd:
        st.error("Incorrect Password.")
