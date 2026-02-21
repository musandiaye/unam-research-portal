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

# --- 1. LOGIN / SIGNUP SCREEN (GATEKEEPER) ---
if not st.session_state['authenticated']:
    st.title("UNAM Engineering Portal")
    st.subheader("Department of Electrical and Computer Engineering")
    
    auth_tab1, auth_tab2 = st.tabs(["Login", "Create Account"])
    
    with auth_tab1:
        with st.form("login_form"):
            l_user = st.text_input("Username")
            l_pw = st.text_input("Password", type="password")
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
                else: st.error("User database empty. Please register.")
                
    with auth_tab2:
        with st.form("signup_form"):
            reg_full = st.text_input("Full Name")
            reg_user = st.text_input("Username")
            reg_pw = st.text_input("Password", type="password")
            reg_email = st.text_input("Email")
            reg_role = st.selectbox("Register as:", ["Student", "Examiner", "Coordinator"])
            auth_key = st.text_input("Access Key (For Examiner/Coordinator)", type="password")
            
            if st.form_submit_button("Create Account"):
                if reg_role in ["Examiner", "Coordinator"] and auth_key != "JEDSECE2026":
                    st.error("Invalid Access Key.")
                elif not reg_full or not reg_user or not reg_pw:
                    st.error("Please fill all required fields.")
                else:
                    u_df = load_data("users")
                    new_u = pd.DataFrame([{"full_name": reg_full, "username": reg_user, "password": hash_password(reg_pw), "email": reg_email, "role": reg_role}])
                    conn.update(worksheet="users", data=pd.concat([u_df, new_u], ignore_index=True))
                    st.success("Account created! Go to Login tab.")

# --- 2. AUTHENTICATED DASHBOARD ---
else:
    # Sidebar logout and info
    st.sidebar.title("UNAM Engineering")
    st.sidebar.info(f"User: {st.session_state['user_name']}\nRole: {st.session_state['user_role']}")
    if st.sidebar.button("Sign Out"):
        st.session_state['authenticated'] = False
        st.rerun()

    # --- DEFINE ROLE-BASED MENU ---
    menu_options = ["Registration", "Project Suggestions"]
    if st.session_state['user_role'] in ["Examiner", "Coordinator"]:
        menu_options.append("Panelist / Examiner")
    if st.session_state['user_role'] == "Coordinator":
        menu_options.append("Coordinator Dashboard")
    
    choice = st.sidebar.radio("Main Menu", menu_options)
    project_type = st.sidebar.radio("Project Stream", ["Research Project", "Design Project"])

    # --- MENU: REGISTRATION ---
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
                g_name, superv = st.text_input("Group Name/Project Title"), st.text_input("Supervisor")
                m1_n, m1_id = st.text_input("M1 Name"), st.text_input("M1 ID")
                m2_n, m2_id = st.text_input("M2 Name"), st.text_input("M2 ID")
                m3_n, m3_id = st.text_input("M3 Name"), st.text_input("M3 ID")
                m4_n, m4_id = st.text_input("M4 Name (Opt)"), st.text_input("M4 ID (Opt)")
                if st.form_submit_button("Register Group"):
                    dg = load_data("design_groups")
                    new_mems = []
                    for name, sid in [(m1_n, m1_id), (m2_n, m2_id), (m3_n, m3_id), (m4_n, m4_id)]:
                        if name and sid: new_mems.append({"group_name": g_name, "student_name": name, "student_id": clean_id(sid), "supervisor": superv})
                    conn.update(worksheet="design_groups", data=pd.concat([dg, pd.DataFrame(new_mems)], ignore_index=True))
                    st.success("Group Registered!")

    # --- MENU: PROJECT SUGGESTIONS ---
    elif choice == "Project Suggestions":
        st.header(f"🔭 {project_type} Suggestions")
        ps_df = load_data("project_suggestions")
        if not ps_df.empty:
            filtered = ps_df[ps_df['type'] == project_type]
            for _, row in filtered.iterrows():
                with st.expander(f"📌 {row['title']}"):
                    st.write(f"**Supervisor:** {row['supervisor']}")
                    st.write(f"**Email:** {row['email']}")
                    st.write(f"**Abstract:** {row['abstract']}")
        else: st.info("No projects yet.")

    # --- MENU: PANELIST / EXAMINER ---
    elif choice == "Panelist / Examiner":
        st.header(f"🧑‍🏫 Examiner Portal ({project_type})")
        assess_t, suggest_t = st.tabs(["Assess Students", "Post New Project"])
        
        with assess_t:
            mark_options = [float(x) for x in np.arange(0, 10.5, 0.5)]
            ws = "design_marks" if project_type == "Design Project" else "marks"
            m_df = load_data(ws)
            
            if project_type == "Research Project":
                s_df = load_data("students")
                target = st.selectbox("Select Student", [""] + sorted(s_df['student_name'].tolist()) if not s_df.empty else [""])
                stage = st.selectbox("Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Research Report (60%)"])
            else:
                g_df = load_data("design_groups")
                target = st.selectbox("Select Group", [""] + sorted(g_df['group_name'].unique().tolist()) if not g_df.empty else [""])
                stage = st.selectbox("Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Design Report (60%)"])

            with st.form("mark_form", clear_on_submit=True):
                m_c1 = m_c2 = m_c3 = 0.0
                if "Report" in stage:
                    raw_mark = st.number_input("Final Mark (0-100)", 0.0, 100.0)
                else:
                    m_c1 = st.select_slider("Criteria 1", mark_options)
                    m_c2 = st.select_slider("Criteria 2", mark_options)
                    m_c3 = st.select_slider("Criteria 3", mark_options)
                    raw_mark = float(m_c1 + m_c2 + m_c3)
                
                rem = st.text_area("Remarks")
                if st.form_submit_button("Submit Marks"):
                    id_col = "student_id" if project_type == "Research Project" else "group_name"
                    new_r = pd.DataFrame([{id_col: target, "assessment_type": stage, "raw_mark": raw_mark, "examiner": st.session_state['user_name'], "timestamp": datetime.now().strftime("%Y-%m-%d")}])
                    conn.update(worksheet=ws, data=pd.concat([m_df, new_r], ignore_index=True))
                    st.success("Marks Saved!")

        with suggest_t:
            with st.form("sug_form", clear_on_submit=True):
                s_t = st.text_input("Project Title")
                s_a = st.text_area("Abstract")
                if st.form_submit_button("Post"):
                    ps_df = load_data("project_suggestions")
                    new_s = pd.DataFrame([{"type": project_type, "title": s_t, "abstract": s_a, "supervisor": st.session_state['user_name'], "email": st.session_state['user_email']}])
                    conn.update(worksheet="project_suggestions", data=pd.concat([ps_df, new_s], ignore_index=True))
                    st.success("Posted!")

    # --- MENU: COORDINATOR ---
    elif choice == "Coordinator Dashboard":
        st.header(f"🔑 {project_type} Gradebook")
        pwd = st.sidebar.text_input("Admin Password", type="password")
        if (project_type == "Research Project" and pwd == "Blackberry") or (project_type == "Design Project" and pwd == "Apple"):
            # Existing dashboard code from rolled back version
            st.success("Access Granted")
            # [Insert Coordinator Table Logic here]
