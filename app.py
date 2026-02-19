import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import io
from datetime import datetime

# --- SETTINGS ---
st.set_page_config(page_title="UNAM Research Portal", layout="wide")
st.title("UNAM: School of Engineering and the Built Environment")

# --- CONNECT TO GOOGLE SHEETS ---
# Note: You will set the URL in the Streamlit Cloud Secrets or a config file
conn = st.connection("gsheets", type=GSheetsConnection)

# --- SIDEBAR ---
role = st.sidebar.radio("Select Role", ["Panelist / Examiner", "Research Coordinator", "Student View"])

# --- ROLE 1: PANELIST / EXAMINER ---
if role == "Panelist / Examiner":
    st.header("Assessment Form")
    with st.form("scoring_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            s_name = st.text_input("Student's Name")
            s_num = st.text_input("Student Number")
        with col2:
            p_type = st.selectbox("Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Research Report (60%)"])
            ex_name = st.text_input("Examiner Name")

        st.markdown("### Scoring (Based on Dept. Guidelines)")
        d_coll = st.slider("Data Collection /10", 0, 10, 0)
        d_anal = st.slider("Data Analysis /10", 0, 10, 0)
        d_comm = st.slider("Communication /10", 0, 10, 0)
        rem = st.text_area("Remarks")
        
        if st.form_submit_button("Submit Marks"):
            # Fetch existing data
            existing_data = conn.read(worksheet="marks", ttl=0)
            
            # Create new row
            new_entry = pd.DataFrame([{
                "student_id": s_num, "student_name": s_name, "assessment_type": p_type,
                "data_coll": d_coll, "data_anal": d_anal, "comm": d_comm,
                "total_out_of_30": d_coll + d_anal + d_comm, "examiner": ex_name,
                "remarks": rem, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
            }])
            
            # Append and Update Google Sheet
            updated_df = pd.concat([existing_data, new_entry], ignore_index=True)
            conn.update(worksheet="marks", data=updated_df)
            st.success("Marks saved to Google Sheets!")

# --- ROLE 2: COORDINATOR ---
elif role == "Research Coordinator":
    pwd = st.sidebar.text_input("Password", type="password")
    if pwd == "UNAM2026":
        df = conn.read(worksheet="marks", ttl=0)
        st.dataframe(df)
        
        # Final Grade Calculation (40/60 Split)
        if not df.empty:
            pivot = df.pivot_table(index=['student_id', 'student_name'], 
                                   columns='assessment_type', 
                                   values='total_out_of_30').reset_index()
            
            def calc_final(row):
                p1 = (row.get('Presentation 1 (10%)', 0) / 30) * 10
                p2 = (row.get('Presentation 2 (10%)', 0) / 30) * 10
                p3 = (row.get('Presentation 3 (20%)', 0) / 30) * 20
                rep = (row.get('Final Research Report (60%)', 0) / 30) * 60
                return round(p1 + p2 + p3 + rep, 2)

            pivot['Final_100%'] = pivot.apply(calc_final, axis=1)
            st.write("### Weighted Final Grades")
            st.dataframe(pivot)

# --- ROLE 3: STUDENT ---
else:
    search_id = st.text_input("Enter Student Number")
    if search_id:
        df = conn.read(worksheet="marks", ttl=0)
        res = df[df['student_id'] == search_id]
        st.table(res[['assessment_type', 'total_out_of_30', 'timestamp']])