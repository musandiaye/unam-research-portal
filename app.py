import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="UNAM Research Portal", layout="wide")

# --- LOGO (Replace with your GitHub/Local Path) ---
LOGO_URL = "unam_logo.png" 
try:
    st.sidebar.image(LOGO_URL, use_container_width=True)
except:
    st.sidebar.write("### UNAM Engineering")

st.title("UNAM: School of Engineering and the Built Environment")
st.subheader("Department of Electrical and Computer Engineering")

# --- GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- HELPERS: DATA CLEANING ---
def clean_id(val):
    if pd.isna(val) or val == "": return ""
    return str(val).split('.')[0].strip()

def load_marks():
    try:
        df = conn.read(worksheet="marks", ttl=0)
        if not df.empty: df['student_id'] = df['student_id'].apply(clean_id)
        return df
    except: return pd.DataFrame()

def load_students():
    try:
        df = conn.read(worksheet="students", ttl=0)
        if not df.empty: df['student_id'] = df['student_id'].apply(clean_id)
        return df
    except: return pd.DataFrame()

# --- ROLE SELECTION ---
role = st.sidebar.radio("Management Menu", ["Student Registration", "Student View (Results)", "Panelist / Examiner", "Research Coordinator"])

# --- ROLE 2: PANELIST / EXAMINER (Restored Guidelines) ---
if role == "Panelist / Examiner":
    st.header("🧑‍🏫 Examiner Portal")
    if st.sidebar.text_input("Examiner Access Code", type="password") == "Engineering@2026":
        students_df = load_students()
        marks_df = load_marks()
        
        names_list = sorted(students_df['student_name'].unique().tolist()) if not students_df.empty else []
        s_name_sel = st.selectbox("Search Student Name", options=["[New Student]"] + names_list)
        
        selected_id, selected_title, selected_email = "", "", ""
        if s_name_sel != "[New Student]":
            row = students_df[students_df['student_name'] == s_name_sel].iloc[0]
            selected_id, selected_title, selected_email = row['student_id'], row.get('research_title', ""), row.get('email', "")

        with st.form("scoring_form", clear_on_submit=True):
            st.subheader("1. Identity & Stage")
            col1, col2 = st.columns(2)
            with col1:
                final_name = st.text_input("Student Name", value=s_name_sel if s_name_sel != "[New Student]" else "")
                final_id = st.text_input("Student Number", value=selected_id)
                final_email = st.text_input("Email", value=selected_email)
            with col2:
                final_title = st.text_area("Research Title", value=selected_title)
                p_type = st.selectbox("Assessment Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Research Report (60%)"])
                ex_name = st.text_input("Name of Examiner")

            st.divider()
            st.subheader("2. Scoring Rubric")

            # --- RESTORED SCORING GUIDELINES ---
            st.markdown("#### A. Data Collection")
            st.caption("Criteria: LO 1, 2 & 3 + ECN ELO 4 & 5 (Methods, Ethics, and Quality of Data)")
            d_coll = st.slider("Mark for Data Collection", 0.0, 10.0, 0.0, 0.5, key="sc1")

            st.markdown("#### B. Data Analysis and Interpretation")
            st.caption("Criteria: LO 1, 2 & 3 + ECN ELO 4 & 5 (Analytical depth, Validity of conclusions)")
            d_anal = st.slider("Mark for Data Analysis", 0.0, 10.0, 0.0, 0.5, key="sc2")

            st.markdown("#### C. Professional and Technical Communication")
            st.caption("Criteria: LO 5 and ECN ELO 6 (Clarity, Structure, Visual Aids, and Q&A)")
            d_comm = st.slider("Mark for Communication", 0.0, 10.0, 0.0, 0.5, key="sc3")

            st.divider()
            remarks = st.text_area("General Remarks / Feedback")
            
            if st.form_submit_button("Submit Assessment"):
                cid = clean_id(final_id)
                if not cid or not final_name or not ex_name:
                    st.error("Missing Student ID, Name, or Examiner Name.")
                else:
                    total = float(d_coll + d_anal + d_comm)
                    new_mark = pd.DataFrame([{
                        "student_id": cid, "student_name": final_name, "email": final_email,
                        "research_title": final_title, "assessment_type": p_type,
                        "data_coll": d_coll, "data_anal": d_anal, "comm": d_comm,
                        "total_out_of_30": total, "examiner": ex_name, 
                        "remarks": remarks, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                    }])
                    conn.update(worksheet="marks", data=pd.concat([marks_df, new_mark], ignore_index=True))
                    st.success(f"Score of {total:.1f}/30 submitted!")
                    st.balloons()

# (Other roles: Registration, Student View, Coordinator logic remains same as previous version)
elif role == "Student Registration":
    st.header("📝 Research Project Registration")
    # ... [Same Registration code as before]
    with st.form("reg"):
        n = st.text_input("Full Name"); i = st.text_input("Student ID"); e = st.text_input("Email")
        s = st.text_input("Supervisor"); t = st.text_area("Title")
        if st.form_submit_button("Register"):
            sd = load_students(); ci = clean_id(i)
            if not all([n, ci, e, s, t]): st.error("Fill all fields")
            elif not sd.empty and ci in sd['student_id'].values: st.error("Already registered")
            else:
                new_s = pd.DataFrame([{"student_id":ci,"student_name":n,"email":e,"supervisor":s,"research_title":t}])
                conn.update(worksheet="students", data=pd.concat([sd, new_s], ignore_index=True))
                st.success("Registered!")

elif role == "Student View (Results)":
    st.header("📋 Student Grade Tracker")
    sid = st.text_input("Enter Student Number")
    if sid:
        m = load_marks(); tid = clean_id(sid)
        res = m[m['student_id'] == tid]
        if not res.empty:
            st.write(f"### Results for: {res.iloc[0]['student_name']}")
            avg = res.groupby('assessment_type')['total_out_of_30'].mean().reset_index()
            avg['total_out_of_30'] = avg['total_out_of_30'].map('{:,.1f}'.format)
            st.table(avg)

elif role == "Research Coordinator":
    st.header("🔑 Coordinator Dashboard")
    if st.sidebar.text_input("Password", type="password") == "Blackberry":
        sd = load_students(); md = load_marks()
        if not sd.empty:
            if not md.empty:
                piv = md.pivot_table(index='student_id', columns='assessment_type', values='total_out_of_30', aggfunc='mean').reset_index()
                rep = pd.merge(sd, piv, on='student_id', how='left').fillna(0.0)
            else: rep = sd
            st.dataframe(rep, use_container_width=True)
