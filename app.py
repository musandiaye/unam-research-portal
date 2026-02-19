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
# This connection now uses the Service Account credentials from your Secrets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- ROLE SELECTION ---
st.sidebar.title("Management Menu")
role = st.sidebar.radio("Select Role", ["Panelist / Examiner", "Research Coordinator", "Student View"])

# --- HELPERS: ROBUST DATA LOADING ---
def load_data():
    try:
        # We specify the worksheet name 'marks' which you renamed in your Google Sheet
        return conn.read(worksheet="marks", ttl=0)
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return pd.DataFrame()

# --- ROLE 1: PANELIST / EXAMINER ---
if role == "Panelist / Examiner":
    st.header("Research Project Assessment Form")
    
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
                st.error("Please fill in all student and examiner details.")
            else:
                # 1. Fetch current data
                existing_data = load_data()
                
                # 2. Create new row
                new_entry = pd.DataFrame([{
                    "student_id": str(s_num),
                    "student_name": s_name,
                    "assessment_type": p_type,
                    "data_coll": d_coll,
                    "data_anal": d_anal,
                    "comm": d_comm,
                    "total_out_of_30": d_coll + d_anal + d_comm,
                    "examiner": ex_name,
                    "remarks": remarks,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                }])
                
                # 3. Append and Update
                # Note: 'worksheet' must match your tab name exactly (case sensitive)
                updated_df = pd.concat([existing_data, new_entry], ignore_index=True)
                
                try:
                    conn.update(worksheet="marks", data=updated_df)
                    st.success(f"✅ Assessment for {s_name} successfully saved to Google Sheets!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Failed to save to Google Sheets. Ensure you are using a Service Account. Error: {e}")

# --- ROLE 2: COORDINATOR DASHBOARD ---
elif role == "Research Coordinator":
    pwd = st.sidebar.text_input("Enter Password", type="password")
    if pwd == "UNAM2026":
        marks_df = load_data()

        tab1, tab2 = st.tabs(["📊 Grade Management", "🔔 Automated Reminders"])

        with tab1:
            if not marks_df.empty:
                st.subheader("Current Gradebook")
                st.dataframe(marks_df, use_container_width=True)
                
                # Summary View
                if st.checkbox("Show Summary (Pivot Table)"):
                    pivot = marks_df.pivot_table(index=['student_id', 'student_name'], 
                                               columns='assessment_type', 
                                               values='total_out_of_30').reset_index()
                    st.dataframe(pivot)
            else:
                st.warning("The marks database is currently empty.")

        with tab2:
            st.subheader("Identify Missing Submissions")
            # Using File Uploader for student list is safer/easier than connecting another sheet
            uploaded_list = st.file_uploader("Upload Student Master List (CSV)", type="csv")
            
            if uploaded_list and not marks_df.empty:
                student_list_df = pd.read_csv(uploaded_list)
                check_stage = st.selectbox("Check completion for:", 
                                         ["Presentation 1 (10%)", "Presentation 2 (10%)", 
                                          "Presentation 3 (20%)", "Final Research Report (60%)"])
                
                if st.button("Identify Defaulters"):
                    # Match IDs as strings to avoid format errors
                    submitted_ids = marks_df[marks_df['assessment_type'] == check_stage]['student_id'].astype(str).tolist()
                    defaulters = student_list_df[~student_list_df['student_id'].astype(str).isin(submitted_ids)]
                    
                    if not defaulters.empty:
                        st.warning(f"Found {len(defaulters)} students who have not submitted marks for {check_stage}.")
                        st.dataframe(defaulters[['student_id', 'student_name', 'email', 'supervisor']])
                        
                        # Email Nudge Feature
                        emails = ",".join(defaulters['email'].astype(str).tolist())
                        subject = f"URGENT: Missing {check_stage} Submission"
                        body = "Dear Student,\n\nOur records show that your research marks for the current stage are missing. Please contact your supervisor immediately."
                        mailto_link = f"mailto:{emails}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
                        st.markdown(f'<a href="{mailto_link}" target="_blank" style="padding: 10px; background-color: #ff4b4b; color: white; border-radius: 5px; text-decoration: none;">📧 Send Reminder to all Defaulters</a>', unsafe_allow_html=True)
                    else:
                        st.success("All students in the master list have submitted marks for this stage!")

# --- ROLE 3: STUDENT VIEW ---
else:
    st.header("Student Grade Tracker")
    search_id = st.text_input("Enter Student Number to view your marks")
    if search_id:
        df = load_data()
        if not df.empty:
            res = df[df['student_id'].astype(str) == str(search_id)]
            if not res.empty:
                st.write(f"Results for: {res.iloc[0]['student_name']}")
                st.table(res[['assessment_type', 'total_out_of_30', 'timestamp']])
            else:
                st.info("No marks found for this Student Number.")
