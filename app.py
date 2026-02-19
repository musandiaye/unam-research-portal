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
        # Reads the tab named 'marks'
        return conn.read(worksheet="marks", ttl=0)
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return pd.DataFrame()

# --- ROLE 1: STUDENT VIEW (Extra-Safe Search Fix) ---
if role == "Student View":
    st.header("📋 Student Grade Tracker")
    search_id = st.text_input("Enter Student Number to view your marks").strip()
    
    if search_id:
        df = load_data()
        if not df.empty:
            # Check if the column exists to avoid errors
            if 'student_id' in df.columns:
                # 1. Clean the Database column: 
                # Convert to string -> Remove decimals -> Remove spaces
                df['student_id'] = df['student_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                
                # 2. Clean the User Input the same way
                clean_search = str(search_id).replace('.0', '').strip()
                
                # 3. Filter for matching ID
                res = df[df['student_id'] == clean_search]
                
                if not res.empty:
                    # Successfully found the student
                    student_name = res.iloc[0]['student_name']
                    st.write(f"### Results for: **{student_name}**")
                    
                    # Formatting the display table
                    display_df = res[['assessment_type', 'total_out_of_30', 'timestamp']].copy()
                    display_df.columns = ['Assessment Stage', 'Mark (/30)', 'Date Recorded']
                    st.table(display_df)
                else:
                    st.info(f"🔍 No marks found for Student Number: **{search_id}**")
                    st.warning("Note: If you have recently presented, please allow time for examiners to upload results.")
            else:
                st.error("Header Error: Please ensure your Google Sheet has a 'student_id' column.")
        else:
            st.error("The database is currently empty.")

# --- ROLE 2: PANELIST / EXAMINER (Password & Searchable Suggestions) ---
elif role == "Panelist / Examiner":
    st.header("🧑‍🏫 Examiner Portal")
    ex_pwd = st.sidebar.text_input("Examiner Access Code", type="password")
    
    if ex_pwd == "UNAM_EXAM_2026":
        st.subheader("Research Project Assessment Form")
        
        # Load data to provide name suggestions
        existing_df = load_data()
        known_names = []
        known_ids = []
        
        if not existing_df.empty and 'student_id' in existing_df.columns:
            existing_df['student_id'] = existing_df['student_id'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            known_names = sorted(existing_df['student_name'].unique().tolist())
            known_ids = sorted(existing_df['student_id'].unique().tolist())

        with st.form("scoring_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                # Suggestion logic for Names
                s_name_sel = st.selectbox("Search Existing Names", options=["[New Student]"] + known_names)
                if s_name_sel == "[New Student]":
                    s_name = st.text_input("Enter New Student Name")
                else:
                    s_name = s_name_sel

                # Suggestion logic for IDs
                s_num_sel = st.selectbox("Search Existing IDs", options=["[New ID]"] + known_ids)
                if s_num_sel == "[New ID]":
                    s_num = st.text_input("Enter New Student Number")
                else:
                    s_num = s_num_sel

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
                    # Create new row
                    new_entry = pd.DataFrame([{
                        "student_id": str(s_num).replace('.0', '').strip(),
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
                    
                    # Merge with existing data
                    updated_df = pd.concat([existing_df, new_entry], ignore_index=True)
                    
                    try:
                        conn.update(worksheet="marks", data=updated_df)
                        st.success(f"✅ Assessment for {s_name} saved!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error saving data: {e}")
    elif ex_pwd != "":
        st.error("Incorrect Access Code.")
    else:
        st.info("Enter the Examiner Access Code in the sidebar.")

# --- ROLE 3: RESEARCH COORDINATOR ---
elif role == "Research Coordinator":
    st.header("🔑 Coordinator Dashboard")
    coord_pwd = st.sidebar.text_input("Coordinator Password", type="password")
    
    if coord_pwd == "UNAM2026":
        marks_df = load_data()
        
        if not marks_df.empty:
            st.subheader("📊 Grade Summary")
            # Pivot table for easy grade viewing
            pivot = marks_df.pivot_table(index=['student_id', 'student_name'], 
                                       columns='assessment_type', 
                                       values='total_out_of_30').reset_index()
            st.dataframe(pivot, use_container_width=True)
            
            with st.expander("View Full Raw Database"):
                st.dataframe(marks_df, use_container_width=True)
            
            # Export to CSV
            csv = pivot.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Summary as CSV", csv, "UNAM_Research_Marks.csv", "text/csv")
        else:
            st.warning("No marks have been recorded yet.")
    elif coord_pwd != "":
        st.error("Incorrect Password.")
