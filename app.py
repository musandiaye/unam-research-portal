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
                # FIX: Create a name-to-ID mapping so we save IDs in the marks sheet, not names
                name_to_id = dict(zip(s_df['student_name'], s_df['student_id'])) if not s_df.empty else {}
                target_name = st.selectbox("Select Student", options=[""] + sorted(list(name_to_id.keys())))
                target_id = name_to_id.get(target_name, "")
                f_stage = st.selectbox("Assessment Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Research Report (60%)"])
            else:
                g_df = load_data("design_groups")
                target_id = st.selectbox("Select Design Group", options=[""] + sorted(g_df['group_name'].unique().tolist()) if not g_df.empty else [""])
                f_stage = st.selectbox("Assessment Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Design Report (60%)"])

            with st.form("score_form", clear_on_submit=True):
                st.write(f"**Target:** {target_id}")
                m_c1 = m_c2 = m_c3 = m_c4 = m_c5 = 0.0

                if "Report" in f_stage:
                    st.subheader("📝 Final Report Mark")
                    raw_mark = st.number_input("Mark (0-100)", 0.0, 100.0, step=0.5)
                
                elif project_type == "Research Project":
                    if "Presentation 1" in f_stage:
                        st.subheader("🏗️ Proposal Assessment (Out of 50)")
                        m_c1 = st.select_slider("1. Problem statement", options=mark_options)
                        m_c2 = st.select_slider("2. Literature Review", options=mark_options)
                        m_c3 = st.select_slider("3. Methodology", options=mark_options)
                        m_c4 = st.select_slider("4. Project Planning", options=mark_options)
                        m_c5 = st.select_slider("5. Technical Communication", options=mark_options)
                        raw_mark = float(m_c1 + m_c2 + m_c3 + m_c4 + m_c5)
                    elif "Presentation 2" in f_stage:
                        st.subheader("📊 Progress Assessment (Out of 20)")
                        m_c1 = st.select_slider("1. Progress", options=mark_options)
                        m_c2 = st.select_slider("2. Technical Communication", options=mark_options)
                        raw_mark = float(m_c1 + m_c2)
                    else: 
                        st.subheader("🏁 Final Presentation Assessment (Out of 30)")
                        m_c1 = st.select_slider("1. Data Collection", options=mark_options)
                        m_c2 = st.select_slider("2. Data analysis", options=mark_options)
                        m_c3 = st.select_slider("3. Technical Communication", options=mark_options)
                        raw_mark = float(m_c1 + m_c2 + m_c3)
                else:
                    m_c1 = st.select_slider("Crit 1", mark_options)
                    m_c2 = st.select_slider("Crit 2", mark_options)
                    m_c3 = st.select_slider("Crit 3", mark_options)
                    raw_mark = float(m_c1 + m_c2 + m_c3)

                remarks = st.text_area("Examiner Remarks")
                if st.form_submit_button("Submit Marks"):
                    if not target_id: st.error("Select a target.")
                    else:
                        id_col = "student_id" if project_type == "Research Project" else "group_name"
                        new_row = pd.DataFrame([{id_col: target_id, "assessment_type": f_stage, "raw_mark": raw_mark, 
                                                 "crit_1": m_c1, "crit_2": m_c2, "crit_3": m_c3, "crit_4":m_c4, "crit_5":m_c5,
                                                 "examiner": st.session_state['user_name'], "remarks": remarks, 
                                                 "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")}])
                        conn.update(worksheet=ws, data=pd.concat([m_df, new_row], ignore_index=True))
                        st.success("Marks saved successfully!")

# --- ROLE: COORDINATOR ---
elif role == "Coordinator":
    st.header("🔑 Coordinator Dashboard")
    pwd = st.sidebar.text_input("Coordinator Password", type="password")
    if (project_type == "Research Project" and pwd == "Blackberry") or (project_type == "Design Project" and pwd == "Apple"):
        ws, target_col = ("marks", "student_id") if project_type == "Research Project" else ("design_marks", "group_name")
        md = load_data(ws)
        base_df = load_data("students" if project_type == "Research Project" else "design_groups")
        
        if not base_df.empty and not md.empty:
            # FIX: Clean IDs in marks data to match registration sheet format
            if target_col == 'student_id':
                md[target_col] = md[target_col].astype(str).apply(clean_id)

            piv = md.pivot_table(index=target_col, columns='assessment_type', values='raw_mark', aggfunc='mean')
            display_df = pd.DataFrame(index=piv.index)
            weighted_total = pd.Series(0.0, index=piv.index)
            
            stages = {
                "Presentation 1 (10%)": {"weight": 10, "max": 50 if project_type == "Research Project" else 30},
                "Presentation 2 (10%)": {"weight": 10, "max": 20 if project_type == "Research Project" else 30},
                "Presentation 3 (20%)": {"weight": 20, "max": 30}
            }
            
            for stage, info in stages.items():
                if stage in piv.columns:
                    display_df[f"{stage.split(' (')[0]} (%)"] = ((piv[stage] / info['max']) * 100).round(1)
                    weighted_total += (piv[stage] / info['max']) * info['weight']
            
            report_col = "Final Research Report (60%)" if project_type == "Research Project" else "Final Design Report (60%)"
            if report_col in piv.columns:
                display_df["Final Report (%)"] = piv[report_col].round(1)
                weighted_total += (piv[report_col] / 100) * 60
                
            display_df['FINAL_GRADE_%'] = weighted_total.round(1)
            # FIX: Use pd.merge on the cleaned target columns
            final_view = pd.merge(base_df, display_df.reset_index(), on=target_col, how='left').fillna(0)
            st.dataframe(final_view, use_container_width=True)

# --- ROLE: PROJECT SUGGESTIONS ---
elif role == "Project Suggestions":
    st.header("🔭 Suggestions")
    ps_df = load_data("project_suggestions")
    if not ps_df.empty:
        filtered_ps = ps_df[ps_df['type'] == project_type]
        for _, row in filtered_ps.iterrows():
            with st.expander(f"📌 {row['title']}"):
                st.write(f"**Supervisor:** {row['supervisor']}"); st.write(row['abstract'])
