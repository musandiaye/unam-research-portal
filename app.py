import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import hashlib

# --- PAGE CONFIG ---
st.set_page_config(page_title="UNAM Research Portal", layout="wide")

# --- LOGO ---
try:
    st.sidebar.image("unam_logo.png", use_container_width=True)
except:
    st.sidebar.write("### UNAM Engineering")

st.title("UNAM: School of Engineering and the Built Environment")
st.subheader("Department of Electrical and Computer Engineering")

# --- CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- HELPERS ---
def clean_id(val):
    if pd.isna(val) or val == "": return ""
    return str(val).split('.')[0].strip()

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def load_data(sheet_name):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if not df.empty and 'student_id' in df.columns:
            df['student_id'] = df['student_id'].astype(str).apply(clean_id)
        return df
    except:
        return pd.DataFrame()

# --- AUTHENTICATION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_name'] = ""

# --- SIDEBAR NAVIGATION ---
role = st.sidebar.radio("Management Menu", ["Student Registration", "Student View (Results)", "Panelist / Examiner", "Research Coordinator"])

# --- ROLE: STUDENT REGISTRATION ---
if role == "Student Registration":
    st.header("📝 Student Research Registration")
    with st.form("reg_form", clear_on_submit=True):
        n = st.text_input("Full Name")
        i = st.text_input("Student ID")
        e = st.text_input("Email")
        s = st.text_input("Supervisor")
        t = st.text_area("Research Title")
        if st.form_submit_button("Submit Registration"):
            sd = load_data("students")
            ci = clean_id(i)
            if not all([n, ci, e, s, t]):
                st.error("Please fill in all fields.")
            elif not sd.empty and ci in sd['student_id'].values:
                st.error(f"ID {ci} is already registered.")
            else:
                nr = pd.DataFrame([{"student_id":ci,"student_name":n,"email":e,"supervisor":s,"research_title":t}])
                conn.update(worksheet="students", data=pd.concat([sd, nr], ignore_index=True))
                st.success("Successfully Registered!")
                st.balloons()

# --- ROLE: STUDENT VIEW (ANONYMIZED & AVERAGED) ---
elif role == "Student View (Results)":
    st.header("📋 View Your Results")
    sid_input = st.text_input("Enter Student ID").strip()
    if sid_input:
        tid = clean_id(sid_input)
        m_df = load_data("marks")
        if not m_df.empty:
            student_results = m_df[m_df['student_id'] == tid].copy()
            if not student_results.empty:
                st.success(f"Viewing Results for: {student_results.iloc[0]['student_name']}")
                # Grouping by stage to calculate average
                final_view = student_results.groupby('assessment_type')['total_out_of_30'].mean().reset_index()
                final_view.columns = ['Assessment Stage', 'Final Average Mark (/30)']
                final_view['Final Average Mark (/30)'] = final_view['Final Average Mark (/30)'].astype(float).round(1)
                st.table(final_view)
            else:
                st.warning(f"No marks found for ID: {tid}")
        else:
            st.info("The results database is currently empty.")

# --- ROLE: PANELIST / EXAMINER ---
elif role == "Panelist / Examiner":
    st.header("🧑‍🏫 Examiner Portal")
    if not st.session_state['logged_in']:
        tab1, tab2 = st.tabs(["Login", "Create Account"])
        with tab1:
            l_user = st.text_input("Username")
            l_pw = st.text_input("Password", type="password")
            if st.button("Login"):
                u_df = load_data("users")
                if not u_df.empty:
                    match = u_df[(u_df['username'] == l_user) & (u_df['password'] == hash_password(l_pw))]
                    if not match.empty:
                        st.session_state['logged_in'] = True
                        st.session_state['user_name'] = match.iloc[0]['full_name']
                        st.rerun()
                    else: st.error("Invalid credentials.")
        with tab2:
            st.subheader("New Account Registration")
            # UPDATED PLACEHOLDER HERE
            reg_full = st.text_input("Full Name", placeholder="e.g. Mr/Dr/Prof. Smith")
            reg_user = st.text_input("Choose Username")
            reg_pw = st.text_input("Choose Password", type="password")
            auth_key = st.text_input("Department Key", type="password")
            if st.button("Register Account"):
                if auth_key != "JEDSECE2026": 
                    st.error("Invalid Department Key.")
                else:
                    u_df = load_data("users")
                    new_u = pd.DataFrame([{"full_name": reg_full, "username": reg_user, "password": hash_password(reg_pw)}])
                    conn.update(worksheet="users", data=pd.concat([u_df, new_u], ignore_index=True))
                    st.success("Account created! Please switch to Login tab.")
    else:
        st.sidebar.info(f"Signed in: {st.session_state['user_name']}")
        if st.sidebar.button("Sign Out"):
            st.session_state['logged_in'] = False
            st.rerun()

        s_df = load_data("students")
        m_df = load_data("marks")
        s_names = sorted(s_df['student_name'].unique().tolist()) if not s_df.empty else []
        sel_name = st.selectbox("Select Student", options=["[New Student]"] + s_names)
        
        sid, stitle = "", ""
        if sel_name != "[New Student]":
            row = s_df[s_df['student_name'] == sel_name].iloc[0]
            sid, stitle = clean_id(row['student_id']), row.get('research_title', "")

        with st.form("score_form", clear_on_submit=True):
            f_name = st.text_input("Student Name", value=sel_name if sel_name != "[New Student]" else "")
            f_id = st.text_input("Student ID", value=sid)
            st.text_input("Assigned Examiner", value=st.session_state['user_name'], disabled=True)
            f_stage = st.selectbox("Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Research Report (60%)"])
            
            st.divider()
            st.info("**LO 1-5 & ECN ELO 4-6 applied below**")
            m_coll = st.slider("Data Collection (0-10)", 0.0, 10.0, 0.0, 0.5)
            m_anal = st.slider("Analysis (0-10)", 0.0, 10.0, 0.0, 0.5)
            m_comm = st.slider("Communication (0-10)", 0.0, 10.0, 0.0, 0.5)
            
            if st.form_submit_button("Submit Marks"):
                final_total = float(m_coll + m_anal + m_comm)
                new_row = pd.DataFrame([{
                    "student_id": clean_id(f_id), "student_name": f_name,
                    "assessment_type": f_stage, "total_out_of_30": final_total,
                    "examiner": st.session_state['user_name'],
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                }])
                conn.update(worksheet="marks", data=pd.concat([m_df, new_row], ignore_index=True))
                st.success("Marks Submitted Successfully!")

# --- ROLE: RESEARCH COORDINATOR ---
elif role == "Research Coordinator":
    st.header("🔑 Coordinator Dashboard")
    if st.sidebar.text_input("Coordinator Password", type="password") == "Blackberry":
        sd, md = load_data("students"), load_data("marks")
        if not sd.empty:
            if not md.empty:
                piv = md.pivot_table(index='student_id', columns='assessment_type', values='total_out_of_30', aggfunc='mean').reset_index()
                final_report = pd.merge(sd, piv, on='student_id', how='left').fillna(0)
                st.dataframe(final_report, use_container_width=True)
                st.write("### Raw Submission Log")
                st.dataframe(md.sort_values(by="timestamp", ascending=False), use_container_width=True)
            else:
                st.dataframe(sd, use_container_width=True)
