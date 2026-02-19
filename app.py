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
def load_data():
    try:
        return conn.read(worksheet="marks", ttl=0)
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return pd.DataFrame()

# --- ROLE SELECTION ---
st.sidebar.title("Management Menu")
role = st.sidebar.radio("Select Role", ["Student View", "Panelist / Examiner", "Research Coordinator"])

# --- ROLE 1: STUDENT VIEW ---
if role == "Student View":
    st.header("📋 Student Grade Tracker")
    search_id = st.text_input("Enter Student Number to view your marks").strip()
    
    if search_id:
        df = load_data()
        if not df.empty and 'student_id' in df.columns:
            df['student_id'] = df['student_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            clean_search = str(search_id).replace('.0', '').strip()
            res = df[df['student_id'] == clean_search].copy()
            
            if not res.empty:
                student_name = res.iloc[0]['student_name']
                st.write(f"### Results for: **{student_name}**")
                summary = res.groupby('assessment_type')['total_out_of_30'].mean().reset_index()
                summary['total_out_of_30'] = summary['total_out_of_30'].round(0).astype(int)
                summary.columns = ['Assessment Stage', 'Final Average Mark (/30)']
                st.table(summary)
            else:
                st.info(f"🔍 No marks found for Student Number: **{search_id}**")
        else:
            st.error("The database is currently empty.")

# --- ROLE 2: PANELIST / EXAMINER (Filtered ID Logic) ---
elif role == "Panelist / Examiner":
    st.header("🧑‍🏫 Examiner Portal")
    ex_pwd = st.sidebar.text_input("Examiner Access Code", type="password")
    
    if ex_pwd == "Engineering@2026":
        existing_df = load_data()
        
        # Prepare Data
        if not existing_df.empty:
            existing_df['student_id'] = existing_df['student_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            names_list = sorted(existing_df['student_name'].unique().tolist())
            all_ids = sorted(existing_df['student_id'].unique().tolist())
        else:
            names_list = []
            all_ids = []

        st.subheader("Student Details")
        
        # 1. Name Selection happens OUTSIDE the form to trigger the ID filter
        s_name_sel = st.selectbox("1. Search/Select Name", options=["[New Student]"] + names_list)
        
        # 2. Filter ID options based on Name selection
        if s_name_sel != "[New Student]":
            # Filter the database for this name to find the specific ID
            filtered_ids = existing_df[existing_df['student_name'] == s_name_sel]['student_id'].unique().tolist()
            id_options = filtered_ids # This list will now only contain one ID
        else:
            id_options = ["[New ID]"] + all_ids

        # 3. ID Selection
        s_id_sel = st.selectbox("2. Search/Select ID", options=id_options)

        # 4. Assessment Form
        with st.form("scoring_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                # Manual entry fields if [New] is selected
                final_name = st.text_input("Confirm/New Name", value="" if s_name_sel == "[New Student]" else s_name_sel)
                final_id = st.text_input("Confirm/New ID", value="" if s_id_sel == "[New ID]" else s_id_sel)
            
            with col2:
                p_type = st.selectbox("Assessment Stage", 
                                    ["Presentation 1 (10%)", "Presentation 2 (10%)", 
                                     "Presentation 3 (20%)", "Final Research Report (60%)"])
                ex_name = st.text_input("Examiner Name")

            st.markdown("---")
            d_coll = st.slider("Data Collection /10", 0, 10, 0)
            d_anal = st.slider("Data Analysis /10", 0, 10, 0)
            d_comm = st.slider("Communication /10", 0, 10, 0)
            remarks = st.text_area("Remarks")
            
            if st.form_submit_button("Submit Marks"):
                if not final_id or not final_name or not ex_name:
                    st.error("Please ensure all fields are filled.")
                else:
                    total_score = d_coll + d_anal + d_comm
                    new_entry = pd.DataFrame([{
                        "student_id": str(final_id).strip(),
                        "student_name": str(final_name).strip(),
                        "assessment_type": p_type,
                        "total_out_of_30": total_score,
                        "examiner": ex_name, "remarks": remarks,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }])
                    
                    updated_df = pd.concat([existing_df, new_entry], ignore_index=True)
                    try:
                        conn.update(worksheet="marks", data=updated_df)
                        st.success(f"Marks saved for {final_name}")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error: {e}")

# --- ROLE 3: RESEARCH COORDINATOR ---
elif role == "Research Coordinator":
    st.header("🔑 Coordinator Dashboard")
    coord_pwd = st.sidebar.text_input("Coordinator Password", type="password")
    
    if coord_pwd == "Blackberry":
        marks_df = load_data()
        if not marks_df.empty:
            pivot = marks_df.pivot_table(index=['student_id', 'student_name'], 
                                       columns='assessment_type', 
                                       values='total_out_of_30',
                                       aggfunc='mean').reset_index()
            for col in pivot.columns:
                if col not in ['student_id', 'student_name']:
                    pivot[col] = pivot[col].fillna(0).round(0).astype(int)
            st.dataframe(pivot, use_container_width=True)
            csv = pivot.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", csv, "Grades.csv", "text/csv")
    elif coord_pwd:
        st.error("Incorrect Password.")
