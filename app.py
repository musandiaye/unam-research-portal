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
        return conn.read(worksheet=sheet_name, ttl=0)
    except:
        return pd.DataFrame()

# --- AUTHENTICATION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_name'] = ""

# --- SIDEBAR NAVIGATION ---
role = st.sidebar.radio("Management Menu", ["Student Registration", "Student View (Results)", "Panelist / Examiner", "Research Coordinator"])

# --- ROLE: PANELIST / EXAMINER ---
if role == "Panelist / Examiner":
    st.header("🧑‍🏫 Examiner Portal")
    
    if not st.session_state['logged_in']:
        tab1, tab2 = st.tabs(["Login", "Create Account"])
        
        with tab1:
            st.subheader("Lecturer Login")
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
            st.subheader("Register New Account")
            # RESTORED THE EXAMPLE FOR FULL NAME ONLY
            reg_full = st.text_input("Full Name", placeholder="e.g. Dr. Smith")
            reg_user = st.text_input("Choose Username")
            reg_pw = st.text_input("Choose Password", type="password")
            auth_key = st.text_input("Department Key", type="password")
            
            if st.button("Register Account"):
                if auth_key != "JEDSECE2026": 
                    st.error("Invalid Department Key. Access Denied.")
                elif not reg_full or not reg_user or not reg_pw:
                    st.error("Please fill in all registration fields.")
                else:
                    u_df = load_data("users")
                    if not u_df.empty and reg_user in u_df['username'].values:
                        st.error("Username already taken.")
                    else:
                        new_u = pd.DataFrame([{"full_name": reg_full, "username": reg_user, "password": hash_password(reg_pw)}])
                        conn.update(worksheet="users", data=pd.concat([u_df, new_u], ignore_index=True))
                        st.success("Account created! You can now login.")

    else:
        st.sidebar.info(f"Signed in: {st.session_state['user_name']}")
        if st.sidebar.button("Sign Out"):
            st.session_state['logged_in'] = False
            st.rerun()

        # --- SCORING INTERFACE ---
        s_df = load_data("students")
        m_df = load_data("marks")
        
        s_names = sorted(s_df['student_name'].unique().tolist()) if not s_df.empty else []
        sel_name = st.selectbox("Select Student to Grade", options=["[New Student]"] + s_names)
        
        sid, stitle, semail = "", "", ""
        if sel_name != "[New Student]":
            row = s_df[s_df['student_name'] == sel_name].iloc[0]
            sid, stitle, semail = clean_id(row['student_id']), row.get('research_title', ""), row.get('email', "")

        with st.form("score_form", clear_on_submit=True):
            st.subheader("1. Assessment Identification")
            c1, c2 = st.columns(2)
            with c1:
                f_name = st.text_input("Student Name", value=sel_name if sel_name != "[New Student]" else "")
                f_id = st.text_input("Student ID", value=sid)
                f_email = st.text_input("Student Email", value=semail)
            with c2:
                f_title = st.text_area("Research Title", value=stitle)
                f_stage = st.selectbox("Assessment Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Research Report (60%)"])

            st.divider()
            st.subheader("📊 Assessment Rubric & Guidelines")

            # --- VISUAL GUIDELINES ---
            st.markdown("### 1. Data Collection")
            st.info("**LO 1, 2 & 3 + ECN ELO 4 & 5**\n\n*Focus: Appropriateness of methods, data quality, and ethical considerations.*")
            m_coll = st.slider("Score for Data Collection (0-10)", 0.0, 10.0, 0.0, 0.5, key="m1")

            st.markdown("### 2. Data Analysis & Interpretation")
            st.info("**LO 1, 2 & 3 + ECN ELO 4 & 5**\n\n*Focus: Analytical depth, validity of conclusions, and link to research objectives.*")
            m_anal = st.slider("Score for Data Analysis (0-10)", 0.0, 10.0, 0.0, 0.5, key="m2")

            st.markdown("### 3. Professional Communication")
            st.info("**LO 5 + ECN ELO 6**\n\n*Focus: Visual aids, verbal delivery, technical writing quality, and response to questions.*")
            m_comm = st.slider("Score for Communication (0-10)", 0.0, 10.0, 0.0, 0.5, key="m3")

            st.divider()
            f_rem = st.text_area("Examiner Remarks & Feedback")
            
            if st.form_submit_button("Submit Final Marks"):
                final_total = float(m_coll + m_anal + m_comm)
                new_row = pd.DataFrame([{
                    "student_id": clean_id(f_id), "student_name": f_name, "email": f_email,
                    "research_title": f_title, "assessment_type": f_stage,
                    "data_coll": m_coll, "data_anal": m_anal, "comm": m_comm,
                    "total_out_of_30": final_total, "examiner": st.session_state['user_name'],
                    "remarks": f_rem, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                }])
                conn.update(worksheet="marks", data=pd.concat([m_df, new_row], ignore_index=True))
                st.success(f"Marks successfully saved for {f_name} ({final_total:.1f}/30)")
                st.balloons()

# --- OTHER ROLES ---
elif role == "Student Registration":
    st.header("📝 Student Research Registration")
    with st.form("r"):
        n = st.text_input("Full Name"); i = st.text_input("Student ID"); e = st.text_input("Email")
        s = st.text_input("Supervisor"); t = st.text_area("Research Title")
        if st.form_submit_button("Submit Registration"):
            sd = load_data("students"); ci = clean_id(i)
            if not sd.empty and ci in sd['student_id'].astype(str).values: st.error("This ID is already registered.")
            else:
                nr = pd.DataFrame([{"student_id":ci,"student_name":n,"email":e,"supervisor":s,"research_title":t}])
                conn.update(worksheet="students", data=pd.concat([sd, nr], ignore_index=True))
                st.success("Successfully Registered!")

elif role == "Student View (Results)":
    st.header("📋 View Your Results")
    sid = st.text_input("Enter Student ID")
    if sid:
        m = load_data("marks"); tid = clean_id(sid)
        res = m[m['student_id'] == tid]
        if not res.empty:
            st.table(res.groupby('assessment_type')['total_out_of_30'].mean().reset_index())

elif role == "Research Coordinator":
    st.header("🔑 Coordinator Dashboard")
    if st.sidebar.text_input("Coordinator Password", type="password") == "Blackberry":
        sd, md = load_data("students"), load_data("marks")
        if not sd.empty:
            md['student_id'] = md['student_id'].apply(clean_id)
            piv = md.pivot_table(index='student_id', columns='assessment_type', values='total_out_of_30', aggfunc='mean').reset_index() if not md.empty else pd.DataFrame()
            st.dataframe(pd.merge(sd, piv, on='student_id', how='left').fillna(0), use_container_width=True)
