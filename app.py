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

mark_options = [float(x) for x in np.arange(0, 10.5, 0.5)]

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
                elif word_count > 250: st.error(f"Abstract too long ({word_count} words).")
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
            if st.form_submit_button("Submit Group Registration"):
                word_count = len(g_abst.split())
                if word_count > 250: st.error("Abstract too long.")
                else:
                    dg = load_data("design_groups")
                    new_mems = []
                    for name, sid in [(m1_n, m1_id), (m2_n, m2_id), (m3_n, m3_id)]:
                        if name and sid:
                            new_mems.append({"group_name": g_name, "student_name": name, "student_id": clean_id(sid), "supervisor": superv, "abstract": g_abst})
                    conn.update(worksheet="design_groups", data=pd.concat([dg, pd.DataFrame(new_mems)], ignore_index=True))
                    st.success("Design Group Registered!")

# --- ROLE: PANELIST / EXAMINER ---
elif role == "Panelist / Examiner":
    if not st.session_state['logged_in']:
        tab1, tab2 = st.tabs(["Login", "Create Account"])
        with tab1:
            with st.form("login"):
                u, p = st.text_input("Username"), st.text_input("Password", type="password")
                if st.form_submit_button("Login"):
                    u_df = load_data("users")
                    match = u_df[(u_df['username'] == u) & (u_df['password'] == hash_password(p))]
                    if not match.empty:
                        st.session_state['logged_in'] = True
                        st.session_state['user_name'] = match.iloc[0]['full_name']
                        st.session_state['user_email'] = match.iloc[0].get('email', "")
                        st.rerun()
                    else: st.error("Invalid credentials.")
        with tab2:
            with st.form("create"):
                fn, un, pw, em, ak = st.text_input("Full Name"), st.text_input("Username"), st.text_input("Password", type="password"), st.text_input("Email"), st.text_input("Key")
                if st.form_submit_button("Register"):
                    if ak == "JEDSECE2026":
                        ud = load_data("users")
                        nu = pd.DataFrame([{"full_name":fn,"username":un,"password":hash_password(pw),"email":em}])
                        conn.update(worksheet="users", data=pd.concat([ud, nu], ignore_index=True))
                        st.success("Account Created!")
    else:
        st.sidebar.info(f"Signed in: {st.session_state['user_name']}")
        if st.sidebar.button("Sign Out"): st.session_state['logged_in'] = False; st.rerun()
        
        ws = "design_marks" if project_type == "Design Project" else "marks"
        m_df = load_data(ws)

        if project_type == "Research Project":
            s_df = load_data("students")
            # Map student names to IDs to ensure we store IDs in the marks sheet
            name_to_id = dict(zip(s_df['student_name'], s_df['student_id'])) if not s_df.empty else {}
            target_name = st.selectbox("Select Student", options=[""] + sorted(list(name_to_id.keys())))
            target_id = name_to_id.get(target_name, "")
            f_stage = st.selectbox("Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Research Report (60%)"])
        else:
            g_df = load_data("design_groups")
            target_id = st.selectbox("Select Group", options=[""] + sorted(g_df['group_name'].unique().tolist()) if not g_df.empty else [""])
            f_stage = st.selectbox("Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Design Report (60%)"])

        with st.form("score_form", clear_on_submit=True):
            m_c1 = m_c2 = m_c3 = m_c4 = m_c5 = 0.0
            if "Report" in f_stage:
                raw_mark = st.number_input("Mark (0-100)", 0.0, 100.0)
            elif project_type == "Research Project":
                if "Presentation 1" in f_stage:
                    st.subheader("🏗️ Proposal (Out of 50)")
                    m_c1 = st.select_slider("1. Problem Statement", mark_options)
                    m_c2 = st.select_slider("2. Literature Review", mark_options)
                    m_c3 = st.select_slider("3. Methodology", mark_options)
                    m_c4 = st.select_slider("4. Planning", mark_options)
                    m_c5 = st.select_slider("5. Communication", mark_options)
                    raw_mark = float(m_c1 + m_c2 + m_c3 + m_c4 + m_c5)
                elif "Presentation 2" in f_stage:
                    st.subheader("📊 Progress (Out of 20)")
                    m_c1 = st.select_slider("1. Progress", mark_options)
                    m_c2 = st.select_slider("2. Communication", mark_options)
                    raw_mark = float(m_c1 + m_c2)
                else:
                    st.subheader("🏁 Final (Out of 30)")
                    m_c1 = st.select_slider("1. Collection", mark_options)
                    m_c2 = st.select_slider("2. Analysis", mark_options)
                    m_c3 = st.select_slider("3. Communication", mark_options)
                    raw_mark = float(m_c1 + m_c2 + m_c3)
            else:
                m_c1 = st.select_slider("Crit 1", mark_options); m_c2 = st.select_slider("Crit 2", mark_options); m_c3 = st.select_slider("Crit 3", mark_options)
                raw_mark = float(m_c1 + m_c2 + m_c3)

            remarks = st.text_area("Remarks")
            if st.form_submit_button("Submit Marks"):
                if not target_id: st.error("Selection required.")
                else:
                    id_col = "student_id" if project_type == "Research Project" else "group_name"
                    new_row = pd.DataFrame([{id_col: target_id, "assessment_type": f_stage, "raw_mark": raw_mark, 
                                             "crit_1": m_c1, "crit_2": m_c2, "crit_3": m_c3, "crit_4": m_c4, "crit_5": m_c5,
                                             "examiner": st.session_state['user_name'], "remarks": remarks, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")}])
                    conn.update(worksheet=ws, data=pd.concat([m_df, new_row], ignore_index=True))
                    st.success("Marks Saved!")

# --- ROLE: COORDINATOR ---
elif role == "Coordinator":
    st.header("🔑 Coordinator Dashboard")
    pwd = st.sidebar.text_input("Password", type="password")
    if (project_type == "Research Project" and pwd == "Blackberry") or (project_type == "Design Project" and pwd == "Apple"):
        ws, target_col = ("marks", "student_id") if project_type == "Research Project" else ("design_marks", "group_name")
        md = load_data(ws)
        base_df = load_data("students" if project_type == "Research Project" else "design_groups")
        
        if not base_df.empty and not md.empty:
            # Pivot marks - handles multiple examiners by averaging
            piv = md.pivot_table(index=target_col, columns='assessment_type', values='raw_mark', aggfunc='mean')
            
            display_df = pd.DataFrame(index=piv.index)
            weighted_total = pd.Series(0.0, index=piv.index)
            
            # Weights & Max scores for Research Stream
            if project_type == "Research Project":
                configs = {
                    "Presentation 1 (10%)": {"weight": 10, "max": 50},
                    "Presentation 2 (10%)": {"weight": 10, "max": 20},
                    "Presentation 3 (20%)": {"weight": 20, "max": 30},
                    "Final Research Report (60%)": {"weight": 60, "max": 100}
                }
            else:
                configs = {
                    "Presentation 1 (10%)": {"weight": 10, "max": 30},
                    "Presentation 2 (10%)": {"weight": 10, "max": 30},
                    "Presentation 3 (20%)": {"weight": 20, "max": 30},
                    "Final Design Report (60%)": {"weight": 60, "max": 100}
                }

            for stage, cfg in configs.items():
                if stage in piv.columns:
                    display_df[f"{stage.split(' (')[0]} %"] = ((piv[stage] / cfg['max']) * 100).round(1)
                    weighted_total += (piv[stage] / cfg['max']) * cfg['weight']
            
            display_df['FINAL_GRADE_%'] = weighted_total.round(1)
            
            # Clean IDs in registration data before merging to ensure matching
            if target_col == 'student_id':
                base_df['student_id'] = base_df['student_id'].astype(str).apply(clean_id)
            
            final_view = pd.merge(base_df, display_df.reset_index(), on=target_col, how='left').fillna(0)
            st.dataframe(final_view, use_container_width=True)

# --- ROLE: PROJECT SUGGESTIONS ---
elif role == "Project Suggestions":
    st.header("🔭 Suggestions")
    ps = load_data("project_suggestions")
    if not ps.empty:
        for _, row in ps[ps['type'] == project_type].iterrows():
            with st.expander(row['title']):
                st.write(f"By: {row['supervisor']}"); st.write(row['abstract'])
