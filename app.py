import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import hashlib
import numpy as np

# --- PAGE CONFIG ---
st.set_page_config(page_title="UNAM Engineering Portal", layout="wide")

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
    st.session_state['user_email'] = ""

# --- SIDEBAR NAVIGATION ---
st.sidebar.header("Navigation")
project_type = st.sidebar.radio("Select Project Stream", ["Research Project", "Design Project"])
role = st.sidebar.radio("Management Menu", ["Registration", "Panelist / Examiner", "Coordinator", "Project Suggestions"])

# --- ROLE: REGISTRATION ---
if role == "Registration":
    st.header(f"📝 {project_type} Registration")
    if project_type == "Research Project":
        with st.form("reg_form", clear_on_submit=True):
            n, i, e, s = st.text_input("Full Name"), st.text_input("Student ID"), st.text_input("Email"), st.text_input("Supervisor")
            t = st.text_area("Research Title")
            if st.form_submit_button("Submit Research Registration"):
                sd = load_data("students")
                nr = pd.DataFrame([{"student_id":clean_id(i),"student_name":n,"email":e,"supervisor":s,"research_title":t}])
                conn.update(worksheet="students", data=pd.concat([sd, nr], ignore_index=True))
                st.success("Research Student Registered!")
    else:
        with st.form("design_reg", clear_on_submit=True):
            g_name, superv = st.text_input("Group Name/Project Title"), st.text_input("Supervisor")
            c1, c2 = st.columns(2)
            with c1:
                m1, m1_id = st.text_input("M1 Name"), st.text_input("M1 ID")
                m3, m3_id = st.text_input("M3 Name"), st.text_input("M3 ID")
            with c2:
                m2, m2_id = st.text_input("M2 Name"), st.text_input("M2 ID")
                m4, m4_id = st.text_input("M4 Name (Optional)"), st.text_input("M4 ID (Optional)")
            if st.form_submit_button("Register Design Group"):
                dg = load_data("design_groups")
                new_rows = []
                for name, sid in [(m1, m1_id), (m2, m2_id), (m3, m3_id), (m4, m4_id)]:
                    if name and sid:
                        new_rows.append({"group_name": g_name, "student_name": name, "student_id": clean_id(sid), "supervisor": superv})
                conn.update(worksheet="design_groups", data=pd.concat([dg, pd.DataFrame(new_rows)], ignore_index=True))
                st.success("Design Group Registered!")

