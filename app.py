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
        df = conn.read(worksheet=sheet_name, ttl=0)
        if not df.empty and 'student_id' in df.columns:
            df['student_id'] = df['student_id'].astype(str).apply(clean_id)
        return df
    except:
        return pd.DataFrame()

# --- INITIALIZE SESSION STATE ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
    st.session_state['user_role'] = None
    st.session_state['user_name'] = ""
    st.session_state['user_email'] = ""

# --- 1. GATEKEEPER: LOGIN/SIGNUP ---
if not st.session_state['authenticated']:
    st.title("UNAM Engineering Portal")
    auth_tab1, auth_tab2 = st.tabs(["Login", "Create Account"])
    
    with auth_tab1:
        with st.form("login_form"):
            l_user, l_pw = st.text_input("Username"), st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                u_df = load_data("users")
                if not u_df.empty:
                    match = u_df[(u_df['username'] == l_user) & (u_df['password'] == hash_password(l_pw))]
                    if not match.empty:
                        st.session_state['authenticated'] = True
                        st.session_state['user_name'] = match.iloc[0]['full_name']
                        st.session_state['user_role'] = match.iloc[0]['role']
                        st.session_state['user_email'] = match.iloc[0].get('email', "")
                        st.rerun()
                    else: st.error("Invalid credentials.")
                else: st.error("User database empty.")
    with auth_tab2:
        with st.form("signup_form"):
            reg_full, reg_user, reg_pw, reg_email = st.text_input("Full Name"), st.text_input("Username"), st.text_input("Password", type="password"), st.text_input("Email")
            reg_role = st.selectbox("Register as:", ["Student", "Examiner", "Coordinator"])
            auth_key = st.text_input("Access Key (For Examiner/Coordinator)", type="password")
            if st.form_submit_button("Create Account"):
                if reg_role in ["Examiner", "Coordinator"] and auth_key != "JEDSECE2026":
                    st.error("Invalid Access Key.")
                else:
                    u_df = load_data("users")
                    new_u = pd.DataFrame([{"full_name": reg_full, "username": reg_user, "password": hash_password(reg_pw), "email": reg_email, "role": reg_role}])
                    conn.update(worksheet="users", data=pd.concat([u_df, new_u], ignore_index=True))
                    st.success("Account created!")

