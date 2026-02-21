import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import hashlib
import numpy as np

# --- PAGE CONFIG ---
st.set_page_config(page_title="UNAM Engineering Portal", layout="wide")

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

# --- OPTIONS FOR SELECT SLIDER ---
mark_options = [float(x) for x in np.arange(0, 10.5, 0.5)]

# --- AUTHENTICATION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_name'] = ""

# --- SIDEBAR NAVIGATION ---
st.sidebar.header("Project Stream")
project_type = st.sidebar.radio("Select Stream", ["Research Project", "Design Project"])
role = st.sidebar.radio("Management Menu", ["Registration", "Panelist / Examiner", "Coordinator"])

# --- ROLE: REGISTRATION ---
if role == "Registration":
    if project_type == "Research Project":
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
                if not all([n, ci, e, s, t]): st.error("Please fill in all fields.")
                else:
                    nr = pd.DataFrame([{"student_id":ci,"student_name":n,"email":e,"supervisor":s,"research_title":t}])
                    conn.update(worksheet="students", data=pd.concat([sd, nr], ignore_index=True))
                    st.success("Research Registered!")
    else:
        st.header("👥 Design Project Group Registration")
        with st.form("design_reg_form", clear_on_submit=True):
            g_name = st.text_input("Group Name / Project Title")
            superv = st.text_input("Supervisor")
            st.write("--- Group Members (Min 3) ---")
            m1_n = st.text_input("M1 Name"); m1_id = st.text_input("M1 ID")
            m2_n = st.text_input("M2 Name"); m2_id = st.text_input("M2 ID")
            m3_n = st.text_input("M3 Name"); m3_id = st.text_input("M3 ID")
            m4_n = st.text_input("M4 Name (Optional)"); m4_id = st.text_input("M4 ID (Optional)")
            if st.form_submit_button("Submit Group Registration"):
                if not all([g_name, superv, m1_n, m1_id, m2_n, m2_id, m3_n, m3_id]):
                    st.error("Please provide at least 3 group members.")
                else:
                    dg = load_data("design_groups")
                    new_mems = []
                    for name, sid in [(m1_n, m1_id), (m2_n, m2_id), (m3_n, m3_id), (m4_n, m4_id)]:
                        if name and sid:
                            new_mems.append({"group_name": g_name, "student_name": name, "student_id": clean_id(sid), "supervisor": superv})
                    conn.update(worksheet="design_groups", data=pd.concat([dg, pd.DataFrame(new_mems)], ignore_index=True))
                    st.success("Design Group Registered!")

# --- ROLE: PANELIST / EXAMINER ---
elif role == "Panelist / Examiner":
    st.header(f"🧑‍🏫 Examiner Portal ({project_type})")
    if not st.session_state['logged_in']:
        tab1, tab2 = st.tabs(["Login", "Create Account"])
        with tab1:
            with st.form("login_form"):
                l_user, l_pw = st.text_input("Username"), st.text_input("Password", type="password")
                if st.form_submit_button("Login"):
                    u_df = load_data("users")
                    match = u_df[(u_df['username'] == l_user) & (u_df['password'] == hash_password(l_pw))]
                    if not match.empty:
                        st.session_state['logged_in'], st.session_state['user_name'] = True, match.iloc[0]['full_name']
                        st.rerun()
                    else: st.error("Invalid credentials.")
        with tab2:
            with st.form("create_acc"):
                reg_full, reg_user, reg_pw, auth_key = st.text_input("Full Name"), st.text_input("Username"), st.text_input("Password", type="password"), st.text_input("Department Key", type="password")
                if st.form_submit_button("Create Account"):
                    if auth_key == "JEDSECE2026":
                        u_df = load_data("users")
                        new_u = pd.DataFrame([{"full_name": reg_full, "username": reg_user, "password": hash_password(reg_pw)}])
                        conn.update(worksheet="users", data=pd.concat([u_df, new_u], ignore_index=True))
                        st.success("Account created!")
                    else: st.error("Invalid Key.")
    else:
        st.sidebar.info(f"Signed in: {st.session_state['user_name']}")
        if st.sidebar.button("Sign Out"): st.session_state['logged_in'] = False; st.rerun()

        ws = "design_marks" if project_type == "Design Project" else "marks"
        m_df = load_data(ws)

        if project_type == "Research Project":
            s_df = load_data("students")
            options = sorted(s_df['student_name'].tolist()) if not s_df.empty else []
            target = st.selectbox("Select Student", options=[""] + options)
            f_stage = st.selectbox("Assessment Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Research Report (60%)"])
        else:
            g_df = load_data("design_groups")
            options = sorted(g_df['group_name'].unique().tolist()) if not g_df.empty else []
            target = st.selectbox("Select Design Group", options=[""] + options)
            f_stage = st.selectbox("Assessment Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Design Report (60%)"])

        with st.form("score_form", clear_on_submit=True):
            st.write(f"**Examiner:** {st.session_state['user_name']} | **Target:** {target}")
            
            if "Report" in f_stage:
                st.subheader("📝 Final Report Mark")
                raw_mark = st.number_input("Mark (0-100)", 0.0, 100.0, step=0.5)
                m_c1 = m_c2 = m_c3 = 0.0
            
            elif project_type == "Research Project":
                if "Presentation 1" in f_stage:
                    st.subheader("🏗️ Proposal Rubric (Out of 30)")
                    m_c1 = st.select_slider("Problem Identification & Justification", options=mark_options, value=0.0)
                    m_c2 = st.select_slider("Literature Review & Technical Background", options=mark_options, value=0.0)
                    m_c3 = st.select_slider("Proposed Methodology & Feasibility", options=mark_options, value=0.0)
                elif "Presentation 2" in f_stage:
                    st.subheader("📊 Progress Rubric (Out of 30)")
                    m_c1 = st.select_slider("Implementation & Work Done", options=mark_options, value=0.0)
                    m_c2 = st.select_slider("Preliminary Results & Analysis", options=mark_options, value=0.0)
                    m_c3 = st.select_slider("Current Planning & Q&A", options=mark_options, value=0.0)
                else: 
                    st.subheader("🏁 Final Presentation Rubric (Out of 30)")
                    m_c1 = st.select_slider("Technical Depth & Mastery", options=mark_options, value=0.0)
                    m_c2 = st.select_slider("Discussion of Results & Conclusion", options=mark_options, value=0.0)
                    m_c3 = st.select_slider("Quality of Presentation & Defense", options=mark_options, value=0.0)
                raw_mark = float(m_c1 + m_c2 + m_c3)

            else:
                if "Presentation 1" in f_stage:
                    st.subheader("🏗️ Design Proposal")
                    m_c1 = st.select_slider("Problem Statement & Justification", mark_options, 0.0)
                    m_c2 = st.select_slider("Comparison Matrix (Decision Techniques)", mark_options, 0.0)
                    m_c3 = st.select_slider("Selection of Materials & Methods", mark_options, 0.0)
                elif "Presentation 2" in f_stage:
                    st.subheader("📊 Progress Presentation")
                    m_c1 = st.select_slider("Progress & Sustainability Analysis (LO 1, 2, 4)", mark_options, 0.0)
                    m_c2 = st.select_slider("Technical Communication (LO 5)", mark_options, 0.0)
                    m_c3 = st.select_slider("Q&A Defense", mark_options, 0.0)
                else: 
                    st.subheader("🏁 Final Presentation")
                    m_c1 = st.select_slider("Design Approaches (LO 4, 7)", mark_options, 0.0)
                    m_c2 = st.select_slider("Synthesis & Test Results (LO 1, 4)", mark_options, 0.0)
                    m_c3 = st.select_slider("Prototype Functionality (LO 7)", mark_options, 0.0)
                raw_mark = float(m_c1 + m_c2 + m_c3)

            remarks = st.text_area("Examiner Remarks")
            if st.form_submit_button("Submit Marks"):
                if not target: st.error("Select a target.")
                else:
                    id_col = "student_id" if project_type == "Research Project" else "group_name"
                    new_row = pd.DataFrame([{id_col: target, "assessment_type": f_stage, "raw_mark": raw_mark, 
                                             "crit_1": m_c1, "crit_2": m_c2, "crit_3": m_c3,
                                             "examiner": st.session_state['user_name'], "remarks": remarks, 
                                             "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")}])
                    conn.update(worksheet=ws, data=pd.concat([m_df, new_row], ignore_index=True))
                    st.success("Marks saved successfully!")

