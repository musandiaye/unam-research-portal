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
# Student View is now the first option (default)
role = st.sidebar.radio("Select Role", ["Student View", "Panelist / Examiner", "Research Coordinator"])

# --- HELPERS: ROBUST DATA LOADING ---
def load_data():
    try:
        return conn.read(worksheet="marks", ttl=0)
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return pd.DataFrame()

# --- ROLE 1: STUDENT VIEW (Default) ---
if role == "Student View":
    st.header("📋 Student Grade Tracker")
    search_id = st.text_input("Enter Student Number to view your marks")
    if search_id:
        df = load_data()
        if not df.empty:
            # Ensure student_id is treated as string for matching
            res = df[df['student_id'].astype(str) == str(search_id)]
            if not res.empty:
                st.write(f"### Results for: {res.iloc[0]['student_name']}")
                st.table(res[['assessment_type', 'total_out_of_30', 'timestamp']])
            else:
                st.info("No marks found for this Student Number. Please check with your supervisor.")
        else:
            st.warning("The database is currently unreachable.")

# --- ROLE 2: PANELIST / EXAMINER (Password Protected) ---
elif role == "Panelist / Examiner":
    st.header("🧑‍🏫 Examiner Portal")
    ex_pwd = st.sidebar.text_input("Examiner Access Code", type="password")
    
    # Change "Engineering@2026" to your preferred password
    if ex_pwd == "Engineering@2026":
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
        st.info("Please enter the Examiner Access Code in the sidebar to access the assessment form.")

# --- ROLE 3: RESEARCH COORDINATOR (Password Protected) ---
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
                
                if st.checkbox("Show Final Weighted Grades (Pivot)"):
                    pivot = marks_df.pivot_table(index=['student_id', 'student_name'], 
                                               columns='assessment_type', 
                                               values='total_out_of_30').reset_index()
                    st.dataframe(pivot)
            else:
                st.warning("No data available in the marks sheet.")

        with tab2:
            st.subheader("Identify Defaulters")
            uploaded_list = st.file_uploader("Upload Student Master List (CSV)", type="csv")
            
            if uploaded_list and not marks_df.empty:
                student_list_df = pd.read_csv(uploaded_list)
                check_stage = st.selectbox("Check completion for:", 
                                         ["Presentation 1 (10%)", "Presentation 2 (10%)", 
                                          "Presentation 3 (20%)", "Final Research Report (60%)"])
                
                if st.button("Identify Defaulters"):
                    submitted_ids = marks_df[marks_df['assessment_type'] == check_stage]['student_id'].astype(str).tolist()
                    defaulters = student_list_df[~student_list_df['student_id'].astype(str).isin(submitted_ids)]
                    
                    if not defaulters.empty:
                        st.warning(f"Found {len(defaulters)} students missing {check_stage}.")
                        st.dataframe(defaulters[['student_id', 'student_name', 'email', 'supervisor']])
                        
                        emails = ",".join(defaulters['email'].astype(str).tolist())
                        subject = f"URGENT: Missing {check_stage} Submission"
                        body = "Dear Student,\n\nOur records indicate your research marks for the current stage are missing."
                        mailto_link = f"mailto:{emails}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
                        st.markdown(f'<a href="{mailto_link}" target="_blank" style="padding: 10px; background-color: #ff4b4b; color: white; border-radius: 5px; text-decoration: none;">📧 Send Batch Reminder</a>', unsafe_allow_html=True)
                    else:
                        st.success("All students are up to date!")
    elif coord_pwd != "":
        st.error("Incorrect Coordinator Password.")
    else:
        st.info("Enter the Coordinator Password to view management tools.")

