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
# Requires Service Account JSON in Streamlit Secrets for 'update' functionality
conn = st.connection("gsheets", type=GSheetsConnection)

# --- ROLE SELECTION ---
st.sidebar.title("Management Menu")
role = st.sidebar.radio("Select Role", ["Student View", "Panelist / Examiner", "Research Coordinator"])

# --- HELPERS: DATA LOADING ---
def load_data():
    try:
        # Connects to the worksheet tab named 'marks'
        return conn.read(worksheet="marks", ttl=0)
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return pd.DataFrame()

# --- ROLE 1: STUDENT VIEW (Smart-Search Fix) ---
if role == "Student View":
    st.header("📋 Student Grade Tracker")
    search_id = st.text_input("Enter Student Number to view your marks").strip()
    
    if search_id:
        df = load_data()
        if not df.empty:
            # FIX: Convert the 'student_id' column to String and strip spaces
            # This ensures '202100123' (number) matches "202100123" (text)
            df['student_id'] = df['student_id'].astype(str).str.strip()
            
            # Filter the database for the entered ID
            res = df[df['student_id'] == str(search_id)]
            
            if not res.empty:
                # If we found the student, show the name AND the marks table
                student_name = res.iloc[0]['student_name']
                st.write(f"### Results for: **{student_name}**")
                
                # Format the table for display
                display_df = res[['assessment_type', 'total_out_of_30', 'timestamp']].copy()
                display_df.columns = ['Assessment Stage', 'Mark (/30)', 'Date Recorded']
                st.table(display_df)
            else:
                st.info(f"🔍 No marks found for Student Number: **{search_id}**")
                st.warning("Ensure the ID is correct. If you recently presented, marks may not be uploaded yet.")
        else:
            st.error("The database is currently empty or unreachable.")

# --- ROLE 2: PANELIST / EXAMINER (Password Protected) ---
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
        st.info("Enter the Examiner Access Code in the sidebar to access the assessment form.")

# --- ROLE 3: RESEARCH COORDINATOR (Password & 1-Week Logic) ---
elif role == "Research Coordinator":
    st.header("🔑 Coordinator Dashboard")
    coord_pwd = st.sidebar.text_input("Coordinator Password", type="password")
    
    if coord_pwd == "UNAM2026":
        marks_df = load_data()
        tab1, tab2 = st.tabs(["📊 Grade Management", "🔔 Automated Reminders"])

        with tab1:
            if not marks_df.empty:
                st.subheader("Consolidated Gradebook")
                st.dataframe(marks_df, use_container_width=True)
                
                if st.checkbox("Show Summary Pivot"):
                    pivot = marks_df.pivot_table(index=['student_id', 'student_name'], 
                                               columns='assessment_type', 
                                               values='total_out_of_30').reset_index()
                    st.dataframe(pivot)
            else:
                st.warning("No marks recorded yet.")

        with tab2:
            st.subheader("Identify Missing Submissions")
            uploaded_list = st.file_uploader("Upload Student Master List (CSV)", type="csv")
            
            if uploaded_list:
                student_list_df = pd.read_csv(uploaded_list)
                
                col1, col2 = st.columns(2)
                with col1:
                    check_stage = st.selectbox("Check completion for:", 
                                             ["Presentation 1 (10%)", "Presentation 2 (10%)", 
                                              "Presentation 3 (20%)", "Final Research Report (60%)"])
                with col2:
                    pres_date = st.date_input("Actual Presentation Date", value=datetime.now())

                # Calculate if 7 days have passed
                days_since_pres = (datetime.now().date() - pres_date).days
                
                if st.button("Identify Defaulters"):
                    if not marks_df.empty:
                        # Normalize both lists for comparison
                        marks_df['student_id'] = marks_df['student_id'].astype(str).str.strip()
                        student_list_df['student_id'] = student_list_df['student_id'].astype(str).str.strip()
                        
                        submitted_ids = marks_df[marks_df['assessment_type'] == check_stage]['student_id'].tolist()
                        defaulters = student_list_df[~student_list_df['student_id'].isin(submitted_ids)]
                        
                        if not defaulters.empty:
                            st.warning(f"Found {len(defaulters)} students missing {check_stage}.")
                            st.dataframe(defaulters[['student_id', 'student_name', 'email', 'supervisor']])
                            
                            if days_since_pres >= 7:
                                st.success(f"✅ Grace period complete ({days_since_pres} days). Reminders allowed.")
                                emails = ",".join(defaulters['email'].astype(str).tolist())
                                subject = f"URGENT: Missing {check_stage} Submission"
                                body = f"Dear Student,\n\nOur records indicate your research marks for {check_stage} (held on {pres_date}) are missing after the 1-week grace period."
                                mailto_link = f"mailto:{emails}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
                                st.markdown(f'<a href="{mailto_link}" target="_blank" style="padding: 10px; background-color: #ff4b4b; color: white; border-radius: 5px; text-decoration: none;">📧 Send Batch Reminder Email</a>', unsafe_allow_html=True)
                            else:
                                st.error(f"⚠️ Reminder Blocked: Wait {7 - days_since_pres} more day(s) to reach the 1-week rule.")
                        else:
                            st.success("All students in the master list have recorded marks!")
    elif coord_pwd != "":
        st.error("Incorrect Coordinator Password.")
    else:
        st.info("Enter the Coordinator Password to view management tools.")
