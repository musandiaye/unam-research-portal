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

# --- CONNECTION ---import streamlit as st
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
    reg_tab, view_tab = st.tabs(["New Registration", "Check My Registration"])
    
    with reg_tab:
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
                m4_n = st.text_input("M4 Name (Optional)"); m4_id = st.text_input("M4 ID (Optional)")
                if st.form_submit_button("Submit Group Registration"):
                    word_count = len(g_abst.split())
                    if not all([g_name, superv, g_abst, m1_n, m1_id, m2_n, m2_id, m3_n, m3_id]):
                        st.error("Please provide at least 3 group members.")
                    elif word_count > 250: st.error(f"Abstract too long ({word_count} words).")
                    else:
                        dg = load_data("design_groups")
                        new_mems = []
                        for name, sid in [(m1_n, m1_id), (m2_n, m2_id), (m3_n, m3_id), (m4_n, m4_id)]:
                            if name and sid:
                                new_mems.append({"group_name": g_name, "student_name": name, "student_id": clean_id(sid), "supervisor": superv, "abstract": g_abst})
                        conn.update(worksheet="design_groups", data=pd.concat([dg, pd.DataFrame(new_mems)], ignore_index=True))
                        st.success("Design Group Registered!")

    with view_tab:
        st.header("🔍 View Registration Details")
        if project_type == "Research Project":
            search_id = st.text_input("Enter Student ID to find your details")
            if search_id:
                sd = load_data("students")
                ci = clean_id(search_id)
                match = sd[sd['student_id'] == ci]
                if not match.empty:
                    st.write("### Your Registration Information")
                    st.table(match)
                else: st.warning("No registration found for this ID.")
        else:
            search_group = st.text_input("Enter Group Name to find group details")
            if search_group:
                dg = load_data("design_groups")
                match = dg[dg['group_name'].str.contains(search_group, case=False, na=False)]
                if not match.empty:
                    st.write("### Group Registration Information")
                    st.dataframe(match, use_container_width=True)
                else: st.warning("No registration found for this group name.")

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
                if 'sel_id' not in st.session_state: st.session_state.sel_id = ""
                if 'sel_name' not in st.session_state: st.session_state.sel_name = ""
                def update_by_id(): st.session_state.sel_name = s_df[s_df['student_id'] == st.session_state.sel_id]['student_name'].iloc[0] if st.session_state.sel_id else ""
                def update_by_name(): st.session_state.sel_id = s_df[s_df['student_name'] == st.session_state.sel_name]['student_id'].iloc[0] if st.session_state.sel_name else ""
                col1, col2 = st.columns(2)
                with col1: target_id = st.selectbox("Select Student ID", options=id_list, key="sel_id", on_change=update_by_id)
                with col2: target_name = st.selectbox("Select Student Name", options=name_list, key="sel_name", on_change=update_by_name)
                f_stage = st.selectbox("Assessment Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Research Report (60%)"])
            else:
                g_df = load_data("design_groups")
                target_id = st.selectbox("Select Design Group", options=[""] + sorted(g_df['group_name'].unique().tolist()) if not g_df.empty else [""])
                f_stage = st.selectbox("Assessment Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Design Report (60%)"])

            with st.form("score_form", clear_on_submit=True):
                st.write(f"**Target ID:** {target_id}")
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
                        st.caption("Guidelines: Adherence to method, setup, analysis, milestones.")
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
                        st.subheader("🏗️ Design Proposal (Out of 30)")
                        m_c1 = st.select_slider("Problem Statement & Justification", options=mark_options)
                        st.caption("Guidelines: Identification of engineering problem and scope.")
                        m_c2 = st.select_slider("Comparison Matrix", options=mark_options)
                        st.caption("Guidelines: Selection of optimal solution based on metrics.")
                        m_c3 = st.select_slider("Materials & Methods", options=mark_options)
                        st.caption("Guidelines: Component suitability and design methodology.")
                    elif "Presentation 2" in f_stage:
                        st.subheader("📊 Progress Presentation (Out of 30)")
                        m_c1 = st.select_slider("Sustainability Analysis (LO 1, 2, 4)", options=mark_options)
                        st.caption("Guidelines: Environmental and social impact considerations.")
                        m_c2 = st.select_slider("Technical Comms (LO 5)", options=mark_options)
                        st.caption("Guidelines: Quality of diagrams, schematics, and flow.")
                        m_c3 = st.select_slider("Q&A Defense", options=mark_options)
                        st.caption("Guidelines: Addressing technical queries about the design.")
                    else: 
                        st.subheader("🏁 Final Presentation (Out of 30)")
                        m_c1 = st.select_slider("Design Approaches (LO 4, 7)", options=mark_options)
                        st.caption("Guidelines: Engineering standards and design synthesis.")
                        m_c2 = st.select_slider("Synthesis & Results (LO 1, 4)", options=mark_options)
                        st.caption("Guidelines: Validation through testing and data.")
                        m_c3 = st.select_slider("Prototype Functionality (LO 7)", options=mark_options)
                        st.caption("Guidelines: Demonstration of prototype/built design.")
                    raw_mark = float(m_c1 + m_c2 + m_c3)

                remarks = st.text_area("Remarks")
                initials = st.text_input("Initials (Required)")
                if st.form_submit_button("Submit Marks"):
                    if not target_id or not initials.strip(): st.error("Fill required fields.")
                    else:
                        id_col = "student_id" if project_type == "Research Project" else "group_name"
                        new_row = pd.DataFrame([{id_col: target_id, "assessment_type": f_stage, "raw_mark": raw_mark, 
                                                 "examiner": f"{st.session_state['user_name']} ({initials.upper()})", 
                                                 "remarks": remarks, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")}])
                        conn.update(worksheet=ws, data=pd.concat([m_df, new_row], ignore_index=True))
                        st.success("Marks saved!")

        with suggest_tab:
            st.subheader("💡 Suggest a New Project")
            with st.form("new_suggest_form", clear_on_submit=True):
                s_type = st.radio("Category", ["Research Project", "Design Project"])
                s_title = st.text_input("Title")
                s_abstract = st.text_area("Abstract")
                if st.form_submit_button("Post"):
                    ps_df = load_data("project_suggestions")
                    new_s = pd.DataFrame([{"type": s_type, "title": s_title, "abstract": s_abstract, 
                                           "supervisor": st.session_state['user_name'], "email": st.session_state['user_email']}])
                    conn.update(worksheet="project_suggestions", data=pd.concat([ps_df, new_s], ignore_index=True))
                    st.success("Posted!")

# --- ROLE: COORDINATOR ---
elif role == "Coordinator":
    st.header("🔑 Coordinator Dashboard")
    pwd = st.sidebar.text_input("Password", type="password")
    if (project_type == "Research Project" and pwd == "Blackberry") or (project_type == "Design Project" and pwd == "Apple"):
        ws, target_col = ("marks", "student_id") if project_type == "Research Project" else ("design_marks", "group_name")
        md = load_data(ws); base_df = load_data("students" if project_type == "Research Project" else "design_groups")
        if not base_df.empty and not md.empty:
            if target_col == 'student_id': md[target_col] = md[target_col].astype(str).apply(clean_id)
            piv = md.pivot_table(index=target_col, columns='assessment_type', values='raw_mark', aggfunc='mean')
            display_df = pd.DataFrame(index=piv.index); wt = pd.Series(0.0, index=piv.index)
            stages = {"Presentation 1 (10%)": {"weight": 10, "max": 50 if project_type == "Research Project" else 30},
                      "Presentation 2 (10%)": {"weight": 10, "max": 20 if project_type == "Research Project" else 30},
                      "Presentation 3 (20%)": {"weight": 20, "max": 30}}
            for stage, info in stages.items():
                if stage in piv.columns:
                    display_df[f"{stage.split(' (')[0]} (%)"] = ((piv[stage] / info['max']) * 100).round(1)
                    wt += (piv[stage] / info['max']) * info['weight']
            rep = "Final Research Report (60%)" if project_type == "Research Project" else "Final Design Report (60%)"
            if rep in piv.columns:
                display_df["Final Report (%)"] = piv[rep].round(1)
                wt += (piv[rep] / 100) * 60
            display_df['FINAL_GRADE_%'] = wt.round(1)
            st.dataframe(pd.merge(base_df, display_df.reset_index(), on=target_col, how='left').fillna(0), use_container_width=True)

# --- ROLE: PROJECT SUGGESTIONS ---
elif role == "Project Suggestions":
    st.header(f"🔭 Available {project_type} Suggestions")
    ps_df = load_data("project_suggestions")
    if not ps_df.empty:
        filtered_ps = ps_df[ps_df['type'] == project_type]
        if not filtered_ps.empty:
            for _, row in filtered_ps.iterrows():
                with st.expander(f"📌 {row['title']}"):
                    st.write(f"**Supervisor:** {row['supervisor']} ({row['email']})")
                    st.write(f"**Abstract:** {row['abstract']}")
        else: st.info(f"No {project_type} suggestions available yet.")
    else: st.info("No suggestions available yet.")

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

def display_vertical_card(data_dict, title="Details"):
    html = f"""
    <div style="border: 1px solid #ddd; border-radius: 10px; padding: 20px; background-color: #f9f9f9; margin-bottom: 20px;">
        <h4 style="margin-top:0; color: #1f77b4;">{title}</h4>
        <table style="width: 100%; border-collapse: collapse;">
    """
    for key, value in data_dict.items():
        html += f"""
        <tr style="border-bottom: 1px solid #eee;">
            <td style="padding: 12px; font-weight: bold; width: 280px; white-space: nowrap; vertical-align: top; color: #333; background-color: #f0f2f6;">
                {key.replace('_', ' ').title()}
            </td>
            <td style="padding: 12px; vertical-align: top; color: #444; background-color: #ffffff;">
                {value}
            </td>
        </tr>
        """
    html += "</table></div>"
    st.markdown(html, unsafe_allow_html=True)

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
    reg_tab, view_tab = st.tabs(["New Registration", "Check My Registration"])
    
    with reg_tab:
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
                m4_n = st.text_input("M4 Name (Optional)"); m4_id = st.text_input("M4 ID (Optional)")
                if st.form_submit_button("Submit Group Registration"):
                    word_count = len(g_abst.split())
                    if not all([g_name, superv, g_abst, m1_n, m1_id, m2_n, m2_id, m3_n, m3_id]):
                        st.error("Please provide at least 3 group members.")
                    elif word_count > 250: st.error(f"Abstract too long ({word_count} words).")
                    else:
                        dg = load_data("design_groups")
                        new_mems = []
                        for name, sid in [(m1_n, m1_id), (m2_n, m2_id), (m3_n, m3_id), (m4_n, m4_id)]:
                            if name and sid:
                                new_mems.append({"group_name": g_name, "student_name": name, "student_id": clean_id(sid), "supervisor": superv, "abstract": g_abst})
                        conn.update(worksheet="design_groups", data=pd.concat([dg, pd.DataFrame(new_mems)], ignore_index=True))
                        st.success("Design Group Registered!")

    with view_tab:
        st.header("🔍 Check Registration")
        if project_type == "Research Project":
            search_id = st.text_input("Enter Student ID")
            if search_id:
                sd = load_data("students")
                ci = clean_id(search_id)
                match = sd[sd['student_id'] == ci]
                if not match.empty:
                    st.success("Registration Found")
                    display_vertical_card(match.iloc[0].to_dict(), "Student Info")
                else: st.warning("No registration found.")
        else:
            search_group = st.text_input("Enter Group Name")
            if search_group:
                dg = load_data("design_groups")
                match = dg[dg['group_name'].str.contains(search_group, case=False, na=False)]
                if not match.empty:
                    st.success("Group Found")
                    display_vertical_card(match[['group_name', 'supervisor', 'abstract']].iloc[0].to_dict(), "Group Info")
                    st.dataframe(match[['student_name', 'student_id']], use_container_width=True)
                else: st.warning("No registration found.")

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
                target_id = st.selectbox("Select Student ID", options=id_list)
                f_stage = st.selectbox("Assessment Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Research Report (60%)"])
            else:
                g_df = load_data("design_groups")
                target_id = st.selectbox("Select Design Group", options=[""] + sorted(g_df['group_name'].unique().tolist()) if not g_df.empty else [""])
                f_stage = st.selectbox("Assessment Stage", ["Presentation 1 (10%)", "Presentation 2 (10%)", "Presentation 3 (20%)", "Final Design Report (60%)"])

            with st.form("score_form", clear_on_submit=True):
                st.write(f"**Target:** {target_id}")
                # Initialize variables to ensure they are defined for the submission
                m_c1 = m_c2 = m_c3 = m_c4 = m_c5 = 0.0

                if "Report" in f_stage:
                    raw_mark = st.number_input("Mark (0-100)", 0.0, 100.0, step=0.5)
                elif project_type == "Research Project":
                    if "Presentation 1" in f_stage:
                        st.subheader("🏗️ Proposal Assessment (Out of 50)")
                        m_c1 = st.select_slider("1. Problem statement (LO 1, 2, ECN 4)", options=mark_options)
                        st.caption("Guidelines: Problem clearly defined, scope, significance.")
                        m_c2 = st.select_slider("2. Literature Review (LO 6)", options=mark_options)
                        st.caption("Guidelines: Cite/reference ability, critique, identify gaps.")
                        m_c3 = st.select_slider("3. Methodology (LO 2, 3, ECN 5)", options=mark_options)
                        st.caption("Guidelines: Valid design, specify ICT tools.")
                        m_c4 = st.select_slider("4. Project Planning (LO 1)", options=mark_options)
                        st.caption("Guidelines: Plan with milestones and resources.")
                        m_c5 = st.select_slider("5. Technical Communication (LO 5, ECN 6)", options=mark_options)
                        st.caption("Guidelines: Presentation and Q&A defense.")
                        raw_mark = float(m_c1 + m_c2 + m_c3 + m_c4 + m_c5)
                    elif "Presentation 2" in f_stage:
                        st.subheader("📊 Progress Assessment (Out of 20)")
                        m_c1 = st.select_slider("1. Progress (LO 1, 2, 4, ECN 4)", options=mark_options)
                        st.caption("Guidelines: Adherence to plan, analysis, setup.")
                        m_c2 = st.select_slider("2. Technical Communication (LO 5, ECN 6)", options=mark_options)
                        st.caption("Guidelines: Terminology, graphs, Q&A.")
                        raw_mark = float(m_c1 + m_c2)
                    else: 
                        st.subheader("🏁 Final Presentation Assessment (Out of 30)")
                        m_c1 = st.select_slider("1. Data Collection", options=mark_options)
                        m_c2 = st.select_slider("2. Data analysis", options=mark_options)
                        m_c3 = st.select_slider("3. Technical Communication", options=mark_options)
                        raw_mark = float(m_c1 + m_c2 + m_c3)
                else: # DESIGN STREAM
                    if "Presentation 1" in f_stage:
                        st.subheader("🏗️ Design Proposal (Out of 30)")
                        m_c1 = st.select_slider("Problem Statement & Justification", options=mark_options)
                        m_c2 = st.select_slider("Comparison Matrix", options=mark_options)
                        m_c3 = st.select_slider("Materials & Methods", options=mark_options)
                    elif "Presentation 2" in f_stage:
                        st.subheader("📊 Progress Presentation (Out of 30)")
                        m_c1 = st.select_slider("Sustainability Analysis (LO 1, 2, 4)", options=mark_options)
                        m_c2 = st.select_slider("Technical Comms (LO 5)", options=mark_options)
                        m_c3 = st.select_slider("Q&A Defense", options=mark_options)
                    else: 
                        st.subheader("🏁 Final Presentation (Out of 30)")
                        m_c1 = st.select_slider("Design Approaches (LO 4, 7)", options=mark_options)
                        m_c2 = st.select_slider("Synthesis & Results (LO 1, 4)", options=mark_options)
                        m_c3 = st.select_slider("Prototype Functionality (LO 7)", options=mark_options)
                    raw_mark = float(m_c1 + m_c2 + m_c3)

                remarks = st.text_area("Remarks")
                initials = st.text_input("Initials (Required)")
                if st.form_submit_button("Submit Marks"):
                    if not target_id or not initials.strip(): st.error("Fill required fields.")
                    else:
                        id_col = "student_id" if project_type == "Research Project" else "group_name"
                        new_row = pd.DataFrame([{
                            id_col: target_id, 
                            "assessment_type": f_stage, 
                            "raw_mark": raw_mark, 
                            "crit_1": m_c1, "crit_2": m_c2, "crit_3": m_c3, "crit_4": m_c4, "crit_5": m_c5, # Added criteria here
                            "examiner": f"{st.session_state['user_name']} ({initials.upper()})", 
                            "remarks": remarks, 
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }])
                        conn.update(worksheet=ws, data=pd.concat([m_df, new_row], ignore_index=True))
                        st.success("Marks & Criteria saved successfully!")

        with suggest_tab:
            st.subheader("💡 Suggest Project")
            with st.form("new_suggest_form", clear_on_submit=True):
                s_type = st.radio("Category", ["Research Project", "Design Project"])
                s_title = st.text_input("Title"); s_abstract = st.text_area("Abstract")
                if st.form_submit_button("Post"):
                    ps_df = load_data("project_suggestions")
                    new_s = pd.DataFrame([{"type": s_type, "title": s_title, "abstract": s_abstract, 
                                           "supervisor": st.session_state['user_name'], "email": st.session_state['user_email']}])
                    conn.update(worksheet="project_suggestions", data=pd.concat([ps_df, new_s], ignore_index=True))
                    st.success("Posted!")

# --- ROLE: COORDINATOR ---
elif role == "Coordinator":
    st.header("🔑 Coordinator Dashboard")
    pwd = st.sidebar.text_input("Password", type="password")
    if (project_type == "Research Project" and pwd == "Blackberry") or (project_type == "Design Project" and pwd == "Apple"):
        ws, target_col = ("marks", "student_id") if project_type == "Research Project" else ("design_marks", "group_name")
        md = load_data(ws); base_df = load_data("students" if project_type == "Research Project" else "design_groups")
        if not base_df.empty and not md.empty:
            piv = md.pivot_table(index=target_col, columns='assessment_type', values='raw_mark', aggfunc='mean')
            display_df = pd.DataFrame(index=piv.index); wt = pd.Series(0.0, index=piv.index)
            stages = {"Presentation 1 (10%)": {"weight": 10, "max": 50 if project_type == "Research Project" else 30},
                      "Presentation 2 (10%)": {"weight": 10, "max": 20 if project_type == "Research Project" else 30},
                      "Presentation 3 (20%)": {"weight": 20, "max": 30}}
            for stage, info in stages.items():
                if stage in piv.columns:
                    display_df[f"{stage.split(' (')[0]} (%)"] = ((piv[stage] / info['max']) * 100).round(1)
                    wt += (piv[stage] / info['max']) * info['weight']
            rep = "Final Research Report (60%)" if project_type == "Research Project" else "Final Design Report (60%)"
            if rep in piv.columns:
                display_df["Final Report (%)"] = piv[rep].round(1)
                wt += (piv[rep] / 100) * 60
            display_df['FINAL_GRADE_%'] = wt.round(1)
            st.dataframe(pd.merge(base_df, display_df.reset_index(), on=target_col, how='left').fillna(0), use_container_width=True)

# --- ROLE: PROJECT SUGGESTIONS ---
elif role == "Project Suggestions":
    st.header(f"🔭 Available {project_type} Suggestions")
    ps_df = load_data("project_suggestions")
    if not ps_df.empty:
        filtered_ps = ps_df[ps_df['type'] == project_type]
        if not filtered_ps.empty:
            for _, row in filtered_ps.iterrows():
                with st.expander(f"📌 {row['title']}"):
                    st.write(f"**Supervisor:** {row['supervisor']} ({row['email']})")
                    st.write(f"**Abstract:** {row['abstract']}")
        else: st.info(f"No {project_type} suggestions available.")
    else: st.info("No suggestions available.")