# --- ROLE: PANELIST / EXAMINER ---
elif role == "Panelist / Examiner":
    if not st.session_state['logged_in']:
        tab1, tab2 = st.tabs(["Login", "Create Account"])
        with tab1:
            with st.form("login_form"):
                l_user, l_pw = st.text_input("Username"), st.text_input("Password", type="password")
                if st.form_submit_button("Login"):
                    u_df = load_data("users")
                    match = u_df[(u_df['username'] == l_user) & (u_df['password'] == hash_password(l_pw))]
                    if not match.empty:
                        st.session_state['logged_in'] = True
                        st.session_state['user_name'] = match.iloc[0]['full_name']
                        email_raw = match.iloc[0].get('email', "")
                        st.session_state['user_email'] = "" if pd.isna(email_raw) else str(email_raw)
                        st.rerun()
                    else: st.error("Invalid credentials.")
        with tab2:
            with st.form("create_acc"):
                rf, ru, rp, re, ak = st.text_input("Full Name"), st.text_input("Username"), st.text_input("Password", type="password"), st.text_input("Email"), st.text_input("Key", type="password")
                if st.form_submit_button("Create Account"):
                    if ak == "JEDSECE2026":
                        u_df = load_data("users")
                        new_u = pd.DataFrame([{"full_name": rf, "username": ru, "password": hash_password(rp), "email": re}])
                        conn.update(worksheet="users", data=pd.concat([u_df, new_u], ignore_index=True))
                        st.success("Account created!")
    else:
        st.sidebar.info(f"User: {st.session_state['user_name']}")
        if st.sidebar.button("Sign Out"): st.session_state['logged_in'] = False; st.rerun()
        
        assess_t, suggest_t = st.tabs(["Assess Students", "Suggest Projects"])
        
        with assess_t:
            st.subheader(f"Marking: {project_type}")
            mark_options = [float(x) for x in np.arange(0, 10.5, 0.5)]
            ws = "design_marks" if project_type == "Design Project" else "marks"
            m_df = load_data(ws)

            if project_type == "Research Project":
                s_df = load_data("students")
                target = st.selectbox("Select Student", options=[""] + sorted(s_df['student_name'].tolist()) if not s_df.empty else [""])
                f_stage = st.selectbox("Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Research Report (60%)"])
            else:
                g_df = load_data("design_groups")
                target = st.selectbox("Select Design Group", options=[""] + sorted(g_df['group_name'].unique().tolist()) if not g_df.empty else [""])
                f_stage = st.selectbox("Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Design Report (60%)"])

            with st.form("score_form", clear_on_submit=True):
                m_c1 = m_c2 = m_c3 = 0.0
                if "Report" in f_stage:
                    raw_mark = st.number_input("Final Mark (0-100)", 0.0, 100.0)
                elif project_type == "Research Project":
                    m_c1 = st.select_slider("Crit 1", mark_options)
                    m_c2 = st.select_slider("Crit 2", mark_options)
                    m_c3 = st.select_slider("Crit 3", mark_options)
                    raw_mark = float(m_c1 + m_c2 + m_c3)
                else:
                    if "Presentation 1" in f_stage:
                        m_c1 = st.select_slider("Problem Statement", mark_options)
                        m_c2 = st.select_slider("Comparison Matrix", mark_options)
                        m_c3 = st.select_slider("Materials/Method", mark_options)
                    elif "Presentation 2" in f_stage:
                        m_c1 = st.select_slider("Progress/Sustainability (LO 1,2,4)", mark_options)
                        m_c2 = st.select_slider("Communication (LO 5)", mark_options)
                        m_c3 = st.select_slider("Q&A", mark_options)
                    else:
                        m_c1 = st.select_slider("Design Approaches (LO 4,7)", mark_options)
                        m_c2 = st.select_slider("Synthesis & Results (LO 1,4)", mark_options)
                        m_c3 = st.select_slider("Prototype Functionality (LO 7)", mark_options)
                    raw_mark = float(m_c1 + m_c2 + m_c3)

                remarks = st.text_area("Remarks")
                if st.form_submit_button("Submit Marks"):
                    if target:
                        id_col = "student_id" if project_type == "Research Project" else "group_name"
                        new_row = pd.DataFrame([{id_col: target, "assessment_type": f_stage, "raw_mark": raw_mark, "crit_1":m_c1, "crit_2":m_c2, "crit_3":m_c3, "examiner": st.session_state['user_name'], "remarks": remarks, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")}])
                        conn.update(worksheet=ws, data=pd.concat([m_df, new_row], ignore_index=True))
                        st.success("Marks Saved!")

        with suggest_t:
            st.subheader("💡 Suggest Project")
            with st.form("suggest_form", clear_on_submit=True):
                stitle = st.text_input("Project Title")
                sabs = st.text_area("Brief Abstract")
                if st.form_submit_button("Post Suggestion"):
                    ps_df = load_data("project_suggestions")
                    # Explicitly using the captured email from session state
                    new_s = pd.DataFrame([{"type": project_type, "title": stitle, "abstract": sabs, "supervisor": st.session_state['user_name'], "email": st.session_state['user_email']}])
                    conn.update(worksheet="project_suggestions", data=pd.concat([ps_df, new_s], ignore_index=True))
                    st.success("Posted!")

# --- ROLE: PROJECT SUGGESTIONS ---
elif role == "Project Suggestions":
    st.header(f"🔭 {project_type} Suggestions")
    ps_df = load_data("project_suggestions")
    if not ps_df.empty:
        display_df = ps_df[ps_df['type'] == project_type]
        for _, row in display_df.iterrows():
            with st.expander(f"📌 {row['title']}"):
                st.write(f"**Supervisor:** {row['supervisor']}")
                u_email = str(row['email']) if pd.notna(row['email']) and str(row['email']).strip() != "" else ""
                if u_email:
                    st.write(f"**Email:** {u_email}")
                st.write(f"**Abstract:** {row['abstract']}")
                if u_email:
                    st.markdown(f'<a href="mailto:{u_email}" style="background-color:#007bff; color:white; padding:8px; border-radius:5px; text-decoration:none;">📧 Contact</a>', unsafe_allow_html=True)

# --- ROLE: COORDINATOR ---
elif role == "Coordinator":
    st.header(f"🔑 {project_type} Dashboard")
    pwd = st.sidebar.text_input("Password", type="password")
    if (project_type == "Research Project" and pwd == "Blackberry") or (project_type == "Design Project" and pwd == "Apple"):
        if project_type == "Research Project":
            sd, md = load_data("students"), load_data("marks")
            if not sd.empty and not md.empty:
                piv = md.pivot_table(index='student_id', columns='assessment_type', values='raw_mark', aggfunc='mean').reset_index()
                st.dataframe(pd.merge(sd, piv, on="student_id", how="left").fillna(0))
        else:
            gd, dm = load_data("design_groups"), load_data("design_marks")
            if not gd.empty and not dm.empty:
                piv = dm.pivot_table(index='group_name', columns='assessment_type', values='raw_mark', aggfunc='mean').reset_index()
                st.dataframe(pd.merge(gd, piv, on="group_name", how="left").fillna(0))
