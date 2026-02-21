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
st.sidebar.header("Navigation")
project_stream = st.sidebar.selectbox("Select Project Stream", ["Research Project", "Design Project"])
role = st.sidebar.radio("Management Menu", ["Registration", "Panelist / Examiner", "Coordinator"])

# --- ROLE: REGISTRATION ---
if role == "Registration":
    if project_stream == "Research Project":
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
                if not all([n, ci, e, s, t]): st.error("Fill all fields.")
                else:
                    nr = pd.DataFrame([{"student_id":ci,"student_name":n,"email":e,"supervisor":s,"research_title":t}])
                    conn.update(worksheet="students", data=pd.concat([sd, nr], ignore_index=True))
                    st.success("Research Registered!")

    else: # Design Project Registration (Groups)
        st.header("👥 Design Project Group Registration")
        with st.form("design_reg_form", clear_on_submit=True):
            g_name = st.text_input("Group Name / Project Title")
            superv = st.text_input("Supervisor")
            st.write("---")
            st.write("Enter Group Member Details (3-4 Members):")
            m1 = st.text_input("Member 1 Name & Student ID (e.g. John Doe - 2021001)")
            m2 = st.text_input("Member 2 Name & Student ID")
            m3 = st.text_input("Member 3 Name & Student ID")
            m4 = st.text_input("Member 4 Name & Student ID (Optional)")
            
            if st.form_submit_button("Register Group"):
                if not all([g_name, superv, m1, m2, m3]):
                    st.error("Min 3 members required.")
                else:
                    gd = load_data("groups")
                    members = [m1, m2, m3, m4]
                    new_rows = []
                    for m in members:
                        if m:
                            name_part = m.split('-')[0].strip()
                            id_part = clean_id(m.split('-')[-1])
                            new_rows.append({"group_id": g_name, "student_name": name_part, "student_id": id_part, "supervisor": superv})
                    
                    conn.update(worksheet="groups", data=pd.concat([gd, pd.DataFrame(new_rows)], ignore_index=True))
                    st.success("Design Group Registered!")

# --- ROLE: PANELIST / EXAMINER ---
elif role == "Panelist / Examiner":
    st.header(f"🧑‍🏫 Examiner Portal: {project_stream}")
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
        # ... (Registration tab logic same as research)
    else:
        st.sidebar.info(f"Signed in: {st.session_state['user_name']}")
        if st.sidebar.button("Sign Out"): st.session_state['logged_in'] = False; st.rerun()

        # Data Loading based on stream
        if project_stream == "Research Project":
            s_df = load_data("students")
            options = sorted(s_df['student_name'].tolist()) if not s_df.empty else []
            id_col = "student_id"
        else:
            g_df = load_data("groups")
            options = sorted(g_df['group_id'].unique().tolist()) if not g_df.empty else []
            id_col = "group_id"

        target = st.selectbox(f"Select {'Student' if project_stream == 'Research Project' else 'Group'}", options=[""] + options)
        f_stage = st.selectbox("Assessment Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Report (60%)"])

        with st.form("score_form", clear_on_submit=True):
            st.write(f"**Examiner:** {st.session_state['user_name']} | **Target:** {target}")
            
            if "Report" in f_stage:
                raw_mark = st.number_input("Final Mark (0-100)", 0.0, 100.0, step=0.5)
                m_c1 = m_c2 = m_c3 = 0.0
            
            elif project_stream == "Design Project":
                if "Presentation 1" in f_stage:
                    st.subheader("🏗️ Design Proposal Rubric")
                    m_c1 = st.select_slider("Problem Statement & Justification", mark_options, 0.0)
                    m_c2 = st.select_slider("Comparison Matrix & Decision Techniques", mark_options, 0.0)
                    m_c3 = st.select_slider("Selection of Materials/Methods", mark_options, 0.0)
                elif "Presentation 2" in f_stage:
                    st.subheader("📊 Progress Rubric")
                    m_c1 = st.select_slider("Design Calculations & Simulation", mark_options, 0.0)
                    m_c2 = st.select_slider("Schematic/Block Diagram Accuracy", mark_options, 0.0)
                    m_c3 = st.select_slider("Component Procurement & Initial Testing", mark_options, 0.0)
                else: # Presentation 3
                    st.subheader("🏁 Final Prototype Rubric")
                    m_c1 = st.select_slider("Prototype Functionality & Performance", mark_options, 0.0)
                    m_c2 = st.select_slider("Integration of Subsystems", mark_options, 0.0)
                    m_c3 = st.select_slider("Technical Defense & Demonstration", mark_options, 0.0)
                raw_mark = float(m_c1 + m_c2 + m_c3)
            
            else: # Research Rubric (Your existing working logic)
                # ... [Existing Research Sliders] ...
                m_c1 = st.select_slider("Criterion 1", mark_options, 0.0)
                m_c2 = st.select_slider("Criterion 2", mark_options, 0.0)
                m_c3 = st.select_slider("Criterion 3", mark_options, 0.0)
                raw_mark = float(m_c1 + m_c2 + m_c3)

            if st.form_submit_button("Submit Marks"):
                if not target: st.error("Select target.")
                else:
                    m_df = load_data("design_marks" if project_stream == "Design Project" else "marks")
                    nr = pd.DataFrame([{id_col: target, "assessment_type": f_stage, "raw_mark": raw_mark, "examiner": st.session_state['user_name'], "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")}])
                    conn.update(worksheet="design_marks" if project_stream == "Design Project" else "marks", data=pd.concat([m_df, nr], ignore_index=True))
                    st.success("Marks saved!")

# --- ROLE: COORDINATOR ---
elif role == "Coordinator":
    st.header("🔑 Coordinator Dashboard")
    pwd = st.sidebar.text_input("Coordinator Password", type="password")
    
    # Check separate passwords
    access = (project_stream == "Research Project" and pwd == "Blackberry") or (project_stream == "Design Project" and pwd == "Apple")
    
    if access:
        if project_stream == "Research Project":
            # ... [Your existing working Research Coordinator Code] ...
            st.write("Research Projects Overview")
        else:
            st.subheader("Design Projects: Individual Student List")
            gd, md = load_data("groups"), load_data("design_marks")
            if not gd.empty and not md.empty:
                # Average marks per group
                piv = md.pivot_table(index='group_id', columns='assessment_type', values='raw_mark', aggfunc='mean')
                
                # Weighting Math (Identical to Research)
                weighted = pd.Series(0.0, index=piv.index)
                if "Presentation 1 (10%)" in piv.columns: weighted += (piv["Presentation 1 (10%)"]/30)*10
                if "Presentation 2 (10%)" in piv.columns: weighted += (piv["Presentation 2 (10%)"]/30)*10
                if "Presentation 3 (20%)" in piv.columns: weighted += (piv["Presentation 3 (20%)"]/30)*20
                if "Final Report (60%)" in piv.columns: weighted += (piv["Final Report (60%)"]/100)*60
                
                piv['FINAL_GRADE_%'] = weighted.round(1)
                
                # Merge individual students with their group marks
                final_list = pd.merge(gd, piv.reset_index(), on='group_id', how='left').fillna(0)
                st.dataframe(final_list, use_container_width=True)