# --- 2. AUTHENTICATED PORTAL ---
else:
    st.sidebar.title("UNAM Engineering")
    st.sidebar.info(f"User: {st.session_state['user_name']}\nRole: {st.session_state['user_role']}")
    if st.sidebar.button("Sign Out"):
        st.session_state['authenticated'] = False
        st.rerun()

    menu_options = ["Registration", "Project Suggestions"]
    if st.session_state['user_role'] in ["Examiner", "Coordinator"]:
        menu_options.append("Panelist / Examiner")
    if st.session_state['user_role'] == "Coordinator":
        menu_options.append("Coordinator")
    
    choice = st.sidebar.radio("Main Menu", menu_options)
    project_type = st.sidebar.radio("Project Stream", ["Research Project", "Design Project"])

    # --- REGISTRATION ---
    if choice == "Registration":
        if project_type == "Research Project":
            st.header("📝 Student Research Registration")
            with st.form("reg_form", clear_on_submit=True):
                n, i, e, s = st.text_input("Full Name"), st.text_input("Student ID"), st.text_input("Email"), st.text_input("Supervisor")
                t = st.text_area("Research Title")
                if st.form_submit_button("Submit"):
                    sd = load_data("students")
                    nr = pd.DataFrame([{"student_id":clean_id(i),"student_name":n,"email":e,"supervisor":s,"research_title":t}])
                    conn.update(worksheet="students", data=pd.concat([sd, nr], ignore_index=True))
                    st.success("Registered!")
        else:
            st.header("👥 Design Group Registration")
            with st.form("design_reg_form", clear_on_submit=True):
                g_name, superv = st.text_input("Group Name/Title"), st.text_input("Supervisor")
                m1_n, m1_id = st.text_input("M1 Name"), st.text_input("M1 ID")
                m2_n, m2_id = st.text_input("M2 Name"), st.text_input("M2 ID")
                m3_n, m3_id = st.text_input("M3 Name"), st.text_input("M3 ID")
                m4_n, m4_id = st.text_input("M4 Name (Opt)"), st.text_input("M4 ID (Opt)")
                if st.form_submit_button("Register"):
                    dg = load_data("design_groups")
                    new_mems = []
                    for name, sid in [(m1_n, m1_id), (m2_n, m2_id), (m3_n, m3_id), (m4_n, m4_id)]:
                        if name and sid: new_mems.append({"group_name": g_name, "student_name": name, "student_id": clean_id(sid), "supervisor": superv})
                    conn.update(worksheet="design_groups", data=pd.concat([dg, pd.DataFrame(new_mems)], ignore_index=True))
                    st.success("Group Registered!")

    # --- PROJECT SUGGESTIONS ---
    elif choice == "Project Suggestions":
        st.header(f"🔭 {project_type} Suggestions")
        ps_df = load_data("project_suggestions")
        if not ps_df.empty:
            filtered = ps_df[ps_df['type'] == project_type]
            for _, row in filtered.iterrows():
                with st.expander(f"📌 {row['title']}"):
                    st.write(f"**Supervisor:** {row['supervisor']} | **Email:** {row['email']}")
                    st.write(f"**Abstract:** {row['abstract']}")
        else: st.info("No projects yet.")

    # --- PANELIST / EXAMINER ---
    elif choice == "Panelist / Examiner":
        st.header(f"🧑‍🏫 Examiner Portal ({project_type})")
        assess_t, suggest_t = st.tabs(["Assess Students", "Suggest New Project"])
        
        with assess_t:
            mark_options = [float(x) for x in np.arange(0, 10.5, 0.5)]
            ws = "design_marks" if project_type == "Design Project" else "marks"
            m_df = load_data(ws)
            
            if project_type == "Research Project":
                s_df = load_data("students")
                target = st.selectbox("Select Student", [""] + sorted(s_df['student_name'].tolist()) if not s_df.empty else [""])
                f_stage = st.selectbox("Assessment Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Research Report (60%)"])
            else:
                g_df = load_data("design_groups")
                target = st.selectbox("Select Design Group", [""] + sorted(g_df['group_name'].unique().tolist()) if not g_df.empty else [""])
                f_stage = st.selectbox("Assessment Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Design Report (60%)"])

            with st.form("score_form", clear_on_submit=True):
                m_c1 = m_c2 = m_c3 = 0.0
                if "Report" in f_stage:
                    raw_mark = st.number_input("Final Mark (0-100)", 0.0, 100.0)
                elif project_type == "Research Project":
                    if "Presentation 1" in f_stage:
                        m_c1 = st.select_slider("Problem Identification", mark_options)
                        m_c2 = st.select_slider("Literature Review", mark_options)
                        m_c3 = st.select_slider("Proposed Methodology", mark_options)
                    elif "Presentation 2" in f_stage:
                        m_c1 = st.select_slider("Implementation/Work Done", mark_options)
                        m_c2 = st.select_slider("Preliminary Results", mark_options)
                        m_c3 = st.select_slider("Current Planning/Q&A", mark_options)
                    else:
                        m_c1 = st.select_slider("Technical Mastery", mark_options)
                        m_c2 = st.select_slider("Discussion/Conclusion", mark_options)
                        m_c3 = st.select_slider("Presentation Quality", mark_options)
                    raw_mark = float(m_c1 + m_c2 + m_c3)
                else: # Design Project Rubrics
                    if "Presentation 1" in f_stage:
                        m_c1 = st.select_slider("Problem Statement (1.1-1.2)", mark_options)
                        m_c2 = st.select_slider("Comparison Matrix (1.3)", mark_options)
                        m_c3 = st.select_slider("Materials/Method (1.4-1.5)", mark_options)
                    elif "Presentation 2" in f_stage:
                        m_c1 = st.select_slider("Progress & Sustainability (LO 1, 2, 4)", mark_options)
                        m_c2 = st.select_slider("Technical Communication (LO 5)", mark_options)
                        m_c3 = st.select_slider("Q&A Defense", mark_options)
                    else:
                        m_c1 = st.select_slider("Design Approaches (LO 4, 7)", mark_options)
                        m_c2 = st.select_slider("Synthesis & Results (LO 1, 4)", mark_options)
                        m_c3 = st.select_slider("Prototype Functionality (LO 7)", mark_options)
                    raw_mark = float(m_c1 + m_c2 + m_c3)

                rem = st.text_area("Remarks")
                if st.form_submit_button("Submit Marks"):
                    id_col = "student_id" if project_type == "Research Project" else "group_name"
                    new_r = pd.DataFrame([{id_col: target, "assessment_type": f_stage, "raw_mark": raw_mark, "crit_1":m_c1, "crit_2":m_c2, "crit_3":m_c3, "examiner": st.session_state['user_name'], "remarks": rem, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")}])
                    conn.update(worksheet=ws, data=pd.concat([m_df, new_r], ignore_index=True))
                    st.success("Assessment Saved!")

        with suggest_t:
            with st.form("sug_form", clear_on_submit=True):
                s_t = st.text_input("Project Title")
                s_a = st.text_area("Brief Abstract")
                if st.form_submit_button("Post"):
                    ps_df = load_data("project_suggestions")
                    new_s = pd.DataFrame([{"type": project_type, "title": s_t, "abstract": s_a, "supervisor": st.session_state['user_name'], "email": st.session_state['user_email']}])
                    conn.update(worksheet="project_suggestions", data=pd.concat([ps_df, new_s], ignore_index=True))
                    st.success("Suggestion Posted!")

    # --- COORDINATOR ---
    elif choice == "Coordinator":
        st.header(f"🔑 Coordinator Gradebook ({project_type})")
        pwd = st.sidebar.text_input("Dashboard Password", type="password")
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
