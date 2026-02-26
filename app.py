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
    st.session_state['user_email'] = ""

# --- SIDEBAR NAVIGATION ---
st.sidebar.header("Navigation")
role = st.sidebar.radio("Management Menu", ["Registration", "Panelist / Examiner", "Coordinator", "Project Suggestions"])
project_type = st.sidebar.radio("Select Stream", ["Research Project", "Design Project"])

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
            abst = st.text_area("Research Abstract (Max 250 words)")
            
            if st.form_submit_button("Submit Registration"):
                sd = load_data("students")
                ci = clean_id(i)
                word_count = len(abst.split())
                if not all([n, ci, e, s, t, abst]): st.error("Please fill in all fields.")
                elif word_count > 250: st.error(f"Abstract is too long ({word_count} words). Max 250 words allowed.")
                else:
                    nr = pd.DataFrame([{"student_id":ci,"student_name":n,"email":e,"supervisor":s,"research_title":t, "abstract": abst}])
                    conn.update(worksheet="students", data=pd.concat([sd, nr], ignore_index=True))
                    st.success("Research Registered!")
    else:
        st.header("👥 Design Project Group Registration")
        with st.form("design_reg_form", clear_on_submit=True):
            g_name = st.text_input("Group Name / Project Title")
            superv = st.text_input("Supervisor")
            g_abst = st.text_area("Project Abstract (Max 250 words)")
            st.write("--- Group Members (Min 3) ---")
            m1_n = st.text_input("M1 Name"); m1_id = st.text_input("M1 ID")
            m2_n = st.text_input("M2 Name"); m2_id = st.text_input("M2 ID")
            m3_n = st.text_input("M3 Name"); m3_id = st.text_input("M3 ID")
            m4_n = st.text_input("M4 Name (Optional)"); m4_id = st.text_input("M4 ID (Optional)")
            if st.form_submit_button("Submit Group Registration"):
                word_count = len(g_abst.split())
                if not all([g_name, superv, g_abst, m1_n, m1_id, m2_n, m2_id, m3_n, m3_id]):
                    st.error("Please provide at least 3 group members and the abstract.")
                elif word_count > 250: st.error(f"Abstract is too long ({word_count} words). Max 250 words allowed.")
                else:
                    dg = load_data("design_groups")
                    new_mems = []
                    for name, sid in [(m1_n, m1_id), (m2_n, m2_id), (m3_n, m3_id), (m4_n, m4_id)]:
                        if name and sid:
                            new_mems.append({"group_name": g_name, "student_name": name, "student_id": clean_id(sid), "supervisor": superv, "abstract": g_abst})
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
                        st.session_state['logged_in'] = True
                        st.session_state['user_name'] = match.iloc[0]['full_name']
                        st.session_state['user_email'] = match.iloc[0].get('email', "")
                        st.rerun()
                    else: st.error("Invalid credentials.")
        with tab2:
            with st.form("create_acc"):
                reg_full, reg_user, reg_pw, reg_email, auth_key = st.text_input("Full Name"), st.text_input("Username"), st.text_input("Password", type="password"), st.text_input("Email"), st.text_input("Department Key", type="password")
                if st.form_submit_button("Create Account"):
                    if auth_key == "JEDSECE2026":
                        u_df = load_data("users")
                        new_u = pd.DataFrame([{"full_name": reg_full, "username": reg_user, "password": hash_password(reg_pw), "email": reg_email}])
                        conn.update(worksheet="users", data=pd.concat([u_df, new_u], ignore_index=True))
                        st.success("Account created!")
                    else: st.error("Invalid Key.")
    else:
        st.sidebar.info(f"Signed in: {st.session_state['user_name']}")
        if st.sidebar.button("Sign Out"): st.session_state['logged_in'] = False; st.rerun()
        
        assess_tab, suggest_tab = st.tabs(["Assess Students", "Suggest New Projects"])
        
        with assess_tab:
            ws = "design_marks" if project_type == "Design Project" else "marks"
            m_df = load_data(ws)

            if project_type == "Research Project":
                s_df = load_data("students")
                id_list = [""] + sorted(s_df['student_id'].unique().tolist()) if not s_df.empty else [""]
                name_list = [""] + sorted(s_df['student_name'].unique().tolist()) if not s_df.empty else [""]
                
                # Bi-directional logic using session state
                if 'sel_id' not in st.session_state: st.session_state.sel_id = ""
                if 'sel_name' not in st.session_state: st.session_state.sel_name = ""

                def update_by_id():
                    st.session_state.sel_name = s_df[s_df['student_id'] == st.session_state.sel_id]['student_name'].iloc[0] if st.session_state.sel_id else ""

                def update_by_name():
                    st.session_state.sel_id = s_df[s_df['student_name'] == st.session_state.sel_name]['student_id'].iloc[0] if st.session_state.sel_name else ""

                col1, col2 = st.columns(2)
                with col1:
                    target_id = st.selectbox("Select Student ID", options=id_list, key="sel_id", on_change=update_by_id)
                with col2:
                    target_name = st.selectbox("Select Student Name", options=name_list, key="sel_name", on_change=update_by_name)
                
                f_stage = st.selectbox("Assessment Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Research Report (60%)"])
            else:
                g_df = load_data("design_groups")
                target_id = st.selectbox("Select Design Group", options=[""] + sorted(g_df['group_name'].unique().tolist()) if not g_df.empty else [""])
                f_stage = st.selectbox("Assessment Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Design Report (60%)"])

            with st.form("score_form", clear_on_submit=True):
                st.write(f"**Target ID:** {target_id}")
                m_c1 = m_c2 = m_c3 = m_c4 = m_c5 = 0.0

                if "Report" in f_stage:
                    st.subheader("📝 Final Report Mark")
                    raw_mark = st.number_input("Mark (0-100)", 0.0, 100.0, step=0.5)
                
                elif project_type == "Research Project":
                    if "Presentation 1" in f_stage:
                        st.subheader("🏗️ Proposal Assessment (Out of 50)")
                        m_c1 = st.select_slider("1. Problem statement (LO 1, 2, ECN 4)", options=mark_options)
                        st.caption("Guidelines: Problem clearly defined (WHAT/WHERE/WHEN/HOW/WHY), scope, significance.")
                        m_c2 = st.select_slider("2. Literature Review (LO 6)", options=mark_options)
                        st.caption("Guidelines: Cite/reference ability, critique related work, identify gaps.")
                        m_c3 = st.select_slider("3. Methodology (LO 2, 3, ECN 5)", options=mark_options)
                        st.caption("Guidelines: Identify approaches, valid design, specify ICT tools.")
                        m_c4 = st.select_slider("4. Project Planning (LO 1)", options=mark_options)
                        st.caption("Guidelines: Plan with valid milestones and resources.")
                        m_c5 = st.select_slider("5. Technical Communication (LO 5, ECN 6)", options=mark_options)
                        st.caption("Guidelines: Presentation, terminology, illustrations, Q&A defense.")
                        raw_mark = float(m_c1 + m_c2 + m_c3 + m_c4 + m_c5)
                    elif "Presentation 2" in f_stage:
                        st.subheader("📊 Progress Assessment (Out of 20)")
                        m_c1 = st.select_slider("1. Progress (LO 1, 2, 4, ECN 4)", options=mark_options)
                        st.caption("Guidelines: Adherence to method, preliminary setup, analysis, milestones.")
                        m_c2 = st.select_slider("2. Technical Communication (LO 5, ECN 6)", options=mark_options)
                        st.caption("Guidelines: Graphs/flowcharts, terminology, Q&A.")
                        raw_mark = float(m_c1 + m_c2)
                    else: 
                        st.subheader("🏁 Final Presentation Assessment (Out of 30)")
                        m_c1 = st.select_slider("1. Data Collection (LO 1, 2, 3, ECN 4, 5)", options=mark_options)
                        st.caption("Guidelines: Valid data collection, appropriate tools, effective display.")
                        m_c2 = st.select_slider("2. Data analysis and interpretation (LO 1, 2, 3, ECN 4, 5)", options=mark_options)
                        st.caption("Guidelines: ICT tools, results vs objectives, valid conclusions.")
                        m_c3 = st.select_slider("3. Technical Communication (LO 5, ECN 6)", options=mark_options)
                        st.caption("Guidelines: Presentation of findings, defense of research.")
                        raw_mark = float(m_c1 + m_c2 + m_c3)

                else: # DESIGN STREAM
                    if "Presentation 1" in f_stage:
                        st.subheader("🏗️ Design Proposal")
                        m_c1 = st.select_slider("Problem Statement & Justification", options=mark_options)
                        st.caption("Guidelines: Identification of engineering problem and scope.")
                        m_c2 = st.select_slider("Comparison Matrix", options=mark_options)
                        st.caption("Guidelines: Selection of optimal solution based on metrics.")
                        m_c3 = st.select_slider("Materials & Methods", options=mark_options)
                        st.caption("Guidelines: Component suitability and design methodology.")
                    elif "Presentation 2" in f_stage:
                        st.subheader("📊 Progress Presentation")
                        m_c1 = st.select_slider("Sustainability Analysis (LO 1, 2, 4)", options=mark_options)
                        st.caption("Guidelines: Environmental and social impact considerations.")
                        m_c2 = st.select_slider("Technical Comms (LO 5)", options=mark_options)
                        st.caption("Guidelines: Quality of diagrams, schematics, and flow.")
                        m_c3 = st.select_slider("Q&A Defense", options=mark_options)
                        st.caption("Guidelines: Addressing technical queries about the design.")
                    else: 
                        st.subheader("🏁 Final Presentation")
                        m_c1 = st.select_slider("Design Approaches (LO 4, 7)", options=mark_options)
                        st.caption("Guidelines: Engineering standards and design synthesis.")
                        m_c2 = st.select_slider("Synthesis & Results (LO 1, 4)", options=mark_options)
                        st.caption("Guidelines: Validation through testing and data.")
                        m_c3 = st.select_slider("Prototype Functionality (LO 7)", options=mark_options)
                        st.caption("Guidelines: Demonstration of prototype/built design.")
                    raw_mark = float(m_c1 + m_c2 + m_c3)

                remarks = st.text_area("Examiner Remarks")
                initials = st.text_input("Examiner Initials (Required)")
                if st.form_submit_button("Submit Marks"):
                    if not target_id or not initials.strip(): st.error("Please provide all required fields.")
                    else:
                        id_col = "student_id" if project_type == "Research Project" else "group_name"
                        new_row = pd.DataFrame([{id_col: target_id, "assessment_type": f_stage, "raw_mark": raw_mark, 
                                                 "crit_1": m_c1, "crit_2": m_c2, "crit_3": m_c3, "crit_4":m_c4, "crit_5":m_c5,
                                                 "examiner": f"{st.session_state['user_name']} ({initials.upper()})", 
                                                 "remarks": remarks, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")}])
                        conn.update(worksheet=ws, data=pd.concat([m_df, new_row], ignore_index=True))
                        st.success("Marks saved!")

        with suggest_tab:
            st.subheader("💡 Suggest a New Project")
            with st.form("new_suggest_form", clear_on_submit=True):
                s_type = st.radio("Select Project Category", ["Research Project", "Design Project"])
                s_title = st.text_input("Project Title")
                s_abstract = st.text_area("Project Abstract")
                if st.form_submit_button("Post Suggestion"):
                    if s_title and s_abstract:
                        ps_df = load_data("project_suggestions")
                        new_s = pd.DataFrame([{"type": s_type, "title": s_title, "abstract": s_abstract, 
                                               "supervisor": st.session_state['user_name'], "email": st.session_state['user_email']}])
                        conn.update(worksheet="project_suggestions", data=pd.concat([ps_df, new_s], ignore_index=True))
                        st.success(f"Suggestion for {s_type} successfully posted!")

# --- ROLE: COORDINATOR ---
elif role == "Coordinator":
    st.header("🔑 Coordinator Dashboard")
    pwd = st.sidebar.text_input("Coordinator Password", type="password")
    if (project_type == "Research Project" and pwd == "Blackberry") or (project_type == "Design Project" and pwd == "Apple"):
        ws, target_col = ("marks", "student_id") if project_type == "Research Project" else ("design_marks", "group_name")
        md = load_data(ws)
        base_df = load_data("students" if project_type == "Research Project" else "design_groups")
        if not base_df.empty and not md.empty:
            piv = md.pivot_table(index=target_col, columns='assessment_type', values='raw_mark', aggfunc='mean')
            st.dataframe(pd.merge(base_df, piv.reset_index(), on=target_col, how='left').fillna(0), use_container_width=True)

# --- ROLE: PROJECT SUGGESTIONS ---
elif role == "Project Suggestions":
    st.header(f"🔭 {project_type} Suggestions Portal")
    ps_df = load_data("project_suggestions")
    if not ps_df.empty:
        filtered_ps = ps_df[ps_df['type'] == project_type]
        for _, row in filtered_ps.iterrows():
            with st.expander(f"📌 {row['title']}"):
                st.write(f"**Supervisor:** {row['supervisor']} ({row['email']})")
                st.write(f"**Abstract:** {row['abstract']}")
