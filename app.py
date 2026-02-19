import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import urllib.parse
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
            # Normalize ID strings for clean matching
            df['student_id'] = df['student_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            clean_search = str(search_id).replace('.0', '').strip()
            
            res = df[df['student_id'] == clean_search].copy()
            
            if not res.empty:
                student_name = res.iloc[0]['student_name']
                st.write(f"### Results for: **{student_name}**")
                
                # Average calculation for cases where multiple examiners graded the student
                summary = res.groupby('assessment_type')['total_out_of_30'].mean().reset_index()
                summary['total_out_of_30'] = summary['total_out_of_30'].round(0).astype(int)
                summary.columns = ['Assessment Stage', 'Final Average Mark (/30)']
                st.table(summary)
            else:
                st.info(f"🔍 No marks found for Student Number: **{search_id}**")
        else:
            st.error("The database is currently empty.")

# --- ROLE 2: PANELIST / EXAMINER (Manual Entry Restored) ---
elif role == "Panelist / Examiner":
    st.header("🧑‍🏫 Examiner Portal")
    ex_pwd = st.sidebar.text_input("Examiner Access Code", type="password")
    
    if ex_pwd == "Engineering@2026":
        st.subheader("Research Project Assessment Form")
        
        with st.form("scoring_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                # Restored to simple manual text inputs
                s_name = st.text_input("Student Name")
                s_num = st.text_input("Student Number")
            
            with col2:
                p_type = st.selectbox("Assessment Stage", 
                                    ["Presentation 1 (10%)", "Presentation 2 (10%)", 
                                     "Presentation 3 (20%)", "Final Research Report (60%)"])
                ex_name = st.text_input("Examiner Name")

            st.markdown("---")
            st.write("### Scoring Rubric")
            d_coll = st.slider("1. Data Collection /10", 0, 10, 0)
            d_anal = st.slider("2. Data Analysis /10", 0, 10, 0)
            d_comm = st.slider("3. Professional Communication /10", 0, 10, 0)
            remarks = st.text_area("General Remarks")
            
            if st.form_submit_button("Submit Marks"):
                if not s_num or not s_name or not ex_name:
                    st.error("Please ensure all fields (Name, ID, and Examiner) are filled.")
                else:
                    total_score = d_coll + d_anal + d_comm
                    
                    # Ensure the data being sent to the sheet is clean
                    new_entry = pd.DataFrame([{
                        "student_id": str(s_num).replace('.0', '').strip(),
                        "student_name": s_name.strip(),
                        "assessment_type": p_type,
                        "data_coll": d_coll, 
                        "data_anal": d_anal, 
                        "comm": d_comm,
                        "total_out_of_30": total_score,
                        "examiner": ex_name, 
                        "remarks": remarks,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }])
                    
                    # Get existing data to append
                    existing_df = load_data()
                    updated_df = pd.concat([existing_df, new_entry], ignore_index=True)
                    
                    try:
                        conn.update(worksheet="marks", data=updated_df)
                        st.success(f"Success! {total_score}/30 recorded for {s_name}.")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error saving to Google Sheets: {e}")
    elif ex_pwd:
        st.error("Incorrect Password.")

# --- ROLE 3: RESEARCH COORDINATOR ---
elif role == "Research Coordinator":
    st.header("🔑 Coordinator Dashboard")
    coord_pwd = st.sidebar.text_input("Coordinator Password", type="password")
    
    if coord_pwd == "Blackberry":
        marks_df = load_data()
        if not marks_df.empty:
            st.subheader("📊 Average Grade Summary")
            
            # Grouping entries to find the average if multiple examiners graded the same presentation
            pivot = marks_df.pivot_table(index=['student_id', 'student_name'], 
                                       columns='assessment_type', 
                                       values='total_out_of_30',
                                       aggfunc='mean').reset_index()
            
            # Formatting for clean display (integers)
            for col in pivot.columns:
                if col not in ['student_id', 'student_name']:
                    pivot[col] = pivot[col].fillna(0).round(0).astype(int)
            
            st.dataframe(pivot, use_container_width=True)
            
            with st.expander("View Audit Log (Individual Entries)"):
                st.dataframe(marks_df)
            
            csv = pivot.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Export Results to CSV", csv, "Research_Marks_Averages.csv", "text/csv")
    elif coord_pwd:
        st.error("Incorrect Password.")
