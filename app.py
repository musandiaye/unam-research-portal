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
            else:
                nr = pd.DataFrame([{"student_id":ci,"student_name":n,"email":e,"supervisor":s,"research_title":t}])
                conn.update(worksheet="students", data=pd.concat([sd, nr], ignore_index=True))
                st.success("Successfully Registered!")

# --- ROLE: STUDENT VIEW ---
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
                
                # Average scores per stage
                final_view = student_results.groupby('assessment_type')['raw_score'].mean().reset_index()
                
                # Dynamic Labeling
                def format_display(row):
                    val = float(row['raw_score'])
                    if "Report" in row['assessment_type']:
                        return f"{val:.1f} / 100"
                    return f"{val:.1f} / 30"

                final_view['Result'] = final_view.apply(format_display, axis=1)
                st.table(final_view[['assessment_type', 'Result']])
            else:
                st.warning(f"No marks found for ID: {tid}")

# --- ROLE: PANELIST / EXAMINER ---
elif role == "Panelist / Examiner":
    st.header("🧑‍🏫 Examiner Portal")
    if not st.session_state['logged_in']:
        # [Login logic same as before...]
        tab1, tab2 = st.tabs(["Login", "Create Account"])
        with tab1:
            l_user = st.text_input("Username")
            l_pw = st.text_input("Password", type="password")
            if st.button("Login"):
                u_df = load_data("users")
                if not u_df.empty and not (u_df[(u_df['username'] == l_user) & (u_df['password'] == hash_password(l_pw))]).empty:
                    match = u_df[(u_df['username'] == l_user) & (u_df['password'] == hash_password(l_pw))]
                    st.session_state['logged_in'] = True
                    st.session_state['user_name'] = match.iloc[0]['full_name']
                    st.rerun()
                else: st.error("Invalid credentials.")
        with tab2:
            reg_full = st.text_input("Full Name")
            reg_user = st.text_input("Username")
            reg_pw = st.text_input("Password", type="password")
            auth_key = st.text_input("Department Key", type="password")
            if st.button("Register"):
                if auth_key == "JEDSECE2026":
                    u_df = load_data("users")
                    new_u = pd.DataFrame([{"full_name": reg_full, "username": reg_user, "password": hash_password(reg_pw)}])
                    conn.update(worksheet="users", data=pd.concat([u_df, new_u], ignore_index=True))
                    st.success("Account Created!")
    else:
        st.sidebar.info(f"Signed in: {st.session_state['user_name']}")
        if st.sidebar.button("Sign Out"):
            st.session_state['logged_in'] = False
            st.rerun()

        s_df, m_df = load_data("students"), load_data("marks")
        s_names = sorted(s_df['student_name'].tolist()) if not s_df.empty else []
        sel_name = st.selectbox("Select Student", s_names)
        
        sid, stitle, semail = "", "", ""
        if sel_name:
            row = s_df[s_df['student_name'] == sel_name].iloc[0]
            sid, stitle, semail = clean_id(row['student_id']), row.get('research_title', ""), row.get('email', "")

        with st.form("score_form", clear_on_submit=True):
            f_stage = st.selectbox("Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Research Report (60%)"])
            
            st.divider()
            
            # FIXED: Detect "Report" regardless of other text in the selection
            if "Report" in f_stage:
                st.subheader("📝 Final Report Entry")
                st.info("Enter the holistic mark out of 100. This will be automatically weighted to 60%.")
                raw_score = st.number_input("Final Mark (0 - 100)", min_value=0.0, max_value=100.0, step=0.5)
                m_coll = m_anal = m_comm = 0.0
            else:
                st.subheader("📊 Presentation Rubric (/30)")
                m_coll = st.slider("Data Collection (0-10)", 0.0, 10.0, 0.0, 0.5)
                m_anal = st.slider("Analysis (0-10)", 0.0, 10.0, 0.0, 0.5)
                m_comm = st.slider("Communication (0-10)", 0.0, 10.0, 0.0, 0.5)
                raw_score = float(m_coll + m_anal + m_comm)

            f_rem = st.text_area("Examiner Remarks")
            
            if st.form_submit_button("Submit Marks"):
                nr = pd.DataFrame([{
                    "student_id": sid, "student_name": sel_name, "email": semail, 
                    "research_title": stitle, "assessment_type": f_stage,
                    "raw_score": raw_score, "data_coll": m_coll, "data_anal": m_anal, "comm": m_comm,
                    "examiner": st.session_state['user_name'], "remarks": f_rem, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                }])
                conn.update(worksheet="marks", data=pd.concat([m_df, nr], ignore_index=True))
                st.success(f"Successfully recorded {f_stage} for {sel_name}")

# --- ROLE: RESEARCH COORDINATOR ---
elif role == "Research Coordinator":
    st.header("🔑 Coordinator Dashboard")
    if st.sidebar.text_input("Coordinator Password", type="password") == "Blackberry":
        sd, md = load_data("students"), load_data("marks")
        if not sd.empty and not md.empty:
            piv = md.pivot_table(index='student_id', columns='assessment_type', values='raw_score', aggfunc='mean')
            
            # Weighted Math
            weighted_total = pd.Series(0, index=piv.index)
            if "Presentation 1 (10%)" in piv.columns: weighted_total += (piv["Presentation 1 (10%)"] / 30) * 10
            if "Presentation 2 (10%)" in piv.columns: weighted_total += (piv["Presentation 2 (10%)"] / 30) * 10
            if "Presentation 3 (20%)" in piv.columns: weighted_total += (piv["Presentation 3 (20%)"] / 30) * 20
            if "Final Research Report (60%)" in piv.columns: weighted_total += (piv["Final Research Report (60%)"] / 100) * 60
            
            piv['FINAL_GRADE_%'] = weighted_total.apply(lambda x: "{:.1f}".format(x))
            st.dataframe(pd.merge(sd, piv.reset_index(), on='student_id', how='left').fillna(0), use_container_width=True)
        else:
            st.info("No research data found yet.")
