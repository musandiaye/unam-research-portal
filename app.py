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

# --- ROLE SELECTION ---
st.sidebar.title("Management Menu")
role = st.sidebar.radio("Select Role", ["Student View", "Panelist / Examiner", "Research Coordinator"])

# --- HELPERS: DATA LOADING ---
def load_data():
    try:
        return conn.read(worksheet="marks", ttl=0)
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return pd.DataFrame()

# --- ROLE 1: STUDENT VIEW ---
if role == "Student View":
    st.header("📋 Student Grade Tracker")
    search_id = st.text_input("Enter Student Number to view your marks").strip()
    
    if search_id:
        df = load_data()
        if not df.empty:
            df['student_id'] = df['student_id'].astype(str).str.strip()
            res = df[df['student_id'] == str(search_id)]
            
            if not res.empty:
                student_name = res.iloc[0]['student_name']
                st.write(f"### Results for: **{student_name}**")
                display_df = res[['assessment_type', 'total_out_of_30', 'timestamp']].copy()
                display_df.columns = ['Assessment Stage', 'Mark (/30)', 'Date Recorded']
                st.table(display_df)
            else:
                st.info(f"🔍 No marks found for Student Number: **{search_id}**")
                st.warning("Ensure the ID is correct. Marks may not be uploaded yet.")
        else:
            st.error("The database is currently empty.")

# --- ROLE 2: PANELIST / EXAMINER ---
elif role == "Panelist / Examiner":
    st.header("🧑‍🏫 Examiner Portal")
    ex_pwd = st.sidebar.text_input("Examiner Access Code", type="password")
    
    if ex_pwd == "UNAM_EXAM_2026":
        st.subheader("Research Project Assessment Form")
        
        with st.form("scoring_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                s_name = st.text_input("Student's Name")
                s_num = st.text_input("Student Number")
            with col2:
                p_type = st.selectbox("Assessment Stage", 
                                    ["Presentation 1 (10%)", "Presentation 2 (10%)", 
                                     "Presentation 3 (20%)", "Final Research Report (60%)"])
                ex_name = st.text_input("Name of Examiner")

            st.markdown("---")
            st.write("Scoring (0-10 for each category)")
            d_coll = st.slider("1. Data Collection /10", 0, 10, 0)
            d_anal = st.slider("2. Data Analysis /10", 0, 10, 0)
            d_comm = st.slider("3. Professional Communication /10", 0, 10, 0)
            remarks = st.text_area("General Remarks")
            
            if st.form_submit_button("Submit Marks"):
                if not s_num or not s_name or not ex_name:
                    st.error("Please fill in all details before submitting.")
                else:
                    existing_data = load_data()
                    new_entry = pd.DataFrame([{
                        "student_id": str(s_num).strip(),
                        "student_name": s_name.strip(),
                        "assessment_type": p_type,
                        "data_coll": d_coll,
                        "data_anal": d_anal,
                        "comm": d_comm,
                        "total_out_of_30": d_coll + d_anal + d_comm,
                        "examiner": ex_name,
                        "remarks": remarks,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }])
                    
                    updated_df = pd.concat([existing_data, new_entry], ignore_index=True)
                    
                    try:
                        conn.update(worksheet="marks", data=updated_df)
                        st.success(f"✅ Assessment for {s_name} saved!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error saving data: {e}")
    elif ex_pwd != "":
        st.error("Incorrect Examiner Access Code.")
    else:
        st.info("Enter the Examiner Access Code in the sidebar.")

# --- ROLE 3: RESEARCH COORDINATOR (Simplified) ---
elif role == "Research Coordinator":
    st.header("🔑 Coordinator Dashboard")
    coord_pwd = st.sidebar.text_input("Coordinator Password", type="password")
    
    if coord_pwd == "UNAM2026":
        marks_df = load_data()
        
        if not marks_df.empty:
            st.subheader("📊 Grade Management")
            
            # Show the raw data first
            st.write("### Raw Marks Database")
            st.dataframe(marks_df, use_container_width=True)
            
            st.markdown("---")
            
            # Summary Pivot Table
            st.write("### Summary of Marks per Student")
            pivot = marks_df.pivot_table(index=['student_id', 'student_name'], 
                                       columns='assessment_type', 
                                       values='total_out_of_30').reset_index()
            st.dataframe(pivot, use_container_width=True)
            
            # Download Button for the summary
            csv = pivot.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Grade Summary as CSV",
                data=csv,
                file_name=f"UNAM_Grades_{datetime.now().strftime('%Y%m%d')}.csv",
                mime='text/csv',
            )
        else:
            st.warning("No marks have been recorded in the database yet.")
            
    elif coord_pwd != "":
        st.error("Incorrect Coordinator Password.")
    else:
        st.info("Enter the Coordinator Password in the sidebar.")