# --- ROLE: COORDINATOR ---
elif role == "Coordinator":
    st.header("🔑 Coordinator Dashboard")
    pwd = st.sidebar.text_input("Coordinator Password", type="password")
    if (project_type == "Research Project" and pwd == "Blackberry") or (project_type == "Design Project" and pwd == "Apple"):
        if project_type == "Research Project":
            sd, md = load_data("students"), load_data("marks")
            if not sd.empty and not md.empty:
                piv = md.pivot_table(index='student_id', columns='assessment_type', values='raw_mark', aggfunc='mean')
                display_df = pd.DataFrame(index=piv.index)
                weighted_total = pd.Series(0.0, index=piv.index)
                stages = {"Presentation 1 (10%)": 10, "Presentation 2 (10%)": 10, "Presentation 3 (20%)": 20}
                for stage, weight in stages.items():
                    if stage in piv.columns:
                        display_df[f"{stage.split(' (')[0]} (%)"] = ((piv[stage] / 30) * 100).round(1)
                        weighted_total += (piv[stage] / 30) * weight
                if "Final Research Report (60%)" in piv.columns:
                    display_df["Final Report (%)"] = piv["Final Research Report (60%)"].round(1)
                    weighted_total += (piv["Final Research Report (60%)"] / 100) * 60
                display_df['FINAL_GRADE_%'] = weighted_total.round(1)
                st.dataframe(pd.merge(sd, display_df.reset_index(), on='student_id', how='left').fillna(0), use_container_width=True)
        else:
            gd, md = load_data("design_groups"), load_data("design_marks")
            if not gd.empty and not md.empty:
                piv = md.pivot_table(index='group_name', columns='assessment_type', values='raw_mark', aggfunc='mean')
                display_df = pd.DataFrame(index=piv.index)
                weighted_total = pd.Series(0.0, index=piv.index)
                # Design Weighting
                stages = {"Presentation 1 (10%)": 10, "Presentation 2 (10%)": 10, "Presentation 3 (20%)": 20}
                for stage, weight in stages.items():
                    if stage in piv.columns:
                        display_df[f"{stage.split(' (')[0]} (%)"] = ((piv[stage] / 30) * 100).round(1)
                        weighted_total += (piv[stage] / 30) * weight
                if "Final Design Report (60%)" in piv.columns:
                    display_df["Final Report (%)"] = piv["Final Design Report (60%)"].round(1)
                    weighted_total += (piv["Final Design Report (60%)"] / 100) * 60
                display_df['FINAL_GRADE_%'] = weighted_total.round(1)
                st.dataframe(pd.merge(gd, display_df.reset_index(), left_on='group_name', right_on='group_name', how='left').fillna(0), use_container_width=True)
