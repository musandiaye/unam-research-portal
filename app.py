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
        
        # Pull details from students tab based on selection
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
            
            # 0.5 step sliders for precision
            d_coll = st.slider("1. Data Collection", 0.0, 10.0, 0.0, 0.5)
            d_anal = st.slider("2. Data Analysis & Interpretation", 0.0, 10.0, 0.0, 0.5)
            d_comm = st.slider("3. Professional Communication", 0.0, 10.0, 0.0, 0.5)

            st.divider()
            remarks = st.text_area("General Remarks")
            
            if st.form_submit_button("Submit Assessment"):
                if not final_id or not final_name or not ex_name:
                    st.error("Error: Student Name, Number, and Examiner Name are required.")
                else:
                    total_score = float(d_coll + d_anal + d_comm)
                    new_entry = pd.DataFrame([{
                        "student_id": str(final_id).strip(),
                        "student_name": str(final_name).strip(),
                        "research_title": str(final_title).strip(),
                        "assessment_type": p_type,
                        "data_coll": float(d_coll), 
                        "data_anal": float(d_anal), 
                        "comm": float(d_comm),
                        "total_out_of_30": total_score,
                        "examiner": ex_name, 
                        "remarks": remarks,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }])
                    
                    updated_df = pd.concat([marks_df, new_entry], ignore_index=True)
                    try:
                        conn.update(worksheet="marks", data=updated_df)
                        st.success(f"Assessment submitted for {final_name} ({total_score:.1f}/30)!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Save failed: {e}")

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
                pivot = marks_df.pivot_table(index='student_id', 
                                           columns='assessment_type', 
                                           values='total_out_of_30',
                                           aggfunc='mean').reset_index()
                # Merges master info (Supervisor/Title) with the calculated averages
                final_report = pd.merge(students_df, pivot, on='student_id', how='left')
            else:
                final_report = students_df.copy()
            
            mark_cols = ["Presentation 1 (10%)", "Presentation 2 (10%)", 
                         "Presentation 3 (20%)", "Final Research Report (60%)"]
            
            for col in mark_cols:
                if col in final_report.columns:
                    final_report[col] = final_report[col].fillna(0.0).astype(float).round(1)
                else:
                    final_report[col] = 0.0
            
            st.subheader("📊 Master Research Summary")
            st.dataframe(final_report.style.format(subset=pd.IndexSlice[:, final_report.columns.isin(mark_cols)], formatter="{:.1f}"), use_container_width=True)
            
            csv = final_report.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Export Master Sheet", csv, "Master_Grades_Full.csv", "text/csv")
        else:
            st.warning("No students found in the 'students' worksheet.")
    elif coord_pwd:
        st.error("Incorrect Password.")
