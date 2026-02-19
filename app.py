import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import io
import urllib.parse
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="UNAM Research Portal", layout="wide")
st.title("UNAM: School of Engineering and the Built Environment")
st.subheader("Automated Research Coordination System")

# --- GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("Management Menu")
role = st.sidebar.radio("Select Role", ["Panelist / Examiner", "Research Coordinator", "Student View"])

# --- ROLE 1: PANELIST / EXAMINER (Unchanged) ---
if role == "Panelist / Examiner":
    st.header("Research Project Assessment Form")
    with st.form("scoring_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            s_name = st.text_input("Student's Name")
            s_num = st.text_input("Student Number")
        with col2:
            p_type = st.selectbox("Assessment Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Research Report (60%)"])
            ex_name = st.text_input("Name of Examiner")
        
        st.markdown("---")
        d_coll = st.slider("1. Data Collection /10", 0, 10, 0)
        d_anal = st.slider("2. Data Analysis /10", 0, 10, 0)
        d_comm = st.slider("3. Communication /10", 0, 10, 0)
        remarks = st.text_area("General Remarks")
        
        if st.form_submit_button("Submit Marks"):
            existing_data = conn.read(worksheet="marks", ttl=0)
            new_entry = pd.DataFrame([{"student_id": s_num, "student_name": s_name, "assessment_type": p_type, "data_coll": d_coll, "data_anal": d_anal, "comm": d_comm, "total_out_of_30": d_coll + d_anal + d_comm, "examiner": ex_name, "remarks": remarks, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")}])
            updated_df = pd.concat([existing_data, new_entry], ignore_index=True)
            conn.update(worksheet="marks", data=updated_df)
            st.success("Marks recorded!")

# --- ROLE 2: COORDINATOR DASHBOARD (With Automated Reminders) ---
elif role == "Research Coordinator":
    pwd = st.sidebar.text_input("Enter Coordinator Password", type="password")
    if pwd == "UNAM2026":
        st.header("Coordinator Control Panel")
        
        # Load both tabs from Google Sheets
        marks_df = conn.read(worksheet="marks", ttl=0)
        student_list_df = conn.read(worksheet="students", ttl=0)

        tab1, tab2 = st.tabs(["📊 Grade Management", "🔔 Automated Reminders"])

        with tab1:
            if not marks_df.empty:
                st.subheader("Calculated Final Marks")
                pivot = marks_df.pivot_table(index=['student_id', 'student_name'], columns='assessment_type', values='total_out_of_30').reset_index()
                
                def calc_final(row):
                    p1 = (row.get('Presentation 1 (10%)', 0) / 30) * 10
                    p2 = (row.get('Presentation 2 (10%)', 0) / 30) * 10
                    p3 = (row.get('Presentation 3 (20%)', 0) / 30) * 20
                    rep = (row.get('Final Research Report (60%)', 0) / 30) * 60
                    return round(p1 + p2 + p3 + rep, 2)

                pivot['Final_Mark_100%'] = pivot.apply(calc_final, axis=1)
                st.dataframe(pivot)
            else:
                st.warning("No marks found.")

        with tab2:
            st.subheader("Deadlines & Nudges")
            check_stage = st.selectbox("Check completion for:", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Research Report (60%)"])
            
            if st.button("Identify Defaulters"):
                # Logic: Filter marks for the selected stage
                submitted_ids = marks_df[marks_df['assessment_type'] == check_stage]['student_id'].tolist()
                
                # Identify students in the master list who ARE NOT in the submitted list
                defaulters = student_list_df[~student_list_df['student_id'].astype(str).isin([str(x) for x in submitted_ids])]
                
                if not defaulters.empty:
                    st.warning(f"Found {len(defaulters)} students who haven't submitted/presented for {check_stage}.")
                    st.dataframe(defaulters[['student_id', 'student_name', 'email', 'supervisor']])
                    
                    # Create a "Nudge All" email link
                    emails = ",".join(defaulters['email'].tolist())
                    subject = f"URGENT: Missing Submission for {check_stage}"
                    body = f"Dear Student,\n\nOur records show that your marks for {check_stage} have not been recorded. Please ensure you stick to the research calendar.\n\nRegards,\nResearch Coordinator"
                    
                    # Encode for URL
                    mailto_link = f"mailto:{emails}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
                    st.markdown(f'<a href="{mailto_link}" target="_blank" style="padding: 10px; background-color: #ff4b4b; color: white; border-radius: 5px; text-decoration: none;">📧 Send Group Reminder Email</a>', unsafe_allow_name=True)
                else:
                    st.success("Everyone has submitted! No reminders needed.")

# --- ROLE 3: STUDENT VIEW (Unchanged) ---
else:
    search_id = st.text_input("Enter Student Number")
    if search_id:
        df = conn.read(worksheet="marks", ttl=0)
        res = df[df['student_id'] == search_id]
        if not res.empty:
            st.table(res[['assessment_type', 'total_out_of_30', 'timestamp']])
        else:
            st.error("No marks found.")
