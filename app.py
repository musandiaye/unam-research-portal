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

# --- ROLE 0: STUDENT REGISTRATION (Including Email) ---
if role == "Student Registration":
    st.header("📝 Research Project Registration")
    st.info("Registration is a once-off entry. Please double-check your UNAM Email before submitting.")
    
    with st.form("registration_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            reg_name = st.text_input("Full Name")
            reg_id = st.text_input("Student Number")
            reg_email = st.text_input("UNAM Email Address")
        with col2:
            reg_supervisor = st.text_input("Assigned Supervisor")
            reg_title = st.text_area("Research Project Title")
            
        submit_reg = st.form_submit_button("Register Project")
        
        if submit_reg:
            if not all([reg_name, reg_id, reg_email, reg_supervisor, reg_title]):
                st.error("All fields, including Email, are required.")
            elif "@" not in reg_email:
                st.error("Please enter a valid email address.")
            else:
                existing_students = load_students()
                clean_reg_id = str(reg_id).strip()
                
                # Duplicate Check
                is_duplicate = False
                if not existing_students.empty:
                    existing_ids = existing_students['student_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().values
                    if clean_reg_id in existing_ids:
                        is_duplicate = True

                if is_duplicate:
                    st.error(f"Error: Student {clean_reg_id} is already registered. Only the Coordinator can make changes.")
                else:
                    new_student = pd.DataFrame([{
                        "student_id": clean_reg_id,
                        "student_name": str(reg_name).strip(),
                        "email": str(reg_email).strip().lower(),
                        "supervisor": str(reg_supervisor).strip(),
                        "research_title": str(reg_title).strip()
                    }])
                    updated_students = pd.concat([existing_students, new_student], ignore_index=True)
                    try:
                        conn.update(worksheet="students", data=updated_students)
                        st.success(f"Registration successful for {reg_name}!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Database Error: {e}")

# --- ROLE 1: STUDENT VIEW (RESULTS) ---
elif role == "Student View (Results)":
    st.header("📋 Student Grade Tracker")
    search_id = st.text_input("Enter Student Number to view your marks").strip()
    
    if search_id:
        df = load_marks()
        if not df.empty and 'student_id' in df.columns:
            df['student_id'] = df['student_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            res = df[df['student_id'] == str(search_id).replace('.0', '').strip()].copy()
            
            if not res.empty:
                st.write(f"### Results for: **{res.iloc[0]['student_name']}**")
                summary = res.groupby('assessment_type')['total_out_of_30'].mean().reset_index()
                summary['total_out_of_30'] = summary['total_out_of_30'].map('{:,.1f}'.format)
                st.table(summary)
            else:
                st.info("🔍 No marks found.")

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
        
        selected_title = ""
        selected_email = ""
        if s_name_sel != "[New Student]":
            student_data = students_df[students_df['student_name'] == s_name_sel]
            id_opts = student_data['student_id'].unique().tolist()
            selected_title = student_data.iloc[0].get('research_title', "")
            selected_email = student_data.iloc[0].get('email', "")
        else:
            id_opts = ["[New ID]"]

        s_id_sel = st.selectbox("Search ID", options=id_opts)

        with st.form("scoring_form", clear_on_submit=True):
            st.subheader("2. Assessment Rubric")
            col1, col2 = st.columns(2)
            with col1:
                final_name = st.text_input("Student Name", value=s_name_sel if s_name_sel != "[New Student]" else "")
                final_id = st.text_input("Student Number", value=s_id_sel if s_id_sel != "[New ID]" else "")
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
                if not final_id or not final_name or not ex_name:
                    st.error("Missing required identity fields.")
                else:
                    total_score = float(d_coll + d_anal + d_comm)
                    new_entry = pd.DataFrame([{
                        "student_id": str(final_id).strip(),
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
                        st.success(f"Marks saved for {final_name}!")
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
            students_df['student_id'] = students_df['student_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            if not marks_df.empty:
                marks_df['student_id'] = marks_df['student_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                pivot = marks_df.pivot_table(index='student_id', columns='assessment_type', values='total_out_of_30', aggfunc='mean').reset_index()
                final_report = pd.merge(students_df, pivot, on='student_id', how='left')
            else:
                final_report = students_df.copy()
            
            st.subheader("📊 Master Grade Sheet")
            st.dataframe(final_report, use_container_width=True)
    elif coord_pwd:
        st.error("Incorrect Password.")
