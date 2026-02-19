import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import io
import urllib.parse
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="UNAM Research Portal", layout="wide")
st.title("UNAM: School of Engineering and the Built Environment")
st.subheader("Department of Electrical and Computer Engineering")

# --- GOOGLE SHEETS CONNECTION ---
# Note: Ensure your Secret URL is set in Streamlit Cloud Settings
conn = st.connection("gsheets", type=GSheetsConnection)

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("Management Menu")
role = st.sidebar.radio("Select Role", ["Panelist / Examiner", "Research Coordinator", "Student View"])

# --- ROLE 1: PANELIST / EXAMINER ---
if role == "Panelist / Examiner":
    st.header("Research Project Assessment Form")
    st.info("Record marks based on the department's assessment criteria.")

    with st.form("scoring_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            s_name = st.text_input("Student's Name")
            s_num = st.text_input("Student Number")
        with col2:
            p_type = st.selectbox("Assessment Stage", 
                                ["Presentation 1 (10%)", 
                                 "Presentation 2 (10%)", 
                                 "Presentation 3 (20%)", 
                                 "Final Research Report (60%)"])
            ex_name = st.text_input("Name of Examiner")

        st.markdown("---")
        st.markdown("### Scoring (LO 1, 2, 3, 5)")
        d_coll = st.slider("1. Data Collection /10", 0, 10, 0)
        d_anal = st.slider("2. Data Analysis /10", 0, 10, 0)
        d_comm = st.slider("3. Professional Communication /10", 0, 10, 0)
        remarks = st.text_area("General Remarks")
        
        if st.form_submit_button("Submit Marks to Google Sheets"):
            # Fetch current data from the 'marks' tab
            existing_data = conn.read(worksheet="marks", ttl=0)
            
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
            conn.update(worksheet="marks", data=updated_df)
            st.success(f"Assessment for {s_name} saved!")

# --- ROLE 2: COORDINATOR DASHBOARD ---
elif role == "Research Coordinator":
    pwd = st.sidebar.text_input("Enter Coordinator Password", type="password")
    if pwd == "UNAM2026":
        st.header("Coordinator Control Panel")
        
        # Load marks from Google Sheets
        marks_df = conn.read(worksheet="marks", ttl=0)

        tab1, tab2 = st.tabs(["📊 Grade Management", "🔔 Automated Reminders"])

        with tab1:
            if not marks_df.empty:
                st.subheader("Final Calculated Grades (40/60 Split)")
                pivot = marks_df.pivot_table(index=['student_id', 'student_name'], 
                                           columns='assessment_type', 
                                           values='total_out_of_30').reset_index()
                
                def calc_final(row):
                    p1 = (row.get('Presentation 1 (10%)', 0) / 30) * 10
                    p2 = (row.get('Presentation 2 (10%)', 0) / 30) * 10
                    p3 = (row.get('Presentation 3 (20%)', 0) / 30) * 20
                    rep = (row.get('Final Research Report (60%)', 0) / 30) * 60
                    return round(p1 + p2 + p3 + rep, 2)

                pivot['Final_Mark_100%'] = pivot.apply(calc_final, axis=1)
                st.dataframe(pivot, use_container_width=True)

                # Excel Export
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    pivot.to_excel(writer, index=False, sheet_name='Final_Results')
                    marks_df.to_excel(writer, index=False, sheet_name='Raw_Entries')
                
                st.download_button("📥 Download Official Marks (Excel)", buffer.getvalue(), 
                                 file_name="UNAM_Research_Final.xlsx", mime="application/vnd.ms-excel")
            else:
                st.warning("No marks recorded yet.")

        with tab2:
            st.subheader("Identify Missing Submissions")
            st.info("Upload your class list CSV (headers: student_id, student_name, email, supervisor)")
            
            uploaded_list = st.file_uploader("Upload Student Master List (CSV)", type="csv")
            
            if uploaded_list:
                student_list_df = pd.read_csv(uploaded_list)
                check_stage = st.selectbox("Check completion for:", 
                                         ["Presentation 1 (10%)", "Presentation 2 (10%)", 
                                          "Presentation 3 (20%)", "Final Research Report (60%)"])
                
                if st.button("Identify Defaulters"):
                    # Compare student list vs marks
                    submitted_ids = marks_df[marks_df['assessment_type'] == check_stage]['student_id'].astype(str).tolist()
                    defaulters = student_list_df[~student_list_df['student_id'].astype(str).isin(submitted_ids)]
                    
                    if not defaulters.empty:
                        st.warning(f"Found {len(defaulters)} students with missing marks for {check_stage}.")
                        st.dataframe(defaulters)
                        
                        # Generate Email Nudge
                        emails = ",".join(defaulters['email'].astype(str).tolist())
                        subject = f"URGENT: Missing Research Submission - {check_stage}"
                        body = "Dear Student, our records show your marks for the current stage are missing. Please contact your supervisor immediately."
                        mailto_link = f"mailto:{emails}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
                        st.markdown(f'<a href="{mailto_link}" target="_blank" style="padding: 10px; background-color: #ff4b4b; color: white; border-radius: 5px; text-decoration: none;">📧 Send Group Reminder Email</a>', unsafe_allow_html=True)
                    else:
                        st.success("All students in your uploaded list have been graded for this stage!")

# --- ROLE 3: STUDENT VIEW ---
else:
    st.header("Student Grade Tracker")
    search_id = st.text_input("Enter Student Number to view your marks")
    if search_id:
        df = conn.read(worksheet="marks", ttl=0)
        res = df[df['student_id'].astype(str) == str(search_id)]
        if not res.empty:
            st.table(res[['assessment_type', 'total_out_of_30', 'timestamp']])
        else:
            st.error("No marks found for this Student Number.")
